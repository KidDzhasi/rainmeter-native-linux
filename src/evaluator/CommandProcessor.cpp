#include <functional>
#include <string>
#include "CommandProcessor.hpp"
InputTextState g_InputState;
#include "MeasureEvaluator.hpp"
#include "parser/IniLexer.hpp"
#include "NowPlayingMeasure.hpp"
#include "ScriptEnvironment.hpp"
#include "MathParser.hpp"
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <vector>

namespace {
std::vector<std::string> tokenizeBang(const std::string &bang) {
  std::vector<std::string> tokens;
  std::string current;
  bool inQuotes = false;

  for (std::size_t i = 0; i < bang.size(); ++i) {
    char c = bang[i];
    if (c == '"') {
      inQuotes = !inQuotes;
    } else if (c == ' ' && !inQuotes) {
      if (!current.empty()) {
        tokens.push_back(current);
        current.clear();
      }
    } else {
      current += c;
    }
  }
  if (!current.empty()) {
    tokens.push_back(current);
  }
  return tokens;
}
} // namespace

BangResult CommandProcessor::execute(const std::string &bangString,
                                   IniLexer &skin,
                                   MeasureEvaluator &measures,
                                   void* skinInstance) {
  BangResult result;
  std::cout << "[BANG] Executing Action: " << bangString << std::endl;

  // If there are no brackets but it's a valid action, wrap it in brackets for standard processing
  std::string processedBang = bangString;
  if (processedBang.find('[') == std::string::npos && !processedBang.empty()) {
      if (processedBang.front() == '"' && processedBang.back() == '"') {
          processedBang = "[" + processedBang + "]";
      } else {
          processedBang = "[" + processedBang + "]";
      }
  }

  for (std::size_t i = 0; i < processedBang.size();) {
    std::size_t start = processedBang.find('[', i);
    if (start == std::string::npos) {
      break;
    }
    std::size_t end = processedBang.find(']', start);
    if (end == std::string::npos) {
      break;
    }

    std::string payload = processedBang.substr(start + 1, end - start - 1);
    i = end + 1;

    std::cout << "[DEBUG_CLICK] Engine received action payload: '" << payload << "'" << std::endl;
    if (payload.empty()) {
      continue;
    }



    // Handle non-bang system actions (like web URLs or shell commands)
    if (payload[0] != '!') {
      std::string cmdStr = payload;
      if (cmdStr.size() >= 2 && cmdStr.front() == '"' && cmdStr.back() == '"') {
        cmdStr = cmdStr.substr(1, cmdStr.size() - 2);
      }

      std::string sysCmd;
      if (cmdStr.find("http://") == 0 || cmdStr.find("https://") == 0) {
        sysCmd = "xdg-open \"" + cmdStr + "\" &";
      } else {
        sysCmd = cmdStr + " &";
      }

      std::cout << "[SYSTEM] Executing OS Command: " << sysCmd << std::endl;
      int ret = std::system(sysCmd.c_str());
      (void)ret;
      continue;
    }

    std::vector<std::string> tokens = tokenizeBang(payload);
    if (tokens.empty()) {
      continue;
    }

    std::string cmd = tokens[0];
    for (char &c : cmd) {
      if (c >= 'a' && c <= 'z') {
        c = static_cast<char>(c - 'a' + 'A');
      }
    }

    if (cmd == "!SETVARIABLE") {
      if (tokens.size() >= 3) {
        std::string value = tokens[2];
        if (value.size() >= 2 && value.front() == '(' && value.back() == ')') {
          MathParser math(
              [&skin](const std::string &name) {
                return skin.getCaseInsensitive("Variables", name).value_or("");
              },
              [&measures](const std::string &name) {
                return measures.numericValue(name);
              });
          double mathResult = 0.0;
          std::string expr = value.substr(1, value.size() - 2);
          if (math.evaluate(expr, mathResult)) {
            char buf[64];
            std::snprintf(buf, sizeof(buf), "%g", mathResult);
            value = buf;
          }
        }
        skin.setVariable(tokens[1], value);
        result.needsUpdate = true;
        result.needsRedraw = true;
      }
    } else if (cmd == "!WRITEKEYVALUE") {
      if (tokens.size() >= 4) {
        std::string section = tokens[1];
        std::string key = tokens[2];
        std::string value = tokens[3];
        
        // FilePath is optional (token 4)
        std::string filePath = "";
        if (tokens.size() >= 5) {
            filePath = tokens[4];
            // Expand #@# if present
            filePath = skin.expandMacros(filePath);
        } else {
            // Default to current skin file path, but unfortunately CommandProcessor 
            // doesn't have the skin path directly. We can fetch it via EnvironmentManager 
            // if we add a way, but since we usually don't know it in this scope, we can 
            // assume it's passed or try to use #CURRENTPATH##CURRENTFILE#. 
            // Let's resolve via builtins if possible, else it's tricky.
            // Wait, we can evaluate #CURRENTFILE# through IniLexer expandBuiltins.
            filePath = skin.expandBuiltins("#CURRENTPATH##CURRENTFILE#");
        }
        
        // Strip quotes if they were kept around the file path
        if (!filePath.empty() && filePath.front() == '"' && filePath.back() == '"') {
            filePath = filePath.substr(1, filePath.size() - 2);
        }
        
        if (!filePath.empty()) {
            bool success = IniLexer::writeKeyValue(filePath, section, key, value);
            if (success) {
                std::cout << "[!WRITEKEYVALUE] Wrote " << key << "=" << value << " to [" << section << "] in " << filePath << "\n";
            } else {
                std::cout << "[!WRITEKEYVALUE] Error writing to " << filePath << "\n";
            }
        } else {
            std::cout << "[!WRITEKEYVALUE] Error: No file path provided or could not resolve current skin path.\n";
        }
      }
    } else if (cmd == "!UPDATE") {
      result.needsUpdate = true;
    } else if (cmd == "!REDRAW") {
      result.needsRedraw = true;
    } else if (cmd == "!UPDATEMEASURE") {
      result.needsUpdate = true;
    } else if (cmd == "!UPDATEMETER") {
      result.needsRedraw = true;
    } else if (cmd == "!COMMANDMEASURE") {
      if (tokens.size() >= 3) {
         std::string measureName = tokens[1];
         std::string measureCmd = tokens[2];
         
         auto measureKind = skin.getCaseInsensitive(measureName, "Measure");
         auto pluginName = skin.getCaseInsensitive(measureName, "Plugin");
         if (measureKind && *measureKind == "Plugin" && pluginName && 
             (*pluginName == "InputText" || *pluginName == "InputText.dll") && 
             measureCmd == "ExecuteBatch 1") {
             
             g_InputState.active = true;
             g_InputState.measureName = measureName;
             g_InputState.command = skin.getOr(measureName, "Command1", "");
             g_InputState.buffer = "";
             
             // Extract metrics for drawing the overlay
             MathParser tempMath([](const std::string&){return "0";}, [](const std::string&){return 0.0;});
             g_InputState.x = tempMath.evaluateOr(skin.getOr(measureName, "X", "0"), 0);
             g_InputState.y = tempMath.evaluateOr(skin.getOr(measureName, "Y", "0"), 0);
             g_InputState.w = tempMath.evaluateOr(skin.getOr(measureName, "W", "0"), 0);
             g_InputState.h = tempMath.evaluateOr(skin.getOr(measureName, "H", "0"), 0);
             g_InputState.fontSize = tempMath.evaluateOr(skin.getOr(measureName, "FontSize", "12"), 12);
             g_InputState.fontFace = skin.getOr(measureName, "FontFace", "sans");
             g_InputState.fontColor = skin.getOr(measureName, "FontColor", "255,255,255,255");
             g_InputState.solidColor = skin.getOr(measureName, "SolidColor", "0,0,0,255");
             g_InputState.skinInstance = skinInstance;
             
             extern std::function<void()> g_RequestKeyboardFocus;
             if (g_RequestKeyboardFocus) g_RequestKeyboardFocus();
             
             std::cout << "[ENGINE] InputText mode activated for " << measureName << std::endl;
             result.needsRedraw = true;
             result.needsUpdate = true;
         } else if (auto timer = measures.getActionTimer(measureName)) {
             timer->handleCommand(measureCmd);
         } else if (auto scriptEnv = measures.getScript(measureName)) {
             scriptEnv->executeCommand(measureCmd);
         } else {
             // For NowPlaying, any CommandMeasure is routed to the shared backend
             NowPlayingBackend::getInstance().sendCommand(measureCmd);
         }
      }
    } else if (cmd == "!DEACTIVATECONFIG") {
      result.deactivateConfig = true;
    } else {
      std::cout << "Warning: unhandled bang '" << cmd << "'\n";
    }
  }

  return result;
}
