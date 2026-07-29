#pragma once

#include <string>

class IniLexer;
class MeasureEvaluator;

struct BangResult {
  bool needsUpdate = false;
  bool needsRedraw = false;
  bool deactivateConfig = false;
};

struct InputTextState {
    bool active = false;
    std::string measureName;
    std::string command;
    std::string buffer;
    double x = 0;
    double y = 0;
    double w = 0;
    double h = 0;
    std::string fontFace;
    double fontSize = 12.0;
    std::string fontColor;
    std::string solidColor;
    void* skinInstance = nullptr;
    std::string pendingCommand;
};

extern InputTextState g_InputState;

// Parses and executes Rainmeter bangs (e.g. [!SetVariable "Key" "Value"])
// Supports chaining multiple bangs in one string: [!Update][!Redraw]
class CommandProcessor {
public:
  static BangResult execute(const std::string &bangString, IniLexer &skin,
                            MeasureEvaluator &measures, void* skinInstance = nullptr);
};
