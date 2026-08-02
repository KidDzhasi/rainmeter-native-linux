#include "engine/SkinManager.hpp"

#include <iostream>
#include "evaluator/SysfsParser.hpp"

bool SkinManager::LoadSkin(const std::string &iniPath, int overrideMonitor) {
  auto inst = SkinInstance::Load(iniPath, overrideMonitor);
  if (!inst) {
    std::cerr << "SkinManager: failed to load '" << iniPath << "'\n";
    return false;
  }
  
  // Register custom fonts from @Resources/Fonts
  std::filesystem::path resPath = inst->GetResourcesPath();
  if (!resPath.empty()) {
      std::string fontsDir = (resPath / "Fonts").string();
      if (std::filesystem::exists(fontsDir)) {
          inst->GetRenderer().registerFontDirectory(fontsDir);
      }
  }
  
  skins_.push_back(std::move(inst));
  return true;
}

void SkinManager::UpdateAll(double dtMs) {
  SysfsParser::getInstance().update();
  for (auto &skin : skins_) {
    if (!skin->IsActive())
      continue;
    // On a tick boundary every skin is evaluated unconditionally,
    // matching the original behaviour where doTick || forceUpdate
    // was always true at the tick boundary.
    skin->Update(dtMs);
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
      skin.Update(0.0);
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
