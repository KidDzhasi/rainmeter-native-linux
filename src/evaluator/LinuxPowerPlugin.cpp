#include "LinuxPowerPlugin.hpp"
#include <fstream>
#include <algorithm>

void LinuxPowerPlugin::loadFrom(const IniLexer &skin, const std::string &section) {
    powerState_ = skin.getOr(section, "PowerState", "Percent");
    // lowercase
    for (char &c : powerState_) {
        if (c >= 'A' && c <= 'Z') c += ('a' - 'A');
    }
}

double LinuxPowerPlugin::numericValue() const {
    if (powerState_ == "acline") {
        std::ifstream ac("/sys/class/power_supply/AC/online");
        int online = 0;
        if (ac >> online) return online;
        return 1.0;
    } else if (powerState_ == "percent" || powerState_ == "battery") {
        std::ifstream bat("/sys/class/power_supply/BAT0/capacity");
        int cap = 100;
        if (bat >> cap) return cap;
        return 100.0;
    } else if (powerState_ == "status") {
        std::ifstream status("/sys/class/power_supply/BAT0/status");
        std::string s;
        if (status >> s) {
            if (s == "Charging") return 1.0;
            if (s == "Discharging") return 0.0;
            if (s == "Full") return 0.0;
        }
        return 0.0;
    }
    return 0.0;
}

std::string LinuxPowerPlugin::stringValue() const {
    double val = numericValue();
    if (powerState_ == "percent" || powerState_ == "battery") {
        return std::to_string(static_cast<int>(val));
    }
    return "";
}
