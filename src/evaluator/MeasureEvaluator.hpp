#pragma once

#include <string>
#include <string_view>
#include <unordered_map>

#include "PluginManager.hpp"
#include "SystemMeasures.hpp"

class IniLexer;

// MeasureEvaluator processes Rainmeter [Measure] sections and produces the
// live values that meters reference (via %1 in a Text field, [Measure] in a
// formula, or a Bar's fill percentage).
//
// Supported measure types:
//   * Measure=Time            -> local time formatted with the Format key.
//   * Measure=CPU             -> CPU busy percentage (0-100) from /proc/stat,
//                                computed as a delta between ticks.
//   * Measure=PhysicalMemory  -> RAM used percentage from /proc/meminfo.
//   * Measure=FreeDiskSpace   -> disk used percentage via statvfs on Drive.
//
// Call loadFrom() once after parsing, then evaluate() on every engine tick.
class MeasureEvaluator {
public:
  MeasureEvaluator() = default;

  void loadFrom(const IniLexer &skin);
  void evaluate();

  // String output of a measure (for %1 substitution / display).
  std::string value(std::string_view measureName) const;

  // Numeric output of a measure (for math formulas and bar percentages).
  // Time measures return 0. Returns 0 for unknown measures.
  double numericValue(std::string_view measureName) const;

  std::size_t count() const noexcept { return measures_.size(); }

private:
  enum class Type {
    Unknown,
    Time,
    Cpu,
    PhysicalMemory,
    FreeDiskSpace,
    Plugin,
  };

  struct Measure {
    Type type = Type::Unknown;
    std::string format;            // Time: strftime format
    std::string drive = "/";       // FreeDiskSpace: mount path
    std::string pluginName;        // Plugin: the requested .dll / plugin name
    std::string current;           // last evaluated string value
    double numeric = 0.0;          // last evaluated numeric value
    sysmeasure::CpuSample prevCpu; // CPU: previous tick sample
  };

  static std::string formatTime(const std::string &format);

  std::unordered_map<std::string, Measure> measures_;
  PluginManager plugins_; // mocks Windows Measure=Plugin measures
};
