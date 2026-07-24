#pragma once

#include <optional>
#include <string>
#include <unordered_map>

// EnvironmentManager provides Rainmeter's hardcoded built-in variables that
// exist independently of any [Variables] section in a skin file.
//
// Each skin file gets its own EnvironmentManager instance, constructed from the
// absolute path to the skin .ini.  The manager computes and caches:
//
//   #SKINSPATH#        — the global skins root directory
//   #@#                — this skin's @Resources/ folder (same as IniLexer's
//                        resourcesPath_, kept here for the new expansion pass)
//   #CURRENTFILE#      — the filename of the skin .ini  (e.g. "Clock.ini")
//   #CURRENTPATH#      — the directory containing the skin .ini (trailing /)
//   #ROOTCONFIGPATH#   — the skin's root folder under #SKINSPATH# (trailing /)
//
// All paths use forward slashes and are absolute.
//
// Usage:
//   EnvironmentManager env(skinFilePath);
//   auto val = env.resolve("SKINSPATH");   // -> "~/.config/.../Skins/"
class EnvironmentManager {
public:
  EnvironmentManager() = default;

  // Constructs and populates built-in variables from the skin file path.
  explicit EnvironmentManager(const std::string &skinFilePath);

  // Case-insensitive lookup of a built-in variable by name (without the
  // surrounding '#' delimiters).  Returns std::nullopt if the name is not a
  // recognised built-in.
  std::optional<std::string> resolve(const std::string &name) const;

  // The canonical skins root directory:
  //   $XDG_CONFIG_HOME/rainmeter-native/Skins/   (default ~/.config/...)
  // Shared across all EnvironmentManager instances.
  static std::string skinsRoot();

  // Read-only access to the full table (for debugging / logging).
  const std::unordered_map<std::string, std::string> &table() const noexcept {
    return vars_;
  }

private:
  // Keys are stored in lowercase for case-insensitive matching.
  std::unordered_map<std::string, std::string> vars_;
};
