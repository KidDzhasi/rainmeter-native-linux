#pragma once

#include <string>
#include <string_view>
#include <unordered_map>

#include <memory>

#include "PluginManager.hpp"
#include "SystemMeasures.hpp"
#include "MathParser.hpp"
#include "WebFetcher.hpp"
#include "MprisClient.hpp"
#include "ScriptEnvironment.hpp"
#include "ActionTimer.hpp"
#include "LinuxUsageMonitor.hpp"
#include "LinuxCoreTemp.hpp"
#include "LinuxAudioLevel.hpp"
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
class MeasureEvaluator {
public:
  MeasureEvaluator() = default;

  void loadFrom(const IniLexer &skin);
  void evaluate(const IniLexer &skin, std::function<void(const std::string&)> executeBangs = nullptr);

  // String output of a measure (for %1 substitution / display).
  std::string value(std::string_view measureName) const;

  // Numeric output of a measure (for math formulas and bar percentages).
  // Time measures return 0. Returns 0 for unknown measures.
  double numericValue(std::string_view measureName) const;

  // Percentage output of a measure (0.0 to 1.0). Used by Bar meters.
  double percentValue(std::string_view measureName) const;

  // Check if a measure exists by name (case-insensitive)
  bool hasMeasure(std::string_view measureName) const;

  // Returns the MPRIS client if active, nullptr otherwise.
  std::shared_ptr<MprisClient> getMpris() const { return mpris_; }

  std::shared_ptr<ScriptEnvironment> getScript(const std::string& measureName) const {
      auto it = measures_.find(measureName);
      if (it != measures_.end() && it->second.type == Type::Script) {
          return it->second.script;
      }
      return nullptr;
  }

  // Expose bang execution to ScriptEnvironment
  void fireBang(const std::string& bang) const;

  // Returns the ActionTimer for a named measure, or nullptr.
  std::shared_ptr<ActionTimer> getActionTimer(const std::string& measureName) const {
      auto it = measures_.find(measureName);
      if (it != measures_.end() && it->second.type == Type::ActionTimerType) {
          return it->second.actionTimer;
      }
      return nullptr;
  }

  // Tick all active ActionTimers with the render thread delta time.
  void tickActionTimers(double dtMs, std::function<void(const std::string&)> fireBang);

  std::size_t count() const noexcept { return measures_.size(); }

private:
  enum class Type {
    Unknown,
    Time,
    Cpu,
    PhysicalMemory,
    SwapMemory,
    FreeDiskSpace,
    NetIn,
    NetOut,
    Uptime,
    Calc,
    WebParser,
    NowPlaying,
    Plugin,
    Script,
    ActionTimerType,
    UsageMonitorType,
    CoreTempType,
    AudioLevelType,
  };

  struct Measure {
    Type type = Type::Unknown;
    std::string format;            // Time: strftime format
    std::string drive = "/";       // FreeDiskSpace: mount path
    std::string pluginName;        // Plugin: the requested .dll / plugin name
    std::string current;           // last evaluated string value
    double numeric = 0.0;          // last evaluated numeric value
    double percent = 0.0;          // last evaluated percentage (0.0 to 1.0)
    sysmeasure::CpuSample prevCpu; // CPU: previous tick sample
    sysmeasure::NetStats prevNet;  // NetIn/NetOut: previous tick sample
    std::string interfaceName;     // NetIn/NetOut: interface name
    
    std::string formula;           // Calc: the expression string
    std::string ifCondition;       // Calc: IfCondition expression
    std::string ifTrueAction;      // Calc: bang string
    std::string ifFalseAction;     // Calc: bang string
    int lastConditionState = -1;   // Calc: -1=unknown, 0=false, 1=true
    
    std::shared_ptr<WebFetcher> fetcher; // WebParser: background fetcher
    std::string url;               // WebParser: requested URL
    
    std::string playerType;        // NowPlaying: property to extract
    std::shared_ptr<ScriptEnvironment> script; // Script: Lua environment
    std::shared_ptr<ActionTimer> actionTimer;  // ActionTimer: native plugin
    std::shared_ptr<LinuxUsageMonitor> usageMonitor; // UsageMonitor adapter
    std::shared_ptr<LinuxCoreTemp> coreTemp;   // CoreTemp adapter
    std::shared_ptr<LinuxAudioLevel> audioLevel; // AudioLevel adapter
    
    bool dynamicVariables = false; // re-evaluate format/drive/pluginName/formula
  };

  std::unordered_map<std::string, Measure> measures_;
  PluginManager plugins_; // mocks Windows Measure=Plugin measures
  MathParser math_;       // For Measure=Calc
  std::shared_ptr<MprisClient> mpris_; // MPRIS background client
  
  mutable std::function<void(const std::string&)> currentBangCb_;
};
