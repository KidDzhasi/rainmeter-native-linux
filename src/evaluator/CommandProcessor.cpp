#include "CommandProcessor.hpp"
#include "MeasureEvaluator.hpp"
#include "parser/IniLexer.hpp"
#include "MprisClient.hpp"
#include "ScriptEnvironment.hpp"

#include <iostream>
#include <vector>

namespace {
// Splits a bang payload (e.g. "!SetVariable \"Key\" \"Value\"") into tokens.
// Handles quotes to keep arguments together.
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
                                     MeasureEvaluator &measures) {
  BangResult result;

  // Extract each [!Bang] block.
  for (std::size_t i = 0; i < bangString.size();) {
    std::size_t start = bangString.find('[', i);
    if (start == std::string::npos) {
      break;
    }
    std::size_t end = bangString.find(']', start);
    if (end == std::string::npos) {
      break;
    }

    std::string payload = bangString.substr(start + 1, end - start - 1);
    i = end + 1;

    // Check if it's actually a bang
    if (payload.empty() || payload[0] != '!') {
      continue;
    }

    std::vector<std::string> tokens = tokenizeBang(payload);
    if (tokens.empty()) {
      continue;
    }

    std::string cmd = tokens[0];
    // Convert command to uppercase for case-insensitive matching.
    for (char &c : cmd) {
      if (c >= 'a' && c <= 'z') {
        c = static_cast<char>(c - 'a' + 'A');
      }
    }

    if (cmd == "!SETVARIABLE") {
      if (tokens.size() >= 3) {
        skin.setVariable(tokens[1], tokens[2]);
      }
    } else if (cmd == "!UPDATE") {
      result.needsUpdate = true;
    } else if (cmd == "!REDRAW") {
      result.needsRedraw = true;
    } else if (cmd == "!UPDATEMEASURE") {
      // Currently, evaluate() runs on all measures at once. To support targeted
      // updates, we'd need a specific update function. For now, trigger a global update.
      result.needsUpdate = true;
    } else if (cmd == "!COMMANDMEASURE") {
      if (tokens.size() >= 3) {
         std::string measureName = tokens[1];
         std::string measureCmd = tokens[2];
         
         // 1. Try sending to Script Measure
         if (auto scriptEnv = measures.getScript(measureName)) {
             scriptEnv->executeCommand(measureCmd);
         }
         // 2. Try sending to MPRIS if active
         else if (auto mpris = measures.getMpris()) {
             mpris->sendCommand(measureCmd);
         }
      }
      std::cout << "CommandProcessor: executing " << payload << "\n";
    } else if (cmd == "!DEACTIVATECONFIG") {
      result.deactivateConfig = true;
    } else {
      std::cout << "CommandProcessor: unknown bang '" << cmd << "'\n";
    }
  }

  return result;
}
