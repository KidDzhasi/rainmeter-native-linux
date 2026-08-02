#pragma once

#include <string>
#include <unordered_map>
#include <vector>

// SysfsParser acts as the unified Linux Hardware Metrics Bridge.
// It parses /proc/stat, /proc/meminfo, and /sys/class/hwmon/ to provide
// telemetry data for Rainmeter skins using HWiNFO, CoreTemp, CPU, and Memory measures.
class SysfsParser {
public:
    struct HwmonSensor {
        std::string hwmonName;
        std::string label;
        std::string inputPath;
        double value = 0.0;
    };

    static SysfsParser& getInstance();

    SysfsParser();

    // Polls /proc/stat, /proc/meminfo, and /sys/class/hwmon/ for the latest values
    void update();

    // Gets fuzzy matched hardware metric from HWiNFO or CoreTemp plugins
    double getHwmonValue(const std::string& sensorName, const std::string& entryName) const;

    // CPU and Memory specific accessors
    double getCpuPercent() const { return cpuPercent_; }
    double getMemoryUsedPercent() const { return memUsedPercent_; }
    double getMemoryTotal() const { return memTotal_; }
    double getMemoryUsed() const { return memUsed_; }

private:
    void scanHwmon();
    void updateHwmon();
    void updateCpu();
    void updateMemory();

    std::vector<HwmonSensor> sensors_;
    
    // CPU state
    unsigned long long lastCpuTotal_ = 0;
    unsigned long long lastCpuIdle_ = 0;
    double cpuPercent_ = 0.0;

    // Memory state
    double memTotal_ = 0.0;
    double memUsed_ = 0.0;
    double memUsedPercent_ = 0.0;
};
