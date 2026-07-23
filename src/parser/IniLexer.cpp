#include "IniLexer.hpp"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <sstream>

namespace fs = std::filesystem;

namespace {
// ASCII whitespace characters trimmed from lines, keys, and values.
constexpr std::string_view kWhitespace = " \t\r\n\f\v";

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

std::string IniLexer::utf16leToUtf8(const char *bytes, std::size_t byteCount) {
  std::string out;
  out.reserve(byteCount / 2);

  const std::size_t units = byteCount / 2;
  auto readUnit = [&](std::size_t i) -> std::uint32_t {
    const auto lo = static_cast<unsigned char>(bytes[2 * i]);
    const auto hi = static_cast<unsigned char>(bytes[2 * i + 1]);
    return static_cast<std::uint32_t>(lo) |
           (static_cast<std::uint32_t>(hi) << 8);
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

  // Peek at the first two bytes to detect a UTF-16 LE BOM (0xFF 0xFE).
  unsigned char bom[2] = {0, 0};
  file.read(reinterpret_cast<char *>(bom), 2);
  const std::streamsize bomRead = file.gcount();

  if (bomRead == 2 && bom[0] == 0xFF && bom[1] == 0xFE) {
    // UTF-16 LE: read the remainder (after the BOM) as char16_t data and
    // convert it to UTF-8. The stream is already positioned past the BOM.
    std::ostringstream buffer;
    buffer << file.rdbuf();
    const std::string raw = buffer.str();
    out = utf16leToUtf8(raw.data(), raw.size());
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

  fs::path probe = dir;
  for (int i = 0; i < 8 && !probe.empty(); ++i) {
    fs::path candidate = probe / "@Resources";
    if (fs::exists(candidate, ec) && fs::is_directory(candidate, ec)) {
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

bool IniLexer::parseFile(const std::string &filePath) {
  data_.clear();

  std::string content;
  if (!readFileUtf8(filePath, content)) {
    return false;
  }

  resourcesPath_ = computeResourcesPath(filePath);
  const std::string baseDir = fs::path(filePath).parent_path().string();
  return parseContent(content, baseDir, 0);
}

bool IniLexer::parseString(std::string_view content) {
  data_.clear();
  // No file context: #@# expands to whatever resourcesPath_ currently holds
  // (empty by default), and relative @include targets resolve against ".".
  return parseContent(content, ".", 0);
}

bool IniLexer::parseContent(std::string_view content,
                            const std::string &baseDir, int depth) {
  std::string currentSection; // empty => keys before any [Section]
  std::size_t pos = 0;
  const std::size_t size = content.size();

  while (pos < size) {
    // Extract the next line (up to '\n'); handle trailing '\r' via trim.
    std::size_t eol = content.find('\n', pos);
    std::string_view rawLine = (eol == std::string_view::npos)
                                   ? content.substr(pos)
                                   : content.substr(pos, eol - pos);
    pos = (eol == std::string_view::npos) ? size : eol + 1;

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
        data_.try_emplace(currentSection);
      }
      continue;
    }

    // Key=Value pair.
    const auto eq = line.find('=');
    if (eq == std::string_view::npos) {
      continue;
    }

    std::string_view key = trim(line.substr(0, eq));
    std::string_view rawValue = trim(line.substr(eq + 1));
    if (key.empty()) {
      continue;
    }

    // Expand the #@# macro into the value.
    const std::string value = expandMacros(rawValue);

    // Recursive @include (e.g. @include, @include2 = #@#Settings.inc).
    if (startsWithIgnoreCase(key, "@include")) {
      if (depth >= kMaxIncludeDepth || value.empty()) {
        continue;
      }
      // Resolve the include target: absolute paths as-is, otherwise
      // relative to the current file's directory.
      fs::path target(value);
      if (!target.is_absolute()) {
        target = fs::path(baseDir) / target;
      }

      std::string includeContent;
      if (readFileUtf8(target.string(), includeContent)) {
        const std::string includeBase = target.parent_path().string();
        parseContent(includeContent, includeBase, depth + 1);
      }
      continue;
    }

    data_[currentSection].insert_or_assign(std::string(key), value);
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

  if (auto value = get(section, key)) {
    return *value;
  }
  return std::string(fallback);
}

bool IniLexer::hasSection(std::string_view section) const {
  return data_.find(std::string(section)) != data_.end();
}
