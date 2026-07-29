#pragma once
#include <string>
#include "parser/IniLexer.hpp"

class InputTextPlugin {
public:
    InputTextPlugin() = default;
    void loadFrom(const IniLexer &skin, const std::string &section) {}
    double numericValue() const { return 0.0; }
    std::string stringValue() const { return ""; }
};
