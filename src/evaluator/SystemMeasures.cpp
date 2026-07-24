#include "SystemMeasures.hpp"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#include <sys/statvfs.h>

namespace sysmeasure {

CpuSample readCpuSample() {
  CpuSample s;
  std::ifstream stat("/proc/stat");
  if (!stat.is_open()) {
    return s;
  }

  std::string label;
  stat >> label;
  if (label != "cpu") {
    return s;
  }

  // Fields: user nice system idle iowait irq softirq steal guest guest_nice
  unsigned long long user = 0, nice = 0, system = 0, idle = 0, iowait = 0,
                     irq = 0, softirq = 0, steal = 0;
  stat >> user >> nice >> system >> idle >> iowait >> irq >> softirq >> steal;

  s.idle = idle + iowait;
  s.total = user + nice + system + idle + iowait + irq + softirq + steal;
  s.valid = true;
  return s;
}

double cpuPercent(const CpuSample &prev, const CpuSample &cur) {
  if (!prev.valid || !cur.valid) {
    return 0.0;
  }
  const long long totalDelta =
      static_cast<long long>(cur.total) - static_cast<long long>(prev.total);
  const long long idleDelta =
      static_cast<long long>(cur.idle) - static_cast<long long>(prev.idle);
  if (totalDelta <= 0) {
    return 0.0;
  }
  const double busy = static_cast<double>(totalDelta - idleDelta) /
                      static_cast<double>(totalDelta);
  double pct = busy * 100.0;
  if (pct < 0.0) {
    pct = 0.0;
  }
  if (pct > 100.0) {
    pct = 100.0;
  }
  return pct;
}

MemoryInfo readMemory() {
  MemoryInfo m;
  std::ifstream meminfo("/proc/meminfo");
  if (!meminfo.is_open()) {
    return m;
  }

  unsigned long long totalKb = 0;
  unsigned long long availableKb = 0;
  bool haveTotal = false;
  bool haveAvail = false;

  std::string line;
  while (std::getline(meminfo, line)) {
    std::istringstream iss(line);
    std::string key;
    unsigned long long value = 0;
    std::string unit;
    iss >> key >> value >> unit;
    if (key == "MemTotal:") {
      totalKb = value;
      haveTotal = true;
    } else if (key == "MemAvailable:") {
      availableKb = value;
      haveAvail = true;
    } else if (key == "SwapTotal:") {
      m.swapTotalBytes = value * 1024ULL;
    } else if (key == "SwapFree:") {
      m.swapFreeBytes = value * 1024ULL;
    }
  }

  if (!haveTotal || totalKb == 0) {
    return m;
  }

  m.totalBytes = totalKb * 1024ULL;
  m.availableBytes = availableKb * 1024ULL;
  m.usedBytes =
      (availableKb <= totalKb) ? (totalKb - availableKb) * 1024ULL : 0ULL;
  m.usedPercent = 100.0 * static_cast<double>(totalKb - availableKb) /
                  static_cast<double>(totalKb);
                  
  if (m.swapTotalBytes > 0) {
    unsigned long long usedSwap = m.swapTotalBytes - m.swapFreeBytes;
    m.swapUsedPercent = 100.0 * static_cast<double>(usedSwap) / static_cast<double>(m.swapTotalBytes);
  }
  
  m.valid = true;
  return m;
}

DiskInfo readDisk(const std::string &path) {
  DiskInfo d;
  struct statvfs vfs {};
  if (statvfs(path.c_str(), &vfs) != 0) {
    return d;
  }

  const unsigned long long blockSize =
      (vfs.f_frsize != 0) ? vfs.f_frsize : vfs.f_bsize;
  d.totalBytes = static_cast<unsigned long long>(vfs.f_blocks) * blockSize;
  d.freeBytes = static_cast<unsigned long long>(vfs.f_bavail) * blockSize;
  d.usedBytes =
      (d.totalBytes >= d.freeBytes) ? (d.totalBytes - d.freeBytes) : 0ULL;
  if (d.totalBytes > 0) {
    d.usedPercent = 100.0 * static_cast<double>(d.usedBytes) /
                    static_cast<double>(d.totalBytes);
  }
  d.valid = true;
  return d;
}

NetStats readNetStats(const std::string &interfaceName) {
  NetStats n;
  std::ifstream netdev("/proc/net/dev");
  if (!netdev.is_open()) return n;

  std::string line;
  // Skip the first two header lines
  std::getline(netdev, line);
  std::getline(netdev, line);

  unsigned long long totalRx = 0;
  unsigned long long totalTx = 0;
  bool found = false;

  while (std::getline(netdev, line)) {
    std::istringstream iss(line);
    std::string iface;
    iss >> iface;
    if (iface.empty()) continue;
    
    // Remove trailing colon
    if (iface.back() == ':') {
      iface.pop_back();
    }
    
    if (!interfaceName.empty() && iface != interfaceName) {
      continue;
    }
    
    // If we're summing all, skip loopback
    if (interfaceName.empty() && iface == "lo") {
      continue;
    }

    unsigned long long rxBytes = 0, txBytes = 0, dummy = 0;
    iss >> rxBytes;
    // Skip 7 fields
    for (int i = 0; i < 7; ++i) iss >> dummy;
    iss >> txBytes;
    
    totalRx += rxBytes;
    totalTx += txBytes;
    found = true;
    
    if (!interfaceName.empty()) break;
  }

  if (found) {
    n.rxBytes = totalRx;
    n.txBytes = totalTx;
    n.valid = true;
  }
  return n;
}

UptimeInfo readUptime() {
  UptimeInfo u;
  std::ifstream f("/proc/uptime");
  if (!f.is_open()) return u;
  
  if (f >> u.uptimeSeconds) {
    u.valid = true;
  }
  return u;
}

} // namespace sysmeasure
