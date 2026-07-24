#include "WebFetcher.hpp"

#include <curl/curl.h>
#include <iostream>

namespace {
size_t writeCallback(void *contents, size_t size, size_t nmemb, std::string *s) {
  size_t newLength = size * nmemb;
  try {
    s->append(static_cast<char *>(contents), newLength);
  } catch (std::bad_alloc &) {
    return 0;
  }
  return newLength;
}

std::string performFetch(const std::string &url) {
  std::string result;
  CURL *curl = curl_easy_init();
  if (curl) {
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &result);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L); // 10 seconds timeout
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L); // Follow redirects
    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
      std::cerr << "WebFetcher failed: " << curl_easy_strerror(res) << "\n";
    }
    curl_easy_cleanup(curl);
  }
  return result;
}
} // namespace

void WebFetcher::start(const std::string &url) {
  if (running_) {
    return;
  }
  running_ = true;
  future_ = std::async(std::launch::async, [this, url]() {
    std::string res = performFetch(url);
    running_ = false;
    return res;
  });
}

bool WebFetcher::poll(std::string &out) {
  if (!future_.valid()) {
    return false;
  }
  if (future_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
    out = future_.get();
    return true;
  }
  return false;
}
