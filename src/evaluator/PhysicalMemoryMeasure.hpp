#pragma once

#include "BaseMeasure.hpp"
#include "evaluator/SysfsParser.hpp"
#include <string>

class PhysicalMemoryMeasure : public BaseMeasure {
public:
    void onLoad(const IniLexer& skin, const std::string& section) override {
        // MaxValue will be dynamically updated to total memory.
    }

protected:
    void onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) override {
        numeric_ = SysfsParser::getInstance().getMemoryUsedPercent();
        
        // Update maxValue so getPercent() works correctly
        maxValue_ = 100.0;

        current_ = std::to_string(static_cast<unsigned long long>(numeric_));
    }
};
