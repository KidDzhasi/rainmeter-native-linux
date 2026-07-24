#include <chrono>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "evaluator/CommandProcessor.hpp"
#include "evaluator/MathParser.hpp"
#include "evaluator/MeasureEvaluator.hpp"
#include "evaluator/ThemeParser.hpp"
#include "graphics/CairoRenderer.hpp"
#include "installer/SkinInstaller.hpp"
#include "parser/IniLexer.hpp"
#include "wayland/LayerShell.hpp"

#include <filesystem>
#include <linux/input-event-codes.h>

namespace fs = std::filesystem;

namespace {

constexpr int kDefaultWidth = 260;
constexpr int kDefaultHeight = 200;
constexpr auto kTickInterval = std::chrono::milliseconds(1000);

using Color = CairoRenderer::Color;

struct MeterBounds {
  std::string section;
  double x, y, w, h;
};

// Resolves a meter property that may be a plain number or a formula
// (#Variable# / [Measure] / arithmetic). Falls back to `def` if unset.
double resolveNum(const IniLexer &skin, const MathParser &math,
                  const std::string &section, const std::string &key,
                  double def) {
  const std::string raw = skin.getOr(section, key, "");
  if (raw.empty()) {
    return def;
  }
  return math.evaluateOr(raw, def);
}

// Reads a section key trying a couple of case variants, since Rainmeter
// treats keys like X/x and Y/y as case-insensitive.
std::string getKeyCI(const IniLexer &skin, const std::string &section,
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

// Resolves a Rainmeter X/Y coordinate string that may carry a relative
// suffix:
//   "50"   -> absolute 50
//   "5r"   -> relBase + 5      (relative to the previous meter's X or Y)
//   "5R"   -> relStack + 5     (relative to previous X+W or Y+H)
// The numeric part may itself be a #Variable#/formula and can be negative.
double resolveCoord(const IniLexer &skin, const MathParser &math,
                    const std::string &section, const std::string &key,
                    double relBase, double relStack, double def) {
  std::string raw = getKeyCI(skin, section, key);
  // Trim trailing whitespace.
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

// Maps a StringAlign value to the renderer's alignment enum.
CairoRenderer::TextAlign parseAlign(const std::string &spec) {
  if (spec == "CenterCenter" || spec == "CENTERCENTER" || spec == "centercenter") {
    return CairoRenderer::TextAlign::CenterCenter;
  }
  if (spec == "Center" || spec == "CENTER" || spec == "center") {
    return CairoRenderer::TextAlign::Center;
  }
  if (spec == "Right" || spec == "RIGHT" || spec == "right") {
    return CairoRenderer::TextAlign::Right;
  }
  return CairoRenderer::TextAlign::Left;
}

// Resolves any #Variable# tokens embedded in `text` against the skin's
// [Variables] section. Unknown variables are left untouched.
std::string resolveVariables(const IniLexer &skin, const std::string &text) {
  std::string out;
  out.reserve(text.size());
  for (std::size_t i = 0; i < text.size();) {
    if (text[i] == '#') {
      const std::size_t close = text.find('#', i + 1);
      if (close != std::string::npos && close > i + 1) {
        const std::string name = text.substr(i + 1, close - i - 1);
        // Rainmeter variables are case-insensitive: #format# resolves a
        // variable defined as "Format=".
        auto value = skin.getCaseInsensitive("Variables", name);
        if (value) {
          out += *value;
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

std::string resolveImagePath(const IniLexer &skin, const std::string &section,
                             const std::string &iniPath) {
  std::string imageName = skin.getOr(section, "ImageName", "");
  if (imageName.empty()) {
    return "";
  }
  // If absolute path
  if (imageName.front() == '/') {
    return imageName;
  }

  std::string imagePath = skin.getOr(section, "ImagePath", "");
  fs::path skinDir = fs::path(iniPath).parent_path();

  if (!imagePath.empty()) {
    fs::path tryPath = skinDir / imagePath / imageName;
    if (fs::exists(tryPath)) return tryPath.string();
  }

  fs::path tryPath1 = skinDir / imageName;
  if (fs::exists(tryPath1)) return tryPath1.string();

  // Search upwards for @Resources
  fs::path curr = skinDir;
  while (curr != curr.parent_path() && curr.string() != "/") {
    fs::path resPath = curr / "@Resources" / "Images" / imageName;
    if (fs::exists(resPath)) return resPath.string();
    curr = curr.parent_path();
  }

  return tryPath1.string();
}

void paintScene(CairoRenderer &r, const IniLexer &skin,
                const MeasureEvaluator &measures, const MathParser &math,
                std::vector<MeterBounds> &bounds,
                const std::string &iniPath) {
  bounds.clear();
  // Start every frame from a fully transparent surface so the desktop shows
  // through wherever the skin does not paint.
  r.clear(Color{0.0, 0.0, 0.0, 0.0});

  const std::string fontName = skin.getOr("Variables", "fontName", "Sans");
  const Color textColor =
      Color::parse(skin.getOr("Variables", "colorText", "255,255,255,255"));
  const Color barColor =
      Color::parse(skin.getOr("Variables", "colorBar", "235,170,0,255"));
  const Color trackColor{1.0, 1.0, 1.0, 0.12};

  // State for Rainmeter relative-coordinate layout (X=5r / Y=5R). Each meter
  // can position itself relative to the previous meter's origin (r) or the
  // previous meter's far edge (R).
  double prevX = 0.0;
  double prevY = 0.0;
  double prevWidth = 0.0;
  double prevHeight = 0.0;

  for (const auto &[section, keys] : skin.data()) {
    auto meterIt = keys.find("Meter");
    if (meterIt == keys.end()) {
      continue; // Not a meter section.
    }
    const std::string &type = meterIt->second;

    const double x =
        resolveCoord(skin, math, section, "X", prevX, prevX + prevWidth, 0);
    const double y =
        resolveCoord(skin, math, section, "Y", prevY, prevY + prevHeight, 0);
    const double w = resolveNum(skin, math, section, "W", 0);
    const double h = resolveNum(skin, math, section, "H", 0);

    // Dimensions of this meter, used to update the relative-layout state
    // after it is drawn. String meters override width/height with their
    // measured text extents.
    double curWidth = w;
    double curHeight = h;

    if (type == "String") {
      // Collect MeasureName, MeasureName2, MeasureName3, ... into an ordered
      // list of live string values so "%1", "%2", ... can be substituted.
      std::vector<std::string> measureValues;
      for (int idx = 1;; ++idx) {
        const std::string key =
            (idx == 1) ? "MeasureName" : "MeasureName" + std::to_string(idx);
        const std::string mName = skin.getOr(section, key, "");
        if (mName.empty()) {
          break;
        }
        measureValues.push_back(measures.value(mName));
      }

      // Resolve any #Variables# in the raw Text first, then substitute the
      // %1/%2/... measure tokens.
      const std::string rawTemplate = skin.getOr(section, "Text", "%1");
      const std::string textTemplate = resolveVariables(skin, rawTemplate);
      const std::string out =
          CairoRenderer::substituteText(textTemplate, measureValues);
      const double fontSize = resolveNum(skin, math, section, "FontSize", 12.0);

      Color color = textColor;
      const std::string fc = skin.getOr(section, "FontColor", "");
      if (!fc.empty()) {
        color = Color::parse(fc);
      }
      const CairoRenderer::TextAlign align =
          parseAlign(skin.getOr(section, "StringAlign", "Left"));
      const std::string meterFontFace = skin.getOr(section, "FontFace", fontName);
      const CairoRenderer::TextMetrics tm =
          r.drawText(out, x, y, meterFontFace, fontSize, color, align);
      // Use the measured text extents to advance the relative-layout state.
      curWidth = tm.width;
      curHeight = tm.height;

    } else if (type == "Image") {
      const std::string path = resolveImagePath(skin, section, iniPath);
      if (!path.empty()) {
        int preserveAspectRatio = static_cast<int>(resolveNum(skin, math, section, "PreserveAspectRatio", 0.0));
        auto im = r.drawImage(path, x, y, w, h, preserveAspectRatio);
        if (im.success) {
          curWidth = im.width;
          curHeight = im.height;
        }
      } else {
        // No asset: draw a placeholder rectangle so layout is visible.
        curWidth = w > 0 ? w : 32;
        curHeight = h > 0 ? h : 32;
        r.strokeRect(x, y, curWidth, curHeight, 1.0, textColor);
      }

    } else if (type == "Shape") {
      curWidth = w;
      curHeight = h;
      for (int i = 1; ; ++i) {
        std::string key = (i == 1) ? "Shape" : "Shape" + std::to_string(i);
        std::string shapeDef = skin.getOr(section, key, "");
        if (shapeDef.empty()) break;
        
        // Parse the definition
        std::vector<std::string> parts;
        std::size_t start = 0;
        while (start < shapeDef.size()) {
          std::size_t end = shapeDef.find('|', start);
          if (end == std::string::npos) end = shapeDef.size();
          std::string part = shapeDef.substr(start, end - start);
          while (!part.empty() && std::isspace(part.front())) part.erase(0, 1);
          while (!part.empty() && std::isspace(part.back())) part.pop_back();
          if (!part.empty()) parts.push_back(part);
          start = end + 1;
        }
        
        if (parts.empty()) continue;
        
        // Setup default shape styling
        Color fill = Color::parse("0,0,0,0");
        Color stroke = Color::parse("255,255,255,255");
        double lw = 1.0;
        
        // Parse modifiers
        for (size_t j = 1; j < parts.size(); ++j) {
            std::string mod = parts[j];
            if (mod.find("Fill Color ") == 0) {
               fill = Color::parse(mod.substr(11));
            } else if (mod.find("Stroke Color ") == 0) {
               stroke = Color::parse(mod.substr(13));
            } else if (mod.find("StrokeWidth ") == 0) {
               try { lw = std::stod(mod.substr(12)); } catch(...) {}
            }
        }
        
        // Parse geometry
        std::string geom = parts[0];
        std::size_t space = geom.find(' ');
        std::string shapeType = geom.substr(0, space);
        std::string argsStr = (space != std::string::npos) ? geom.substr(space + 1) : "";
        std::vector<double> args;
        std::size_t pstart = 0;
        while (pstart < argsStr.size()) {
           std::size_t pend = argsStr.find(',', pstart);
           if (pend == std::string::npos) pend = argsStr.size();
           std::string arg = argsStr.substr(pstart, pend - pstart);
           args.push_back(math.evaluateOr(arg, 0.0));
           pstart = pend + 1;
        }
        
        if (shapeType == "Rectangle" && args.size() >= 4) {
           double sx = x + args[0];
           double sy = y + args[1];
           double sw = args[2];
           double sh = args[3];
           if (fill.a > 0) r.fillRect(sx, sy, sw, sh, fill);
           if (stroke.a > 0 && lw > 0) r.strokeRect(sx, sy, sw, sh, lw, stroke);
           curWidth = std::max(curWidth, args[0] + sw);
           curHeight = std::max(curHeight, args[1] + sh);
        } else if (shapeType == "Ellipse" && args.size() >= 4) {
           double cx = x + args[0];
           double cy = y + args[1];
           double rx = args[2];
           double ry = args[3];
           r.drawEllipse(cx - rx, cy - ry, rx * 2, ry * 2, fill, stroke, lw);
           curWidth = std::max(curWidth, args[0] + rx);
           curHeight = std::max(curHeight, args[1] + ry);
        }
      }

    } else if (type == "Bar") {
      const std::string measureName = skin.getOr(section, "MeasureName", "");
      const double pct =
          measureName.empty() ? 0.0 : measures.numericValue(measureName);
      Color bc = barColor;
      const std::string bcSpec = skin.getOr(section, "BarColor", "");
      if (!bcSpec.empty()) {
        bc = Color::parse(bcSpec);
      }
      curWidth = w > 0 ? w : 200;
      curHeight = h > 0 ? h : 12;
      r.drawBar(x, y, curWidth, curHeight, pct, bc, trackColor);
    }

    // Record this meter's final placement so subsequent meters can position
    // themselves relatively (r = relative to origin, R = relative to edge).
    prevX = x;
    prevY = y;
    prevWidth = curWidth;
    prevHeight = curHeight;

    bounds.push_back({section, x, y, curWidth, curHeight});
  }
}

// A single running skin widget: its parsed .ini, live measures, formula
// evaluator, Cairo surface, and Wayland layer surface. Each widget owns its
// own Wayland connection so multiple widgets run concurrently and
// independently. Held via unique_ptr because MathParser captures pointers
// into this struct (which must stay put) and LayerShellWindow is not movable.
struct WidgetInstance {
  std::string iniPath;
  IniLexer skin;
  MeasureEvaluator measures;
  std::unique_ptr<MathParser> math;
  CairoRenderer renderer;
  LayerShellWindow window;
  std::vector<MeterBounds> meterBounds;

  bool forceUpdate = true; // true initially to draw first frame
  bool forceRedraw = true;
  bool active = true;
};

// Parses one widget .ini and brings up its surface. Returns nullptr on any
// failure (unreadable skin, no compositor, surface/Cairo init failure).
std::unique_ptr<WidgetInstance> loadWidget(const std::string &iniPath) {
  auto w = std::make_unique<WidgetInstance>();
  w->iniPath = iniPath;

  if (!w->skin.parseFile(iniPath)) {
    std::cerr << "Widget: could not open '" << iniPath << "'\n";
    return nullptr;
  }
  w->measures.loadFrom(w->skin);

  // Register any custom fonts bundled with the skin so Pango can find them by
  // family name. Rainmeter skins ship these under @Resources/Fonts. The
  // resources path is resolved case-insensitively against the real filesystem.
  const std::string resources = w->skin.resourcesPath();
  if (!resources.empty()) {
    const std::string fontsDir =
        ThemeParser::resolveCaseInsensitivePath(resources, "Fonts");
    CairoRenderer::registerFontDirectory(fontsDir);
  }

  // Math parser wired to this widget's own variables + measures. Capture raw
  // pointers to members (the WidgetInstance is heap-stable behind unique_ptr).
  IniLexer *skinPtr = &w->skin;
  MeasureEvaluator *measPtr = &w->measures;
  w->math = std::make_unique<MathParser>(
      [skinPtr](const std::string &name) {
        return skinPtr->getOr("Variables", name, "0");
      },
      [measPtr](const std::string &name) {
        return measPtr->numericValue(name);
      });

  if (!w->window.connect()) {
    std::cerr << "Widget '" << iniPath
              << "': could not connect to a Wayland compositor.\n";
    return nullptr;
  }
  // Use the widget's config name as the layer-surface scope so compositors
  // can tell the surfaces apart.
  if (!w->window.initLayerSurface(kDefaultWidth, kDefaultHeight, iniPath)) {
    std::cerr << "Widget '" << iniPath
              << "': failed to initialize layer surface.\n";
    return nullptr;
  }
  if (!w->renderer.beginImage(w->window.width(), w->window.height())) {
    std::cerr << "Widget '" << iniPath
              << "': failed to create Cairo surface.\n";
    return nullptr;
  }

  w->window.setMouseCallback([wPtr = w.get()](double x, double y, uint32_t button) {
    if (button != BTN_LEFT) return;
    for (auto it = wPtr->meterBounds.rbegin(); it != wPtr->meterBounds.rend(); ++it) {
      if (x >= it->x && x <= it->x + it->w && y >= it->y && y <= it->y + it->h) {
        std::string action = wPtr->skin.getCaseInsensitive(it->section, "LeftMouseUpAction").value_or("");
        if (!action.empty()) {
          BangResult res = CommandProcessor::execute(action, wPtr->skin, wPtr->measures);
          if (res.needsUpdate) wPtr->forceUpdate = true;
          if (res.needsRedraw) wPtr->forceRedraw = true;
        }
        break; // Only handle the topmost clicked meter
      }
    }
  });

  std::cout << "  Widget up: " << iniPath << " (" << w->window.width() << "x"
            << w->window.height() << ")\n";
  return w;
}



// Case-insensitive check for a ".rmskin" file extension.
bool isRmskinFile(const std::string &path) {
  if (path.size() < 7) {
    return false;
  }
  std::string ext = path.substr(path.size() - 7);
  for (char &c : ext) {
    if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>(c - 'A' + 'a');
    }
  }
  return ext == ".rmskin";
}

} // namespace

int main(int argc, char **argv) {
  std::cout << "rainmeter-native: starting up..." << std::endl;

  // --install <path.rmskin>: extract a skin package and exit without
  // launching the Wayland compositor.
  std::string inputPath =
      "/home/remember/Desktop/Projects/rainmeter-to-eww/illustro_clock.ini";
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--install") {
      if (i + 1 >= argc) {
        std::cerr << "Error: --install requires a path to a .rmskin file.\n";
        return 1;
      }
      const std::string rmskinPath = argv[i + 1];
      SkinInstaller installer;
      if (!installer.install(rmskinPath).has_value()) {
        std::cerr << "Installation failed.\n";
        return 1;
      }
      std::cout << "Skin installed successfully.\n";
      return 0;
    }
    // Otherwise treat the first non-flag argument as a skin/theme path.
    if (!arg.empty() && arg[0] != '-') {
      inputPath = arg;
    }
  }

  // If the user passed an .rmskin file as a positional argument, auto-install
  // it to the skins directory and then load the primary .ini from the package.
  if (isRmskinFile(inputPath)) {
    std::cout << "Auto-installing skin package: " << inputPath << "\n";
    SkinInstaller installer;
    auto installedIni = installer.install(inputPath);
    if (!installedIni.has_value()) {
      std::cerr << "Error: auto-install of '" << inputPath << "' failed or no .ini found.\n";
      return 1;
    }
    
    std::cout << "Launching installed skin: " << *installedIni << "\n";
    inputPath = *installedIni;
  }

  // Decide whether we were handed a single widget (.ini) or a full theme
  // (.thm / Rainmeter.ini) that references multiple active widgets.
  std::vector<std::string> widgetPaths;
  if (ThemeParser::isThemeFile(inputPath)) {
    std::cout << "Loading theme: " << inputPath << "\n";
    ThemeParser theme;
    if (!theme.parse(inputPath)) {
      std::cerr << "Error: could not open theme '" << inputPath << "'\n";
      return 1;
    }
    for (const auto &widget : theme.widgets()) {
      std::cout << "  Active widget: " << widget.config << " -> "
                << widget.iniPath << "\n";
      widgetPaths.push_back(widget.iniPath);
    }
    if (widgetPaths.empty()) {
      std::cerr << "Theme has no active (Active=1) widgets; nothing to show.\n";
      return 1;
    }
  } else {
    std::cout << "Loading single skin: " << inputPath << "\n";
    widgetPaths.push_back(inputPath);
  }

  // Bring up a layer surface for each widget, running them concurrently.
  std::vector<std::unique_ptr<WidgetInstance>> widgets;
  for (const auto &path : widgetPaths) {
    if (auto w = loadWidget(path)) {
      widgets.push_back(std::move(w));
    }
  }
  if (widgets.empty()) {
    std::cerr << "Error: no widgets could be started.\n";
    return 1;
  }

  std::cout << "Presenting " << widgets.size()
            << " widget(s) on the desktop. Updating every 1000ms. "
               "Ctrl+C to exit.\n";

  auto nextTick = std::chrono::steady_clock::now() + kTickInterval;

  // Live event loop: poll Wayland events continuously (approx 60fps).
  // Evaluate measures on the tick interval, and redraw when necessary.
  while (!widgets.empty()) {
    auto now = std::chrono::steady_clock::now();
    bool doTick = (now >= nextTick);
    if (doTick) {
      nextTick = now + kTickInterval;
    }

    for (auto it = widgets.begin(); it != widgets.end();) {
      WidgetInstance &w = **it;
      if (doTick || w.forceUpdate) {
        w.measures.evaluate(w.skin, [&w](const std::string& bang) {
           BangResult result = CommandProcessor::execute(bang, w.skin, w.measures);
           if (result.needsUpdate) w.forceUpdate = true;
           if (result.needsRedraw) w.forceRedraw = true;
           if (result.deactivateConfig) w.active = false;
        });
        w.forceUpdate = false;
        w.forceRedraw = true;
      }
      if (!w.active) {
        it = widgets.erase(it);
        continue;
      }
      if (w.forceRedraw) {
        paintScene(w.renderer, w.skin, w.measures, *w.math, w.meterBounds, w.iniPath);
        w.renderer.flush();
        w.window.render(w.renderer);
        w.forceRedraw = false;
      }

      if (w.window.dispatchPending()) {
        ++it;
      } else {
        it = widgets.erase(it); // Surface closed / connection broken.
      }
    }
    if (widgets.empty()) {
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(16));
  }

  return 0;
}
