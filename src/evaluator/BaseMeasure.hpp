#pragma once

#include "IMeasure.hpp"
#include "parser/IniLexer.hpp"
#include <cmath>
#include <algorithm>

// BaseMeasure provides common functionality for polling measures:
// handles MinValue/MaxValue parsing, UpdateDivider timing, and value clamping.
class BaseMeasure : public IMeasure {
public:
    virtual ~BaseMeasure() = default;

    void loadFrom(const IniLexer& skin, const std::string& section) override {
        minValue_ = 0.0;
        try {
            std::string minStr = skin.getOr(section, "MinValue", "0.0");
            if (!minStr.empty()) {
                minValue_ = std::stod(minStr);
            }
        } catch (...) {}

        maxValue_ = 1.0;
        try {
            std::string maxStr = skin.getOr(section, "MaxValue", "");
            if (!maxStr.empty()) {
                maxValue_ = std::stod(maxStr);
            }
        } catch (...) {}

        dynamicVariables_ = (skin.getOr(section, "DynamicVariables", "0") == "1");
        
        double updateDivider = 1.0;
        try {
            updateDivider = std::stod(skin.getOr(section, "UpdateDivider", "1"));
        } catch (...) {}
        
        updateInterval_ = updateDivider * 1000.0; // Typically Rainmeter ticks are 1000ms
        
        // Let derived class parse custom fields
        onLoad(skin, section);
    }

    void update(const IniLexer& skin, double dtMs, std::function<void(const std::string&)> executeBangs) override {
        updateTimer_ += dtMs;
        if (updateTimer_ >= updateInterval_ || forceUpdate_) {
            updateTimer_ = std::fmod(updateTimer_, updateInterval_);
            forceUpdate_ = false;
            onUpdate(skin, executeBangs);
        }
    }

    std::string getString() const override { return current_; }
    double getNumeric() const override { return numeric_; }
    double getPercent() const override {
        double range = maxValue_ - minValue_;
        if (range <= 0.0) return 0.0;
        return std::clamp((numeric_ - minValue_) / range, 0.0, 1.0);
    }

protected:
    virtual void onLoad(const IniLexer& skin, const std::string& section) {}
    virtual void onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) = 0;

    std::string current_;
    double numeric_ = 0.0;
    
    double minValue_ = 0.0;
    double maxValue_ = 1.0;
    bool dynamicVariables_ = false;
    double updateTimer_ = 1000.0; // High initial value forces immediate update
    double updateInterval_ = 1000.0;
    bool forceUpdate_ = true;
};
