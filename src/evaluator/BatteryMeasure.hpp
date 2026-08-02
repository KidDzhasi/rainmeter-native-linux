#pragma once

#include "BaseMeasure.hpp"
#include <fstream>
#include <string>
#include <filesystem>
#include <iostream>

class BatteryMeasure : public BaseMeasure {
public:
    void onLoad(const IniLexer& skin, const std::string& section) override {
        // Allow dynamic targeting of battery name (e.g. BAT0, BAT1)
        batteryName_ = skin.getOr(section, "BatteryName", "BAT0");
        if (skin.getOr(section, "MaxValue", "").empty()) {
            maxValue_ = 100.0;
        }
    }

protected:
    void onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) override {
        if (dynamicVariables_) {
            // Rough approximation if they change it
            batteryName_ = skin.getOr(skin.getCaseInsensitive("", "section").value_or(""), "BatteryName", "BAT0");
        }

        std::string capPath = "/sys/class/power_supply/" + batteryName_ + "/capacity";
        std::string statPath = "/sys/class/power_supply/" + batteryName_ + "/status";

        double capacity = 0.0;
        std::ifstream capFile(capPath);
        if (capFile.is_open()) {
            capFile >> capacity;
            numeric_ = capacity;
        }

        std::ifstream statFile(statPath);
        if (statFile.is_open()) {
            std::string status;
            statFile >> status;
            current_ = std::to_string(static_cast<int>(capacity)) + "% (" + status + ")";
        } else {
            current_ = std::to_string(static_cast<int>(capacity)) + "%";
        }
    }

private:
    std::string batteryName_ = "BAT0";
};
