#include "ThemeParser.hpp"

#include <cstdlib>
#include <filesystem>
#include <iostream>

#include "parser/IniLexer.hpp"
#include "parser/EnvironmentManager.hpp"

namespace {

// Lowercases an ASCII string (for case-insensitive extension/name checks).
std::string toLower(std::string s) {
  for (char &c : s) {
    if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>(c - 'A' + 'a');
    }
  }
  return s;
}

// Strips carriage returns / newlines and surrounding whitespace. Windows
// theme files carry CRLF line endings, so parsed section names and values can
// keep a trailing '\r' that breaks filesystem lookups on Linux.
std::string sanitize(const std::string &s) {
  std::size_t begin = 0;
  std::size_t end = s.size();
  auto isTrim = [](char c) {
    return c == '\r' || c == '\n' || c == ' ' || c == '\t';
  };
  while (begin < end && isTrim(s[begin])) {
    ++begin;
  }
  while (end > begin && isTrim(s[end - 1])) {
    --end;
  }
  // Also drop any stray CR/LF embedded in the middle (defensive).
  std::string out;
  out.reserve(end - begin);
  for (std::size_t i = begin; i < end; ++i) {
    if (s[i] != '\r' && s[i] != '\n') {
      out += s[i];
    }
  }
  return out;
}

// Returns the filename component of a path (after the last '/' or '\\').

std::string baseName(const std::string &path) {
  const std::size_t sep = path.find_last_of("/\\");
  return (sep == std::string::npos) ? path : path.substr(sep + 1);
}

// True if `s` ends with `suffix`.
bool endsWith(const std::string &s, const std::string &suffix) {
  return s.size() >= suffix.size() &&
         s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
}

} // namespace

bool ThemeParser::isThemeFile(const std::string &path) {
  const std::string lower = toLower(path);
  if (endsWith(lower, ".thm")) {
    return true;
  }
  return toLower(baseName(path)) == "rainmeter.ini";
}

std::string ThemeParser::defaultSkinsRoot() {
  // Delegate to the centralised EnvironmentManager so all components agree
  // on the canonical skins root (~/.config/rainmeter-native/Skins/).
  std::string root = EnvironmentManager::skinsRoot();
  // Strip the trailing '/' that EnvironmentManager guarantees, since callers
  // of defaultSkinsRoot() may append their own separators.
  if (!root.empty() && root.back() == '/') {
    root.pop_back();
  }
  return root;
}

std::string
ThemeParser::resolveCaseInsensitivePath(const std::string &basePath,
                                        const std::string &relativePath) {
  // Normalize Windows separators to '/'.
  std::string rel = relativePath;
  for (char &c : rel) {
    if (c == '\\') {
      c = '/';
    }
  }

  std::filesystem::path current(basePath);
  std::size_t start = 0;
  bool broken = false; // once a component is missing, stop scanning disk

  while (start <= rel.size()) {
    const std::size_t slash = rel.find('/', start);
    const std::string component = (slash == std::string::npos)
                                      ? rel.substr(start)
                                      : rel.substr(start, slash - start);

    if (!component.empty() && component != ".") {
      if (broken) {
        current /= component;
      } else {
        // Scan the current directory for a case-insensitive match.
        const std::string wanted = toLower(component);
        std::string matched;
        std::error_code ec;
        for (const auto &entry :
             std::filesystem::directory_iterator(current, ec)) {
          if (toLower(entry.path().filename().string()) == wanted) {
            matched = entry.path().filename().string();
            break;
          }
        }
        if (matched.empty()) {
          current /= component;
          broken = true;
        } else {
          current /= matched;
        }
      }
    }

    if (slash == std::string::npos) {
      break;
    }
    start = slash + 1;
  }

  return current.string();
}

std::string ThemeParser::resolveWidgetIni(const std::string &config,
                                          const std::string &iniFile,
                                          const std::string &skinsRoot) {

  // Normalize backslashes (Rainmeter config paths) to forward slashes.
  std::string rel = config;
  for (char &c : rel) {
    if (c == '\\') {
      c = '/';
    }
  }
  // Trim any leading/trailing slashes.
  while (!rel.empty() && rel.front() == '/') {
    rel.erase(rel.begin());
  }
  while (!rel.empty() && rel.back() == '/') {
    rel.pop_back();
  }

  std::string root = skinsRoot;
  if (!root.empty() && root.back() == '/') {
    root.pop_back();
  }

  // If the config already names a .ini file, resolve it directly.
  if (endsWith(toLower(rel), ".ini")) {
    return resolveCaseInsensitivePath(root, rel);
  }

  // Resolve the skin folder path case-insensitively first.
  const std::string folderPath = resolveCaseInsensitivePath(root, rel);

  // If an explicit IniFile= hint was provided, append it to the folder.
  if (!iniFile.empty()) {
    return resolveCaseInsensitivePath(folderPath, iniFile);
  }

  // No explicit hint: scan the resolved folder for the first *.ini file.
  std::error_code ec;
  for (const auto &entry :
       std::filesystem::directory_iterator(folderPath, ec)) {
    if (entry.is_regular_file(ec)) {
      const std::string ext = toLower(entry.path().extension().string());
      if (ext == ".ini") {
        return entry.path().string();
      }
    }
  }

  // Nothing found: fall back to the old "<folder>/<leaf>.ini" guess so the
  // caller still gets a path (and a clear open-failure message later).
  const std::string leaf = baseName(rel);
  return folderPath + "/" + leaf + ".ini";
}

bool ThemeParser::parse(const std::string &path) {
  return parse(path, defaultSkinsRoot());
}

bool ThemeParser::parse(const std::string &path, const std::string &skinsRoot) {
  widgets_.clear();

  IniLexer theme;
  if (!theme.parseFile(path)) {
    return false;
  }

  for (const auto &[section, keys] : theme.data()) {
    auto activeIt = keys.find("Active");
    if (activeIt == keys.end()) {
      continue; // Not an active-skin entry.
    }

    // Sanitize parsed strings up front: Windows CRLF endings can leave a
    // trailing '\r' clinging to section names and values, which would break
    // both the integer parse and the filesystem lookup.
    const std::string cleanSection = sanitize(section);
    const std::string cleanActive = sanitize(activeIt->second);

    // Active is considered "on" if it parses to a value greater than zero.
    int active = 0;
    try {
      active = std::stoi(cleanActive);
    } catch (...) {
      active = 0;
    }
    if (active <= 0) {
      continue;
    }

    // Extract and sanitize the optional IniFile= hint.
    std::string cleanIniFile;
    auto iniFileIt = keys.find("IniFile");
    if (iniFileIt != keys.end()) {
      cleanIniFile = sanitize(iniFileIt->second);
    }

    Widget w;
    w.config = cleanSection;
    w.iniPath = resolveWidgetIni(cleanSection, cleanIniFile, skinsRoot);
    widgets_.push_back(std::move(w));
  }

  return true;
}
