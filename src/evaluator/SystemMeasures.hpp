#pragma once

#include <string>

// SystemMeasures: thin wrappers over Linux telemetry sources used by
// MeasureEvaluator to implement Rainmeter's system measure plugins.
namespace sysmeasure {

// Aggregate CPU tick counters from /proc/stat's first "cpu" line.
struct CpuSample {
  unsigned long long total = 0;
  unsigned long long idle = 0;
  bool valid = false;
};

// Reads the aggregate CPU sample. total = sum of all fields, idle =
// idle+iowait.
CpuSample readCpuSample();

// Busy percentage (0-100) between two samples. Returns 0 if the delta is
// zero or a sample is invalid.
double cpuPercent(const CpuSample &prev, const CpuSample &cur);

// Physical memory usage from /proc/meminfo.
struct MemoryInfo {
  unsigned long long totalBytes = 0;
  unsigned long long availableBytes = 0;
  unsigned long long usedBytes = 0;
  double usedPercent = 0.0; // 0-100
  unsigned long long swapTotalBytes = 0;
  unsigned long long swapFreeBytes = 0;
  double swapUsedPercent = 0.0; // 0-100
  bool valid = false;
};

MemoryInfo readMemory();

// Free disk space for the filesystem containing `path` (via statvfs).
struct DiskInfo {
  unsigned long long totalBytes = 0;
  unsigned long long freeBytes = 0;
  unsigned long long usedBytes = 0;
  double usedPercent = 0.0; // 0-100
  bool valid = false;
};

DiskInfo readDisk(const std::string &path);

// Network usage from /proc/net/dev
struct NetStats {
  unsigned long long rxBytes = 0;
  unsigned long long txBytes = 0;
  bool valid = false;
};

NetStats readNetStats(const std::string &interfaceName = "");

// System Uptime from /proc/uptime
struct UptimeInfo {
  double uptimeSeconds = 0.0;
  bool valid = false;
};

UptimeInfo readUptime();

} // namespace sysmeasure
