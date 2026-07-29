#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "engine/SkinInstance.hpp"

// SkinManager is the centralized orchestrator that owns all active
// SkinInstance objects. It replaces the inline loop logic that was
// previously in main() for iterating over widgets.
//
// The owning code (main.cpp) calls:
//   - LoadSkin()          once per skin path at startup
//   - UpdateAll()         every tick interval from the main thread
//   - RenderAll()         every frame from the render thread
//   - HandleGlobalEvents() every iteration of the main loop
class SkinManager {
public:
  SkinManager() = default;

  // Load a single skin from an INI path. Returns false on failure
  // (bad path, compositor unavailable, etc.).
  bool LoadSkin(const std::string &iniPath);

  // Per-tick: evaluates all measures and sets redraw flags.
  // Called from the main thread every tick interval.
  void UpdateAll(double dtMs);

  // Per-frame: renders all skins that need a redraw.
  // Must be called from the render thread.
  void RenderAll(double dtMs);

  // Per-frame (main loop): ticks action timers.
  void UpdateAnimations(double dtMs);

  // Dispatches Wayland events for all skins, applies pending resizes,
  // and garbage-collects closed/deactivated skins.
  // Returns false when no skins remain.
  bool HandleGlobalEvents();

  // Number of currently active skin instances.
  std::size_t ActiveCount() const { return skins_.size(); }

private:
  std::vector<std::unique_ptr<SkinInstance>> skins_;
};
