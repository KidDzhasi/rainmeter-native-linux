#include "WeatherMeasure.hpp"

#include <curl/curl.h>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>

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

int metSymbolToWmo(const std::string& sym) {
    if (sym.find("thunder") != std::string::npos) return 95;
    if (sym.find("heavyrain") != std::string::npos) return 65;
    if (sym.find("rainshowers") != std::string::npos) return 80;
    if (sym.find("lightrain") != std::string::npos) return 61;
    if (sym.find("rain") != std::string::npos || sym.find("sleet") != std::string::npos) return 63;
    if (sym.find("snow") != std::string::npos) return 73;
    if (sym.find("fog") != std::string::npos) return 45;
    if (sym.find("partlycloudy") != std::string::npos) return 2;
    if (sym.find("fair") != std::string::npos) return 1;
    if (sym.find("cloudy") != std::string::npos) return 3;
    if (sym.find("clearsky") != std::string::npos) return 0;
    return 2;
}

std::string cacheFilePath(double lat, double lon, bool imperial) {
    const char* home = std::getenv("HOME");
    std::filesystem::path dir = home ? (std::filesystem::path(home) / ".cache" / "trad-desktop")
                                     : std::filesystem::path("/tmp/trad-desktop");
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    char fname[96];
    std::snprintf(fname, sizeof(fname), "c_weather_%.3f_%.3f_%d.txt", lat, lon, imperial ? 1 : 0);
    return (dir / fname).string();
}

bool readWeatherDiskCache(const std::string& path, WeatherData& out, bool allowStale) {
    std::error_code ec;
    if (!std::filesystem::exists(path, ec)) return false;
    auto ftime = std::filesystem::last_write_time(path, ec);
    if (!ec && !allowStale) {
        auto age = std::chrono::file_clock::now() - ftime;
        if (age > std::chrono::minutes(15)) return false;
    }
    std::ifstream in(path);
    if (!in.is_open()) return false;
    WeatherData d;
    std::string line;
    if (!std::getline(in, d.updated)) return false;
    in >> d.temperature >> d.feelsLike >> d.humidity >> d.rainChance
       >> d.windSpeed >> d.windDirDeg >> d.high >> d.low >> d.weatherCode >> d.isDay;
    if (in.fail()) return false;
    d.valid = true;
    d.fetching = false;
    out = d;
    return true;
}

void writeWeatherDiskCache(const std::string& path, const WeatherData& d) {
    if (!d.valid) return;
    std::ofstream out(path, std::ios::trunc);
    if (!out.is_open()) return;
    out << d.updated << "\n"
        << d.temperature << " " << d.feelsLike << " " << d.humidity << " " << d.rainChance << " "
        << d.windSpeed << " " << d.windDirDeg << " " << d.high << " " << d.low << " "
        << d.weatherCode << " " << (d.isDay ? 1 : 0) << "\n";
}

bool httpGetUrl(const std::string& url, std::string& body, long& httpCode) {
    body.clear();
    httpCode = 0;
    CURL* curl = curl_easy_init();
    if (!curl) return false;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writeCb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 12L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "TradDesktop/1.2 (github.com/KidDzhasi/Trad-Desktop)");
    CURLcode res = curl_easy_perform(curl);
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
    curl_easy_cleanup(curl);
    return (res == CURLE_OK && httpCode == 200);
}

bool parseMetNo(const std::string& body, bool imperial, WeatherData& next) {
    std::string details = objectBody(body, "details");
    double tempC = 0.0;
    if (!numberField(details, "air_temperature", tempC)) return false;

    double hum = 0.0, windMs = 0.0, windDir = 0.0;
    numberField(details, "relative_humidity", hum);
    numberField(details, "wind_speed", windMs);
    numberField(details, "wind_from_direction", windDir);

    // Find first symbol_code
    std::string sym;
    std::size_t sp = body.find("\"symbol_code\":\"");
    if (sp != std::string::npos) {
        sp += 15;
        std::size_t se = body.find('"', sp);
        if (se != std::string::npos) sym = body.substr(sp, se - sp);
    }

    // Scan first 24 timeseries air_temperature values for High / Low
    double hiC = tempC, loC = tempC;
    std::size_t pos = 0;
    for (int k = 0; k < 24; ++k) {
        std::size_t tp = body.find("\"air_temperature\":", pos);
        if (tp == std::string::npos) break;
        double tv = tempC;
        char* end = nullptr;
        tv = std::strtod(body.c_str() + tp + 18, &end);
        if (end != body.c_str() + tp + 18) {
            hiC = std::max(hiC, tv);
            loC = std::min(loC, tv);
        }
        pos = tp + 18;
    }

    auto convTemp = [&](double c) { return imperial ? (c * 9.0 / 5.0 + 32.0) : c; };
    next.temperature = convTemp(tempC);
    next.feelsLike = next.temperature;
    next.high = convTemp(hiC);
    next.low = convTemp(loC);
    next.humidity = hum;
    next.windSpeed = imperial ? (windMs * 2.23694) : (windMs * 3.6);
    next.windDirDeg = windDir;
    next.weatherCode = metSymbolToWmo(sym);
    next.rainChance = (sym.find("rain") != std::string::npos || sym.find("thunder") != std::string::npos) ? 65.0 : 10.0;
    return true;
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
    const std::string cpath = cacheFilePath(lat_, lon_, imperial_);
    WeatherData cached;
    if (readWeatherDiskCache(cpath, cached, false)) {
        std::lock_guard<std::mutex> lock(mutex_);
        data_ = cached;
        return true;
    }

    char url[768];
    std::snprintf(url, sizeof(url),
                  "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
                  "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
                  "precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m,is_day"
                  "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                  "&timezone=auto&forecast_days=1%s",
                  lat_, lon_, imperial_ ? "&temperature_unit=fahrenheit&wind_speed_unit=mph" : "");

    std::string body;
    long httpCode = 0;
    bool ok = false;

    WeatherData next;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        next = data_; // keep last good values on failure
    }
    next.fetching = false;

    if (httpGetUrl(url, body, httpCode)) {
        std::string cur = objectBody(body, "current");
        std::string daily = objectBody(body, "daily");
        double v = 0.0;
        if (numberField(cur, "temperature_2m", v)) {
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
            ok = true;
        }
    }

    // Fallback to Norwegian Meteorological Institute (met.no) if Open-Meteo is rate-limited (429) or unreachable
    if (!ok) {
        std::cerr << "[Weather] Open-Meteo unavailable (HTTP " << httpCode << "), switching to met.no fallback\n";
        char metUrl[256];
        std::snprintf(metUrl, sizeof(metUrl),
                      "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=%.4f&lon=%.4f",
                      lat_, lon_);
        std::string metBody;
        long metCode = 0;
        if (httpGetUrl(metUrl, metBody, metCode) && parseMetNo(metBody, imperial_, next)) {
            ok = true;
        } else {
            std::cerr << "[Weather] met.no fallback failed (HTTP " << metCode << ")\n";
        }
    }

    if (!ok) {
        if (readWeatherDiskCache(cpath, cached, true)) {
            cached.error = "Cached";
            std::lock_guard<std::mutex> lock(mutex_);
            data_ = cached;
            return false;
        }
        next.error = "HTTP " + std::to_string(httpCode);
        std::lock_guard<std::mutex> lock(mutex_);
        data_ = next;
        return false;
    }

    std::time_t now = std::time(nullptr);
    std::tm tmv{};
    localtime_r(&now, &tmv);
    char tbuf[16];
    std::strftime(tbuf, sizeof(tbuf), "%H:%M", &tmv);
    next.updated = tbuf;
    next.valid = true;
    next.error.clear();

    writeWeatherDiskCache(cpath, next);
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
