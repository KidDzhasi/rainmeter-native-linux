#pragma once

#include <string>
#include <vector>

// ThemeParser reads a Rainmeter theme/layout file (a .thm or the classic
// Rainmeter.ini) and produces the list of active skin widgets it references.
//
// A layout file is an INI whose sections describe which skins are loaded and
// where. Each section that represents an active skin carries an "Active"
// key (> 0 means shown) and identifies its skin folder/config. For example:
//
//   [illustro\Clock]
//   Active=1
//
//   [illustro\System]
//   Active=0
//
// The section name (with '\' folder separators) is the config path relative
// to the Skins root. ThemeParser resolves each active entry to the absolute
// path of its widget .ini under:
//   ~/.local/share/rainmeter-native/Skins/<config>/<file>.ini
class ThemeParser {
public:
  // One resolved active widget from the theme.
  struct Widget {
    std::string config;  // e.g. "illustro\\Clock" (the theme section name)
    std::string iniPath; // absolute path to the widget's .ini file
  };

  ThemeParser() = default;

  // True if `path` looks like a theme/layout file rather than a single skin.
  // Matches a ".thm" extension or a filename of "Rainmeter.ini"
  // (case-insensitive).
  static bool isThemeFile(const std::string &path);

  // Parses the theme file at `path`. Every section with Active > 0 becomes a
  // Widget resolved against the Skins root. Returns false if the file could
  // not be opened. The skins root defaults to
  // ~/.local/share/rainmeter-native/Skins.
  bool parse(const std::string &path);

  // Same as parse() but with an explicit skins-root directory (used for
  // testing or non-default installs).
  bool parse(const std::string &path, const std::string &skinsRoot);

  // The active widgets discovered by the last parse().
  const std::vector<Widget> &widgets() const noexcept { return widgets_; }

  // The default skins root: ~/.local/share/rainmeter-native/Skins.
  static std::string defaultSkinsRoot();

  // Resolves `relativePath` under `basePath`, matching each path component
  // case-insensitively against the real (case-sensitive) filesystem. Windows
  // backslashes are normalized to '/'. Reusable for e.g. locating a skin's
  // @Resources/Fonts directory. If a component is not found on disk, the
  // remaining components are appended verbatim (best-effort).
  static std::string
  resolveCaseInsensitivePath(const std::string &basePath,
                             const std::string &relativePath);

private:
  // Given a theme section (config), an optional explicit IniFile= hint, and
  // the Skins root, works out the absolute path to the widget .ini.
  //   * If `iniFile` is provided, it is appended to the resolved skin folder.
  //   * Else if `config` already names a .ini file, that path is used.
  //   * Else the resolved folder is scanned and the first *.ini found is used.
  // All path components are matched case-insensitively against the real
  // (case-sensitive) filesystem.
  static std::string resolveWidgetIni(const std::string &config,
                                      const std::string &iniFile,
                                      const std::string &skinsRoot);

  std::vector<Widget> widgets_;
};
