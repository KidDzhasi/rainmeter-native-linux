#pragma once

#include <string>

class IniLexer;
class MeasureEvaluator;

struct BangResult {
  bool needsUpdate = false;
  bool needsRedraw = false;
  bool deactivateConfig = false;
};

// Parses and executes Rainmeter bangs (e.g. [!SetVariable "Key" "Value"])
// Supports chaining multiple bangs in one string: [!Update][!Redraw]
class CommandProcessor {
public:
  static BangResult execute(const std::string &bangString, IniLexer &skin,
                            MeasureEvaluator &measures);
};
