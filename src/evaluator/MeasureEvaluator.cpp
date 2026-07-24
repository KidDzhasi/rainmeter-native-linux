#include "MeasureEvaluator.hpp"

#include <chrono>
#include <cstdio>
#include <ctime>
#include <iomanip>
#include <sstream>

#include "SystemMeasures.hpp"
#include "parser/IniLexer.hpp"

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
      } else {
        m.type = Type::Plugin;
        m.pluginName = name;
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
          m.script = std::make_shared<ScriptEnvironment>(const_cast<IniLexer*>(&skin), this);
          if (m.script->loadScript(scriptPath)) {
              m.script->callInitialize();
          }
      }
    } else {
      m.type = Type::Unknown;
    }

    measures_.emplace(section, std::move(m));
  }

  evaluate(skin);
}

void MeasureEvaluator::evaluate(const IniLexer &skin, std::function<void(const std::string&)> executeBangs) {
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
      
      // Rainmeter numeric value for time is the Windows FILETIME timestamp
      // (100-nanosecond intervals since Jan 1, 1601).
      // Unix epoch is 11644473600 seconds after Windows epoch.
      uint64_t winTime = (static_cast<uint64_t>(now_c) + 11644473600ULL) * 10000000ULL;
      m.numeric = static_cast<double>(winTime);

      if (m.format.empty()) {
        m.current = std::to_string(winTime);
      } else {
        std::tm localTm{};
        localtime_r(&now_c, &localTm);
        std::ostringstream out;
        out << std::put_time(&localTm, m.format.c_str());
        m.current = out.str();
      }
      break;
    }

    case Type::Cpu: {
      const sysmeasure::CpuSample cur = sysmeasure::readCpuSample();
      m.numeric = sysmeasure::cpuPercent(m.prevCpu, cur);
      m.prevCpu = cur;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::PhysicalMemory: {
      const sysmeasure::MemoryInfo mem = sysmeasure::readMemory();
      m.numeric = mem.usedBytes; // Usually it's bytes in Rainmeter
      m.current = std::to_string(static_cast<long long>(m.numeric));
      break;
    }

    case Type::SwapMemory: {
      const sysmeasure::MemoryInfo mem = sysmeasure::readMemory();
      m.numeric = (mem.swapTotalBytes > 0) ? (mem.swapTotalBytes - mem.swapFreeBytes) : 0;
      m.current = std::to_string(static_cast<long long>(m.numeric));
      break;
    }

    case Type::NetIn: {
      if (m.dynamicVariables) {
        m.interfaceName = resolveVariables(skin, skin.getOr(name, "Interface", ""));
      }
      sysmeasure::NetStats cur = sysmeasure::readNetStats(m.interfaceName);
      if (m.prevNet.valid && cur.valid) {
        m.numeric = static_cast<double>(cur.rxBytes - m.prevNet.rxBytes);
      } else {
        m.numeric = 0.0;
      }
      m.prevNet = cur;
      m.current = std::to_string(static_cast<long long>(m.numeric));
      break;
    }

    case Type::NetOut: {
      if (m.dynamicVariables) {
        m.interfaceName = resolveVariables(skin, skin.getOr(name, "Interface", ""));
      }
      sysmeasure::NetStats cur = sysmeasure::readNetStats(m.interfaceName);
      if (m.prevNet.valid && cur.valid) {
        m.numeric = static_cast<double>(cur.txBytes - m.prevNet.txBytes);
      } else {
        m.numeric = 0.0;
      }
      m.prevNet = cur;
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

    case Type::Unknown:
    default:
      m.current.clear();
      m.numeric = 0.0;
      break;
    }
  }
}

std::string MeasureEvaluator::value(std::string_view measureName) const {
  std::string name(measureName);
  auto it = measures_.find(name);
  if (it != measures_.end()) {
    return it->second.current;
  }
  return "";
}

double MeasureEvaluator::numericValue(std::string_view measureName) const {
  std::string name(measureName);
  auto it = measures_.find(name);
  if (it != measures_.end()) {
    return it->second.numeric;
  }
  return 0.0;
}

void MeasureEvaluator::fireBang(const std::string& bang) const {
    if (currentBangCb_) {
        currentBangCb_(bang);
    }
}

// formatTime removed as it is now inlined in evaluate()
