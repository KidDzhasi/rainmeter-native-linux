#pragma once

#include "NanoVGRenderer.hpp"
#include "parser/IniLexer.hpp"
#include "evaluator/MeasureEvaluator.hpp"

class MathParser;

class ShapeMeter {
public:
    static void Render(const IniLexer &skin, MeasureEvaluator *measures, MathParser *math, NanoVGRenderer &renderer, const std::string &section, double x, double y, double w, double h, double& curWidth, double& curHeight);
};
