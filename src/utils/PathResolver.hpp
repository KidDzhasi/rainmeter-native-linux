#pragma once

#include <string>
#include <cstdlib>

namespace Utils {

inline std::string ResolvePath(const std::string& path) {
    if (path.empty()) return path;
    if (path[0] == '~') {
        const char* homeDir = std::getenv("HOME");
        if (homeDir) {
            return std::string(homeDir) + path.substr(1);
        }
    } else if (path.find("$HOME") == 0) {
        const char* homeDir = std::getenv("HOME");
        if (homeDir) {
            return std::string(homeDir) + path.substr(5);
        }
    }
    return path;
}

} // namespace Utils
