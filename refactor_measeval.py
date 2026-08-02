import re

with open('src/evaluator/MeasureEvaluator.cpp', 'r') as f:
    content = f.read()

# We need to wrap the old Type enum and Measure struct in LegacyMeasure : public IMeasure
legacy_measure_code = """
#include "IMeasure.hpp"
#include "CpuMeasure.hpp"
#include "PhysicalMemoryMeasure.hpp"
#include "BatteryMeasure.hpp"

enum class Type {
    Unknown, Time, Cpu, PhysicalMemory, SwapMemory, FreeDiskSpace, NetIn, NetOut, Uptime, Calc, WebParser, NowPlaying, Plugin, Script, ActionTimerType, UsageMonitorType, CoreTempType, HwInfoType, AudioLevelType, PowerPluginType, InputTextType
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
    std::string playerType;
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
"""

# Extract the old loadFrom body, replace m. with state_.
loadFrom_match = re.search(r'void MeasureEvaluator::loadFrom\(const IniLexer &skin\) \{.*?(for \(const auto &\[section, keys\] : skin\.data\(\)\) \{.*?)\n\}\n', content, re.DOTALL)
loadFrom_body = loadFrom_match.group(1)

# Extract old evaluate body
evaluate_match = re.search(r'void MeasureEvaluator::evaluate.*?\{.*?math_\.setVariableResolver.*?for \(auto &\[name, m\] : measures_\) \{.*?(switch \(m\.type\) \{.*?\n    \})\n  \}\n\}', content, re.DOTALL)
evaluate_body = evaluate_match.group(1)

# Modify evaluate_body: m. -> state_.
evaluate_body = evaluate_body.replace('m.', 'state_.')
evaluate_body = evaluate_body.replace('math_', 'evaluator_->getMath()')
evaluate_body = evaluate_body.replace('mpris_', 'evaluator_->getMprisRef()')
evaluate_body = evaluate_body.replace('plugins_', 'evaluator_->getPlugins()')
evaluate_body = evaluate_body.replace('name', 'name_')
# For script parsing
evaluate_body = evaluate_body.replace('this', 'evaluator_')

# Modify loadFrom_body: m. -> state_.
loadFrom_legacy = loadFrom_body.replace('m.', 'state_.')
loadFrom_legacy = loadFrom_legacy.replace('Measure m;', '')
loadFrom_legacy = loadFrom_legacy.replace('measures_.emplace(section, std::move(m));', '')
# Extract just the inner part of the loop for LegacyMeasure::loadFrom
inner_load = re.search(r'auto measureIt = keys\.find\("Measure"\);.*?if \(kind == "Script"\) \{.*?\} else \{.*?\}', loadFrom_legacy, re.DOTALL)
inner_load_str = inner_load.group(0)

legacy_load_impl = f"""
void LegacyMeasure::loadFrom(const IniLexer& skin, const std::string& section) {{
    auto keysIt = skin.data().find(section);
    if (keysIt == skin.data().end()) return;
    const auto& keys = keysIt->second;
    {inner_load_str}
    // Adjust script parent
    if (state_.script) {{
        // We already passed evaluator_ above because of string replace
    }}
}}
"""

legacy_load_impl = legacy_load_impl.replace('mpris_', 'evaluator_->getMprisRef()')
legacy_load_impl = legacy_load_impl.replace('this', 'evaluator_')

legacy_update_impl = f"""
void LegacyMeasure::update(const IniLexer& skin, double dtMs, std::function<void(const std::string&)> executeBangs) {{
    {evaluate_body}
}}
"""

new_measure_eval = """
void MeasureEvaluator::loadFrom(const IniLexer &skin) {
  measures_.clear();
  for (const auto &[section, keys] : skin.data()) {
    auto measureIt = keys.find("Measure");
    if (measureIt == keys.end()) continue;
    
    std::string kind = measureIt->second;
    std::shared_ptr<IMeasure> measure;
    
    if (kind == "CPU") {
        measure = std::make_shared<CpuMeasure>();
    } else if (kind == "PhysicalMemory") {
        measure = std::make_shared<PhysicalMemoryMeasure>();
    } else if (kind == "Battery") {
        measure = std::make_shared<BatteryMeasure>();
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
"""

new_accessors = """
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
"""

with open('src/evaluator/MeasureEvaluator.cpp', 'r') as f:
    orig = f.read()

# We just take the headers and the namespace from orig
headers = orig[:orig.find('void MeasureEvaluator::loadFrom')]

with open('src/evaluator/MeasureEvaluator.cpp', 'w') as f:
    f.write(headers)
    f.write(legacy_measure_code)
    f.write(legacy_load_impl)
    f.write(legacy_update_impl)
    f.write(new_measure_eval)
    f.write(new_accessors)

