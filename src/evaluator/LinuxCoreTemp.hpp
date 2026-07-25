#pragma once

#include <string>

class IniLexer;

// LinuxCoreTemp mocks Rainmeter's CoreTemp plugin using native Linux thermal paths.
class LinuxCoreTemp {
public:
    LinuxCoreTemp() = default;

    void loadFrom(const IniLexer& skin, const std::string& section);
    void update();

    double numericValue() const { return tempCelsius_; }
    std::string stringValue() const { return std::to_string(static_cast<int>(tempCelsius_)); }

private:
    std::string coreTempType_;
    double tempCelsius_ = 0.0;
    
    // Cached path to the thermal_zone or hwmon input file
    std::string thermalPath_;
    bool findThermalPath();
};
