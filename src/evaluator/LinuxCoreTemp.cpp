#include "LinuxCoreTemp.hpp"
#include "parser/IniLexer.hpp"

#include <fstream>
#include <filesystem>
#include <iostream>

namespace fs = std::filesystem;

void LinuxCoreTemp::loadFrom(const IniLexer& skin, const std::string& section) {
    coreTempType_ = skin.getOr(section, "CoreTempType", "");
    findThermalPath();
}

bool LinuxCoreTemp::findThermalPath() {
    // Basic search for thermal zones
    std::error_code ec;
    
    // Try thermal_zone0 first
    fs::path tzone = "/sys/class/thermal/thermal_zone0/temp";
    if (fs::exists(tzone, ec)) {
        thermalPath_ = tzone.string();
        return true;
    }
    
    // Fallback to hwmon
    fs::path hwmonBase = "/sys/class/hwmon";
    if (fs::exists(hwmonBase, ec)) {
        for (const auto& entry : fs::directory_iterator(hwmonBase, ec)) {
            fs::path tempInput = entry.path() / "temp1_input";
            if (fs::exists(tempInput, ec)) {
                thermalPath_ = tempInput.string();
                return true;
            }
        }
    }
    
    return false;
}

void LinuxCoreTemp::update() {
    if (thermalPath_.empty()) {
        if (!findThermalPath()) {
            return;
        }
    }

    std::ifstream ifs(thermalPath_);
    if (ifs.is_open()) {
        long tempMilli = 0;
        if (ifs >> tempMilli) {
            tempCelsius_ = tempMilli / 1000.0;
        }
    }
}
