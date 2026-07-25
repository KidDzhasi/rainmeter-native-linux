#pragma once

#include <string>
#include <vector>
#include "SystemMeasures.hpp"

class IniLexer;

class LinuxUsageMonitor {
public:
    LinuxUsageMonitor() = default;

    void loadFrom(const IniLexer& skin, const std::string& section);
    void update();

    double numericValue() const { return numeric_; }
    std::string stringValue() const { return current_; }

private:
    std::string alias_;
    std::string category_;
    std::string counter_;
    int index_ = 1;
    
    double numeric_ = 0.0;
    std::string current_;

    sysmeasure::CpuSample prevCpu_;
    bool isCpu_ = false;
    bool isRam_ = false;
    bool isProcess_ = false;
    
    void updateCpu();
    void updateRam();
    void updateProcess();
};
