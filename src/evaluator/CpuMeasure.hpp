#pragma once

#include "BaseMeasure.hpp"
#include "evaluator/SysfsParser.hpp"

class CpuMeasure : public BaseMeasure {
public:
    void onLoad(const IniLexer& skin, const std::string& section) override {
        // CPU implicitly maxes at 100.0, unless overridden. BaseMeasure parses it.
        // We override if not set by user, but let's just default to 100 if they didn't provide it, 
        // actually standard Rainmeter CPU max is 100% implicitly handled as a percentage anyway.
        // Wait, BaseMeasure defaults maxValue_ to 1.0. For CPU, we should probably set it to 100.0 if not overridden.
        if (skin.getOr(section, "MaxValue", "").empty()) {
            maxValue_ = 100.0;
        }
    }

protected:
    void onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) override {
        numeric_ = SysfsParser::getInstance().getCpuPercent();
        
        char buf[64];
        std::snprintf(buf, sizeof(buf), "%.1f", numeric_);
        current_ = buf;
    }
};
