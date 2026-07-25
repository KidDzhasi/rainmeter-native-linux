#include "engine/SkinInstance.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>

#include <linux/input-event-codes.h>

namespace fs = std::filesystem;

namespace {
constexpr int kDefaultWidth = 260;
constexpr int kDefaultHeight = 200;
} // namespace

// ---------------------------------------------------------------------------
// Static helper functions (migrated from main.cpp anonymous namespace)
// ---------------------------------------------------------------------------

double SkinInstance::resolveNum(const IniLexer &skin, const MathParser &math,
                               const std::string &section,
                               const std::string &key, double def) {
  const std::string raw = skin.getOr(section, key, "");
  if (raw.empty()) {
    return def;
  }
  return math.evaluateOr(raw, def);
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

double SkinInstance::resolveCoord(const IniLexer &skin, const MathParser &math,
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

  const double value = math.evaluateOr(raw, 0.0);
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
                                          const std::string &section,
                                          const std::string &iniPath) {
  std::string imageName = skin.getOr(section, "ImageName", "");
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
    // Case-insensitive fallback
    std::string ciPath = IniLexer::resolveCaseInsensitivePath(
        (skinDir / imagePath).string(), imageName);
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

  for (const auto &[section, keys] : skin_.data()) {
    auto meterIt = keys.find("Meter");
    if (meterIt == keys.end()) {
      continue;
    }
    const std::string &type = meterIt->second;

    const double x =
        resolveCoord(skin_, *math_, section, "X", prevX, prevX + prevWidth, 0);
    const double y =
        resolveCoord(skin_, *math_, section, "Y", prevY, prevY + prevHeight, 0);
    const double w = resolveNum(skin_, *math_, section, "W", 0);
    const double h = resolveNum(skin_, *math_, section, "H", 0);

    double curWidth = w;
    double curHeight = h;

    std::string transformStr = skin_.getOr(section, "TransformationMatrix", "");
    transformManager.parse(transformStr);
    renderer_.save();
    renderer_.setTransform(transformManager.toNanoVG());

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

      const std::string rawTemplate = skin_.getOr(section, "Text", "%1");
      const std::string textTemplate =
          resolveVariables(skin_, &measures_, section, rawTemplate);
      const std::string out =
          NanoVGRenderer::substituteText(textTemplate, measureValues);
      const double fontSize =
          resolveNum(skin_, *math_, section, "FontSize", 12.0);

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
      const NanoVGRenderer::TextMetrics tm =
          renderer_.drawText(out, x, y, meterFontFace, fontSize, color, align);
      curWidth = (w > 0) ? w : tm.width;
      curHeight = (h > 0) ? h : tm.height;

    } else if (type == "Image") {
      const std::string path = resolveImagePath(skin_, section, iniPath_);
      if (!path.empty()) {
        int preserveAspectRatio = static_cast<int>(
            resolveNum(skin_, *math_, section, "PreserveAspectRatio", 0.0));
        auto im =
            renderer_.drawImage(path, x, y, w, h, preserveAspectRatio);
        if (im.success) {
          curWidth = im.width;
          curHeight = im.height;
        }
      } else {
        curWidth = w > 0 ? w : 32;
        curHeight = h > 0 ? h : 32;
        renderer_.strokeRect(x, y, curWidth, curHeight, 1.0, textColor);
      }

    } else if (type == "Shape") {
      curWidth = w;
      curHeight = h;
      for (int i = 1;; ++i) {
        std::string key = (i == 1) ? "Shape" : "Shape" + std::to_string(i);
        std::string rawShapeDef = skin_.getOr(section, key, "");
        if (rawShapeDef.empty())
          break;
        std::string shapeDef = resolveVariables(skin_, &measures_, section, rawShapeDef);

        std::vector<std::string> parts;
        std::size_t start = 0;
        while (start < shapeDef.size()) {
          std::size_t end = shapeDef.find('|', start);
          if (end == std::string::npos)
            end = shapeDef.size();
          std::string part = shapeDef.substr(start, end - start);
          while (!part.empty() && std::isspace(part.front()))
            part.erase(0, 1);
          while (!part.empty() && std::isspace(part.back()))
            part.pop_back();
          if (!part.empty())
            parts.push_back(part);
          start = end + 1;
        }

        if (parts.empty())
          continue;

        Color fill = Utils::ParseColor("0,0,0,0");
        Color stroke = Utils::ParseColor("255,255,255,255");
        double lw = 1.0;

        for (size_t j = 1; j < parts.size(); ++j) {
          std::string mod = parts[j];
          if (mod.find("Fill Color ") == 0) {
            fill = Utils::ParseColor(mod.substr(11));
          } else if (mod.find("Stroke Color ") == 0) {
            stroke = Utils::ParseColor(mod.substr(13));
          } else if (mod.find("StrokeWidth ") == 0) {
            try {
              lw = std::stod(mod.substr(12));
            } catch (...) {
            }
          }
        }

        std::string geom = parts[0];
        std::size_t space = geom.find(' ');
        std::string shapeType = geom.substr(0, space);
        std::string argsStr =
            (space != std::string::npos) ? geom.substr(space + 1) : "";
        std::vector<double> args;
        std::size_t pstart = 0;
        while (pstart < argsStr.size()) {
          std::size_t pend = argsStr.find(',', pstart);
          if (pend == std::string::npos)
            pend = argsStr.size();
          std::string arg = argsStr.substr(pstart, pend - pstart);
          args.push_back(math_->evaluateOr(arg, 0.0));
          pstart = pend + 1;
        }

        if (shapeType == "Rectangle" && args.size() >= 4) {
          double sx = x + args[0];
          double sy = y + args[1];
          double sw = args[2];
          double sh = args[3];
          double radius = (args.size() >= 5) ? args[4] : 0.0;
          renderer_.drawRectangle(sx, sy, sw, sh, radius, fill, stroke, lw);
          curWidth = std::max(curWidth, args[0] + sw);
          curHeight = std::max(curHeight, args[1] + sh);
        } else if (shapeType == "Ellipse" && args.size() >= 4) {
          double cx = x + args[0];
          double cy = y + args[1];
          double rx = args[2];
          double ry = args[3];
          renderer_.drawEllipse(cx - rx, cy - ry, rx * 2, ry * 2, fill,
                                stroke, lw);
          curWidth = std::max(curWidth, args[0] + rx);
          curHeight = std::max(curHeight, args[1] + ry);
        }
      }

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
    }

    renderer_.restore();

    prevX = x;
    prevY = y;
    prevWidth = curWidth;
    prevHeight = curHeight;

    meterBounds_.push_back({section, x, y, curWidth, curHeight});
  }
}

// ---------------------------------------------------------------------------
// Load — factory method
// ---------------------------------------------------------------------------

std::unique_ptr<SkinInstance> SkinInstance::Load(const std::string &iniPath) {
  // Can't use make_unique because constructor is private.
  std::unique_ptr<SkinInstance> inst(new SkinInstance());
  inst->iniPath_ = iniPath;

  if (!inst->skin_.parseFile(iniPath)) {
    std::cerr << "SkinInstance: could not open '" << iniPath << "'\n";
    return nullptr;
  }
  inst->measures_.loadFrom(inst->skin_);

  const std::string resources = inst->skin_.resourcesPath();
  if (!resources.empty()) {
    inst->fontsDir_ =
        ThemeParser::resolveCaseInsensitivePath(resources, "Fonts");
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
        for (auto it = raw->meterBounds_.rbegin();
             it != raw->meterBounds_.rend(); ++it) {
          if (x >= it->x && x <= it->x + it->w && y >= it->y &&
              y <= it->y + it->h) {
            std::string action =
                raw->skin_.getOr(it->section, "LeftMouseUpAction", "");
            if (!action.empty()) {
              std::cout << "[ENGINE] Hitbox triggered for Meter: "
                        << it->section << std::endl;
              BangResult res = CommandProcessor::execute(action, raw->skin_,
                                                        raw->measures_);
              if (res.needsUpdate)
                raw->forceUpdate_ = true;
              if (res.needsRedraw)
                raw->forceRedraw_ = true;
              break;
            }
          }
        }
      });

  inst->windowX_ = static_cast<int>(inst->math_->evaluateOr(inst->skin_.getOr("Rainmeter", "WindowX", "0"), 0));
  inst->windowY_ = static_cast<int>(inst->math_->evaluateOr(inst->skin_.getOr("Rainmeter", "WindowY", "0"), 0));

  std::string anchorX = getKeyCI(inst->skin_, "Rainmeter", "AnchorX");
  if (anchorX.empty()) anchorX = "left";
  for (auto &c : anchorX) c = std::tolower(c);
  
  std::string anchorY = getKeyCI(inst->skin_, "Rainmeter", "AnchorY");
  if (anchorY.empty()) anchorY = "top";
  for (auto &c : anchorY) c = std::tolower(c);

  uint32_t anchor = 0;
  if (anchorX == "left") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT;
  else if (anchorX == "right") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT;
  
  if (anchorY == "top") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP;
  else if (anchorY == "bottom") anchor |= ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM;

  std::string monitorStr = getKeyCI(inst->skin_, "Rainmeter", "@Monitor");
  if (monitorStr.empty()) monitorStr = "0";
  int monitorIndex = static_cast<int>(inst->math_->evaluateOr(monitorStr, 0));

  if (!inst->window_.initLayerSurface(kDefaultWidth, kDefaultHeight, inst->windowX_, inst->windowY_, monitorIndex, anchor, iniPath)) {
    std::cerr << "SkinInstance '" << iniPath
              << "': failed to initialize layer surface.\n";
    return nullptr;
  }

  std::cout << "  SkinInstance up: " << iniPath << " (" << inst->window_.width()
            << "x" << inst->window_.height() << ")\n";
  return inst;
}

// ---------------------------------------------------------------------------
// Public methods
// ---------------------------------------------------------------------------

void SkinInstance::Update() {
  std::lock_guard<std::mutex> lock(stateMutex_);
  measures_.evaluate(skin_, [this](const std::string &bang) {
    BangResult result = CommandProcessor::execute(bang, skin_, measures_);
    if (result.needsUpdate)
      forceUpdate_ = true;
    if (result.needsRedraw)
      forceRedraw_ = true;
    if (result.deactivateConfig)
      active_ = false;
  });
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

  if (!renderer_.valid() || renderer_.width() != window_.width() ||
      renderer_.height() != window_.height()) {
    if (!renderer_.beginEGL(window_.width(), window_.height())) {
      std::cerr << "Failed to begin EGL renderer\n";
      return;
    }
    if (!fontsDir_.empty()) {
      renderer_.registerFontDirectory(fontsDir_);
    }
  }

  renderer_.beginFrame(window_.width(), window_.height(), 1.0f);

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

    int newW = std::max(1, static_cast<int>(std::ceil(targetW)));
    int newH = std::max(1, static_cast<int>(std::ceil(targetH)));

    if (newW != window_.width() || newH != window_.height()) {
      targetWidth_ = newW;
      targetHeight_ = newH;
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
  {
    std::lock_guard<std::mutex> lock(stateMutex_);
    if (targetWidth_ > 0 && targetHeight_ > 0) {
      resizeW = targetWidth_;
      resizeH = targetHeight_;
      targetWidth_ = -1;
      targetHeight_ = -1;
    }
  }
  if (resizeW > 0 && resizeH > 0) {
    window_.resize(resizeW, resizeH);
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
