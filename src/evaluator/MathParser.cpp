#include "MathParser.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>
#include <stack>
#include <string>
#include <vector>

std::string MathParser::substitute(const std::string &input) const {
  std::string out;
  out.reserve(input.size());

  for (std::size_t i = 0; i < input.size();) {
    const char c = input[i];

    // #Variable#
    if (c == '#') {
      const auto end = input.find('#', i + 1);
      if (end != std::string::npos) {
        const std::string name = input.substr(i + 1, end - i - 1);
        std::string value;
        if (variables_) {
          value = variables_(name);
        }
        out += value;
        i = end + 1;
        continue;
      }
    }

    // [MeasureName]
    if (c == '[') {
      const auto end = input.find(']', i + 1);
      if (end != std::string::npos) {
        const std::string name = input.substr(i + 1, end - i - 1);
        double value = 0.0;
        if (measures_) {
          value = measures_(name);
        }
        // Format without trailing zeros noise; plain %g is fine for math.
        char buf[64];
        std::snprintf(buf, sizeof(buf), "%g", value);
        out += buf;
        i = end + 1;
        continue;
      }
    }

    out += c;
    ++i;
  }

  return out;
}

namespace {

int precedence(char op) {
  switch (op) {
  case '+':
  case '-':
    return 1;
  case '*':
  case '/':
    return 2;
  default:
    return 0;
  }
}

bool applyOp(std::stack<double> &values, char op) {
  if (values.size() < 2) {
    return false;
  }
  const double b = values.top();
  values.pop();
  const double a = values.top();
  values.pop();
  switch (op) {
  case '+':
    values.push(a + b);
    break;
  case '-':
    values.push(a - b);
    break;
  case '*':
    values.push(a * b);
    break;
  case '/':
    values.push(b != 0.0 ? a / b : 0.0);
    break;
  default:
    return false;
  }
  return true;
}

} // namespace

bool MathParser::evalArithmetic(const std::string &expr, double &out) {
  std::stack<double> values;
  std::stack<char> ops;
  bool expectOperand = true; // for detecting unary +/-

  for (std::size_t i = 0; i < expr.size();) {
    const char c = expr[i];

    if (std::isspace(static_cast<unsigned char>(c))) {
      ++i;
      continue;
    }

    // Numeric literal (supports decimals). Handle unary sign when an
    // operand is expected.
    if (std::isdigit(static_cast<unsigned char>(c)) || c == '.' ||
        ((c == '+' || c == '-') && expectOperand)) {
      char *endPtr = nullptr;
      const double val = std::strtod(expr.c_str() + i, &endPtr);
      if (endPtr == expr.c_str() + i) {
        return false; // no number parsed
      }
      values.push(val);
      i = static_cast<std::size_t>(endPtr - expr.c_str());
      expectOperand = false;
      continue;
    }

    if (std::isalpha(static_cast<unsigned char>(c))) {
      std::string funcName;
      while (i < expr.size() && std::isalpha(static_cast<unsigned char>(expr[i]))) {
        funcName += std::tolower(expr[i]);
        ++i;
      }
      
      // Skip whitespace before '('
      while (i < expr.size() && std::isspace(static_cast<unsigned char>(expr[i]))) {
          ++i;
      }
      
      if (i < expr.size() && expr[i] == '(') {
        int depth = 1;
        std::size_t j = i + 1;
        while (j < expr.size() && depth > 0) {
          if (expr[j] == '(') ++depth;
          else if (expr[j] == ')') --depth;
          ++j;
        }
        if (depth == 0) {
          std::string innerExpr = expr.substr(i + 1, j - i - 2);
          double innerVal = 0.0;
          if (!evalArithmetic(innerExpr, innerVal)) return false;
          
          if (funcName == "rad") {
            values.push(innerVal * M_PI / 180.0);
          } else if (funcName == "deg") {
            values.push(innerVal * 180.0 / M_PI);
          } else if (funcName == "cos") {
            values.push(std::cos(innerVal));
          } else if (funcName == "sin") {
            values.push(std::sin(innerVal));
          } else {
            return false; // unknown function
          }
          
          i = j;
          expectOperand = false;
          continue;
        }
      }
      return false; // syntax error
    }

    if (c == '(') {
      ops.push(c);
      expectOperand = true;
      ++i;
      continue;
    }

    if (c == ')') {
      while (!ops.empty() && ops.top() != '(') {
        if (!applyOp(values, ops.top())) {
          return false;
        }
        ops.pop();
      }
      if (ops.empty()) {
        return false; // mismatched parenthesis
      }
      ops.pop(); // discard '('
      expectOperand = false;
      ++i;
      continue;
    }

    if (c == '+' || c == '-' || c == '*' || c == '/') {
      while (!ops.empty() && ops.top() != '(' &&
             precedence(ops.top()) >= precedence(c)) {
        if (!applyOp(values, ops.top())) {
          return false;
        }
        ops.pop();
      }
      ops.push(c);
      expectOperand = true;
      ++i;
      continue;
    }

    return false; // unexpected character
  }

  while (!ops.empty()) {
    if (ops.top() == '(') {
      return false;
    }
    if (!applyOp(values, ops.top())) {
      return false;
    }
    ops.pop();
  }

  if (values.size() != 1) {
    return false;
  }
  out = values.top();
  return true;
}

bool MathParser::evaluate(const std::string &expr, double &out) const {
  const std::string resolved = substitute(expr);
  return evalArithmetic(resolved, out);
}

double MathParser::evaluateOr(const std::string &expr, double fallback) const {
  double result = 0.0;
  if (evaluate(expr, result)) {
    return result;
  }
  return fallback;
}
