#pragma once

#include <functional>
#include <string>

// MathParser evaluates Rainmeter-style numeric formulas found in meter
// properties, e.g. "W=(40 * #Scale#)" or "X=([MeasureCPU] * 2)".
//
// Before evaluation, two kinds of tokens are resolved to numbers via
// caller-supplied lookups:
//   * #Variable#     -> value from the skin's [Variables] section
//   * [MeasureName]  -> current numeric value of a measure
//
// The remaining infix expression supports + - * / and parentheses with the
// usual precedence, implemented with a shunting-yard algorithm.
class MathParser {
public:
  // Resolves a #Variable# name (without the '#') to its raw string value.
  using VariableResolver = std::function<std::string(const std::string &)>;
  // Resolves a [MeasureName] (without the brackets) to its numeric value.
  using MeasureResolver = std::function<double(const std::string &)>;

  MathParser() = default;
  MathParser(VariableResolver vars, MeasureResolver measures)
      : variables_(std::move(vars)), measures_(std::move(measures)) {}

  void setVariableResolver(VariableResolver r) { variables_ = std::move(r); }
  void setMeasureResolver(MeasureResolver r) { measures_ = std::move(r); }

  // Substitutes #Variable# and [Measure] tokens in `input` with their
  // resolved values, producing a pure arithmetic string.
  std::string substitute(const std::string &input) const;

  // Evaluates `expr` and stores the result in `out`. Returns true on success.
  // Tokens (#Var#, [Measure]) are substituted first.
  bool evaluate(const std::string &expr, double &out) const;

  // Convenience: evaluate, returning `fallback` if the expression is not a
  // valid formula (e.g. a plain string). If the input is a plain number it is
  // returned as-is.
  double evaluateOr(const std::string &expr, double fallback) const;

private:
  // Pure arithmetic evaluation (no token substitution) via shunting-yard.
  static bool evalArithmetic(const std::string &expr, double &out);

  VariableResolver variables_;
  MeasureResolver measures_;
};
