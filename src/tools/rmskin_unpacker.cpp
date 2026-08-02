#include <iostream>
#include <string>
#include <filesystem>
#include <cstdlib>
#include <stdexcept>
#include <unistd.h>
#include <fstream>

#include <fstream>

namespace fs = std::filesystem;

#include "../parser/IniLexer.hpp"
#include "../utils/PathResolver.hpp"

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <path_to.rmskin>\n";
        return 1;
    }

    std::string archivePath = argv[1];
    if (!fs::exists(archivePath)) {
        std::cerr << "Error: File '" << archivePath << "' does not exist.\n";
        return 1;
    }

    // 1. Create a secure temporary directory
    char tmpDirTemplate[] = "/tmp/rmskin_unpacker_XXXXXX";
    char* tmpDirPtr = mkdtemp(tmpDirTemplate);
    if (!tmpDirPtr) {
        std::cerr << "Error: Failed to create temporary directory.\n";
        return 1;
    }
    
    fs::path tmpDir(tmpDirPtr);
    std::cout << "Created temp directory: " << tmpDir << "\n";

    // Ensure cleanup of the temp directory on exit
    struct TempCleanup {
        fs::path p;
        ~TempCleanup() {
            if (fs::exists(p)) {
                std::cout << "Cleaning up " << p << "...\n";
                fs::remove_all(p);
            }
        }
    } cleanup{tmpDir};

    // 2. Execute unzip
    // Use quotes around the archive path in case it contains spaces
    std::string unzipCmd = "unzip -q -o \"" + archivePath + "\" -d \"" + tmpDir.string() + "\"";
    std::cout << "Extracting archive...\n";
    int ret = std::system(unzipCmd.c_str());
    if (ret != 0) {
        std::cerr << "Error: Failed to unzip '" << archivePath << "'. Ensure 'unzip' is installed.\n";
        return 1;
    }

    // 3. Locate Skins/ folder inside the unpacked archive
    fs::path skinsDir = tmpDir / "Skins";
    if (!fs::exists(skinsDir) || !fs::is_directory(skinsDir)) {
        // Some archives might have it lowercased or missing
        skinsDir = tmpDir / "skins";
        if (!fs::exists(skinsDir) || !fs::is_directory(skinsDir)) {
            std::cerr << "Error: No 'Skins/' folder found in the .rmskin package.\n";
            return 1;
        }
    }

    // Determine target installation directory
    fs::path targetSkinsDir = fs::path(Utils::ResolvePath("~/.config/rainmeter-native/Skins"));

    // Ensure target directory exists
    if (!fs::exists(targetSkinsDir)) {
        fs::create_directories(targetSkinsDir);
    }

    // 4. Move skin suite folder(s) to the target directory
    bool foundAnySkins = false;
    for (const auto& entry : fs::directory_iterator(skinsDir)) {
        if (entry.is_directory()) {
            foundAnySkins = true;
            fs::path skinSuiteFolder = entry.path();
            fs::path targetFolder = targetSkinsDir / skinSuiteFolder.filename();

            std::cout << "Installing skin: " << skinSuiteFolder.filename() << " -> " << targetFolder << "\n";

            // If it already exists, remove it first to overwrite cleanly
            if (fs::exists(targetFolder)) {
                std::cout << "Overwriting existing skin installation...\n";
                fs::remove_all(targetFolder);
            }

            // In some cases rename fails across different filesystems (e.g., /tmp to ~).
            // A safer approach is to use fs::copy followed by fs::remove_all.
            std::error_code ec;
            fs::copy(skinSuiteFolder, targetFolder, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
            if (ec) {
                 std::cerr << "Error copying folder: " << ec.message() << "\n";
            } else {
                 fs::remove_all(skinSuiteFolder);
            }
        }
    }

    if (!foundAnySkins) {
        std::cout << "Warning: No skin directories found inside the 'Skins' folder of the package.\n";
    } else {
        std::cout << "Success: .rmskin installed successfully.\n";
        
        // 5. Parse RMSKIN.ini if it exists to extract WindowX/WindowY and save to Rainmeter.ini
        fs::path manifestPath = tmpDir / "RMSKIN.ini";
        if (!fs::exists(manifestPath)) {
            manifestPath = tmpDir / "rmskin.ini";
        }
        
        if (fs::exists(manifestPath)) {
            std::cout << "Found RMSKIN manifest. Extracting layout coordinates...\n";
            std::string rainmeterIniPath = Utils::ResolvePath("~/.config/rainmeter-native/Rainmeter.ini");
            
            IniLexer manifest;
            if (manifest.parseFile(manifestPath.string(), true)) {
                for (const auto& [section, keys] : manifest.data()) {
                    std::string currentConfig = section;
                    // Rainmeter uses backslashes in config names
                    for (char &c : currentConfig) {
                        if (c == '\\') c = '/';
                    }

                    int currentX = -1;
                    int currentY = -1;
                    
                    auto getVal = [&](const std::string& kLower) -> std::string {
                        for (const auto& [k, v] : keys) {
                            std::string lowerK = k;
                            for (char &c : lowerK) c = std::tolower(c);
                            if (lowerK == kLower) return v;
                        }
                        return "";
                    };

                    std::string configVal = getVal("config");
                    if (!configVal.empty()) {
                        for (char &c : configVal) {
                            if (c == '\\') c = '/';
                        }
                        currentConfig = configVal;
                    }

                    std::string wx = getVal("windowx");
                    std::string wy = getVal("windowy");
                    if (!wx.empty()) { try { currentX = std::stoi(wx); } catch(...) {} }
                    if (!wy.empty()) { try { currentY = std::stoi(wy); } catch(...) {} }

                    if (!currentConfig.empty() && currentX != -1 && currentY != -1) {
                        std::cout << "Setting default layout for [" << currentConfig << "] -> X: " << currentX << ", Y: " << currentY << "\n";
                        std::ofstream out(rainmeterIniPath, std::ios::app);
                        out << "\n[" << currentConfig << "]\n";
                        out << "WindowX=" << currentX << "\n";
                        out << "WindowY=" << currentY << "\n";
                    }
                }
            }
        }
    }

    // Cleanup happens automatically via the TempCleanup destructor
    return 0;
}
