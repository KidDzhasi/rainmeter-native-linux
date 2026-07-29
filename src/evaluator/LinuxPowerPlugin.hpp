#pragma once
#include <string>
#include "parser/IniLexer.hpp"

class LinuxPowerPlugin {
public:
    LinuxPowerPlugin() = default;
    void loadFrom(const IniLexer &skin, const std::string &section);
    double numericValue() const;
    std::string stringValue() const;
private:
    std::string powerState_;
};
