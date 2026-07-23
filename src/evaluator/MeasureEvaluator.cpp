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

// Expands #Variable# tokens in `text` against the skin's [Variables] section.
// Unknown variables are left untouched.
std::string resolveVariables(const IniLexer &skin, const std::string &text) {
  std::string out;
  out.reserve(text.size());
  for (std::size_t i = 0; i < text.size();) {
    if (text[i] == '#') {
      const std::size_t close = text.find('#', i + 1);
      if (close != std::string::npos) {
        const std::string name = text.substr(i + 1, close - i - 1);
        // Rainmeter variables are case-insensitive: #format# resolves a
        // variable defined as "Format=".
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
    const std::string &kind = measureIt->second;
    if (kind == "Time") {
      m.type = Type::Time;
      // Resolve any #Variables# embedded in the Format string (e.g.
      // Format=%#DateFormat#) before it reaches strftime.
      m.format = resolveVariables(skin, skin.getOr(section, "Format", "%H:%M"));
    } else if (kind == "CPU") {

      m.type = Type::Cpu;
      m.prevCpu = sysmeasure::readCpuSample();
    } else if (kind == "PhysicalMemory") {
      m.type = Type::PhysicalMemory;
    } else if (kind == "FreeDiskSpace") {
      m.type = Type::FreeDiskSpace;
      m.drive = skin.getOr(section, "Drive", "/");
    } else if (kind == "Plugin") {
      // A Windows plugin measure: capture the requested plugin name so the
      // PluginManager can mock it. Rainmeter accepts either "Plugin=Foo.dll"
      // or a separate "PluginName=Foo.dll" key.
      m.type = Type::Plugin;
      std::string name = skin.getOr(section, "PluginName", "");
      if (name.empty()) {
        name = skin.getOr(section, "Plugin", "");
      }
      m.pluginName = name;
    } else {
      m.type = Type::Unknown;
    }

    measures_.emplace(section, std::move(m));
  }

  evaluate();
}

void MeasureEvaluator::evaluate() {
  for (auto &[name, m] : measures_) {
    switch (m.type) {
    case Type::Time:
      m.current = formatTime(m.format);
      m.numeric = 0.0;
      break;

    case Type::Cpu: {
      const sysmeasure::CpuSample cur = sysmeasure::readCpuSample();
      m.numeric = sysmeasure::cpuPercent(m.prevCpu, cur);
      m.prevCpu = cur;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::PhysicalMemory: {
      const sysmeasure::MemoryInfo mem = sysmeasure::readMemory();
      m.numeric = mem.usedPercent;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::FreeDiskSpace: {
      const sysmeasure::DiskInfo disk = sysmeasure::readDisk(m.drive);
      m.numeric = disk.usedPercent;
      m.current = formatDouble(m.numeric);
      break;
    }

    case Type::Plugin: {
      const PluginManager::MockValue mv = plugins_.resolve(m.pluginName);
      m.numeric = mv.numeric;
      m.current = mv.string;
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
  auto it = measures_.find(std::string(measureName));
  if (it == measures_.end()) {
    return {};
  }
  return it->second.current;
}

double MeasureEvaluator::numericValue(std::string_view measureName) const {
  auto it = measures_.find(std::string(measureName));
  if (it == measures_.end()) {
    return 0.0;
  }
  return it->second.numeric;
}

std::string MeasureEvaluator::formatTime(const std::string &format) {
  using clock = std::chrono::system_clock;
  const std::time_t now = clock::to_time_t(clock::now());

  std::tm localTm{};
  localtime_r(&now, &localTm);

  std::ostringstream out;
  out << std::put_time(&localTm, format.c_str());
  return out.str();
}
