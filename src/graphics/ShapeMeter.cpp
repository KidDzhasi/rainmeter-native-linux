#include "ShapeMeter.hpp"
#include "engine/SkinInstance.hpp" // For resolveVariables
#include "utils/ColorParser.hpp"
#include <iostream>
#include <sstream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cctype>

#include "evaluator/MathParser.hpp"

#include "engine/SkinInstance.hpp"

using Color = Utils::Color;

void ShapeMeter::Render(const IniLexer &skin, MeasureEvaluator *measures, MathParser *math, NanoVGRenderer &renderer, const std::string &section, double x, double y, double w, double h, double& curWidth, double& curHeight) {
    if (!renderer.valid()) return;

    // 1. Multi-Shape Parsing: Extract up to Shape10 into an ordered list
    std::vector<std::string> parsedShapes;
    for (int i = 1; i <= 10; ++i) {
        std::string key = (i == 1) ? "Shape" : "Shape" + std::to_string(i);
        std::string rawShapeDef = skin.getOr(section, key, "");
        if (rawShapeDef.empty()) {
            if (i == 1) continue;
            break;
        }
        parsedShapes.push_back(SkinInstance::resolveVariables(skin, measures, section, rawShapeDef));
    }

    if (parsedShapes.empty()) return;

    NVGcontext* vg = renderer.context();
    
    double pct = 1.0;
    std::string measureName = skin.getOr(section, "MeasureName", "");
    if (!measureName.empty() && measures && measures->hasMeasure(measureName)) {
        pct = measures->percentValue(measureName);
    }

    // Translate the meter's local coordinate space ONCE per meter
    nvgSave(vg);
    nvgTranslate(vg, static_cast<float>(x), static_cast<float>(y));
    if (pct != 1.0 && pct >= 0.0) {
        nvgScale(vg, static_cast<float>(pct), 1.0f);
    }

    auto toNVG = [](const Color& c) { 
        return nvgRGBA(
            static_cast<unsigned char>(c.r), 
            static_cast<unsigned char>(c.g), 
            static_cast<unsigned char>(c.b), 
            static_cast<unsigned char>(c.a)
        ); 
    };

    // 2. Sequential Rendering: Iterate through the parsed shape definitions
    for (const std::string& shapeDef : parsedShapes) {
        std::vector<std::string> parts;
        std::size_t start = 0;
        while (start < shapeDef.size()) {
            std::size_t end = shapeDef.find('|', start);
            if (end == std::string::npos) end = shapeDef.size();
            std::string part = shapeDef.substr(start, end - start);
            while (!part.empty() && std::isspace(static_cast<unsigned char>(part.front()))) part.erase(0, 1);
            while (!part.empty() && std::isspace(static_cast<unsigned char>(part.back()))) part.pop_back();
            if (!part.empty()) parts.push_back(part);
            start = end + 1;
        }

        if (parts.empty()) continue;

        // SAFE PARAMETER SLICING: Extract geometry before any attribute parsing
        std::string geom = parts[0];
        while (!geom.empty() && std::isspace(static_cast<unsigned char>(geom.front()))) geom.erase(0, 1);
        std::size_t space = geom.find(' ');
        std::string shapeType = geom.substr(0, space);
        std::string argsStr = (space != std::string::npos) ? geom.substr(space + 1) : "";
        
        std::vector<double> args;
        if (shapeType != "Path") {
            std::size_t pstart = 0;
            while (pstart < argsStr.size()) {
                std::size_t pend = argsStr.find(',', pstart);
                if (pend == std::string::npos) pend = argsStr.size();
                std::string arg = argsStr.substr(pstart, pend - pstart);
                while (!arg.empty() && std::isspace(static_cast<unsigned char>(arg.front()))) arg.erase(0, 1);
                while (!arg.empty() && std::isspace(static_cast<unsigned char>(arg.back()))) arg.pop_back();
                // Safely evaluate or fallback to 0.0 to prevent comma crashes
                args.push_back(math->evaluateOr(arg, 0.0));
                pstart = pend + 1;
            }
        }

        // 3. State Reset: Explicit reset of variables per individual shape
        bool hasFill = false;
        bool hasStroke = false;
        Color fill = Utils::ParseColor("0,0,0,255");
        Color stroke = Utils::ParseColor("0,0,0,0");
        double lw = 1.0;
        
        bool hasLinearGrad = false;
        double gradAngle = 0.0;
        Color gradStart = fill, gradEnd = fill;

        // DECOUPLED ATTRIBUTES: Parse attributes globally for ALL shapes
        for (size_t j = 1; j < parts.size(); ++j) {
            std::string mod = parts[j];
            
            // AGGRESSIVE TRIMMING
            while (!mod.empty() && std::isspace(static_cast<unsigned char>(mod.front()))) mod.erase(0, 1);
            while (!mod.empty() && std::isspace(static_cast<unsigned char>(mod.back()))) mod.pop_back();

            if (mod.find("Fill Color") == 0) {
                std::string val = mod.substr(10);
                while (!val.empty() && std::isspace(static_cast<unsigned char>(val.front()))) val.erase(0, 1);
                fill = Utils::ParseColor(val);
                hasFill = true;
            } else if (mod.find("Stroke Color") == 0) {
                std::string val = mod.substr(12);
                while (!val.empty() && std::isspace(static_cast<unsigned char>(val.front()))) val.erase(0, 1);
                stroke = Utils::ParseColor(val);
                hasStroke = true;
            } else if (mod.find("StrokeWidth") == 0) {
                std::string val = mod.substr(11);
                while (!val.empty() && std::isspace(static_cast<unsigned char>(val.front()))) val.erase(0, 1);
                try { lw = std::stod(val); } catch (...) {}
                hasStroke = true;
            } else if (mod.find("Fill LinearGradient") == 0) {
                std::string gradDef = mod.substr(19);
                while (!gradDef.empty() && std::isspace(static_cast<unsigned char>(gradDef.front()))) gradDef.erase(0, 1);
                std::vector<std::string> gp;
                std::size_t p0 = 0;
                while (p0 < gradDef.size()) {
                    std::size_t p1 = gradDef.find('|', p0);
                    if (p1 == std::string::npos) p1 = gradDef.size();
                    std::string gpart = gradDef.substr(p0, p1 - p0);
                    while (!gpart.empty() && std::isspace(static_cast<unsigned char>(gpart.front()))) gpart.erase(0, 1);
                    while (!gpart.empty() && std::isspace(static_cast<unsigned char>(gpart.back()))) gpart.pop_back();
                    if (!gpart.empty()) gp.push_back(gpart);
                    p0 = p1 + 1;
                }
                if (gp.size() >= 3) {
                    hasLinearGrad = true;
                    hasFill = true;
                    gradAngle = math->evaluateOr(gp[0], 0.0);
                    
                    auto parseColorStop = [](const std::string& str) {
                        std::size_t semi = str.find(';');
                        std::string colorStr = (semi == std::string::npos) ? str : str.substr(0, semi);
                        while (!colorStr.empty() && std::isspace(static_cast<unsigned char>(colorStr.front()))) colorStr.erase(0, 1);
                        while (!colorStr.empty() && std::isspace(static_cast<unsigned char>(colorStr.back()))) colorStr.pop_back();
                        return Utils::ParseColor(colorStr);
                    };
                    
                    gradStart = parseColorStop(gp[1]);
                    gradEnd = parseColorStop(gp.back());
                }
            }
        }

        if (!hasFill && !hasStroke) {
            hasFill = true;
        }

        double localW = 0.0;
        double localH = 0.0;

        if (shapeType == "Rectangle" && args.size() >= 4) {
            double sx = args[0];
            double sy = args[1];
            double sw = args[2];
            double sh = args[3];
            double radius = (args.size() >= 5) ? args[4] : 0.0;
            
            // STRICT ISOLATION: Clear path immediately before drawing the primitive
            nvgBeginPath(vg);
            if (radius > 0) nvgRoundedRect(vg, sx, sy, sw, sh, radius);
            else nvgRect(vg, sx, sy, sw, sh);
            
            localW = args[0] + sw;
            localH = args[1] + sh;
            
        } else if (shapeType == "Ellipse" && args.size() >= 3) {
            double cx = args[0];
            double cy = args[1];
            double rx = args[2];
            double ry = (args.size() >= 4) ? args[3] : rx;
            
            // STRICT ISOLATION: Clear path immediately before drawing the primitive
            nvgBeginPath(vg);
            nvgEllipse(vg, cx, cy, rx, ry);
            
            localW = args[0] + rx;
            localH = args[1] + ry;
            
        } else if (shapeType == "Polygon" && args.size() >= 2) {
            nvgBeginPath(vg);
            nvgMoveTo(vg, args[0], args[1]);
            localW = std::max(localW, args[0]);
            localH = std::max(localH, args[1]);
            
            for (size_t i = 2; i + 1 < args.size(); i += 2) {
                nvgLineTo(vg, args[i], args[i+1]);
                localW = std::max(localW, args[i]);
                localH = std::max(localH, args[i+1]);
            }
            
            for (size_t j = 1; j < parts.size(); ++j) {
                std::string part = parts[j];
                while (!part.empty() && std::isspace(static_cast<unsigned char>(part.front()))) part.erase(0, 1);
                
                if (part.find("Fill") == 0 || part.find("Stroke") == 0 || 
                    part.find("Extend") == 0 || part.find("Rotate") == 0 || 
                    part.find("Scale") == 0 || part.find("Skew") == 0 || 
                    part.find("Offset") == 0 || part.find("Matrix") == 0) {
                    continue;
                }
                
                std::vector<double> vargs;
                std::size_t ps = 0;
                while (ps < part.size()) {
                    std::size_t pe = part.find(',', ps);
                    if (pe == std::string::npos) pe = part.size();
                    std::string arg = part.substr(ps, pe - ps);
                    vargs.push_back(math->evaluateOr(arg, 0.0));
                    ps = pe + 1;
                }
                
                for (size_t i = 0; i + 1 < vargs.size(); i += 2) {
                    nvgLineTo(vg, vargs[i], vargs[i+1]);
                    localW = std::max(localW, vargs[i]);
                    localH = std::max(localH, vargs[i+1]);
                }
            }
            
            nvgClosePath(vg);
            
        } else if (shapeType == "Path") {
            std::string pathName = argsStr;
            std::string rawPathDef = skin.getOr(section, pathName, "");
            std::string pathDef = SkinInstance::resolveVariables(skin, measures, section, rawPathDef);
            
            std::vector<std::string> pathCmds;
            std::size_t startCmd = 0;
            while (startCmd < pathDef.size()) {
                std::size_t endCmd = pathDef.find('|', startCmd);
                if (endCmd == std::string::npos) endCmd = pathDef.size();
                std::string cmd = pathDef.substr(startCmd, endCmd - startCmd);
                while (!cmd.empty() && std::isspace(cmd.front())) cmd.erase(0, 1);
                while (!cmd.empty() && std::isspace(cmd.back())) cmd.pop_back();
                if (!cmd.empty()) pathCmds.push_back(cmd);
                startCmd = endCmd + 1;
            }
            
            if (!pathCmds.empty()) {
                auto parseArgs = [&](const std::string& argStr) {
                    std::vector<double> res;
                    std::size_t ps = 0;
                    while (ps < argStr.size()) {
                        std::size_t pe = argStr.find(',', ps);
                        if (pe == std::string::npos) pe = argStr.size();
                        std::string arg = argStr.substr(ps, pe - ps);
                        res.push_back(math->evaluateOr(arg, 0.0));
                        ps = pe + 1;
                    }
                    return res;
                };

                // The first command in a Path is implicitly the starting coordinate
                std::vector<double> startCoord = parseArgs(pathCmds[0]);
                if (startCoord.size() >= 2) {
                    // STRICT ISOLATION: Clear path immediately before drawing the primitive
                    nvgBeginPath(vg);
                    nvgMoveTo(vg, startCoord[0], startCoord[1]);
                    localW = std::max(localW, startCoord[0]);
                    localH = std::max(localH, startCoord[1]);
                }

                for (size_t k = 1; k < pathCmds.size(); ++k) {
                    std::string cmd = pathCmds[k];
                    std::size_t sp = cmd.find(' ');
                    std::string ctype = cmd.substr(0, sp);
                    std::string cargsStr = (sp != std::string::npos) ? cmd.substr(sp + 1) : "";
                    std::vector<double> ca = parseArgs(cargsStr);

                    if (ctype == "LineTo" && ca.size() >= 2) {
                        nvgLineTo(vg, ca[0], ca[1]);
                        localW = std::max(localW, ca[0]);
                        localH = std::max(localH, ca[1]);
                    } else if (ctype == "CurveTo" && ca.size() >= 6) {
                        nvgBezierTo(vg, ca[2], ca[3], ca[4], ca[5], ca[0], ca[1]);
                        localW = std::max(localW, ca[0]);
                        localH = std::max(localH, ca[1]);
                    } else if (ctype == "ClosePath") {
                        nvgClosePath(vg);
                    }
                }
            }
        }
        
        if (hasFill) {
            if (hasLinearGrad) {
                float angle_rad = gradAngle * (M_PI / 180.0f);
                float cx = localW / 2.0f;
                float cy = localH / 2.0f;
                
                float L = std::abs(localW * std::cos(angle_rad)) + std::abs(localH * std::sin(angle_rad));
                if (L < 1.0f) L = std::max(localW, localH);

                float gsx = cx - (L * 0.5f) * std::cos(angle_rad);
                float gsy = cy - (L * 0.5f) * std::sin(angle_rad);
                float gex = cx + (L * 0.5f) * std::cos(angle_rad);
                float gey = cy + (L * 0.5f) * std::sin(angle_rad);
                
                NVGpaint paint = nvgLinearGradient(vg, gsx, gsy, gex, gey, toNVG(gradStart), toNVG(gradEnd));
                nvgFillPaint(vg, paint);
            } else {
                nvgFillColor(vg, toNVG(fill));
            }
            nvgFill(vg);
        }

        if (hasStroke) {
            nvgStrokeColor(vg, toNVG(stroke));
            nvgStrokeWidth(vg, lw);
            nvgStroke(vg);
        }

        // Map local bounding size back to the global tracker
        curWidth = std::max(curWidth, localW);
        curHeight = std::max(curHeight, localH);
    }
    
    // Restore the meter's global context after all sequential shapes are drawn
    nvgRestore(vg);
}
