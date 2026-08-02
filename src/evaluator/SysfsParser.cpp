#include "SysfsParser.hpp"

#include <fstream>
#include <sstream>
#include <filesystem>
#include <algorithm>
#include <iostream>
#include <cctype>

namespace fs = std::filesystem;

SysfsParser& SysfsParser::getInstance() {
    static SysfsParser instance;
    return instance;
}

SysfsParser::SysfsParser() {
    scanHwmon();
}

void SysfsParser::update() {
    updateCpu();
    updateMemory();
    updateHwmon();
}

void SysfsParser::scanHwmon() {
    sensors_.clear();
    std::error_code ec;
    fs::path hwmonBase = "/sys/class/hwmon";
    
    if (!fs::exists(hwmonBase, ec)) return;

    for (const auto& entry : fs::directory_iterator(hwmonBase, ec)) {
        std::string hwmonName = "unknown";
        fs::path namePath = entry.path() / "name";
        if (fs::exists(namePath, ec)) {
            std::ifstream nameFile(namePath);
            if (nameFile) nameFile >> hwmonName;
        }

        for (const auto& sensorEntry : fs::directory_iterator(entry.path(), ec)) {
            std::string filename = sensorEntry.path().filename().string();
            if (filename.find("_input") != std::string::npos) {
                HwmonSensor sensor;
                sensor.hwmonName = hwmonName;
                sensor.inputPath = sensorEntry.path().string();
                
                std::string prefix = filename.substr(0, filename.find("_input"));
                fs::path labelPath = entry.path() / (prefix + "_label");
                
                if (fs::exists(labelPath, ec)) {
                    std::ifstream labelFile(labelPath);
                    if (labelFile) std::getline(labelFile, sensor.label);
                } else {
                    sensor.label = prefix;
                }
                
                sensors_.push_back(sensor);
            }
        }
    }
}

void SysfsParser::updateHwmon() {
    for (auto& sensor : sensors_) {
        std::ifstream ifs(sensor.inputPath);
        if (ifs) {
            long rawValue = 0;
            if (ifs >> rawValue) {
                if (sensor.inputPath.find("temp") != std::string::npos) {
                    sensor.value = rawValue / 1000.0;
                } else if (sensor.inputPath.find("in") != std::string::npos) {
                    sensor.value = rawValue / 1000.0;
                } else {
                    sensor.value = rawValue;
                }
            }
        }
    }
}

void SysfsParser::updateCpu() {
    std::ifstream stat("/proc/stat");
    if (!stat.is_open()) return;

    std::string label;
    stat >> label;
    if (label != "cpu") return;

    unsigned long long user = 0, nice = 0, system = 0, idle = 0, iowait = 0,
                       irq = 0, softirq = 0, steal = 0;
    stat >> user >> nice >> system >> idle >> iowait >> irq >> softirq >> steal;

    unsigned long long currentIdle = idle + iowait;
    unsigned long long currentTotal = user + nice + system + idle + iowait + irq + softirq + steal;

    if (lastCpuTotal_ > 0) {
        long long totalDelta = currentTotal - lastCpuTotal_;
        long long idleDelta = currentIdle - lastCpuIdle_;
        if (totalDelta > 0) {
            cpuPercent_ = 100.0 * (totalDelta - idleDelta) / static_cast<double>(totalDelta);
            cpuPercent_ = std::clamp(cpuPercent_, 0.0, 100.0);
        }
    }

    lastCpuTotal_ = currentTotal;
    lastCpuIdle_ = currentIdle;
}

void SysfsParser::updateMemory() {
    std::ifstream meminfo("/proc/meminfo");
    if (!meminfo.is_open()) return;

    unsigned long long totalKb = 0;
    unsigned long long availableKb = 0;

    std::string line;
    while (std::getline(meminfo, line)) {
        std::istringstream iss(line);
        std::string key;
        unsigned long long value = 0;
        std::string unit;
        iss >> key >> value >> unit;
        if (key == "MemTotal:") {
            totalKb = value;
        } else if (key == "MemAvailable:") {
            availableKb = value;
        }
    }

    if (totalKb > 0) {
        memTotal_ = totalKb * 1024.0;
        unsigned long long usedKb = (totalKb > availableKb) ? (totalKb - availableKb) : 0;
        memUsed_ = usedKb * 1024.0;
        memUsedPercent_ = 100.0 * static_cast<double>(usedKb) / static_cast<double>(totalKb);
    }
}

double SysfsParser::getHwmonValue(const std::string& sensorName, const std::string& entryName) const {
    auto toLower = [](std::string s) {
        for (char& c : s) c = std::tolower(c);
        return s;
    };
    
    std::string qSensor = toLower(sensorName);
    std::string qEntry = toLower(entryName);
    
    double bestMatchVal = 0.0;
    int bestScore = -1;
    
    for (const auto& sensor : sensors_) {
        std::string label = toLower(sensor.label);
        std::string hwmonName = toLower(sensor.hwmonName);
        
        int score = 0;
        
        if (!qEntry.empty() && label.find(qEntry) != std::string::npos) score += 2;
        if (!qSensor.empty() && hwmonName.find(qSensor) != std::string::npos) score += 1;
        
        // Exact matches give high score
        if (label == qEntry) score += 10;
        if (hwmonName == qSensor) score += 5;
        
        if (score > bestScore) {
            bestScore = score;
            bestMatchVal = sensor.value;
        }
    }
    
    // Fallback if no match was found (or if we didn't specify strict HWiNFO params)
    if (bestScore <= 0 && !sensors_.empty()) {
        if (!qSensor.empty() && qSensor.find("temp") != std::string::npos) {
            for (const auto& sensor : sensors_) {
                if (sensor.inputPath.find("temp1_input") != std::string::npos) return sensor.value;
            }
        }
        return sensors_[0].value;
    }
    
    return bestMatchVal;
}
