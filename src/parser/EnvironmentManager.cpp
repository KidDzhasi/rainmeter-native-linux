#include "EnvironmentManager.hpp"

#include <algorithm>
#include <cstdlib>
#include <filesystem>

namespace fs = std::filesystem;

namespace {
// ASCII-lowercase a string for case-insensitive key storage / lookup.
std::string toLower(std::string s) {
  for (char &c : s) {
    if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>(c - 'A' + 'a');
    }
  }
  return s;
}

// Ensure a directory path ends with a trailing '/'.
std::string ensureTrailingSlash(std::string s) {
  if (!s.empty() && s.back() != '/') {
    s.push_back('/');
  }
  return s;
}

// Replace Windows backslashes with forward slashes.
void normalizeSlashes(std::string &s) {
  std::replace(s.begin(), s.end(), '\\', '/');
}
} // namespace

// ---------------------------------------------------------------------------
// Static: canonical skins root
// ---------------------------------------------------------------------------

std::string EnvironmentManager::skinsRoot() {
  const char *xdg = std::getenv("XDG_CONFIG_HOME");
  fs::path base;
  if (xdg != nullptr && xdg[0] != '\0') {
    base = fs::path(xdg);
  } else {
    const char *home = std::getenv("HOME");
    base = fs::path(home != nullptr ? home : ".") / ".config";
  }
  std::string root = (base / "rainmeter-native" / "Skins").string();
  normalizeSlashes(root);
  return ensureTrailingSlash(root);
}

// ---------------------------------------------------------------------------
// Per-skin construction
// ---------------------------------------------------------------------------

EnvironmentManager::EnvironmentManager(const std::string &skinFilePath) {
  // --- #SKINSPATH# ---
  std::string skinsPath = skinsRoot();
  vars_["skinspath"] = skinsPath;

  // --- #@# (the skin's @Resources/ directory) ---
  // Walk up from the skin file's directory looking for an existing @Resources
  // folder; fall back to "<file dir>/@Resources/".
  fs::path skinDir = fs::path(skinFilePath).parent_path();
  std::string atResources;
  {
    std::error_code ec;
    fs::path probe = skinDir;
    bool found = false;
    for (int i = 0; i < 8 && !probe.empty(); ++i) {
      fs::path candidate = probe / "@Resources";
      if (fs::exists(candidate, ec) && fs::is_directory(candidate, ec)) {
        atResources = ensureTrailingSlash(candidate.string());
        found = true;
        break;
      }
      if (!probe.has_parent_path()) {
        break;
      }
      probe = probe.parent_path();
    }
    if (!found) {
      atResources = ensureTrailingSlash((skinDir / "@Resources").string());
    }
  }
  normalizeSlashes(atResources);
  vars_["@"] = atResources;

  // --- #CURRENTFILE# ---
  std::string currentFile = fs::path(skinFilePath).filename().string();
  normalizeSlashes(currentFile);
  vars_["currentfile"] = currentFile;

  // --- #CURRENTPATH# ---
  std::string currentPath = ensureTrailingSlash(skinDir.string());
  normalizeSlashes(currentPath);
  vars_["currentpath"] = currentPath;

  // --- #ROOTCONFIGPATH# ---
  // The skin's top-level folder under #SKINSPATH#.  If the skin file lives at
  //   <SKINSPATH>/MySuite/SubFolder/skin.ini
  // then ROOTCONFIGPATH is <SKINSPATH>/MySuite/.
  // If we can't determine the relationship (e.g. skin loaded from outside the
  // skins root) we fall back to #CURRENTPATH#.
  std::string rootConfig = currentPath; // default fallback
  {
    std::error_code ec;
    fs::path canonical_skin = fs::weakly_canonical(skinDir, ec);
    fs::path canonical_root = fs::weakly_canonical(fs::path(skinsPath), ec);
    std::string skinStr = ensureTrailingSlash(canonical_skin.string());
    std::string rootStr = ensureTrailingSlash(canonical_root.string());
    normalizeSlashes(skinStr);
    normalizeSlashes(rootStr);

    // Check if skinStr starts with rootStr.
    if (skinStr.size() >= rootStr.size() &&
        skinStr.compare(0, rootStr.size(), rootStr) == 0) {
      // The remainder after the skins root is e.g. "MySuite/SubFolder/".
      // Take only the first component.
      std::string remainder = skinStr.substr(rootStr.size());
      auto slash = remainder.find('/');
      if (slash != std::string::npos) {
        rootConfig = rootStr + remainder.substr(0, slash + 1);
      } else if (!remainder.empty()) {
        rootConfig = rootStr + ensureTrailingSlash(remainder);
      }
    }
  }
  vars_["rootconfigpath"] = rootConfig;
}

// ---------------------------------------------------------------------------
// Lookup
// ---------------------------------------------------------------------------

std::optional<std::string>
EnvironmentManager::resolve(const std::string &name) const {
  auto it = vars_.find(toLower(name));
  if (it != vars_.end()) {
    return it->second;
  }
  return std::nullopt;
}
