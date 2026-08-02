#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "EnvironmentManager.hpp"

// IniLexer parses Rainmeter .ini skin files.
//
// It reads a file from disk, splits it into [Sections] containing
// Key=Value pairs, trims surrounding whitespace, and ignores comment
// lines that begin with ';'. Parsed data is stored in a nested map:
//   section -> (key -> value)
//
// Advanced Rainmeter features supported:
//   * UTF-16 LE input (with BOM) is transparently converted to UTF-8.
//   * The #@# macro in values expands to the skin's @Resources/ directory.
//   * @includeN keys recursively parse and merge another .inc/.ini file.
class IniLexer {
public:
  using SectionMap = std::unordered_map<std::string, std::string>;
  using DataMap = std::unordered_map<std::string, SectionMap>;

  IniLexer() = default;

  // Constructs the lexer and immediately parses the given file.
  explicit IniLexer(const std::string &filePath);

  // Loads and parses the file at the given path. Returns true on success,
  // false if the file could not be opened. By default, clears prior data.
  // Handles UTF-16 LE (BOM) input and resolves the skin's @Resources path.
  bool parseFile(const std::string &filePath, bool clear = true);

  // Parses INI content already held in memory. Returns true on success.
  // Note: #@# / @include resolution requires a known skin path; use
  // parseFile() for full feature support.
  bool parseString(std::string_view content);

  // Retrieves the value for a given section/key.
  // Returns std::nullopt if the section or key does not exist.
  std::optional<std::string> get(std::string_view section,
                                 std::string_view key) const;

  // Sets or updates a variable in the [Variables] section. Used dynamically
  // by !SetVariable bangs.
  void setVariable(const std::string &name, const std::string &value);

  // Like get(), but matches both the section and key case-insensitively.
  // Rainmeter treats section names, keys, and #Variables# as case-insensitive
  // (so #format# resolves a variable defined as "Format="). Returns the value
  // of the first matching key, or std::nullopt if none is found.
  std::optional<std::string> getCaseInsensitive(std::string_view section,
                                                std::string_view key) const;

  // Retrieves the value for a section/key, or a fallback if not present.
  std::string getOr(std::string_view section, std::string_view key,
                    std::string_view fallback) const;

  // Writes a key-value pair directly to the specified INI/INC file on disk.
  // Overwrites the existing key if present, or appends it to the section.
  static bool writeKeyValue(const std::string& filePath, const std::string& section, const std::string& key, const std::string& value);

  // True if the given section exists.
  bool hasSection(std::string_view section) const;

  // Access to the complete parsed data structure.
  const DataMap &data() const noexcept { return data_; }

  // Access to the list of sections in the order they were parsed (Z-Order).
  const std::vector<std::string>& sectionOrder() const noexcept { return sectionOrder_; }

  const EnvironmentManager &environment() const noexcept { return builtins_; }

  // Number of parsed sections.
  std::size_t sectionCount() const noexcept { return data_.size(); }

  // The resolved absolute path to the skin's @Resources/ directory (with a
  // trailing separator), computed from the first parsed file's location.
  const std::string &resourcesPath() const noexcept { return resourcesPath_; }

  // Reads a file into a UTF-8 std::string, converting from UTF-16 LE if a
  // BOM is present. Returns false if the file cannot be opened.
  static bool readFileUtf8(const std::string &filePath, std::string &out);

  // Replaces every #@# occurrence in `value` with resourcesPath_.
  std::string expandMacros(std::string_view value) const;

  // Expands built-in #VARNAME# tokens (e.g. #SKINSPATH#, #CURRENTFILE#)
  // from the EnvironmentManager before standard variable resolution.
  std::string expandBuiltins(std::string_view value) const;

  // Resolves `relativePath` under `basePath`, matching each component
  // case-insensitively against the real filesystem. Returns the true-cased
  // absolute path. Reusable for locating @include targets, image files, etc.
  static std::string
  resolveCaseInsensitivePath(const std::string &basePath,
                             const std::string &relativePath);

private:
  // Trims leading/trailing ASCII whitespace from a view.
  static std::string_view trim(std::string_view sv);

  // Converts a UTF-16 byte buffer (BOM already stripped) to UTF-8.
  static std::string utf16ToUtf8(const char *bytes, std::size_t byteCount, bool bigEndian);

  // Determines the @Resources/ directory for a skin file path.
  static std::string computeResourcesPath(const std::string &skinFilePath);

  // Parses content from a file already loaded into UTF-8, merging into data_.
  // `baseDir` is the directory of the current file, used to resolve relative
  // @include targets. `depth` guards against include cycles.
  bool parseContent(std::string_view content, const std::string &baseDir,
                    int depth, const std::string& initialSection = "");

  DataMap data_;
  std::vector<std::string> sectionOrder_;
  std::string resourcesPath_;
  EnvironmentManager builtins_;
};
