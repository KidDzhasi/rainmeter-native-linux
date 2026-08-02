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


#include "IMeasure.hpp"
#include "CpuMeasure.hpp"
#include "PhysicalMemoryMeasure.hpp"
#include "BatteryMeasure.hpp"

enum class Type {
    Unknown, Time, Cpu, PhysicalMemory, SwapMemory, FreeDiskSpace, NetIn, NetOut, Uptime, Calc, WebParser, Plugin, Script, ActionTimerType, UsageMonitorType, CoreTempType, HwInfoType, AudioLevelType, PowerPluginType, InputTextType
};

struct LegacyMeasureState {
    Type type = Type::Unknown;
    std::string format;
    std::string drive = "/";
    std::string pluginName;
    std::string hwInfoSensorName;
    std::string hwInfoEntryName;
    std::string current;
    double numeric = 0.0;
    double targetNumeric = 0.0;
    double percent = 0.0;
    double minValue = 0.0;
    double maxValue = 1.0;
    double updateTimer = 1000.0;
    sysmeasure::CpuSample prevCpu;
    sysmeasure::NetStats prevNet;
    std::string interfaceName;
    std::string formula;
    std::string ifCondition;
    std::string ifTrueAction;
    std::string ifFalseAction;
    int lastConditionState = -1;
    std::shared_ptr<WebFetcher> fetcher;
    std::string url;
    std::shared_ptr<ScriptEnvironment> script;
    std::shared_ptr<ActionTimer> actionTimer;
    std::shared_ptr<LinuxUsageMonitor> usageMonitor;
    std::shared_ptr<LinuxAudioLevel> audioLevel;
    std::shared_ptr<LinuxPowerPlugin> powerPlugin;
    std::shared_ptr<InputTextPlugin> inputTextPlugin;
    bool dynamicVariables = false;
};

class LegacyMeasure : public IMeasure {
public:
    LegacyMeasure(MeasureEvaluator* evaluator, const std::string& name) : evaluator_(evaluator), name_(name) {}

    void loadFrom(const IniLexer& skin, const std::string& section) override;
    void update(const IniLexer& skin, double dtMs, std::function<void(const std::string&)> executeBangs) override;
    std::string getString() const override { return state_.current; }
    double getNumeric() const override { return state_.numeric; }
    double getPercent() const override { return state_.percent; }
    std::shared_ptr<ScriptEnvironment> getScript() const override { return state_.script; }
    std::shared_ptr<ActionTimer> getActionTimer() const override { return state_.actionTimer; }
    
    LegacyMeasureState state_;
private:
    MeasureEvaluator* evaluator_;
    std::string name_;
};

void LegacyMeasure::loadFrom(const IniLexer& skin, const std::string& section) {
    auto keysIt = skin.data().find(section);
    if (keysIt == skin.data().end()) return;
    const auto& keys = keysIt->second;
    auto measureIt = keys.find("Measure");
    if (measureIt == keys.end()) {
      return; // Not a measure section.
    }

    
    state_.dynamicVariables = (skin.getOr(section, "DynamicVariables", "0") == "1");
    state_.minValue = std::stod(skin.getOr(section, "MinValue", "0.0"));
    
    // Some measures like CPU implicitly have MaxValue=100.0, but for Time it's defined by user in INI
    // Defaulting MaxValue to 1.0 but parse if it exists.
    std::string maxValStr = skin.getOr(section, "MaxValue", "");
    if (!maxValStr.empty()) {
        try { state_.maxValue = std::stod(maxValStr); } catch (...) { state_.maxValue = 1.0; }
    } else {
        state_.maxValue = 1.0; // We'll handle implicit maximums per-type if needed, or 1.0
    }

    const std::string &kind = measureIt->second;
    if (kind == "Time") {
      state_.type = Type::Time;
      // Resolve any #Variables# embedded in the Format string (e.g.
      // Format=%#DateFormat#) before it reaches strftime.
      state_.format = resolveVariables(skin, skin.getOr(section, "Format", ""));
    } else if (kind == "CPU") {
      state_.type = Type::Cpu;
    } else if (kind == "PhysicalMemory") {
      state_.type = Type::PhysicalMemory;
    } else if (kind == "SwapMemory") {
      state_.type = Type::SwapMemory;
    } else if (kind == "NetIn") {
      state_.type = Type::NetIn;
      state_.interfaceName = skin.getOr(section, "Interface", "");
      state_.prevNet = sysmeasure::readNetStats(state_.interfaceName);
    } else if (kind == "NetOut") {
      state_.type = Type::NetOut;
      state_.interfaceName = skin.getOr(section, "Interface", "");
      state_.prevNet = sysmeasure::readNetStats(state_.interfaceName);
    } else if (kind == "Uptime") {
      state_.type = Type::Uptime;
    } else if (kind == "FreeDiskSpace") {
      state_.type = Type::FreeDiskSpace;
      state_.drive = skin.getOr(section, "Drive", "/");
    } else if (kind == "Calc") {
      state_.type = Type::Calc;
      state_.formula = skin.getOr(section, "Formula", "");
      state_.ifCondition = skin.getOr(section, "IfCondition", "");
      state_.ifTrueAction = skin.getOr(section, "IfTrueAction", "");
      state_.ifFalseAction = skin.getOr(section, "IfFalseAction", "");
      state_.lastConditionState = -1;
    } else if (kind == "WebParser") {
      state_.type = Type::WebParser;
      state_.url = skin.getOr(section, "Url", "");
      state_.fetcher = std::make_shared<WebFetcher>();
      if (!state_.url.empty()) {
         state_.fetcher->start(resolveVariables(skin, state_.url));
      }
    } else if (kind == "Plugin") {
      // Intercept MPRIS NowPlaying measures
      std::string name = skin.getOr(section, "PluginName", "");
      if (name.empty()) {
        name = skin.getOr(section, "Plugin", "");
      }
      
      std::string lname = name;
      toLower(lname);
      if (lname == "actiontimer" || lname == "actiontimer.dll") {
          state_.type = Type::ActionTimerType;
          state_.actionTimer = std::make_shared<ActionTimer>();
          state_.actionTimer->loadFrom(skin, section);
      } else if (lname == "usagemonitor" || lname == "usagemonitor.dll") {
          state_.type = Type::UsageMonitorType;
          state_.usageMonitor = std::make_shared<LinuxUsageMonitor>();
          state_.usageMonitor->loadFrom(skin, section);
      } else if (lname == "hwinfo" || lname == "hwinfo.dll") {
          state_.type = Type::HwInfoType;
          state_.hwInfoSensorName = skin.getOr(section, "HWiNFOSensorName", "");
          state_.hwInfoEntryName = skin.getOr(section, "HWiNFOEntryName", "");
      } else if (lname == "coretemp" || lname == "coretemp.dll") {
          state_.type = Type::CoreTempType;
          state_.hwInfoSensorName = "temp";
          state_.hwInfoEntryName = "core";
      } else if (lname == "audiolevel" || lname == "audiolevel.dll") {
          state_.type = Type::AudioLevelType;
          state_.audioLevel = std::make_shared<LinuxAudioLevel>();
          state_.audioLevel->loadFrom(skin, section);
          if (skin.getOr(section, "Parent", "").empty()) {
              LinuxAudioLevel::registerParent(section, state_.audioLevel);
          }
      } else if (lname == "powerplugin" || lname == "powerplugin.dll") {
          state_.type = Type::PowerPluginType;
          state_.powerPlugin = std::make_shared<LinuxPowerPlugin>();
          state_.powerPlugin->loadFrom(skin, section);
      } else if (lname == "inputtext" || lname == "inputtext.dll") {
          state_.type = Type::InputTextType;
          state_.inputTextPlugin = std::make_shared<InputTextPlugin>();
          state_.inputTextPlugin->loadFrom(skin, section);
      } else {
        std::string sname = section;
        toLower(sname);
        if (sname.find("cpu") != std::string::npos) {
            state_.type = Type::Cpu;
        } else if (sname.find("memory") != std::string::npos || sname.find("ram") != std::string::npos) {
            state_.type = Type::PhysicalMemory;
        } else if (sname.find("temp") != std::string::npos || sname.find("fan") != std::string::npos || sname.find("gpu") != std::string::npos) {
            state_.type = Type::HwInfoType;
            state_.hwInfoSensorName = section;
            state_.hwInfoEntryName = section;
        } else {
            state_.type = Type::Plugin;
            state_.pluginName = name;
            std::cout << "Warning: unsupported Plugin='" << name << "' in [" << section << "], mocking as no-op\n";
        }
      }
    } else if (kind == "Script") {
      state_.type = Type::Script;
      std::string scriptPath = skin.getOr(section, "ScriptFile", "");
      if (!scriptPath.empty()) {
          std::replace(scriptPath.begin(), scriptPath.end(), '\\', '/');
          scriptPath = skin.expandBuiltins(scriptPath);
          scriptPath = skin.expandMacros(scriptPath);
          scriptPath = resolveVariables(skin, scriptPath);
          if (!scriptPath.empty() && scriptPath[0] != '/') {
              scriptPath = skin.environment().resolve("currentpath").value_or("") + scriptPath;
          }
          state_.script = std::make_shared<ScriptEnvironment>(const_cast<IniLexer*>(&skin), evaluator_, section);
          if (state_.script->loadScript(scriptPath)) {
              state_.script->callInitialize();
          }
      }
    } else {
      state_.type = Type::Unknown;
    }
    // Adjust script parent
    if (state_.script) {
        // We already passed evaluator_ above because of string replace
    }
}

void LegacyMeasure::update(const IniLexer& skin, double dtMs, std::function<void(const std::string&)> executeBangs) {
    switch (state_.type) {
    case Type::Time: {
      if (state_.dynamicVariables) {
        state_.format = resolveVariables(skin, skin.getOr(name_, "Format", ""));
      }
      
      using clock = std::chrono::system_clock;
      const auto now_tp = clock::now();
      const std::time_t now_c = clock::to_time_t(now_tp);
      
      auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now_tp.time_since_epoch()) % 1000;
      double msFraction = ms.count() / 1000.0;
      
      uint64_t winTime = (static_cast<uint64_t>(now_c) + 11644473600ULL) * 10000000ULL;
      
      std::tm localTm{};
      localtime_r(&now_c, &localTm);

      if (state_.format.empty()) {
        state_.numeric = static_cast<double>(winTime);
        state_.current = std::to_string(winTime);
        // Fallback for timestamp
        state_.percent = (state_.maxValue > 0.0) ? (state_.numeric / state_.maxValue) : 0.0;
      } else {
        std::string posixFormat = state_.format;
        size_t pos = 0;
        
        // 12-hour Windows %#I fix
        if (posixFormat.find("%#I") != std::string::npos) {
            int h12 = localTm.tm_hour % 12;
            if (h12 == 0) h12 = 12;
            std::string h12Str = std::to_string(h12);
            while ((pos = posixFormat.find("%#I")) != std::string::npos) {
                posixFormat.replace(pos, 3, h12Str);
            }
        }

        pos = 0;
        while ((pos = posixFormat.find("%#", pos)) != std::string::npos) {
            posixFormat.replace(pos, 2, "%-");
            pos += 2;
        }

        std::ostringstream out;
        out << std::put_time(&localTm, posixFormat.c_str());
        state_.current = out.str();
        
        try {
            state_.numeric = std::stod(state_.current);
            
            // Continuous sweeping
            if (state_.format == "%S" || state_.format == "%#S") {
                state_.numeric += msFraction;
            } else if (state_.format == "%M" || state_.format == "%#M") {
                state_.numeric += (localTm.tm_sec + msFraction) / 60.0;
            } else if (state_.format == "%I" || state_.format == "%#I" || state_.format == "%H" || state_.format == "%#H") {
                state_.numeric += (localTm.tm_min + (localTm.tm_sec + msFraction) / 60.0) / 60.0;
            }
            
        } catch (...) {
            state_.numeric = 0.0;
        }
        
        double range = state_.maxValue - state_.minValue;
        if (range > 0.0) {
            state_.percent = (state_.numeric - state_.minValue) / range;
        } else {
            state_.percent = 0.0;
        }
      }
      break;
    }

    case Type::Cpu: {
      state_.numeric = SysfsParser::getInstance().getCpuPercent();
      state_.current = formatDouble(state_.numeric);
      state_.percent = state_.numeric / 100.0;
      break;
    }

    case Type::PhysicalMemory: {
      state_.numeric = SysfsParser::getInstance().getMemoryUsed();
      double total = SysfsParser::getInstance().getMemoryTotal();
      state_.current = std::to_string(static_cast<unsigned long long>(state_.numeric));
      state_.percent = (total > 0.0) ? (state_.numeric / total) : 0.0;
      break;
    }

    case Type::SwapMemory: {
      state_.numeric = 0.0;
      state_.current = "0";
      state_.percent = 0.0;
      break;
    }

    case Type::NetIn: {
      state_.updateTimer += dtMs;
      if (state_.dynamicVariables) {
        state_.interfaceName = resolveVariables(skin, skin.getOr(name_, "Interface", ""));
      }
      if (state_.updateTimer >= 1000.0) {
          state_.updateTimer = std::fmod(state_.updateTimer, 1000.0);
          sysmeasure::NetStats cur = sysmeasure::readNetStats(state_.interfaceName);
          if (state_.prevNet.valid && cur.valid) {
            state_.targetNumeric = static_cast<double>(cur.rxBytes - state_.prevNet.rxBytes);
          } else {
            state_.targetNumeric = 0.0;
          }
          state_.prevNet = cur;
      }
      state_.numeric += (state_.targetNumeric - state_.numeric) * (dtMs / 100.0);
      state_.current = std::to_string(static_cast<long long>(state_.numeric));
      break;
    }

    case Type::NetOut: {
      state_.updateTimer += dtMs;
      if (state_.dynamicVariables) {
        state_.interfaceName = resolveVariables(skin, skin.getOr(name_, "Interface", ""));
      }
      if (state_.updateTimer >= 1000.0) {
          state_.updateTimer = std::fmod(state_.updateTimer, 1000.0);
          sysmeasure::NetStats cur = sysmeasure::readNetStats(state_.interfaceName);
          if (state_.prevNet.valid && cur.valid) {
            state_.targetNumeric = static_cast<double>(cur.txBytes - state_.prevNet.txBytes);
          } else {
            state_.targetNumeric = 0.0;
          }
          state_.prevNet = cur;
      }
      state_.numeric += (state_.targetNumeric - state_.numeric) * (dtMs / 100.0);
      state_.current = std::to_string(static_cast<long long>(state_.numeric));
      break;
    }

    case Type::Uptime: {
      sysmeasure::UptimeInfo u = sysmeasure::readUptime();
      state_.numeric = u.uptimeSeconds;
      state_.current = formatDouble(state_.numeric);
      break;
    }

    case Type::FreeDiskSpace: {
      if (state_.dynamicVariables) {
        state_.drive = resolveVariables(skin, skin.getOr(name_, "Drive", "/"));
      }
      sysmeasure::DiskInfo d = sysmeasure::readDisk(state_.drive);
      state_.numeric = d.usedPercent;
      state_.current = formatDouble(state_.numeric);
      break;
    }

    case Type::Calc: {
      if (state_.dynamicVariables) {
        state_.formula = skin.getOr(name_, "Formula", "");
        state_.ifCondition = skin.getOr(name_, "IfCondition", "");
        state_.ifTrueAction = skin.getOr(name_, "IfTrueAction", "");
        state_.ifFalseAction = skin.getOr(name_, "IfFalseAction", "");
      }
      
      // Rainmeter formulas usually just run through evaluateOr.
      // E.g., Formula=MeasureTime % 2
      std::string f = resolveVariables(skin, state_.formula);
      state_.numeric = evaluator_->getMath().evaluateOr(f, 0.0);
      state_.current = formatDouble(state_.numeric); // Actually calc measures can format as int if no decimal, but formatDouble is ok for now

      if (!state_.ifCondition.empty() && executeBangs) {
        std::string cond = resolveVariables(skin, state_.ifCondition);
        double condResult = evaluator_->getMath().evaluateOr(cond, 0.0);
        int newState = (condResult > 0.0) ? 1 : 0;
        
        // Execute bangs only on state transition
        if (state_.lastConditionState != newState) {
          state_.lastConditionState = newState;
          if (newState == 1 && !state_.ifTrueAction.empty()) {
            executeBangs(state_.ifTrueAction);
          } else if (newState == 0 && !state_.ifFalseAction.empty()) {
            executeBangs(state_.ifFalseAction);
          }
        }
      }
      break;
    }

    case Type::WebParser: {
      if (state_.dynamicVariables) {
         std::string newUrl = resolveVariables(skin, skin.getOr(name_, "Url", ""));
         if (newUrl != state_.url) {
             state_.url = newUrl;
             state_.fetcher->start(state_.url);
         }
      }
      
      std::string out;
      if (state_.fetcher->poll(out)) {
         state_.current = out;
         state_.numeric = 1.0; // Indicate ready
      }
      break;
    }

    case Type::Plugin: {
      if (state_.dynamicVariables) {
        std::string pName = skin.getOr(name_, "PluginName", "");
        if (pName.empty()) {
          pName = skin.getOr(name_, "Plugin", "");
        }
        state_.pluginName = pName;
      }
      PluginManager::MockValue v = evaluator_->getPlugins().resolve(state_.pluginName);
      state_.numeric = v.numeric;
      state_.current = v.string;
      if (state_.current.empty()) {
        state_.current = formatDouble(state_.numeric);
      }
      break;
    }

    case Type::Script: {
      if (state_.script) {
          state_.current = state_.script->callUpdate();
          try {
              state_.numeric = std::stod(state_.current);
          } catch (...) {
              state_.numeric = 0.0;
          }
      }
      break;
    }
    
    case Type::UsageMonitorType: {
      if (state_.usageMonitor) {
          if (state_.dynamicVariables) {
              state_.usageMonitor->loadFrom(skin, name_);
          }
          state_.usageMonitor->update();
          state_.numeric = state_.usageMonitor->numericValue();
          state_.current = state_.usageMonitor->stringValue();
          double range = state_.maxValue - state_.minValue;
          state_.percent = (range > 0.0) ? std::clamp((state_.numeric - state_.minValue) / range, 0.0, 1.0) : state_.numeric;
      }
      break;
    }

    case Type::HwInfoType:
    case Type::CoreTempType: {
      state_.numeric = SysfsParser::getInstance().getHwmonValue(state_.hwInfoSensorName, state_.hwInfoEntryName);
      state_.current = formatDouble(state_.numeric);
      double range = state_.maxValue - state_.minValue;
      state_.percent = (range > 0.0) ? std::clamp((state_.numeric - state_.minValue) / range, 0.0, 1.0) : state_.numeric;
      break;
    }
    
    case Type::AudioLevelType: {
      if (state_.audioLevel) {
          if (state_.dynamicVariables) {
              state_.audioLevel->loadFrom(skin, name_);
          }
          state_.audioLevel->update(dtMs);
          state_.numeric = state_.audioLevel->numericValue();
          state_.current = state_.audioLevel->stringValue();
          // AudioLevel is inherently 0.0 to 1.0, but we apply Min/Max scaling if the user overrode it.
          double range = state_.maxValue - state_.minValue;
          state_.percent = (range > 0.0 && state_.maxValue != 1.0) ? std::clamp((state_.numeric - state_.minValue) / range, 0.0, 1.0) : state_.numeric;
      }
      break;
    }

    case Type::PowerPluginType: {
      if (state_.powerPlugin) {
          if (state_.dynamicVariables) {
              state_.powerPlugin->loadFrom(skin, name_);
          }
          state_.numeric = state_.powerPlugin->numericValue();
          state_.current = state_.powerPlugin->stringValue();
          double range = state_.maxValue - state_.minValue;
          state_.percent = (range > 0.0) ? std::clamp((state_.numeric - state_.minValue) / range, 0.0, 1.0) : state_.numeric;
      }
      break;
    }

    case Type::InputTextType: {
      if (state_.inputTextPlugin) {
          if (state_.dynamicVariables) {
              state_.inputTextPlugin->loadFrom(skin, name_);
          }
          state_.numeric = state_.inputTextPlugin->numericValue();
          state_.current = state_.inputTextPlugin->stringValue();
      }
      break;
    }

    case Type::Unknown:
    default:
      state_.current.clear();
      state_.numeric = 0.0;
      break;
    }
}

void MeasureEvaluator::loadFrom(const IniLexer &skin) {
  measures_.clear();
  for (const auto &[section, keys] : skin.data()) {
    auto measureIt = keys.find("Measure");
    if (measureIt == keys.end()) continue;
    
    std::string kind = measureIt->second;
    std::string plugin = skin.getOr(section, "Plugin", "");
    std::string pluginName = skin.getOr(section, "PluginName", "");
    if (plugin.empty()) plugin = pluginName;
    toLower(plugin);

    std::shared_ptr<IMeasure> measure;
    
    if (kind == "CPU") {
        measure = std::make_shared<CpuMeasure>();
    } else if (kind == "PhysicalMemory") {
        measure = std::make_shared<PhysicalMemoryMeasure>();
    } else if (kind == "Battery") {
        measure = std::make_shared<BatteryMeasure>();
    } else if (kind == "NowPlaying" || plugin == "nowplaying" || plugin == "nowplaying.dll" || plugin == "webnowplaying" || plugin == "webnowplaying.dll") {
        measure = std::make_shared<NowPlayingMeasure>();
    } else {
        auto leg = std::make_shared<LegacyMeasure>(this, section);
        measure = leg;
    }
    
    measure->loadFrom(skin, section);
    measures_.emplace(section, measure);
  }
  evaluate(skin, 1000.0);
}

void MeasureEvaluator::injectVariables(IniLexer &skin) const {
  for (const auto &[name, m] : measures_) {
      // Very basic approximation for legacy variables.
      skin.setVariable(name, m->getString());
  }
}

void MeasureEvaluator::evaluate(const IniLexer &skin, double dtMs, std::function<void(const std::string&)> executeBangs) {
  currentBangCb_ = executeBangs;
  math_.setVariableResolver([&skin](const std::string &var) {
    return skin.getCaseInsensitive("Variables", var).value_or("");
  });
  math_.setMeasureResolver([this](const std::string &meas) {
    return numericValue(meas);
  });

  for (auto &[name, m] : measures_) {
      m->update(skin, dtMs, executeBangs);
  }
}

std::string MeasureEvaluator::value(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
      if (lName == lower) return m->getString();
  }
  return "";
}

double MeasureEvaluator::numericValue(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
      if (lName == lower) return m->getNumeric();
  }
  return 0.0;
}

double MeasureEvaluator::percentValue(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
      if (lName == lower) return m->getPercent();
  }
  return 0.0;
}

bool MeasureEvaluator::hasMeasure(std::string_view measureName) const {
  std::string lower(measureName);
  for (char &c : lower) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
  for (const auto &[name, m] : measures_) {
      std::string lName = name;
      for (char &c : lName) { if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a'); }
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
        if (m->getActionTimer()) {
            m->getActionTimer()->tick(dtMs, fireBang);
        }
    }
}
