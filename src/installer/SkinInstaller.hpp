#pragma once

#include <string>

// SkinInstaller extracts Rainmeter .rmskin packages into the standard Linux
// user data directory (~/.local/share/rainmeter-native/).
//
// A .rmskin file is a ZIP archive with a small custom footer appended by
// Rainmeter's packager. libzip locates the central directory from the end of
// the file, so it opens these archives correctly and the footer is ignored.
//
// This installer reads RMSKIN.ini for metadata (Name/Author/Version) and
// extracts everything under the archive's Skins/ directory into the local
// Skins/ folder.
class SkinInstaller {
public:
  SkinInstaller() = default;

  // Installs the .rmskin at `rmskinPath`. Returns true on success.
  bool install(const std::string &rmskinPath);

  // The resolved installation root (~/.local/share/rainmeter-native).
  static std::string dataDirectory();

private:
  // Ensures the target directory tree exists.
  bool ensureDirectories(const std::string &skinsDir) const;
};
