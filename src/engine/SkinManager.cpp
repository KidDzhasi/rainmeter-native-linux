#include "engine/SkinManager.hpp"

#include <iostream>

bool SkinManager::LoadSkin(const std::string &iniPath) {
  auto inst = SkinInstance::Load(iniPath);
  if (!inst) {
    std::cerr << "SkinManager: failed to load '" << iniPath << "'\n";
    return false;
  }
  skins_.push_back(std::move(inst));
  return true;
}

void SkinManager::UpdateAll(uint32_t /*deltaTimeMs*/) {
  for (auto &skin : skins_) {
    if (!skin->IsActive())
      continue;
    // On a tick boundary every skin is evaluated unconditionally,
    // matching the original behaviour where doTick || forceUpdate
    // was always true at the tick boundary.
    skin->Update();
  }
}

void SkinManager::RenderAll(double dtMs) {
  for (auto &skin : skins_) {
    if (!skin->IsActive())
      continue;
    skin->Render(dtMs);
  }
}

void SkinManager::UpdateAnimations(double dtMs) {
  for (auto &skin : skins_) {
    if (!skin->IsActive())
      continue;
    skin->UpdateAnimations(dtMs);
  }
}

bool SkinManager::HandleGlobalEvents() {
  for (auto it = skins_.begin(); it != skins_.end();) {
    SkinInstance &skin = **it;

    if (!skin.IsActive()) {
      it = skins_.erase(it);
      continue;
    }

    // Process inter-tick forced updates (e.g. from mouse-click bangs).
    if (skin.NeedsUpdate()) {
      skin.Update();
    }

    if (skin.DispatchEvents()) {
      skin.ApplyPendingResize();
      ++it;
    } else {
      // Surface closed or connection broken.
      it = skins_.erase(it);
    }
  }
  return !skins_.empty();
}
