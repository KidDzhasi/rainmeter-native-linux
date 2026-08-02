#pragma once

#include <string>
#include <string_view>
#include <unordered_map>

#include <memory>

#include "PluginManager.hpp"
#include "SystemMeasures.hpp"
#include "MathParser.hpp"
#include "WebFetcher.hpp"
#include "NowPlayingMeasure.hpp"
#include "ScriptEnvironment.hpp"
#include "ActionTimer.hpp"
#include "LinuxUsageMonitor.hpp"
#include "LinuxPowerPlugin.hpp"
#include "InputTextPlugin.hpp"
#include "LinuxAudioLevel.hpp"
#include "SysfsParser.hpp"
#include <functional>

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
#include "IMeasure.hpp"

// Forward declaration of LegacyMeasureState
struct LegacyMeasureState;

class MeasureEvaluator {
public:
  MeasureEvaluator() = default;

  void loadFrom(const IniLexer &skin);
  void evaluate(const IniLexer &skin, double dtMs, std::function<void(const std::string&)> executeBangs = nullptr);
  void injectVariables(IniLexer &skin) const;

  // String output of a measure (for %1 substitution / display).
  std::string value(std::string_view measureName) const;

  // Numeric output of a measure (for math formulas and bar percentages).
  // Time measures return 0. Returns 0 for unknown measures.
  double numericValue(std::string_view measureName) const;

  // Percentage output of a measure (0.0 to 1.0). Used by Bar meters.
  double percentValue(std::string_view measureName) const;

  // Check if a measure exists by name (case-insensitive)
  bool hasMeasure(std::string_view measureName) const;

  std::shared_ptr<ScriptEnvironment> getScript(const std::string& measureName) const {
      auto it = measures_.find(measureName);
      if (it != measures_.end()) {
          return it->second->getScript();
      }
      return nullptr;
  }

  // Expose bang execution to ScriptEnvironment
  void fireBang(const std::string& bang) const;

  // Returns the ActionTimer for a named measure, or nullptr.
  std::shared_ptr<ActionTimer> getActionTimer(const std::string& measureName) const {
      auto it = measures_.find(measureName);
      if (it != measures_.end()) {
          return it->second->getActionTimer();
      }
      return nullptr;
  }

  // Tick all active ActionTimers with the render thread delta time.
  void tickActionTimers(double dtMs, std::function<void(const std::string&)> fireBang);

  std::size_t count() const noexcept { return measures_.size(); }

  // Expose to LegacyMeasure
  MathParser& getMath() { return math_; }
  PluginManager& getPlugins() { return plugins_; }

private:
  std::unordered_map<std::string, std::shared_ptr<IMeasure>> measures_;
  PluginManager plugins_; // mocks Windows Measure=Plugin measures
  MathParser math_;       // For Measure=Calc
  
  mutable std::function<void(const std::string&)> currentBangCb_;
};
