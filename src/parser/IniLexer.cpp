#include "IniLexer.hpp"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>

namespace fs = std::filesystem;

namespace {
// ASCII whitespace characters trimmed from lines, keys, and values.
constexpr std::string_view kWhitespace = " \t\r\n\f\v";

// Strips all carriage-return characters from an owned string so that
// Windows CRLF leftovers never corrupt stored keys, section names, or values.
inline void stripCR(std::string &s) {
  s.erase(std::remove(s.begin(), s.end(), '\r'), s.end());
}

// Converts Windows backslash path separators to forward slashes so that paths
// read from Rainmeter skins (authored on Windows) work on Linux, where
// std::filesystem::path treats '\\' as a literal character.
inline void normalizePathSeparators(std::string &s) {
  std::replace(s.begin(), s.end(), '\\', '/');
}

// Maximum @include recursion depth (guards against include cycles).
constexpr int kMaxIncludeDepth = 16;

// Case-insensitive ASCII prefix test.
bool startsWithIgnoreCase(std::string_view s, std::string_view prefix) {
  if (s.size() < prefix.size()) {
    return false;
  }
  for (std::size_t i = 0; i < prefix.size(); ++i) {
    char a = s[i];
    char b = prefix[i];
    if (a >= 'A' && a <= 'Z') {
      a = static_cast<char>(a - 'A' + 'a');
    }
    if (b >= 'A' && b <= 'Z') {
      b = static_cast<char>(b - 'A' + 'a');
    }
    if (a != b) {
      return false;
    }
  }
  return true;
}
} // namespace

IniLexer::IniLexer(const std::string &filePath) { parseFile(filePath); }

std::string_view IniLexer::trim(std::string_view sv) {
  const auto first = sv.find_first_not_of(kWhitespace);
  if (first == std::string_view::npos) {
    return {};
  }
  const auto last = sv.find_last_not_of(kWhitespace);
  return sv.substr(first, last - first + 1);
}

std::string IniLexer::utf16ToUtf8(const char *bytes, std::size_t byteCount, bool bigEndian) {
  std::string out;
  out.reserve(byteCount / 2);

  const std::size_t units = byteCount / 2;
  auto readUnit = [&](std::size_t i) -> std::uint32_t {
    const auto b0 = static_cast<unsigned char>(bytes[2 * i]);
    const auto b1 = static_cast<unsigned char>(bytes[2 * i + 1]);
    if (bigEndian) {
        return (static_cast<std::uint32_t>(b0) << 8) | static_cast<std::uint32_t>(b1);
    } else {
        return static_cast<std::uint32_t>(b0) | (static_cast<std::uint32_t>(b1) << 8);
    }
  };

  for (std::size_t i = 0; i < units;) {
    std::uint32_t cp = readUnit(i);
    ++i;

    // Surrogate pair handling.
    if (cp >= 0xD800 && cp <= 0xDBFF && i < units) {
      const std::uint32_t low = readUnit(i);
      if (low >= 0xDC00 && low <= 0xDFFF) {
        cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00);
        ++i;
      }
    }

    // Encode code point as UTF-8.
    if (cp < 0x80) {
      out.push_back(static_cast<char>(cp));
    } else if (cp < 0x800) {
      out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else if (cp < 0x10000) {
      out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else {
      out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    }
  }

  return out;
}

bool IniLexer::readFileUtf8(const std::string &filePath, std::string &out) {
  // Always open in binary mode so BOM bytes and CRLFs are preserved.
  std::ifstream file(filePath, std::ios::in | std::ios::binary);
  if (!file.is_open()) {
    return false;
  }

  // Peek at the first two bytes to detect a UTF-16 BOM.
  // LE BOM: 0xFF 0xFE
  // BE BOM: 0xFE 0xFF
  unsigned char bom[2] = {0, 0};
  file.read(reinterpret_cast<char *>(bom), 2);
  const std::streamsize bomRead = file.gcount();

  if (bomRead == 2 && ((bom[0] == 0xFF && bom[1] == 0xFE) || (bom[0] == 0xFE && bom[1] == 0xFF))) {
    bool bigEndian = (bom[0] == 0xFE);
    // UTF-16: read the remainder (after the BOM) as char16_t data and
    // convert it to UTF-8. The stream is already positioned past the BOM.
    std::ostringstream buffer;
    buffer << file.rdbuf();
    const std::string raw = buffer.str();
    out = utf16ToUtf8(raw.data(), raw.size(), bigEndian);
    return true;
  }

  // Not a UTF-16 BOM. Reading two bytes may have set EOF/fail bits on very
  // small files, so reset the stream state before seeking back to the start.
  file.clear();
  file.seekg(0, std::ios::beg);

  std::ostringstream buffer;
  buffer << file.rdbuf();
  std::string raw = buffer.str();

  // Strip a UTF-8 BOM (0xEF 0xBB 0xBF) if present.
  if (raw.size() >= 3 && static_cast<unsigned char>(raw[0]) == 0xEF &&
      static_cast<unsigned char>(raw[1]) == 0xBB &&
      static_cast<unsigned char>(raw[2]) == 0xBF) {
    out = raw.substr(3);
    return true;
  }

  out = std::move(raw);
  return true;
}

std::string IniLexer::computeResourcesPath(const std::string &skinFilePath) {
  // Rainmeter layout: <SkinRoot>/<Skin>/.../skin.ini with a sibling
  // @Resources at the skin root. We walk up from the file's directory
  // looking for an existing @Resources directory; if none is found we
  // default to "<file dir>/@Resources/".
  std::error_code ec;
  fs::path dir = fs::path(skinFilePath).parent_path();

  auto toLowerStr = [](const std::string &s) {
    std::string out = s;
    for (char &c : out) {
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return out;
  };

  fs::path probe = dir;
  for (int i = 0; i < 8 && !probe.empty(); ++i) {
    // Check case-insensitively for @Resources
    std::string matchedRes;
    if (fs::is_directory(probe, ec)) {
      for (const auto &entry : fs::directory_iterator(probe, ec)) {
        if (entry.is_directory(ec) && toLowerStr(entry.path().filename().string()) == "@resources") {
          matchedRes = entry.path().filename().string();
          break;
        }
      }
    }

    if (!matchedRes.empty()) {
      fs::path candidate = probe / matchedRes;
      std::string s = candidate.string();
      if (!s.empty() && s.back() != '/') {
        s.push_back('/');
      }
      return s;
    }
    if (!probe.has_parent_path()) {
      break;
    }
    probe = probe.parent_path();
  }

  // Fallback: assume @Resources sits beside the loaded file.
  std::string s = (dir / "@Resources").string();
  if (!s.empty() && s.back() != '/') {
    s.push_back('/');
  }
  return s;
}

std::string IniLexer::expandMacros(std::string_view value) const {
  constexpr std::string_view kMacro = "#@#";
  if (value.find(kMacro) == std::string_view::npos) {
    return std::string(value);
  }

  std::string out;
  out.reserve(value.size());
  std::size_t pos = 0;
  while (pos < value.size()) {
    const auto next = value.find(kMacro, pos);
    if (next == std::string_view::npos) {
      out.append(value.substr(pos));
      break;
    }
    out.append(value.substr(pos, next - pos));
    out.append(resourcesPath_);
    pos = next + kMacro.size();
  }
  return out;
}

std::string IniLexer::expandBuiltins(std::string_view value) const {
  // Scan for #NAME# tokens and resolve them against the EnvironmentManager.
  // This runs BEFORE expandMacros (which handles the special #@# syntax) and
  // before user [Variables] resolution.  Only recognised built-in names are
  // replaced; everything else passes through untouched.
  std::string out;
  out.reserve(value.size());
  for (std::size_t i = 0; i < value.size();) {
    if (value[i] == '#') {
      const std::size_t close = value.find('#', i + 1);
      if (close != std::string_view::npos && close > i + 1) {
        const std::string name(value.substr(i + 1, close - i - 1));
        // Skip the special #@# macro — that is handled by expandMacros.
        if (name != "@") {
          auto resolved = builtins_.resolve(name);
          if (resolved) {
            out += *resolved;
            i = close + 1;
            continue;
          }
        }
      }
    }
    out += value[i];
    ++i;
  }
  return out;
}

std::string
IniLexer::resolveCaseInsensitivePath(const std::string &basePath,
                                     const std::string &relativePath) {
  // Normalize Windows separators to '/'.
  std::string rel = relativePath;
  std::replace(rel.begin(), rel.end(), '\\', '/');

  fs::path current(basePath);
  std::size_t start = 0;
  bool broken = false;

  // Lowercase helper for ASCII comparison.
  auto toLowerStr = [](const std::string &s) {
    std::string out = s;
    for (char &c : out) {
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return out;
  };

  while (start <= rel.size()) {
    const std::size_t slash = rel.find('/', start);
    const std::string component = (slash == std::string::npos)
                                      ? rel.substr(start)
                                      : rel.substr(start, slash - start);

    if (!component.empty() && component != ".") {
      if (broken) {
        current /= component;
      } else {
        // Scan the directory for a case-insensitive match.
        const std::string wanted = toLowerStr(component);
        std::string matched;
        std::error_code ec;
        if (fs::is_directory(current, ec)) {
          for (const auto &entry : fs::directory_iterator(current, ec)) {
            if (toLowerStr(entry.path().filename().string()) == wanted) {
              matched = entry.path().filename().string();
              break;
            }
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

bool IniLexer::parseFile(const std::string &filePath, bool clear) {
  if (clear) {
    data_.clear();
    sectionOrder_.clear();
  }

  std::string content;
  if (!readFileUtf8(filePath, content)) {
    return false;
  }

  builtins_ = EnvironmentManager(filePath);
  resourcesPath_ = computeResourcesPath(filePath);
  const std::string baseDir = fs::path(filePath).parent_path().string();
  return parseContent(content, baseDir, 0);
}

bool IniLexer::parseString(std::string_view content) {
  data_.clear();
  sectionOrder_.clear();
  // No file context: #@# expands to whatever resourcesPath_ currently holds
  // (empty by default), and relative @include targets resolve against ".".
  return parseContent(content, ".", 0, "");
}

bool IniLexer::parseContent(std::string_view content,
                            const std::string &baseDir, int depth, const std::string& initialSection) {
  std::string currentSection = initialSection; // inherit from parent file if any
  std::size_t pos = 0;
  const std::size_t size = content.size();

  while (pos < size) {
    // Extract the next line (up to '\n').
    std::size_t eol = content.find('\n', pos);
    std::string_view rawLine = (eol == std::string_view::npos)
                                   ? content.substr(pos)
                                   : content.substr(pos, eol - pos);
    pos = (eol == std::string_view::npos) ? size : eol + 1;

    // Strip a trailing '\r' left over from Windows CRLF line endings before
    // the general whitespace trim; this is safer than relying on trim()
    // alone because it guarantees \r can never survive inside a section
    // name, key, or value.
    if (!rawLine.empty() && rawLine.back() == '\r') {
      rawLine.remove_suffix(1);
    }

    std::string_view line = trim(rawLine);

    // Skip blank lines and comments (lines beginning with ';').
    if (line.empty() || line.front() == ';') {
      continue;
    }

    // Section header: [Name]
    if (line.front() == '[') {
      const auto close = line.find(']');
      if (close != std::string_view::npos) {
        std::string_view name = trim(line.substr(1, close - 1));
        currentSection.assign(name);
        stripCR(currentSection);
        auto [it, inserted] = data_.try_emplace(currentSection);
        if (inserted) {
          sectionOrder_.push_back(currentSection);
        }
      }
      continue;
    }

    // Key=Value pair.
    const auto eq = line.find('=');
    if (eq == std::string_view::npos) {
      continue;
    }

    std::string_view keyView = trim(line.substr(0, eq));
    std::string_view rawValue = trim(line.substr(eq + 1));
    if (keyView.empty()) {
      continue;
    }

    // Build owned key and value strings, scrubbing any stray \r and
    // normalising Windows backslash path separators to '/'.
    std::string key(keyView);
    stripCR(key);

    // Expansion pipeline: built-in env vars first (#SKINSPATH# etc.),
    // then the #@# macro, then sanitise.
    std::string value = expandBuiltins(rawValue);
    value = expandMacros(value);
    stripCR(value);
    normalizePathSeparators(value);

    // Recursive @include (e.g. @include, @include2 = #@#Settings.inc).
    if (startsWithIgnoreCase(key, "@include")) {
      if (depth >= kMaxIncludeDepth || value.empty()) {
        continue;
      }
      // Resolve the include target: normalise any remaining Windows
      // backslashes, then treat absolute paths as-is and resolve relative
      // ones against the current file's directory.
      normalizePathSeparators(value);
      fs::path target(value);
      if (!target.is_absolute()) {
        target = fs::path(baseDir) / target;
      }

      std::string includeContent;
      std::string targetStr = target.string();
      if (!readFileUtf8(targetStr, includeContent)) {
        // Fallback: case-insensitive resolution.  Split the target into the
        // directory and filename portions, then use the directory_iterator
        // based resolver from ThemeParser to find the true-cased path.
        fs::path parentDir = target.parent_path();
        std::string filename = target.filename().string();
        if (!parentDir.empty() && !filename.empty()) {
          std::string ciPath = resolveCaseInsensitivePath(parentDir.string(), filename);
          if (ciPath != targetStr) {
            readFileUtf8(ciPath, includeContent);
            targetStr = ciPath;
          }
        }
      }
      if (!includeContent.empty()) {
        const std::string includeBase = fs::path(targetStr).parent_path().string();
        parseContent(includeContent, includeBase, depth + 1, currentSection);
      }
      continue;
    }

    data_[currentSection].insert_or_assign(std::move(key), std::move(value));
  }

  return true;
}

std::optional<std::string> IniLexer::get(std::string_view section,
                                         std::string_view key) const {
  const auto sectionIt = data_.find(std::string(section));
  if (sectionIt == data_.end()) {
    return std::nullopt;
  }
  const auto keyIt = sectionIt->second.find(std::string(key));
  if (keyIt == sectionIt->second.end()) {
    return std::nullopt;
  }
  return keyIt->second;
}

std::optional<std::string>
IniLexer::getCaseInsensitive(std::string_view section,
                             std::string_view key) const {
  // Lowercase helper for ASCII comparison.
  auto lower = [](std::string_view sv) {
    std::string out(sv);
    for (char &c : out) {
      if (c >= 'A' && c <= 'Z') {
        c = static_cast<char>(c - 'A' + 'a');
      }
    }
    return out;
  };

  const std::string wantSection = lower(section);
  const std::string wantKey = lower(key);

  for (const auto &[secName, keys] : data_) {
    if (lower(secName) != wantSection) {
      continue;
    }
    for (const auto &[keyName, value] : keys) {
      if (lower(keyName) == wantKey) {
        return value;
      }
    }
  }
  return std::nullopt;
}

std::string IniLexer::getOr(std::string_view section, std::string_view key,
                            std::string_view fallback) const {
  auto val = get(section, key);
  return val ? *val : std::string(fallback);
}

void IniLexer::setVariable(const std::string &name, const std::string &value) {
  // Rainmeter variable names are case-insensitive but typically stored as they
  // appear. To ensure we overwrite or match existing case-insensitively, we
  // could search for an existing variant, or just store it. Since
  // `getCaseInsensitive` is used for [Variables] lookup, we can just insert it.
  // We should try to overwrite an existing case-variant if it exists.
  std::string lowerName = name;
  for (char &c : lowerName) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }

  auto secIt = data_.find("Variables");
  if (secIt == data_.end()) {
    data_["Variables"][name] = value;
    return;
  }

  // Look for existing key with same lowercase.
  for (auto &kv : secIt->second) {
    std::string existingLower = kv.first;
    for (char &c : existingLower) {
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    if (existingLower == lowerName) {
      secIt->second.erase(kv.first);
      break;
    }
  }
  secIt->second[name] = value;
}

bool IniLexer::hasSection(std::string_view section) const {
  return data_.find(std::string(section)) != data_.end();
}

bool IniLexer::writeKeyValue(const std::string& filePath, const std::string& section, const std::string& key, const std::string& value) {
  std::string content;
  if (!readFileUtf8(filePath, content)) {
    // If the file doesn't exist, we can create it
    content = "";
  }

  // Parse lines to find the section and key
  std::vector<std::string> lines;
  std::size_t pos = 0;
  while (pos < content.size()) {
    std::size_t eol = content.find('\n', pos);
    if (eol == std::string::npos) {
      lines.push_back(content.substr(pos));
      break;
    }
    lines.push_back(content.substr(pos, eol - pos + 1));
    pos = eol + 1;
  }

  // Case-insensitive compare helpers
  auto toLower = [](std::string_view s) {
    std::string out(s);
    for (char &c : out) {
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return out;
  };
  auto trim = [](std::string_view sv) {
    const auto first = sv.find_first_not_of(" \t\r\n\f\v");
    if (first == std::string_view::npos) return std::string_view{};
    const auto last = sv.find_last_not_of(" \t\r\n\f\v");
    return sv.substr(first, last - first + 1);
  };

  std::string wantSection = toLower(section);
  std::string wantKey = toLower(key);
  
  bool inTargetSection = false;
  bool keyFound = false;
  int targetSectionLine = -1;
  int lastSectionLine = -1;

  for (std::size_t i = 0; i < lines.size(); ++i) {
    std::string_view lineView = trim(lines[i]);
    if (lineView.empty() || lineView.front() == ';') continue;

    if (lineView.front() == '[') {
      const auto close = lineView.find(']');
      if (close != std::string_view::npos) {
        std::string name(lineView.substr(1, close - 1));
        inTargetSection = (toLower(name) == wantSection);
        if (inTargetSection) {
          targetSectionLine = i;
        }
        lastSectionLine = i;
      }
      continue;
    }

    if (inTargetSection) {
      const auto eq = lineView.find('=');
      if (eq != std::string_view::npos) {
        std::string_view keyView = trim(lineView.substr(0, eq));
        if (toLower(keyView) == wantKey) {
          // Replace this line
          lines[i] = std::string(key) + "=" + std::string(value) + "\n";
          keyFound = true;
          break;
        }
      }
    }
  }

  if (!keyFound) {
    std::string newLine = std::string(key) + "=" + std::string(value) + "\n";
    if (targetSectionLine != -1) {
      // Find where this section ends
      std::size_t insertIdx = targetSectionLine + 1;
      while (insertIdx < lines.size()) {
        std::string_view lineView = trim(lines[insertIdx]);
        if (!lineView.empty() && lineView.front() == '[') {
          break; // Start of next section
        }
        insertIdx++;
      }
      lines.insert(lines.begin() + insertIdx, newLine);
    } else {
      // Section doesn't exist, append it at the end
      if (!lines.empty() && trim(lines.back()).length() > 0) {
          lines.push_back("\n");
      }
      lines.push_back("[" + section + "]\n");
      lines.push_back(newLine);
    }
  }

  std::ofstream out(filePath, std::ios::out | std::ios::binary | std::ios::trunc);
  if (!out.is_open()) return false;
  for (const auto& line : lines) {
    out.write(line.data(), line.size());
  }
  return true;
}
