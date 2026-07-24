#include "SkinInstaller.hpp"

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include <zip.h>

#include "parser/IniLexer.hpp"

namespace fs = std::filesystem;

std::string SkinInstaller::dataDirectory() {
  // Prefer XDG_CONFIG_HOME, falling back to ~/.config.
  const char *xdg = std::getenv("XDG_CONFIG_HOME");
  fs::path base;
  if (xdg != nullptr && xdg[0] != '\0') {
    base = fs::path(xdg);
  } else {
    const char *home = std::getenv("HOME");
    base = fs::path(home != nullptr ? home : ".") / ".config";
  }
  return (base / "rainmeter-native").string();
}

bool SkinInstaller::ensureDirectories(const std::string &skinsDir) const {
  std::error_code ec;
  fs::create_directories(skinsDir, ec);
  if (ec) {
    std::cerr << "SkinInstaller: failed to create '" << skinsDir
              << "': " << ec.message() << "\n";
    return false;
  }
  return true;
}

std::optional<std::string> SkinInstaller::install(const std::string &rmskinPath) {
  if (!fs::exists(rmskinPath)) {
    std::cerr << "SkinInstaller: file not found: " << rmskinPath << "\n";
    return std::nullopt;
  }

  // Open the archive. libzip reads the ZIP central directory from the end of
  // the file, so the custom Rainmeter footer appended after it is ignored.
  int zipErr = 0;
  zip_t *archive = zip_open(rmskinPath.c_str(), ZIP_RDONLY, &zipErr);
  if (archive == nullptr) {
    zip_error_t error;
    zip_error_init_with_code(&error, zipErr);
    std::cerr << "SkinInstaller: failed to open '" << rmskinPath
              << "' as a zip archive: " << zip_error_strerror(&error) << "\n";
    zip_error_fini(&error);
    return std::nullopt;
  }

  const std::string dataDir = dataDirectory();
  const std::string skinsDir = (fs::path(dataDir) / "Skins").string();
  if (!ensureDirectories(skinsDir)) {
    zip_close(archive);
    return std::nullopt;
  }

  std::string loadTarget;

  // --- Read RMSKIN.ini metadata from the zip stream ---
  {
    zip_stat_t st;
    zip_stat_init(&st);
    if (zip_stat(archive, "RMSKIN.ini", 0, &st) == 0) {
      zip_file_t *f = zip_fopen(archive, "RMSKIN.ini", 0);
      if (f != nullptr) {
        std::string contents;
        contents.resize(static_cast<std::size_t>(st.size));
        const zip_int64_t got = zip_fread(f, contents.data(), contents.size());
        zip_fclose(f);
        if (got >= 0) {
          contents.resize(static_cast<std::size_t>(got));
          IniLexer meta;
          meta.parseString(contents);
          std::cout << "Installing skin package:\n";
          std::cout << "  Name    : "
                    << meta.getOr("rmskin", "Name", "<unknown>") << "\n";
          std::cout << "  Author  : "
                    << meta.getOr("rmskin", "Author", "<unknown>") << "\n";
          std::cout << "  Version : "
                    << meta.getOr("rmskin", "Version", "<unknown>") << "\n";
          loadTarget = meta.getCaseInsensitive("rmskin", "Load").value_or("");
          // Normalize backslashes from Windows paths
          for (char &c : loadTarget) {
            if (c == '\\') {
              c = '/';
            }
          }
        }
      }
    } else {
      std::cout << "SkinInstaller: no RMSKIN.ini found (continuing).\n";
    }
  }

  // --- Extract everything under Skins/ ---
  const zip_int64_t numEntries = zip_get_num_entries(archive, 0);
  int extracted = 0;
  std::vector<std::string> extractedInis;

  for (zip_int64_t i = 0; i < numEntries; ++i) {
    const char *rawName = zip_get_name(archive, i, 0);
    if (rawName == nullptr) {
      continue;
    }
    const std::string name = rawName;

    // Only handle entries inside the archive's Skins/ directory.
    constexpr std::string_view kPrefix = "Skins/";
    if (name.size() < kPrefix.size() ||
        name.compare(0, kPrefix.size(), kPrefix) != 0) {
      continue;
    }

    const fs::path outPath = fs::path(skinsDir) / name.substr(kPrefix.size());

    // Directory entries end with '/'.
    if (!name.empty() && name.back() == '/') {
      std::error_code ec;
      fs::create_directories(outPath, ec);
      continue;
    }

    // Make sure the parent directory exists.
    std::error_code ec;
    fs::create_directories(outPath.parent_path(), ec);

    zip_stat_t st;
    zip_stat_init(&st);
    if (zip_stat_index(archive, i, 0, &st) != 0) {
      continue;
    }

    zip_file_t *f = zip_fopen_index(archive, i, 0);
    if (f == nullptr) {
      std::cerr << "SkinInstaller: could not read entry '" << name << "'\n";
      continue;
    }

    std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
    if (!out.is_open()) {
      std::cerr << "SkinInstaller: could not write '" << outPath.string()
                << "'\n";
      zip_fclose(f);
      continue;
    }

    std::vector<char> buffer(64 * 1024);
    zip_int64_t n = 0;
    while ((n = zip_fread(f, buffer.data(), buffer.size())) > 0) {
      out.write(buffer.data(), n);
    }
    out.close();
    zip_fclose(f);
    ++extracted;

    std::string ext = outPath.extension().string();
    for (char &c : ext) {
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    if (ext == ".ini") {
      extractedInis.push_back(outPath.string());
    }
  }

  zip_close(archive);

  std::cout << "Extracted " << extracted << " file(s) into " << skinsDir << "\n";

  std::string launchIni;
  if (!loadTarget.empty()) {
    fs::path loadPath = fs::path(skinsDir) / loadTarget;
    if (fs::is_regular_file(loadPath)) {
      std::string ext = loadPath.extension().string();
      for (char &c : ext) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
      }
      if (ext == ".ini") {
        launchIni = loadPath.string();
      }
    }
  }

  if (launchIni.empty() && !extractedInis.empty()) {
    launchIni = extractedInis[0];
    std::size_t minDepth = std::string::npos;
    for (const auto &ini : extractedInis) {
      std::size_t depth = std::count(ini.begin(), ini.end(), '/');
      if (depth < minDepth) {
        minDepth = depth;
        launchIni = ini;
      }
    }
  }

  if (launchIni.empty()) {
    return std::nullopt;
  }
  return launchIni;
}
