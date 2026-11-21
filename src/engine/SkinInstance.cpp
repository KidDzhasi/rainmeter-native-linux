#include "engine/SkinInstance.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>

#include <linux/input-event-codes.h>

#include <filesystem>
namespace fs = std::filesystem;

#include "evaluator/CommandProcessor.hpp"
#include "evaluator/ThemeParser.hpp"
#include "graphics/TransformManager.hpp"
#include "graphics/ShapeMeter.hpp"
#include "parser/IniLexer.hpp"
#include "utils/PathResolver.hpp"
namespace {
constexpr int kDefaultWidth = 260;
constexpr int kDefaultHeight = 200;
} // namespace

// ---------------------------------------------------------------------------
// Static helper functions (migrated from main.cpp anonymous namespace)
// ---------------------------------------------------------------------------

double SkinInstance::resolveNum(const IniLexer &skin, const MeasureEvaluator *measures, const MathParser &math,
                               const std::string &section,
                               const std::string &key, double def) {
  const std::string raw = skin.getOr(section, key, "");
  if (raw.empty()) {
    return def;
  }
  std::string resolved = resolveVariables(skin, measures, section, raw);
  if (!resolved.empty() && resolved.front() == '(' && resolved.back() == ')') {
      resolved = resolved.substr(1, resolved.size() - 2);
  }
  return math.evaluateOr(resolved, def);
}

std::string SkinInstance::getKeyCI(const IniLexer &skin,
                                   const std::string &section,
                                   const std::string &key) {
  std::string v = skin.getOr(section, key, "");
  if (!v.empty()) {
    return v;
  }
  std::string alt = key;
  for (char &c : alt) {
    c = (c >= 'a' && c <= 'z') ? static_cast<char>(c - 'a' + 'A')
                               : static_cast<char>(c - 'A' + 'a');
  }
  return skin.getOr(section, alt, "");
}

double SkinInstance::resolveCoord(const IniLexer &skin, const MeasureEvaluator *measures, const MathParser &math,
                                 const std::string &section,
                                 const std::string &key, double relBase,
                                 double relStack, double def) {
  std::string raw = getKeyCI(skin, section, key);
  while (!raw.empty() && (raw.back() == ' ' || raw.back() == '\t')) {
    raw.pop_back();
  }
  if (raw.empty()) {
    return def;
  }

  char suffix = 0;
  if (raw.back() == 'r' || raw.back() == 'R') {
    suffix = raw.back();
    raw.pop_back();
    while (!raw.empty() && (raw.back() == ' ' || raw.back() == '\t')) {
      raw.pop_back();
    }
  }

  std::string resolved = resolveVariables(skin, measures, section, raw);
  if (!resolved.empty() && resolved.front() == '(' && resolved.back() == ')') {
      resolved = resolved.substr(1, resolved.size() - 2);
  }

  const double value = math.evaluateOr(resolved, 0.0);
  if (suffix == 'r') {
    return relBase + value;
  }
  if (suffix == 'R') {
    return relStack + value;
  }
  return value;
}

NanoVGRenderer::TextAlign SkinInstance::parseAlign(const std::string &spec) {
  if (spec == "CenterCenter" || spec == "CENTERCENTER" ||
      spec == "centercenter") {
    return NanoVGRenderer::TextAlign::CenterCenter;
  }
  if (spec == "Center" || spec == "CENTER" || spec == "center") {
    return NanoVGRenderer::TextAlign::Center;
  }
  if (spec == "Right" || spec == "RIGHT" || spec == "right") {
    return NanoVGRenderer::TextAlign::Right;
  }
  return NanoVGRenderer::TextAlign::Left;
}

std::string SkinInstance::resolveVariables(const IniLexer &skin,
                                          const MeasureEvaluator *measures,
                                          const std::string &section,
                                          const std::string &text) {
  std::string out;
  out.reserve(text.size());
  for (std::size_t i = 0; i < text.size();) {
    if (text[i] == '#') {
      const std::size_t close = text.find('#', i + 1);
      if (close != std::string::npos && close > i + 1) {
        const std::string name = text.substr(i + 1, close - i - 1);

        if (name == "CURRENTSECTION" || name == "CURRENT_SECTION") {
          out += section;
          i = close + 1;
          continue;
        }

        auto value = skin.getCaseInsensitive("Variables", name);
        if (value) {
          out += *value;
          i = close + 1;
          continue;
        }
      }
    } else if (measures && text[i] == '[') {
      const std::size_t close = text.find(']', i + 1);
      if (close != std::string::npos && close > i + 1) {
        const std::string name = text.substr(i + 1, close - i - 1);
        if (measures->hasMeasure(name)) {
          out += measures->value(name);
          i = close + 1;
          continue;
        }
      }
    }
    out += text[i];
    ++i;
  }
  return out;
}

std::string SkinInstance::resolveImagePath(const IniLexer &skin,
                                          const MeasureEvaluator *measures,
                                          const std::string &section,
                                          const std::string &iniPath) {
  std::string rawImageName = skin.getOr(section, "ImageName", "");
  std::string imageName = resolveVariables(skin, measures, section, rawImageName);
  
  if (imageName.empty()) {
      std::string mName = skin.getOr(section, "MeasureName", "");
      if (!mName.empty() && measures && measures->hasMeasure(mName)) {
          imageName = measures->value(mName);
      }
  }

  if (imageName.empty()) {
    return "";
  }
  // Normalize Windows backslashes.
  std::replace(imageName.begin(), imageName.end(), '\\', '/');

  if (imageName.front() == '/') {
    return imageName;
  }

  std::string imagePath = skin.getOr(section, "ImagePath", "");
  std::replace(imagePath.begin(), imagePath.end(), '\\', '/');
  fs::path skinDir = fs::path(iniPath).parent_path();

  if (!imagePath.empty()) {
    fs::path tryPath = skinDir / imagePath / imageName;
    if (fs::exists(tryPath))
      return tryPath.string();
    
    // Case-insensitive fallback: resolve both imagePath and imageName relative to skinDir
    std::string ciPath = IniLexer::resolveCaseInsensitivePath(
        skinDir.string(), (fs::path(imagePath) / imageName).string());
    if (fs::exists(ciPath))
      return ciPath;
  }

  fs::path tryPath1 = skinDir / imageName;
  if (fs::exists(tryPath1))
    return tryPath1.string();

  // Case-insensitive fallback for skinDir/imageName
  std::string ciPath1 =
      IniLexer::resolveCaseInsensitivePath(skinDir.string(), imageName);
  if (fs::exists(ciPath1))
    return ciPath1;

  fs::path curr = skinDir;
  while (curr != curr.parent_path() && curr.string() != "/") {
    fs::path resPath = curr / "@Resources" / "Images" / imageName;
    if (fs::exists(resPath))
      return resPath.string();
    // Case-insensitive fallback for @Resources/Images/imageName
    std::string ciRes = IniLexer::resolveCaseInsensitivePath(
        (curr / "@Resources" / "Images").string(), imageName);
    if (fs::exists(ciRes))
      return ciRes;
    curr = curr.parent_path();
  }

  return tryPath1.string();
}

// ---------------------------------------------------------------------------
// paintScene — renders all meters for this skin instance
// ---------------------------------------------------------------------------

void SkinInstance::paintScene() {
  using Color = Utils::Color;

  meterBounds_.clear();
  renderer_.clear(Color{0.0, 0.0, 0.0, 0.0});

  const std::string fontName = skin_.getOr("Variables", "fontName", "sans");
  const Color textColor =
      Utils::ParseColor(skin_.getOr("Variables", "colorText", "255,255,255,255"));
  const std::string rawColorBar =
      skin_.getOr("Variables", "colorBar", "235,170,0,255");
  const Color barColor =
      Utils::ParseColor(resolveVariables(skin_, &measures_, "Variables", rawColorBar));
  const Color trackColor{255.0, 255.0, 255.0, 30.6};

  double prevX = 0.0;
  double prevY = 0.0;
  double prevWidth = 0.0;
  double prevHeight = 0.0;

  TransformManager transformManager;

  // --- Z-ORDER FIX: Preserve INI File Top-to-Bottom Layout ---
  // Rainmeter natively draws meters in the exact order they appear in the .ini file.
  // We iterate over sectionOrder() to guarantee backgrounds are drawn before overlays.
  for (const std::string& sectionName : skin_.sectionOrder()) {
    auto dataIt = skin_.data().find(sectionName);
    if (dataIt == skin_.data().end()) continue;
    
    const auto& section = dataIt->first;
    const auto& keys = dataIt->second;
    
    auto meterIt = keys.find("Meter");
    if (meterIt == keys.end()) {
      continue;
    }
    const std::string &type = meterIt->second;

    const std::string hiddenStr = resolveVariables(skin_, &measures_, section, skin_.getOr(section, "Hidden", "0"));
    bool isHidden = (math_->evaluateOr(hiddenStr, 0.0) != 0.0);

    const double x =
        resolveCoord(skin_, &measures_, *math_, section, "X", prevX, prevX + prevWidth, 0);
    const double y =
        resolveCoord(skin_, &measures_, *math_, section, "Y", prevY, prevY + prevHeight, 0);
    const double w = resolveNum(skin_, &measures_, *math_, section, "W", 0);
    const double h = resolveNum(skin_, &measures_, *math_, section, "H", 0);

    double curWidth = w;
    double curHeight = h;

    if (isHidden) {
        prevX = 0.0;
        prevY = 0.0;
        prevWidth = 0.0;
        prevHeight = 0.0;
        continue;
    }

    std::string transformStr = skin_.getOr(section, "TransformationMatrix", "");
    transformManager.parse(transformStr);
    renderer_.save();
    renderer_.setTransform(transformManager.toNanoVG());

    double actualX = x;
    double actualY = y;

    if (type == "String") {
      std::vector<std::string> measureValues;
      for (int idx = 1;; ++idx) {
        const std::string key =
            (idx == 1) ? "MeasureName"
                       : "MeasureName" + std::to_string(idx);
        const std::string mName = skin_.getOr(section, key, "");
        if (mName.empty()) {
          break;
        }
        measureValues.push_back(measures_.value(mName));
      }

      std::string out;
      const std::string rawTemplate = skin_.getOr(section, "Text", "%1");
          const std::string textTemplate =
              resolveVariables(skin_, &measures_, section, rawTemplate);
          out = NanoVGRenderer::substituteText(textTemplate, measureValues);

      auto stripQuotes = [](std::string& str) {
          while (str.find("\"\"\"") != std::string::npos) {
              str.replace(str.find("\"\"\""), 3, "");
          }
          while (str.find("\"") != std::string::npos) {
              str.replace(str.find("\""), 1, "");
          }
      };
      stripQuotes(out);
      const double fontSize =
          resolveNum(skin_, &measures_, *math_, section, "FontSize", 12.0);

      Color color = textColor;
      const std::string fcRaw = skin_.getOr(section, "FontColor", "");
      const std::string fc = resolveVariables(skin_, &measures_, section, fcRaw);
      if (!fc.empty()) {
        color = Utils::ParseColor(fc);
      }
      const NanoVGRenderer::TextAlign align =
          parseAlign(skin_.getOr(section, "StringAlign", "Left"));
      const std::string meterFontFace =
          skin_.getOr(section, "FontFace", fontName);
      const double angle =
          resolveNum(skin_, &measures_, *math_, section, "Angle", 0.0);

      NanoVGRenderer::TextEffect effect;
      std::string inlineSettingRaw = skin_.getOr(section, "InlineSetting", "");
      std::string inlineSetting = resolveVariables(skin_, &measures_, section, inlineSettingRaw);
      if (inlineSetting.find("Shadow") == 0) {
          effect.shadowEnabled = true;
          // Format: Shadow | X | Y | Blur | Color
          std::vector<std::string> sp;
          std::size_t p0 = 0;
          while (p0 < inlineSetting.size()) {
              std::size_t p1 = inlineSetting.find('|', p0);
              if (p1 == std::string::npos) p1 = inlineSetting.size();
              std::string s = inlineSetting.substr(p0, p1 - p0);
              while (!s.empty() && std::isspace(s.front())) s.erase(0, 1);
              while (!s.empty() && std::isspace(s.back())) s.pop_back();
              if (!s.empty()) sp.push_back(s);
              p0 = p1 + 1;
          }
          if (sp.size() >= 2) effect.shadowX = math_->evaluateOr(sp[1], 0.0);
          if (sp.size() >= 3) effect.shadowY = math_->evaluateOr(sp[2], 0.0);
          if (sp.size() >= 4) effect.shadowBlur = math_->evaluateOr(sp[3], 0.0);
          if (sp.size() >= 5) effect.shadowColor = Utils::ParseColor(sp[4]);
      } else if (inlineSetting.find("GradientColor") == 0) {
          std::vector<std::string> sp;
          std::size_t p0 = 0;
          while (p0 < inlineSetting.size()) {
              std::size_t p1 = inlineSetting.find('|', p0);
              if (p1 == std::string::npos) p1 = inlineSetting.size();
              std::string s = inlineSetting.substr(p0, p1 - p0);
              while (!s.empty() && std::isspace(s.front())) s.erase(0, 1);
              while (!s.empty() && std::isspace(s.back())) s.pop_back();
              if (!s.empty()) sp.push_back(s);
              p0 = p1 + 1;
          }
          // sp[0] = "GradientColor", sp[1] = angle, sp[2..n] = "Color ; pos"
          if (sp.size() >= 3) {
              effect.gradientEnabled = true;
              effect.gradientAngle = math_->evaluateOr(sp[1], 0.0);
              
              auto parseColorStop = [&](const std::string& str) {
                  // Strip the optional "; position" suffix.
                  std::size_t semi = str.find(';');
                  std::string colorStr = (semi == std::string::npos) ? str : str.substr(0, semi);
                  // Trim whitespace from the isolated color token.
                  while (!colorStr.empty() && std::isspace(colorStr.front())) colorStr.erase(0, 1);
                  while (!colorStr.empty() && std::isspace(colorStr.back())) colorStr.pop_back();
                  return Utils::ParseColor(colorStr);
              };
              
              effect.gradientStartColor = parseColorStop(sp[2]);
              effect.gradientEndColor = parseColorStop(sp.back());
          }
      }

      int clipString = static_cast<int>(resolveNum(skin_, &measures_, *math_, section, "ClipString", 0.0));

      NanoVGRenderer::TextMetrics tm = renderer_.drawText(out, x, y, meterFontFace, fontSize, color, align, angle, &effect, w, h, clipString);

      curWidth = (w > 0) ? w : tm.width;
      curHeight = (h > 0) ? h : tm.height;

      if (align == NanoVGRenderer::TextAlign::Center || align == NanoVGRenderer::TextAlign::CenterCenter) {
          actualX -= (curWidth / 2.0);
      } else if (align == NanoVGRenderer::TextAlign::Right) {
          actualX -= curWidth;
      }

      if (align == NanoVGRenderer::TextAlign::CenterCenter) {
          actualY -= (curHeight / 2.0);
      }

    } else if (type == "Image") {
      const std::string path = resolveImagePath(skin_, &measures_, section, iniPath_);
      if (!path.empty()) {
        int preserveAspectRatio = static_cast<int>(
            resolveNum(skin_, &measures_, *math_, section, "PreserveAspectRatio", 0.0));
        auto im =
            renderer_.drawImage(path, x, y, w, h, preserveAspectRatio);
        if (im.success) {
          curWidth = im.width;
          curHeight = im.height;
        }
      } else {
        curWidth = w > 0 ? w : 32;
        curHeight = h > 0 ? h : 32;
        Color fillColor = {0, 0, 0, 0};
        std::string scRaw = skin_.getOr(section, "SolidColor", "");
        if (!scRaw.empty()) {
          std::string scSpec = resolveVariables(skin_, &measures_, section, scRaw);
          if (!scSpec.empty()) fillColor = Utils::ParseColor(scSpec);
        }
        double cornerRadius = resolveNum(skin_, &measures_, *math_, section, "CornerRadius", 0.0);
        
        if (fillColor.a > 0.0) {
          Color emptyStroke = {0, 0, 0, 0};
          renderer_.drawRectangle(x, y, curWidth, curHeight, cornerRadius, fillColor, emptyStroke, 0.0);
        } else {
          renderer_.strokeRect(x, y, curWidth, curHeight, 1.0, textColor);
        }
      }

    } else if (type == "Shape") {
        ShapeMeter::Render(skin_, &measures_, math_.get(), renderer_, section, x, y, w, h, curWidth, curHeight);
    } else if (type == "Bar") {
      const std::string measureName =
          skin_.getOr(section, "MeasureName", "");
      const double pct =
          measureName.empty() ? 0.0 : measures_.percentValue(measureName);

      Color bc = barColor;
      const std::string bcRaw = skin_.getOr(section, "BarColor", "");
      const std::string bcSpec = resolveVariables(skin_, &measures_, section, bcRaw);
      if (!bcSpec.empty()) {
        bc = Utils::ParseColor(bcSpec);
      }

      Color sc = trackColor;
      const std::string scRaw = skin_.getOr(section, "SolidColor", "");
      const std::string scSpec = resolveVariables(skin_, &measures_, section, scRaw);
      if (!scSpec.empty()) {
        sc = Utils::ParseColor(scSpec);
      }

      const std::string orientation =
          skin_.getOr(section, "BarOrientation", "Horizontal");
      std::string lowerOrientation = orientation;
      for (char &c : lowerOrientation) {
        if (c >= 'A' && c <= 'Z')
          c = static_cast<char>(c - 'A' + 'a');
      }
      bool horizontal = (lowerOrientation != "vertical");

      curWidth = w > 0 ? w : 200;
      curHeight = h > 0 ? h : 12;
      renderer_.drawBar(x, y, curWidth, curHeight, pct, bc, sc, horizontal);
    } else if (type == "Roundline") {
      const std::string measureName = skin_.getOr(section, "MeasureName", "");
      const double pct = measureName.empty() ? 1.0 : measures_.percentValue(measureName);

      double startAngle = resolveNum(skin_, &measures_, *math_, section, "StartAngle", 0.0);
      double rotationAngleBase = resolveNum(skin_, &measures_, *math_, section, "RotationAngle", 0.0);
      double lineLength = resolveNum(skin_, &measures_, *math_, section, "LineLength", 0.0);
      double lineStart = resolveNum(skin_, &measures_, *math_, section, "LineStart", 0.0);
      bool solid = resolveNum(skin_, &measures_, *math_, section, "Solid", 0.0) != 0.0;

      Color lineColor = textColor;
      const std::string lcRaw = skin_.getOr(section, "LineColor", "");
      const std::string lcSpec = resolveVariables(skin_, &measures_, section, lcRaw);
      if (!lcSpec.empty()) {
        lineColor = Utils::ParseColor(lcSpec);
      }

      double activeRotation = rotationAngleBase * pct;

      curWidth = w > 0 ? w : lineLength * 2.0;
      curHeight = h > 0 ? h : lineLength * 2.0;
      renderer_.drawRoundline(x, y, curWidth, curHeight, startAngle, activeRotation, lineLength, lineStart, lineColor, solid);
    }

    renderer_.resetScissor();
    renderer_.restore();

    prevX = actualX;
    prevY = actualY;
    prevWidth = curWidth;
    prevHeight = curHeight;

    meterBounds_.push_back({section, actualX, actualY, curWidth, curHeight});
  }

  // Draw InputText overlay if active and belongs to this skin instance
  if (g_InputState.active && (g_InputState.skinInstance == nullptr || g_InputState.skinInstance == this)) {
      renderer_.save();
      
      // Background box
      Color sc = Utils::ParseColor(g_InputState.solidColor);
      renderer_.clearRect(g_InputState.x, g_InputState.y, g_InputState.w, g_InputState.h);
      renderer_.fillRect(g_InputState.x, g_InputState.y, g_InputState.w, g_InputState.h, sc);
      
      // Text
      std::string out = g_InputState.buffer;
      if (out.empty()) out = " "; // Prevent empty string issues
      Color fc = Utils::ParseColor(g_InputState.fontColor);
      
      renderer_.drawText(out, g_InputState.x, g_InputState.y, g_InputState.fontFace, g_InputState.fontSize, fc, NanoVGRenderer::TextAlign::Left);
      
      renderer_.resetScissor();
      renderer_.restore();
  }
}

// ---------------------------------------------------------------------------
// Load — factory method
// ---------------------------------------------------------------------------

std::unique_ptr<SkinInstance> SkinInstance::Load(const std::string &rawIniPath, int overrideMonitor) {
  std::unique_ptr<SkinInstance> inst(new SkinInstance());

  std::string iniPath = rawIniPath;
  int tagMonitor = -1;
  const std::size_t atPos = rawIniPath.rfind('@');
  if (atPos != std::string::npos && atPos > 4) {
    const std::string suffix = rawIniPath.substr(atPos + 1);
    bool allDigits = !suffix.empty();
    for (char c : suffix) {
      if (c < '0' || c > '9') {
        allDigits = false;
        break;
      }
    }
    if (allDigits) {
      iniPath = rawIniPath.substr(0, atPos);
      try {
        tagMonitor = std::stoi(suffix);
      } catch (...) {
        tagMonitor = -1;
      }
    }
  }
  inst->iniPath_ = iniPath;

  // Pre-load common resource files to ensure wildcards and globals are available
  // before the main skin file is evaluated, so the main skin takes precedence.
  std::string parentDir = std::filesystem::path(iniPath).parent_path().string();
  std::string resPath = (std::filesystem::path(parentDir) / "@Resources").string();
  if (!std::filesystem::exists(resPath)) {
      resPath = ""; // fallback computed later
  }

  if (!resPath.empty()) {
      std::string varsInc = (std::filesystem::path(resPath) / "Variables.inc").string();
      std::string confInc = (std::filesystem::path(resPath) / "Config.inc").string();
      if (std::filesystem::exists(varsInc)) inst->skin_.parseFile(varsInc, false);
      if (std::filesystem::exists(confInc)) inst->skin_.parseFile(confInc, false);
  }

  if (!inst->skin_.parseFile(iniPath, false)) {
    std::cerr << "SkinInstance: could not open '" << iniPath << "'\n";
    return nullptr;
  }

  // Apply user-writable Theme.inc and Weather.inc overrides (essential for read-only /usr/share APT installs)
  std::string userThemeInc = Utils::ResolvePath("~/.config/rainmeter-native/Theme.inc");
  if (fs::exists(userThemeInc) && (iniPath.find("widgets/") != std::string::npos || iniPath.find("/widgets/") != std::string::npos)) {
    inst->skin_.parseFile(userThemeInc, false);
  }
  std::string userWeatherInc = Utils::ResolvePath("~/.config/rainmeter-native/Weather.inc");
  if (fs::exists(userWeatherInc)) {
    inst->skin_.parseFile(userWeatherInc, false);
  }

  inst->measures_.loadFrom(inst->skin_);

  const std::string resources = inst->skin_.resourcesPath();
  if (!resources.empty()) {
    inst->fontsDir_ =
        ThemeParser::resolveCaseInsensitivePath(resources, "Fonts");
  }
  if (inst->fontsDir_.empty() || !fs::exists(inst->fontsDir_)) {
    fs::path localFonts =
        fs::path(iniPath).parent_path() / "@Resources" / "Fonts";
    if (fs::exists(localFonts)) {
      inst->fontsDir_ = localFonts.string();
    }
  }

  IniLexer *skinPtr = &inst->skin_;
  MeasureEvaluator *measPtr = &inst->measures_;
  inst->math_ = std::make_unique<MathParser>(
      [skinPtr](const std::string &name) {
        return skinPtr->getOr("Variables", name, "0");
      },
      [measPtr](const std::string &name) {
        return measPtr->numericValue(name);
      });

  if (!inst->window_.connect()) {
    std::cerr << "SkinInstance '" << iniPath
              << "': could not connect to a Wayland compositor.\n";
    return nullptr;
  }

  // Set up mouse callback — captures raw pointer to this instance.
  SkinInstance *raw = inst.get();
  inst->window_.setMouseCallback(
      [raw](double x, double y, uint32_t button) {
        if (button != BTN_LEFT)
          return;
        std::lock_guard<std::mutex> lock(raw->stateMutex_);
        const double invScale =
            (raw->effectiveScale_ > 0.0) ? (1.0 / raw->effectiveScale_) : 1.0;
        const double sx = x * invScale;
        const double sy = y * invScale;
        
        // Z-ORDER ITERATION: Iterate top-to-bottom so foreground elements intercept clicks first.
        for (auto it = raw->meterBounds_.rbegin();
             it != raw->meterBounds_.rend(); ++it) {
          
          // COLLISION DETECTION: Check if click falls within absolute screen-space bounds
          if (sx >= it->x && sx <= it->x + it->w && sy >= it->y &&
              sy <= it->y + it->h) {
            
            std::string actionName = "";
            std::string actionString = "";

            auto actionUpOpt = raw->skin_.getCaseInsensitive(it->section, "LeftMouseUpAction");
            if (actionUpOpt && !actionUpOpt->empty()) {
                actionName = "LeftMouseUpAction";
                actionString = *actionUpOpt;
            } else {
                auto actionDblOpt = raw->skin_.getCaseInsensitive(it->section, "LeftMouseDoubleClickAction");
                if (actionDblOpt && !actionDblOpt->empty()) {
                    actionName = "LeftMouseDoubleClickAction";
                    actionString = *actionDblOpt;
                }
            }

            if (!actionString.empty()) {
              size_t pos = actionString.find("$MouseX:%$");
              if (pos != std::string::npos) {
                  double percent = ((sx - it->x) / it->w) * 100.0;
                  actionString.replace(pos, 10, std::to_string(percent));
              }
              
              std::cout << "[Click Zone] Triggered " << actionName << " on " << it->section << ": " << actionString << std::endl;
              
              // External commands (http:// or standard shell actions) are handled securely inside execute()
              BangResult res = CommandProcessor::execute(actionString, raw->skin_,
                                                        raw->measures_, raw);
              if (res.needsUpdate)
                raw->forceUpdate_ = true;
              if (res.needsRedraw)
                raw->forceRedraw_ = true;
              break;
            }
          }
        }
      });

  // Calculate ConfigName for global layout (prefer exact @monitor section if present)
  std::string configName = rawIniPath;
  std::string skinsPath = fs::path(Utils::ResolvePath("~/.config/rainmeter-native/Skins")).lexically_normal().string();
  std::string absoluteIni = fs::absolute(Utils::ResolvePath(iniPath)).lexically_normal().string();
  
  std::string rainmeterIniPath = Utils::ResolvePath("~/.config/rainmeter-native/Rainmeter.ini");
  IniLexer globalConfig(rainmeterIniPath);
  if (globalConfig.data().find(configName) == globalConfig.data().end()) {
    std::string wantedSuffix = (tagMonitor >= 0) ? ("@" + std::to_string(tagMonitor)) : "";
    bool matched = false;
    if (!wantedSuffix.empty()) {
      for (const auto &sec : globalConfig.sectionOrder()) {
        if (sec.size() > wantedSuffix.size() &&
            sec.compare(sec.size() - wantedSuffix.size(), wantedSuffix.size(), wantedSuffix) == 0) {
          std::string baseSec = sec.substr(0, sec.size() - wantedSuffix.size());
          if (baseSec == iniPath || absoluteIni.find(baseSec) != std::string::npos) {
            configName = sec;
            matched = true;
            break;
          }
        }
      }
    }
    if (!matched) {
      if (globalConfig.data().find(iniPath) != globalConfig.data().end()) {
        configName = iniPath;
      } else {
        for (const auto &sec : globalConfig.sectionOrder()) {
          if (sec == iniPath || absoluteIni.find(sec) != std::string::npos) {
            configName = sec;
            break;
          }
        }
      }
    }
  }

  std::string monitorStr = globalConfig.getOr(
      configName, "Monitor", getKeyCI(inst->skin_, "Rainmeter", "@Monitor"));
  if (monitorStr.empty()) monitorStr = "0";
  int monitorIndex = overrideMonitor >= 0
                         ? overrideMonitor
                         : (tagMonitor >= 0
                                ? tagMonitor
                                : static_cast<int>(inst->math_->evaluateOr(monitorStr, 0)));
  if (inst->window_.getMonitorCount() > 0) {
    monitorIndex = std::clamp(monitorIndex, 0, inst->window_.getMonitorCount() - 1);
  }
  inst->monitorIndex_ = monitorIndex;

  int screenWidth = inst->window_.getScreenWidth(monitorIndex);
  int screenHeight = inst->window_.getScreenHeight(monitorIndex);
  
  // Inject into global config for layout calculations
  globalConfig.setVariable("SCREENAREAWIDTH", std::to_string(screenWidth));
  globalConfig.setVariable("SCREENAREAHEIGHT", std::to_string(screenHeight));
  
  // Also inject into the local skin so all meters have access
  inst->skin_.setVariable("SCREENAREAWIDTH", std::to_string(screenWidth));
  inst->skin_.setVariable("SCREENAREAHEIGHT", std::to_string(screenHeight));

  std::string autoFitStr = globalConfig.getOr(
      configName, "AutoFit", getKeyCI(inst->skin_, "Rainmeter", "AutoFit"));
  if (autoFitStr.empty() && iniPath.find("suites/") != std::string::npos) {
    autoFitStr = "1";
  }
  inst->autoFit_ = (autoFitStr == "1" || autoFitStr == "true" || autoFitStr == "True");

  std::string scaleStr = globalConfig.getOr(
      configName, "Scale", getKeyCI(inst->skin_, "Rainmeter", "Scale"));
  if (!scaleStr.empty()) {
    inst->userScale_ = inst->math_->evaluateOr(scaleStr, 0.0);
  }

  double targetW = inst->math_->evaluateOr(
      inst->skin_.getOr("Rainmeter", "SkinWidth", ""), 0);
  double targetH = inst->math_->evaluateOr(
      inst->skin_.getOr("Rainmeter", "SkinHeight", ""), 0);
  if (targetW <= 0 || targetH <= 0) {
    double estMaxX = kDefaultWidth;
    double estMaxY = kDefaultHeight;
    for (const std::string &secName : inst->skin_.sectionOrder()) {
      auto dIt = inst->skin_.data().find(secName);
      if (dIt == inst->skin_.data().end()) continue;
      if (dIt->second.find("Meter") == dIt->second.end()) continue;
      double mx = resolveNum(inst->skin_, &inst->measures_, *inst->math_, secName, "X", 0);
      double my = resolveNum(inst->skin_, &inst->measures_, *inst->math_, secName, "Y", 0);
      double mw = resolveNum(inst->skin_, &inst->measures_, *inst->math_, secName, "W", 40);
      double mh = resolveNum(inst->skin_, &inst->measures_, *inst->math_, secName, "H", 24);
      estMaxX = std::max(estMaxX, mx + mw);
      estMaxY = std::max(estMaxY, my + mh);
    }
    if (targetW <= 0) targetW = estMaxX;
    if (targetH <= 0) targetH = estMaxY;
  }

  int initWidth = std::max(1, static_cast<int>(std::ceil(targetW)));
  int initHeight = std::max(1, static_cast<int>(std::ceil(targetH)));
  inst->unscaledWidth_ = initWidth;
  inst->unscaledHeight_ = initHeight;

  if (inst->autoFit_) {
    if (initWidth >= 1000 || initHeight >= 650) {
      inst->effectiveScale_ = std::min(static_cast<double>(screenWidth) / initWidth,
                                       static_cast<double>(screenHeight) / initHeight);
    } else {
      inst->effectiveScale_ = std::clamp(static_cast<double>(screenHeight) / 768.0, 0.6, 2.5);
      if (initWidth * inst->effectiveScale_ > screenWidth) {
        inst->effectiveScale_ = static_cast<double>(screenWidth) / initWidth;
      }
    }
  } else if (inst->userScale_ > 0.1 && inst->userScale_ <= 5.0) {
    inst->effectiveScale_ = inst->userScale_;
  } else if (initWidth > screenWidth || initHeight > screenHeight) {
    inst->effectiveScale_ = std::min(static_cast<double>(screenWidth) / initWidth,
                                     static_cast<double>(screenHeight) / initHeight);
  } else {
    inst->effectiveScale_ = 1.0;
  }

  std::string internalX = getKeyCI(inst->skin_, "Rainmeter", "WindowX");
  std::string internalY = getKeyCI(inst->skin_, "Rainmeter", "WindowY");
  
  std::string rawX = globalConfig.getOr(configName, "WindowX", internalX);
  std::string rawY = globalConfig.getOr(configName, "WindowY", internalY);
  inst->hasExplicitX_ = !rawX.empty();
  inst->hasExplicitY_ = !rawY.empty();
  if (rawX.empty()) rawX = "0";
  if (rawY.empty()) rawY = "0";
  
  std::string resolvedX = resolveVariables(globalConfig, nullptr, configName, rawX);
  std::string resolvedY = resolveVariables(globalConfig, nullptr, configName, rawY);
  
  auto parsePercent = [](std::string& str, int screenDim) {
      if (!str.empty() && str.back() == '%') {
          try {
              double val = std::stod(str.substr(0, str.size() - 1));
              str = std::to_string(val / 100.0 * screenDim);
          } catch (...) {}
      }
  };
  
  parsePercent(resolvedX, screenWidth);
  parsePercent(resolvedY, screenHeight);
  
  if (!resolvedX.empty() && resolvedX.front() == '(' && resolvedX.back() == ')') {
      resolvedX = resolvedX.substr(1, resolvedX.size() - 2);
  }
  if (!resolvedY.empty() && resolvedY.front() == '(' && resolvedY.back() == ')') {
      resolvedY = resolvedY.substr(1, resolvedY.size() - 2);
  }
  
  inst->baseOffsetX_ = static_cast<int>(inst->math_->evaluateOr(resolvedX, 0));
  inst->baseOffsetY_ = static_cast<int>(inst->math_->evaluateOr(resolvedY, 0));

  // If AutoFit is enabled and explicit coordinates were authored for a reference monitor size
  // (e.g. RefWidth=1366, RefHeight=768), scale the coordinates proportionally to this monitor.
  if (inst->autoFit_ && (inst->hasExplicitX_ || inst->hasExplicitY_)) {
    int refW = static_cast<int>(inst->math_->evaluateOr(globalConfig.getOr(configName, "RefWidth", "0"), 0));
    int refH = static_cast<int>(inst->math_->evaluateOr(globalConfig.getOr(configName, "RefHeight", "0"), 0));
    if (refW > 0 && refH > 0 && (refW != screenWidth || refH != screenHeight)) {
      inst->baseOffsetX_ = static_cast<int>(std::lround(inst->baseOffsetX_ * (static_cast<double>(screenWidth) / refW)));
      inst->baseOffsetY_ = static_cast<int>(std::lround(inst->baseOffsetY_ * (static_cast<double>(screenHeight) / refH)));
    }
  }

  std::string anchorX = globalConfig.getOr(
      configName, "AnchorX", getKeyCI(inst->skin_, "Rainmeter", "AnchorX"));
  if (anchorX.empty()) anchorX = "left";
  for (auto &c : anchorX) c = std::tolower(c);
  inst->anchorX_ = anchorX;
  
  std::string anchorY = globalConfig.getOr(
      configName, "AnchorY", getKeyCI(inst->skin_, "Rainmeter", "AnchorY"));
  if (anchorY.empty()) anchorY = "top";
  for (auto &c : anchorY) c = std::tolower(c);
  inst->anchorY_ = anchorY;

  uint32_t anchor = 0;
  if (anchorX == "left") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT;
  else if (anchorX == "right") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT;
  
  if (anchorY == "top") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP;
  else if (anchorY == "bottom") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM;

  int scaledInitW = std::max(1, static_cast<int>(std::ceil(initWidth * inst->effectiveScale_)));
  int scaledInitH = std::max(1, static_cast<int>(std::ceil(initHeight * inst->effectiveScale_)));
  inst->computeWindowPosition(scaledInitW, scaledInitH, inst->windowX_, inst->windowY_);

  inst->window_.setPositionCallback([raw, configName](int newX, int newY) {
    std::lock_guard<std::mutex> lock(raw->stateMutex_);
    int monX = raw->window_.getScreenX(raw->monitorIndex_);
    int monY = raw->window_.getScreenY(raw->monitorIndex_);
    raw->windowX_ = newX;
    raw->windowY_ = newY;
    raw->baseOffsetX_ = newX - monX;
    raw->baseOffsetY_ = newY - monY;
    raw->hasExplicitX_ = true;
    raw->hasExplicitY_ = true;

    std::string rmIni = Utils::ResolvePath("~/.config/rainmeter-native/Rainmeter.ini");
    std::string sec = configName.empty() ? raw->iniPath_ : configName;
    IniLexer::writeKeyValue(rmIni, sec, "Active", "1");
    IniLexer::writeKeyValue(rmIni, sec, "WindowX", std::to_string(raw->baseOffsetX_));
    IniLexer::writeKeyValue(rmIni, sec, "WindowY", std::to_string(raw->baseOffsetY_));
  });

  if (!inst->window_.initLayerSurface(scaledInitW, scaledInitH, inst->windowX_, inst->windowY_, monitorIndex, anchor, iniPath)) {
    std::cerr << "SkinInstance '" << iniPath
              << "': failed to initialize layer surface.\n";
    return nullptr;
  }

  std::cout << "  SkinInstance up: " << iniPath << " (" << inst->window_.width()
            << "x" << inst->window_.height() << " at " << inst->windowX_ << ","
            << inst->windowY_ << " on monitor " << monitorIndex << ")\n";
  return inst;
}

void SkinInstance::computeWindowPosition(int winW, int winH, int &outX,
                                         int &outY) const {
  int monX = window_.getScreenX(monitorIndex_);
  int monY = window_.getScreenY(monitorIndex_);
  int monW = window_.getScreenWidth(monitorIndex_);
  int monH = window_.getScreenHeight(monitorIndex_);

  if (hasExplicitX_) {
    int maxOffsetX = std::max(0, monW - winW);
    outX = monX + std::clamp(baseOffsetX_, 0, maxOffsetX);
  } else if (anchorX_ == "center") {
    outX = monX + (monW - winW) / 2;
  } else if (anchorX_ == "right") {
    outX = monX + monW - winW;
  } else {
    outX = monX;
  }

  if (hasExplicitY_) {
    int maxOffsetY = std::max(0, monH - winH);
    outY = monY + std::clamp(baseOffsetY_, 0, maxOffsetY);
  } else if (anchorY_ == "center") {
    outY = monY + (monH - winH) / 2;
  } else if (anchorY_ == "bottom") {
    outY = monY + monH - winH;
  } else {
    outY = monY;
  }
}

// ---------------------------------------------------------------------------
// Public methods
// ---------------------------------------------------------------------------

void SkinInstance::Update(double dtMs) {
  std::lock_guard<std::mutex> lock(stateMutex_);
  
  if (!g_InputState.pendingCommand.empty() && (g_InputState.skinInstance == nullptr || g_InputState.skinInstance == this)) {
      std::string cmd = g_InputState.pendingCommand;
      g_InputState.pendingCommand.clear();
      CommandProcessor::execute(cmd, skin_, measures_, this);
      forceUpdate_ = true;
      forceRedraw_ = true;
  }

  measures_.evaluate(skin_, dtMs, [this](const std::string &bang) {
    BangResult result = CommandProcessor::execute(bang, skin_, measures_, this);
    if (result.needsUpdate)
      forceUpdate_ = true;
    if (result.needsRedraw)
      forceRedraw_ = true;
    if (result.deactivateConfig)
      active_ = false;
  });
  
  measures_.injectVariables(skin_);
  
  forceUpdate_ = false;
  forceRedraw_ = true;
}

void SkinInstance::Render(double dtMs) {
  if (!active_)
    return;

  bool redrawNeeded = false;
  {
    std::lock_guard<std::mutex> lock(stateMutex_);
    redrawNeeded = forceRedraw_;
  }

  if (!redrawNeeded)
    return;

  if (!window_.makeCurrent())
    return;

  if (!renderer_.valid()) {
    if (!renderer_.beginEGL(window_.width(), window_.height())) {
      std::cerr << "Failed to begin EGL renderer\n";
      return;
    }
    if (!fontsDir_.empty()) {
      renderer_.registerFontDirectory(fontsDir_);
    }
  }

  float pixelRatio =
      static_cast<float>(effectiveScale_ * window_.getSurfaceScale());
  renderer_.beginFrame(unscaledWidth_, unscaledHeight_, pixelRatio);

  {
    std::lock_guard<std::mutex> lock(stateMutex_);
    paintScene();
    forceRedraw_ = false;

    double maxX = 0;
    double maxY = 0;
    for (const auto &b : meterBounds_) {
      maxX = std::max(maxX, b.x + b.w);
      maxY = std::max(maxY, b.y + b.h);
    }

    double targetW = math_->evaluateOr(
        skin_.getOr("Rainmeter", "SkinWidth", ""), 0);
    double targetH = math_->evaluateOr(
        skin_.getOr("Rainmeter", "SkinHeight", ""), 0);
    if (targetW <= 0)
      targetW = maxX;
    if (targetH <= 0)
      targetH = maxY;

    int rawW = std::max(1, static_cast<int>(std::ceil(targetW)));
    int rawH = std::max(1, static_cast<int>(std::ceil(targetH)));

    int monW = window_.getScreenWidth(monitorIndex_);
    int monH = window_.getScreenHeight(monitorIndex_);
    if (autoFit_) {
      if (rawW >= 1000 || rawH >= 650) {
        // Full-screen suite: scale to fit monitor dimensions
        effectiveScale_ = std::min(static_cast<double>(monW) / rawW,
                                   static_cast<double>(monH) / rawH);
      } else {
        // Compact suite / widget: scale proportionally to monitor height (768p baseline)
        effectiveScale_ = std::clamp(static_cast<double>(monH) / 768.0, 0.6, 2.5);
        if (rawW * effectiveScale_ > monW) {
          effectiveScale_ = static_cast<double>(monW) / rawW;
        }
      }
    } else if (userScale_ > 0.1 && userScale_ <= 5.0) {
      effectiveScale_ = userScale_;
    } else if (rawW > monW || rawH > monH) {
      effectiveScale_ = std::min(static_cast<double>(monW) / rawW,
                                 static_cast<double>(monH) / rawH);
    } else {
      effectiveScale_ = 1.0;
    }

    unscaledWidth_ = rawW;
    unscaledHeight_ = rawH;

    int newW = std::max(1, static_cast<int>(std::ceil(rawW * effectiveScale_)));
    int newH = std::max(1, static_cast<int>(std::ceil(rawH * effectiveScale_)));

    if (newW != window_.width() || newH != window_.height()) {
      targetWidth_ = newW;
      targetHeight_ = newH;
      forceRedraw_ = true;
    }
  }

  renderer_.endFrame();
  window_.swapBuffers();
}

void SkinInstance::UpdateAnimations(double dtMs) {
  std::lock_guard<std::mutex> lock(stateMutex_);
  measures_.tickActionTimers(dtMs, [this](const std::string &bang) {
    BangResult result = CommandProcessor::execute(bang, skin_, measures_);
    if (result.needsUpdate)
      forceUpdate_ = true;
    
    // explicitly trigger a [!Redraw] command to force the graphics to update immediately
    CommandProcessor::execute("[!Redraw]", skin_, measures_);
    forceRedraw_ = true;
  });
}

bool SkinInstance::DispatchEvents() {
  return window_.dispatchPending();
}

void SkinInstance::ApplyPendingResize() {
  int resizeW = -1;
  int resizeH = -1;
  int newX = windowX_;
  int newY = windowY_;
  {
    std::lock_guard<std::mutex> lock(stateMutex_);
    if (targetWidth_ > 0 && targetHeight_ > 0) {
      resizeW = targetWidth_;
      resizeH = targetHeight_;
      computeWindowPosition(resizeW, resizeH, newX, newY);
      windowX_ = newX;
      windowY_ = newY;
      targetWidth_ = -1;
      targetHeight_ = -1;
    }
  }
  if (resizeW > 0 && resizeH > 0) {
    window_.moveAndResize(newX, newY, resizeW, resizeH);
  }
}

bool SkinInstance::IsActive() const {
  return active_;
}

bool SkinInstance::NeedsUpdate() const {
  return forceUpdate_;
}

bool SkinInstance::NeedsRedraw() const {
  return forceRedraw_;
}
