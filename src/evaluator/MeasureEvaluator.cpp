#include "MeasureEvaluator.hpp"
#include <cmath>

#include <chrono>
#include <cstdio>
#include <ctime>
#include <iomanip>
#include <sstream>

#include "SystemMeasures.hpp"
#include "parser/IniLexer.hpp"

#include <iostream>

namespace {
std::string formatDouble(double v) {
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%.1f", v);
  return buf;
}

// Lowercase an ASCII string in-place for case-insensitive comparison.
void toLower(std::string &s) {
  for (char &c : s) {
    if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>(c - 'A' + 'a');
    }
  }
}

// Expands #Variable# tokens in `text` against the skin's [Variables] section.
// Unknown variables are left untouched.
std::string resolveVariables(const IniLexer &skin, const std::string &text) {
  std::string out;
  out.reserve(text.size());
  for (std::size_t i = 0; i < text.size();) {
    if (text[i] == '#') {
      const std::size_t close = text.find('#', i + 1);
      if (close != std::string::npos) {
        std::string name = text.substr(i + 1, close - i - 1);
        // Rainmeter variables are case-insensitive: #format# resolves a
        // variable defined as "Format=".  Lowercase the name so the lookup
        // matches regardless of how the skin author capitalised the
        // reference or the definition.
        toLower(name);
        auto value = skin.getCaseInsensitive("Variables", name);
        if (value) {
          out += *value;
          i = close + 1;
          continue;
        }
      }
    }
    out += text[i];
    ++i;
  }
  return out;
}
} // namespace

void MeasureEvaluator::loadFrom(const IniLexer &skin) {
  measures_.clear();

  for (const auto &[section, keys] : skin.data()) {
    auto measureIt = keys.find("Measure");
    if (measureIt == keys.end()) {
      continue; // Not a measure section.
    }

    Measure m;
    m.dynamicVariables = (skin.getOr(section, "DynamicVariables", "0") == "1");
    m.minValue = std::stod(skin.getOr(section, "MinValue", "0.0"));
    
    // Some measures like CPU implicitly have MaxValue=100.0, but for Time it's defined by user in INI
    // Defaulting MaxValue to 1.0 but parse if it exists.
    std::string maxValStr = skin.getOr(section, "MaxValue", "");
    if (!maxValStr.empty()) {
        try { m.maxValue = std::stod(maxValStr); } catch (...) { m.maxValue = 1.0; }
    } else {
        m.maxValue = 1.0; // We'll handle implicit maximums per-type if needed, or 1.0
    }

    const std::string &kind = measureIt->second;
    if (kind == "Time") {
      m.type = Type::Time;
      // Resolve any #Variables# embedded in the Format string (e.g.
      // Format=%#DateFormat#) before it reaches strftime.
      m.format = resolveVariables(skin, skin.getOr(section, "Format", ""));
    } else if (kind == "CPU") {

      m.type = Type::Cpu;
      m.prevCpu = sysmeasure::readCpuSample();
    } else if (kind == "PhysicalMemory") {
      m.type = Type::PhysicalMemory;
    } else if (kind == "SwapMemory") {
      m.type = Type::SwapMemory;
    } else if (kind == "NetIn") {
      m.type = Type::NetIn;
      m.interfaceName = skin.getOr(section, "Interface", "");
      m.prevNet = sysmeasure::readNetStats(m.interfaceName);
    } else if (kind == "NetOut") {
      m.type = Type::NetOut;
      m.interfaceName = skin.getOr(section, "Interface", "");
      m.prevNet = sysmeasure::readNetStats(m.interfaceName);
    } else if (kind == "Uptime") {
      m.type = Type::Uptime;
    } else if (kind == "FreeDiskSpace") {
      m.type = Type::FreeDiskSpace;
      m.drive = skin.getOr(section, "Drive", "/");
    } else if (kind == "Calc") {
      m.type = Type::Calc;
      m.formula = skin.getOr(section, "Formula", "");
      m.ifCondition = skin.getOr(section, "IfCondition", "");
      m.ifTrueAction = skin.getOr(section, "IfTrueAction", "");
      m.ifFalseAction = skin.getOr(section, "IfFalseAction", "");
      m.lastConditionState = -1;
    } else if (kind == "WebParser") {
      m.type = Type::WebParser;
      m.url = skin.getOr(section, "Url", "");
      m.fetcher = std::make_shared<WebFetcher>();
      if (!m.url.empty()) {
         m.fetcher->start(resolveVariables(skin, m.url));
      }
    } else if (kind == "Plugin") {
      // Intercept MPRIS NowPlaying measures
      std::string name = skin.getOr(section, "PluginName", "");
      if (name.empty()) {
        name = skin.getOr(section, "Plugin", "");
      }
      
      // Lowercase name for check
      std::string lname = name;
      toLower(lname);
      if (lname == "nowplaying" || lname == "nowplaying.dll" || 
          lname == "webnowplaying" || lname == "webnowplaying.dll") {
          m.type = Type::NowPlaying;
          m.playerType = skin.getOr(section, "PlayerType", "");
          
          if (!mpris_) {
             mpris_ = std::make_shared<MprisClient>();
          }
      } else if (lname == "actiontimer" || lname == "actiontimer.dll") {
          m.type = Type::ActionTimerType;
          m.actionTimer = std::make_shared<ActionTimer>();
          m.actionTimer->loadFrom(skin, section);
      } else if (lname == "usagemonitor" || lname == "usagemonitor.dll") {
          m.type = Type::UsageMonitorType;
          m.usageMonitor = std::make_shared<LinuxUsageMonitor>();
          m.usageMonitor->loadFrom(skin, section);
      } else if (lname == "coretemp" || lname == "coretemp.dll") {
          m.type = Type::CoreTempType;
          m.coreTemp = std::make_shared<LinuxCoreTemp>();
          m.coreTemp->loadFrom(skin, section);
      } else if (lname == "audiolevel" || lname == "audiolevel.dll") {
          m.type = Type::AudioLevelType;
          m.audioLevel = std::make_shared<LinuxAudioLevel>();
          m.audioLevel->loadFrom(skin, section);
          if (skin.getOr(section, "Parent", "").empty()) {
              LinuxAudioLevel::registerParent(section, m.audioLevel);
          }
      } else if (lname == "powerplugin" || lname == "powerplugin.dll") {
          m.type = Type::PowerPluginType;
          m.powerPlugin = std::make_shared<LinuxPowerPlugin>();
          m.powerPlugin->loadFrom(skin, section);
      } else if (lname == "inputtext" || lname == "inputtext.dll") {
          m.type = Type::InputTextType;
          m.inputTextPlugin = std::make_shared<InputTextPlugin>();
          m.inputTextPlugin->loadFrom(skin, section);
      } else {
        m.type = Type::Plugin;
        m.pluginName = name;
        std::cout << "Warning: unsupported Plugin='" << name << "' in [" << section << "], mocking as no-op\n";
      }
    } else if (kind == "Script") {
      m.type = Type::Script;
      std::string scriptPath = skin.getOr(section, "ScriptFile", "");
      if (!scriptPath.empty()) {
          std::replace(scriptPath.begin(), scriptPath.end(), '\\', '/');
          scriptPath = skin.expandBuiltins(scriptPath);
          scriptPath = skin.expandMacros(scriptPath);
          scriptPath = resolveVariables(skin, scriptPath);
          if (!scriptPath.empty() && scriptPath[0] != '/') {
              scriptPath = skin.environment().resolve("currentpath").value_or("") + scriptPath;
          }
          m.script = std::make_shared<ScriptEnvironment>(const_cast<IniLexer*>(&skin), this, section);
          if (m.script->loadScript(scriptPath)) {
              m.script->callInitialize();
          }
      }
    } else {
      m.type = Type::Unknown;
    }

    measures_.emplace(section, std::move(m));
  }

  evaluate(skin, 1000.0); // Force initial fetch
}

void MeasureEvaluator::evaluate(const IniLexer &skin, double dtMs, std::function<void(const std::string&)> executeBangs) {
  currentBangCb_ = executeBangs;
  
  // Configure math parser with current state
  math_.setVariableResolver([&skin](const std::string &var) {
    return skin.getCaseInsensitive("Variables", var).value_or("");
  });
  math_.setMeasureResolver([this](const std::string &meas) {
    return numericValue(meas);
  });

  for (auto &[name, m] : measures_) {
    switch (m.type) {
    case Type::Time: {
      if (m.dynamicVariables) {
        m.format = resolveVariables(skin, skin.getOr(name, "Format", ""));
      }
      
      using clock = std::chrono::system_clock;
      const auto now_tp = clock::now();
      const std::time_t now_c = clock::to_time_t(now_tp);
      
      auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now_tp.time_since_epoch()) % 1000;
      double msFraction = ms.count() / 1000.0;
      
      uint64_t winTime = (static_cast<uint64_t>(now_c) + 11644473600ULL) * 10000000ULL;
      
      std::tm localTm{};
      localtime_r(&now_c, &localTm);

      if (m.format.empty()) {
        m.numeric = static_cast<double>(winTime);
        m.current = std::to_string(winTime);
        // Fallback for timestamp
        m.percent = (m.maxValue > 0.0) ? (m.numeric / m.maxValue) : 0.0;
      } else {
        std::ostringstream out;
        out << std::put_time(&localTm, m.format.c_str());
        m.current = out.str();
        
        try {
            m.numeric = std::stod(m.current);
            
            // Continuous sweeping
            if (m.format == "%S" || m.format == "%#S") {
                m.numeric += msFraction;
            } else if (m.format == "%M" || m.format == "%#M") {
                m.numeric += (localTm.tm_sec + msFraction) / 60.0;
            } else if (m.format == "%I" || m.format == "%#I" || m.format == "%H" || m.format == "%#H") {
                m.numeric += (localTm.tm_min + (localTm.tm_sec + msFraction) / 60.0) / 60.0;
            }
            
        } catch (...) {
            m.numeric = 0.0;
        }
        
        double range = m.maxValue - m.minValue;
        if (range > 0.0) {
            m.percent = (m.numeric - m.minValue) / range;
        } else {
            m.percent = 0.0;
        }
      }
      break;
    }

    case Type::Cpu: {
      m.updateTimer += dtMs;
      if (m.updateTimer >= 1000.0) {
          m.updateTimer = std::fmod(m.updateTimer, 1000.0);
          const sysmeasure::CpuSample cur = sysmeasure::readCpuSample();
          m.targetNumeric = sysmeasure::cpuPercent(m.prevCpu, cur);
          m.prevCpu = cur;
      }
      
      // Interpolate towards target
      m.numeric += (m.targetNumeric - m.numeric) * (dtMs / 100.0); // Simple smoothing factor
      m.percent = m.numeric / 100.0;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::PhysicalMemory: {
      m.updateTimer += dtMs;
      if (m.updateTimer >= 1000.0) {
          m.updateTimer = std::fmod(m.updateTimer, 1000.0);
          const sysmeasure::MemoryInfo mem = sysmeasure::readMemory();
          m.targetNumeric = mem.usedPercent / 100.0;
      }
      m.numeric += (m.targetNumeric - m.numeric) * (dtMs / 100.0);
      m.percent = m.numeric;
      m.current = formatDouble(m.numeric * 100.0);
      break;
    }

    case Type::SwapMemory: {
      m.updateTimer += dtMs;
      if (m.updateTimer >= 1000.0) {
          m.updateTimer = std::fmod(m.updateTimer, 1000.0);
          const sysmeasure::MemoryInfo mem = sysmeasure::readMemory();
          m.targetNumeric = mem.swapUsedPercent / 100.0;
      }
      m.numeric += (m.targetNumeric - m.numeric) * (dtMs / 100.0);
      m.percent = m.numeric;
      m.current = formatDouble(m.numeric * 100.0);
      break;
    }

    case Type::NetIn: {
      m.updateTimer += dtMs;
      if (m.dynamicVariables) {
        m.interfaceName = resolveVariables(skin, skin.getOr(name, "Interface", ""));
      }
      if (m.updateTimer >= 1000.0) {
          m.updateTimer = std::fmod(m.updateTimer, 1000.0);
          sysmeasure::NetStats cur = sysmeasure::readNetStats(m.interfaceName);
          if (m.prevNet.valid && cur.valid) {
            m.targetNumeric = static_cast<double>(cur.rxBytes - m.prevNet.rxBytes);
          } else {
            m.targetNumeric = 0.0;
          }
          m.prevNet = cur;
      }
      m.numeric += (m.targetNumeric - m.numeric) * (dtMs / 100.0);
      m.current = std::to_string(static_cast<long long>(m.numeric));
      break;
    }

    case Type::NetOut: {
      m.updateTimer += dtMs;
      if (m.dynamicVariables) {
        m.interfaceName = resolveVariables(skin, skin.getOr(name, "Interface", ""));
      }
      if (m.updateTimer >= 1000.0) {
          m.updateTimer = std::fmod(m.updateTimer, 1000.0);
          sysmeasure::NetStats cur = sysmeasure::readNetStats(m.interfaceName);
          if (m.prevNet.valid && cur.valid) {
            m.targetNumeric = static_cast<double>(cur.txBytes - m.prevNet.txBytes);
          } else {
            m.targetNumeric = 0.0;
          }
          m.prevNet = cur;
      }
      m.numeric += (m.targetNumeric - m.numeric) * (dtMs / 100.0);
      m.current = std::to_string(static_cast<long long>(m.numeric));
      break;
    }

    case Type::Uptime: {
      sysmeasure::UptimeInfo u = sysmeasure::readUptime();
      m.numeric = u.uptimeSeconds;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::FreeDiskSpace: {
      if (m.dynamicVariables) {
        m.drive = resolveVariables(skin, skin.getOr(name, "Drive", "/"));
      }
      sysmeasure::DiskInfo d = sysmeasure::readDisk(m.drive);
      m.numeric = d.usedPercent;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::Calc: {
      if (m.dynamicVariables) {
        m.formula = skin.getOr(name, "Formula", "");
        m.ifCondition = skin.getOr(name, "IfCondition", "");
        m.ifTrueAction = skin.getOr(name, "IfTrueAction", "");
        m.ifFalseAction = skin.getOr(name, "IfFalseAction", "");
      }
      
      // Rainmeter formulas usually just run through evaluateOr.
      // E.g., Formula=MeasureTime % 2
      std::string f = resolveVariables(skin, m.formula);
      m.numeric = math_.evaluateOr(f, 0.0);
      m.current = formatDouble(m.numeric); // Actually calc measures can format as int if no decimal, but formatDouble is ok for now

      if (!m.ifCondition.empty() && executeBangs) {
        std::string cond = resolveVariables(skin, m.ifCondition);
        double condResult = math_.evaluateOr(cond, 0.0);
        int newState = (condResult > 0.0) ? 1 : 0;
        
        // Execute bangs only on state transition
        if (m.lastConditionState != newState) {
          m.lastConditionState = newState;
          if (newState == 1 && !m.ifTrueAction.empty()) {
            executeBangs(m.ifTrueAction);
          } else if (newState == 0 && !m.ifFalseAction.empty()) {
            executeBangs(m.ifFalseAction);
          }
        }
      }
      break;
    }

    case Type::WebParser: {
      if (m.dynamicVariables) {
         std::string newUrl = resolveVariables(skin, skin.getOr(name, "Url", ""));
         if (newUrl != m.url) {
             m.url = newUrl;
             m.fetcher->start(m.url);
         }
      }
      
      std::string out;
      if (m.fetcher->poll(out)) {
         m.current = out;
         m.numeric = 1.0; // Indicate ready
      }
      break;
    }

    case Type::NowPlaying: {
      if (m.dynamicVariables) {
        m.playerType = resolveVariables(skin, skin.getOr(name, "PlayerType", ""));
      }
      
      if (mpris_) {
         TrackInfo info = mpris_->getTrackInfo();
         std::string ptype = m.playerType;
         toLower(ptype);
         
         if (ptype == "title") {
            m.current = info.title;
         } else if (ptype == "artist") {
            m.current = info.artist;
         } else if (ptype == "album") {
            m.current = info.album;
         } else if (ptype == "cover") {
            m.current = info.coverUrl;
         } else if (ptype == "state") {
            m.numeric = info.state;
            m.current = std::to_string(static_cast<long long>(m.numeric));
         } else if (ptype == "progress" || ptype == "position") {
            m.numeric = info.progress;
            m.current = formatDouble(m.numeric);
         }
      }
      break;
    }

    case Type::Plugin: {
      if (m.dynamicVariables) {
        std::string pName = skin.getOr(name, "PluginName", "");
        if (pName.empty()) {
          pName = skin.getOr(name, "Plugin", "");
        }
        m.pluginName = pName;
      }
      PluginManager::MockValue v = plugins_.resolve(m.pluginName);
      m.numeric = v.numeric;
      m.current = v.string;
      if (m.current.empty()) {
        m.current = formatDouble(m.numeric);
      }
      break;
    }

    case Type::Script: {
      if (m.script) {
          m.current = m.script->callUpdate();
          try {
              m.numeric = std::stod(m.current);
          } catch (...) {
              m.numeric = 0.0;
          }
      }
      break;
    }
    
    case Type::UsageMonitorType: {
      if (m.usageMonitor) {
          if (m.dynamicVariables) {
              m.usageMonitor->loadFrom(skin, name);
          }
          m.usageMonitor->update();
          m.numeric = m.usageMonitor->numericValue();
          m.current = m.usageMonitor->stringValue();
          double range = m.maxValue - m.minValue;
          m.percent = (range > 0.0) ? std::clamp((m.numeric - m.minValue) / range, 0.0, 1.0) : m.numeric;
      }
      break;
    }

    case Type::CoreTempType: {
      if (m.coreTemp) {
          if (m.dynamicVariables) {
              m.coreTemp->loadFrom(skin, name);
          }
          m.coreTemp->update();
          m.numeric = m.coreTemp->numericValue();
          m.current = m.coreTemp->stringValue();
          double range = m.maxValue - m.minValue;
          m.percent = (range > 0.0) ? std::clamp((m.numeric - m.minValue) / range, 0.0, 1.0) : m.numeric;
      }
      break;
    }
    
    case Type::AudioLevelType: {
      if (m.audioLevel) {
          if (m.dynamicVariables) {
              m.audioLevel->loadFrom(skin, name);
          }
          m.audioLevel->update(dtMs);
          m.numeric = m.audioLevel->numericValue();
          m.current = m.audioLevel->stringValue();
          // AudioLevel is inherently 0.0 to 1.0, but we apply Min/Max scaling if the user overrode it.
          double range = m.maxValue - m.minValue;
          m.percent = (range > 0.0 && m.maxValue != 1.0) ? std::clamp((m.numeric - m.minValue) / range, 0.0, 1.0) : m.numeric;
      }
      break;
    }

    case Type::PowerPluginType: {
      if (m.powerPlugin) {
          if (m.dynamicVariables) {
              m.powerPlugin->loadFrom(skin, name);
          }
          m.numeric = m.powerPlugin->numericValue();
          m.current = m.powerPlugin->stringValue();
          double range = m.maxValue - m.minValue;
          m.percent = (range > 0.0) ? std::clamp((m.numeric - m.minValue) / range, 0.0, 1.0) : m.numeric;
      }
      break;
    }

    case Type::InputTextType: {
      if (m.inputTextPlugin) {
          if (m.dynamicVariables) {
              m.inputTextPlugin->loadFrom(skin, name);
          }
          m.numeric = m.inputTextPlugin->numericValue();
          m.current = m.inputTextPlugin->stringValue();
      }
      break;
    }

    case Type::Unknown:
    default:
      m.current.clear();
      m.numeric = 0.0;
      break;
    }
  }
}

std::string MeasureEvaluator::value(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
      }
      if (lName == lower) return m.current;
  }
  return "";
}

double MeasureEvaluator::numericValue(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
      }
      if (lName == lower) return m.numeric;
  }
  return 0.0;
}

double MeasureEvaluator::percentValue(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
      }
      if (lName == lower) return m.percent;
  }
  return 0.0;
}

bool MeasureEvaluator::hasMeasure(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
      }
      if (lName == lower) return true;
  }
  return false;
}

void MeasureEvaluator::fireBang(const std::string& bang) const {
    if (currentBangCb_) {
        currentBangCb_(bang);
    }
}

void MeasureEvaluator::tickActionTimers(double dtMs, std::function<void(const std::string&)> fireBang) {
    for (auto& [name, m] : measures_) {
        if (m.type == Type::ActionTimerType && m.actionTimer) {
            m.actionTimer->tick(dtMs, fireBang);
        }
    }
}

// formatTime removed as it is now inlined in evaluate()
