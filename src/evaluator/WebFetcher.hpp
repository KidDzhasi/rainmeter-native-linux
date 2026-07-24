#pragma once

#include <atomic>
#include <future>
#include <string>

// Non-blocking HTTP fetcher for Measure=WebParser
class WebFetcher {
public:
  WebFetcher() = default;
  ~WebFetcher() = default;

  // Starts an async HTTP GET request to `url`.
  void start(const std::string &url);

  // Checks if the request is finished. If true, `out` is populated.
  bool poll(std::string &out);

private:
  std::future<std::string> future_;
  std::atomic<bool> running_{false};
};
