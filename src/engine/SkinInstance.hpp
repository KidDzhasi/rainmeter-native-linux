#pragma once

#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include "evaluator/CommandProcessor.hpp"
#include "evaluator/MathParser.hpp"
#include "evaluator/MeasureEvaluator.hpp"
#include "evaluator/ThemeParser.hpp"
#include "graphics/NanoVGRenderer.hpp"
#include "graphics/TransformManager.hpp"
#include "parser/IniLexer.hpp"
#include "utils/ColorParser.hpp"
#include "wayland/LayerShell.hpp"

// Bounding rectangle of a rendered meter, used for mouse hit-testing.
struct MeterBounds {
  std::string section;
  double x, y, w, h;
};

// SkinInstance encapsulates all state for a single loaded Rainmeter skin:
// its parsed INI data, measure evaluator, math parser, NanoVG renderer,
// and Wayland layer-shell surface. Each skin runs as an independent widget
// on the desktop.
//
// Use the static Load() factory to create an instance from an .ini path.
// The owning SkinManager calls Update(), Render(), TickActionTimers(),
// DispatchEvents(), and ApplyPendingResize() at appropriate points in
// the engine's main and render loops.
class SkinInstance {
public:
  // Factory: parses the INI file, sets up measures, math parser, Wayland
  // window, and mouse callback. Returns nullptr on any failure (bad path,
  // compositor unavailable, etc.).
  static std::unique_ptr<SkinInstance> Load(const std::string &iniPath);

  ~SkinInstance() = default;
  SkinInstance(const SkinInstance &) = delete;
  SkinInstance &operator=(const SkinInstance &) = delete;

  // Per-tick measure evaluation. Calls CommandProcessor as needed.
  // Called from the main thread every tick interval.
  void Update();

  // Per-frame render. Must be called from the render thread.
  // Paints the scene, calculates auto-size, and swaps buffers.
  void Render(double dtMs);

  // Tick ActionTimers with the main thread delta time (ms).
  void UpdateAnimations(double dtMs);

  // Process pending Wayland events (non-blocking).
  // Returns false if the surface has been closed or the connection is broken.
  bool DispatchEvents();

  // Apply any deferred resize that was computed during the last Render().
  void ApplyPendingResize();

  bool IsActive() const;
  bool NeedsUpdate() const;
  bool NeedsRedraw() const;
  const std::string &IniPath() const { return iniPath_; }

private:
  SkinInstance() = default;

  // --- Scene painting (migrated from main.cpp anonymous namespace) ---
  void paintScene();

  // --- Coordinate / value resolution helpers ---
  static double resolveNum(const IniLexer &skin, const MathParser &math,
                           const std::string &section, const std::string &key,
                           double def);
  static std::string getKeyCI(const IniLexer &skin, const std::string &section,
                              const std::string &key);
  static double resolveCoord(const IniLexer &skin, const MathParser &math,
                             const std::string &section,
                             const std::string &key, double relBase,
                             double relStack, double def);
  static NanoVGRenderer::TextAlign parseAlign(const std::string &spec);
  static std::string resolveVariables(const IniLexer &skin,
                                      const MeasureEvaluator *measures,
                                      const std::string &section,
                                      const std::string &text);
  static std::string resolveImagePath(const IniLexer &skin,
                                      const std::string &section,
                                      const std::string &iniPath);

  // --- Per-skin state ---
  std::string iniPath_;
  IniLexer skin_;
  MeasureEvaluator measures_;
  std::unique_ptr<MathParser> math_;
  NanoVGRenderer renderer_;
  LayerShellWindow window_;
  std::vector<MeterBounds> meterBounds_;
  std::string fontsDir_;

  std::mutex stateMutex_;
  bool forceUpdate_ = true;
  bool forceRedraw_ = true;
  bool active_ = true;
  int targetWidth_ = -1;
  int targetHeight_ = -1;
  int windowX_ = 0;
  int windowY_ = 0;
};
