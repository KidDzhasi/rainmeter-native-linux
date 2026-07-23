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
    }
    if (haveTotal && haveAvail) {
      break;
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

} // namespace sysmeasure
