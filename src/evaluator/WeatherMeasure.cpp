#include "WeatherMeasure.hpp"

#include <curl/curl.h>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <ctime>
#include <iostream>

namespace {

size_t writeCb(void* contents, size_t size, size_t nmemb, std::string* s) {
    s->append(static_cast<char*>(contents), size * nmemb);
    return size * nmemb;
}

std::string lower(std::string s) {
    for (char& c : s) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return s;
}

// Expand #Variable# tokens against the [Variables] section.
std::string expandVars(const IniLexer& skin, const std::string& text) {
    std::string out;
    for (std::size_t i = 0; i < text.size();) {
        if (text[i] == '#') {
            std::size_t close = text.find('#', i + 1);
            if (close != std::string::npos && close > i + 1) {
                auto v = skin.getCaseInsensitive("Variables", lower(text.substr(i + 1, close - i - 1)));
                if (!v) v = skin.getCaseInsensitive("Variables", text.substr(i + 1, close - i - 1));
                if (v) {
                    out += *v;
                    i = close + 1;
                    continue;
                }
            }
        }
        out += text[i++];
    }
    return out;
}

double toDouble(const std::string& s, double def) {
    try {
        return std::stod(s);
    } catch (...) {
        return def;
    }
}

// Extract the JSON object body that follows `"name":{` (flat objects only).
std::string objectBody(const std::string& json, const std::string& name) {
    std::string marker = "\"" + name + "\":{";
    std::size_t p = json.find(marker);
    if (p == std::string::npos) return "";
    p += marker.size();
    std::size_t e = json.find('}', p);
    if (e == std::string::npos) return "";
    return json.substr(p, e - p);
}

// Read a numeric field `"key":123.4` or the first element of `"key":[123.4,...]`.
bool numberField(const std::string& body, const std::string& key, double& out) {
    std::string marker = "\"" + key + "\":";
    std::size_t p = body.find(marker);
    if (p == std::string::npos) return false;
    p += marker.size();
    if (p < body.size() && body[p] == '[') ++p;
    if (body.compare(p, 4, "null") == 0) return false;
    char* end = nullptr;
    const char* start = body.c_str() + p;
    double v = std::strtod(start, &end);
    if (end == start) return false;
    out = v;
    return true;
}

std::string conditionText(int code) {
    switch (code) {
    case 0: return "Clear Sky";
    case 1: return "Mainly Clear";
    case 2: return "Partly Cloudy";
    case 3: return "Overcast";
    case 45: return "Fog";
    case 48: return "Rime Fog";
    case 51: return "Light Drizzle";
    case 53: return "Drizzle";
    case 55: return "Heavy Drizzle";
    case 56: case 57: return "Freezing Drizzle";
    case 61: return "Light Rain";
    case 63: return "Rain";
    case 65: return "Heavy Rain";
    case 66: case 67: return "Freezing Rain";
    case 71: return "Light Snow";
    case 73: return "Snow";
    case 75: return "Heavy Snow";
    case 77: return "Snow Grains";
    case 80: return "Light Showers";
    case 81: return "Showers";
    case 82: return "Heavy Showers";
    case 85: case 86: return "Snow Showers";
    case 95: return "Thunderstorm";
    case 96: case 99: return "Thunderstorm & Hail";
    default: return "Unknown";
    }
}

std::string compass(double deg) {
    static const char* dirs[16] = {"N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"};
    int idx = static_cast<int>(std::floor(std::fmod(deg + 11.25 + 360.0, 360.0) / 22.5)) % 16;
    return dirs[idx];
}

std::string fmt0(double v) {
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%.0f", std::round(v) == 0.0 ? 0.0 : std::round(v));
    return buf;
}

std::mutex g_registryMutex;
std::map<std::string, std::weak_ptr<WeatherBackend>> g_registry;

} // namespace

// ---------------------------------------------------------------------------
// WeatherBackend
// ---------------------------------------------------------------------------

WeatherBackend::WeatherBackend(double lat, double lon, bool imperial, int refreshMinutes)
    : lat_(lat), lon_(lon), imperial_(imperial), refreshMinutes_(std::max(2, refreshMinutes)) {
    thread_ = std::thread(&WeatherBackend::loop, this);
}

WeatherBackend::~WeatherBackend() {
    running_ = false;
    cv_.notify_all();
    if (thread_.joinable()) thread_.join();
}

std::shared_ptr<WeatherBackend> WeatherBackend::acquire(double lat, double lon, bool imperial, int refreshMinutes) {
    char key[128];
    std::snprintf(key, sizeof(key), "%.4f,%.4f,%d", lat, lon, imperial ? 1 : 0);
    std::lock_guard<std::mutex> lock(g_registryMutex);
    static bool curlInit = (curl_global_init(CURL_GLOBAL_DEFAULT) == CURLE_OK);
    (void)curlInit;
    auto it = g_registry.find(key);
    if (it != g_registry.end()) {
        if (auto existing = it->second.lock()) return existing;
    }
    auto created = std::make_shared<WeatherBackend>(lat, lon, imperial, refreshMinutes);
    g_registry[key] = created;
    return created;
}

WeatherData WeatherBackend::snapshot() {
    std::lock_guard<std::mutex> lock(mutex_);
    return data_;
}

void WeatherBackend::requestRefresh() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        refreshRequested_ = true;
    }
    cv_.notify_all();
}

void WeatherBackend::loop() {
    while (running_) {
        bool ok = fetchOnce();
        // Retry quickly (60 s) after a failure, otherwise wait the refresh interval.
        auto wait = ok ? std::chrono::minutes(refreshMinutes_) : std::chrono::minutes(1);
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait_for(lock, wait, [this] { return !running_ || refreshRequested_; });
        refreshRequested_ = false;
    }
}

bool WeatherBackend::fetchOnce() {
    char url[768];
    std::snprintf(url, sizeof(url),
                  "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
                  "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
                  "precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m,is_day"
                  "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                  "&timezone=auto&forecast_days=1%s",
                  lat_, lon_, imperial_ ? "&temperature_unit=fahrenheit&wind_speed_unit=mph" : "");

    std::string body;
    CURLcode res = CURLE_FAILED_INIT;
    long httpCode = 0;
    if (CURL* curl = curl_easy_init()) {
        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCb);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &body);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 15L);
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "TradRainmeter/1.0");
        res = curl_easy_perform(curl);
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
        curl_easy_cleanup(curl);
    }

    WeatherData next;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        next = data_; // keep last good values on failure
    }
    next.fetching = false;

    if (res != CURLE_OK || httpCode != 200) {
        next.error = (res != CURLE_OK) ? curl_easy_strerror(res) : ("HTTP " + std::to_string(httpCode));
        std::cerr << "[Weather] fetch failed: " << next.error << "\n";
        std::lock_guard<std::mutex> lock(mutex_);
        data_ = next;
        return false;
    }

    std::string cur = objectBody(body, "current");
    std::string daily = objectBody(body, "daily");
    double v = 0.0;
    bool gotTemp = numberField(cur, "temperature_2m", v);
    if (!gotTemp) {
        next.error = "Bad response";
        std::lock_guard<std::mutex> lock(mutex_);
        data_ = next;
        return false;
    }
    next.temperature = v;
    if (numberField(cur, "apparent_temperature", v)) next.feelsLike = v;
    if (numberField(cur, "relative_humidity_2m", v)) next.humidity = v;
    if (numberField(cur, "weather_code", v)) next.weatherCode = static_cast<int>(v);
    if (numberField(cur, "wind_speed_10m", v)) next.windSpeed = v;
    if (numberField(cur, "wind_direction_10m", v)) next.windDirDeg = v;
    if (numberField(cur, "is_day", v)) next.isDay = (v != 0.0);
    if (numberField(cur, "precipitation_probability", v)) {
        next.rainChance = v;
    } else if (numberField(daily, "precipitation_probability_max", v)) {
        next.rainChance = v;
    }
    if (numberField(daily, "temperature_2m_max", v)) next.high = v;
    if (numberField(daily, "temperature_2m_min", v)) next.low = v;

    std::time_t now = std::time(nullptr);
    std::tm tmv{};
    localtime_r(&now, &tmv);
    char tbuf[16];
    std::strftime(tbuf, sizeof(tbuf), "%H:%M", &tmv);
    next.updated = tbuf;
    next.valid = true;
    next.error.clear();

    std::lock_guard<std::mutex> lock(mutex_);
    data_ = next;
    return true;
}

// ---------------------------------------------------------------------------
// WeatherMeasure
// ---------------------------------------------------------------------------

void WeatherMeasure::onLoad(const IniLexer& skin, const std::string& section) {
    section_ = section;
    type_ = lower(expandVars(skin, skin.getOr(section, "Type", "Temperature")));
    imperial_ = lower(expandVars(skin, skin.getOr(section, "Units", "#WeatherUnits#"))) == "imperial";

    double lat = toDouble(expandVars(skin, skin.getOr(section, "Latitude", "#WeatherLat#")), -26.2041);
    double lon = toDouble(expandVars(skin, skin.getOr(section, "Longitude", "#WeatherLon#")), 28.0473);
    int refresh = static_cast<int>(toDouble(expandVars(skin, skin.getOr(section, "RefreshMinutes", "10")), 10));

    backend_ = WeatherBackend::acquire(lat, lon, imperial_, refresh);

    if (type_ == "humidity" || type_ == "rainchance") {
        maxValue_ = 100.0;
    }
    current_ = "…";
}

void WeatherMeasure::onUpdate(const IniLexer& /*skin*/, std::function<void(const std::string&)> /*executeBangs*/) {
    if (!backend_) return;
    WeatherData d = backend_->snapshot();

    if (type_ == "status") {
        if (d.fetching && !d.valid) current_ = "Updating…";
        else if (!d.error.empty() && !d.valid) current_ = "Offline";
        else if (!d.error.empty()) current_ = "Offline · " + d.updated;
        else current_ = "Updated " + d.updated;
        numeric_ = d.valid ? 1.0 : 0.0;
        return;
    }
    if (type_ == "tempunit") {
        current_ = imperial_ ? "°F" : "°C";
        return;
    }
    if (type_ == "speedunit") {
        current_ = imperial_ ? "mph" : "km/h";
        return;
    }

    if (!d.valid) {
        numeric_ = 0.0;
        if (type_ == "condition") current_ = d.fetching ? "Fetching weather…" : "Weather unavailable";
        else current_ = "--";
        return;
    }

    if (type_ == "temperature" || type_ == "temp") {
        numeric_ = d.temperature;
        current_ = fmt0(d.temperature);
    } else if (type_ == "feelslike") {
        numeric_ = d.feelsLike;
        current_ = fmt0(d.feelsLike);
    } else if (type_ == "condition") {
        numeric_ = d.weatherCode;
        current_ = conditionText(d.weatherCode);
    } else if (type_ == "code") {
        numeric_ = d.weatherCode;
        current_ = std::to_string(d.weatherCode);
    } else if (type_ == "humidity") {
        numeric_ = d.humidity;
        current_ = fmt0(d.humidity);
    } else if (type_ == "rainchance") {
        numeric_ = d.rainChance;
        current_ = fmt0(d.rainChance);
    } else if (type_ == "windspeed") {
        numeric_ = d.windSpeed;
        current_ = fmt0(d.windSpeed);
    } else if (type_ == "winddirection") {
        numeric_ = d.windDirDeg;
        current_ = compass(d.windDirDeg);
    } else if (type_ == "winddegrees") {
        numeric_ = d.windDirDeg;
        current_ = fmt0(d.windDirDeg);
    } else if (type_ == "high") {
        numeric_ = d.high;
        current_ = fmt0(d.high);
    } else if (type_ == "low") {
        numeric_ = d.low;
        current_ = fmt0(d.low);
    } else if (type_ == "isday") {
        numeric_ = d.isDay ? 1.0 : 0.0;
        current_ = d.isDay ? "1" : "0";
    } else if (type_ == "updated") {
        current_ = d.updated;
    }
}
