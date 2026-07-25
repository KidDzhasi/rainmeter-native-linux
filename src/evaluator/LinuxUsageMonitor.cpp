#include "LinuxUsageMonitor.hpp"
#include "parser/IniLexer.hpp"

#include <cstdio>
#include <iostream>
#include <vector>
#include <algorithm>
#include <sstream>
#include <array>

namespace {
    std::string formatDouble(double v) {
        char buf[64];
        std::snprintf(buf, sizeof(buf), "%.1f", v);
        return buf;
    }
}

void LinuxUsageMonitor::loadFrom(const IniLexer& skin, const std::string& section) {
    alias_ = skin.getOr(section, "Alias", "");
    category_ = skin.getOr(section, "Category", "");
    counter_ = skin.getOr(section, "Counter", "");
    std::string idxStr = skin.getOr(section, "Index", "1");
    try {
        index_ = std::stoi(idxStr);
        if (index_ < 1) index_ = 1;
    } catch(...) {
        index_ = 1;
    }

    std::string lAlias = alias_;
    for (char &c : lAlias) c = std::tolower(c);
    std::string lCat = category_;
    for (char &c : lCat) c = std::tolower(c);

    if (lAlias == "cpu" || lCat == "processor") {
        isCpu_ = true;
        prevCpu_ = sysmeasure::readCpuSample();
    } else if (lAlias == "ram" || lCat == "memory") {
        isRam_ = true;
    } else if (lCat == "process") {
        isProcess_ = true;
    }
}

void LinuxUsageMonitor::update() {
    if (isCpu_) {
        updateCpu();
    } else if (isRam_) {
        updateRam();
    } else if (isProcess_) {
        updateProcess();
    }
}

void LinuxUsageMonitor::updateCpu() {
    sysmeasure::CpuSample cur = sysmeasure::readCpuSample();
    numeric_ = sysmeasure::cpuPercent(prevCpu_, cur);
    current_ = formatDouble(numeric_);
    prevCpu_ = cur;
}

void LinuxUsageMonitor::updateRam() {
    sysmeasure::MemoryInfo mem = sysmeasure::readMemory();
    numeric_ = mem.usedBytes;
    current_ = std::to_string(static_cast<long long>(numeric_));
}

void LinuxUsageMonitor::updateProcess() {
    // Read top processes using ps
    std::string cmd = "ps -eo comm,pcpu,rsz --sort=-pcpu | head -n " + std::to_string(index_ + 1);
    
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return;
    
    std::array<char, 256> buffer;
    std::vector<std::string> lines;
    std::string result;
    
    while (fgets(buffer.data(), buffer.size(), pipe) != nullptr) {
        result += buffer.data();
    }
    pclose(pipe);
    
    std::istringstream iss(result);
    std::string line;
    std::getline(iss, line); // Skip header
    
    int currentIdx = 1;
    while (std::getline(iss, line)) {
        if (currentIdx == index_) {
            std::istringstream lss(line);
            std::string comm;
            double pcpu = 0;
            unsigned long rsz = 0;
            lss >> comm >> pcpu >> rsz;
            
            // Typical usage monitor counter check
            std::string lCounter = counter_;
            for(char &c : lCounter) c = std::tolower(c);
            
            if (lCounter.find("time") != std::string::npos || lCounter.find("%") != std::string::npos) {
                numeric_ = pcpu;
                current_ = formatDouble(numeric_);
            } else if (lCounter.find("bytes") != std::string::npos || lCounter.find("ram") != std::string::npos || lCounter.find("working set") != std::string::npos) {
                numeric_ = rsz * 1024.0; // rsz is in KB
                current_ = std::to_string(static_cast<long long>(numeric_));
            } else {
                // Default to returning the name if no valid numeric counter
                numeric_ = pcpu;
                current_ = comm;
            }
            break;
        }
        currentIdx++;
    }
}
