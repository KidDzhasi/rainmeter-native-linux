#pragma once

#include "BaseMeasure.hpp"

#include <atomic>
#include <condition_variable>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

// Live weather data fetched from the free Open-Meteo API (no API key needed).
struct WeatherData {
    bool valid = false;
    bool fetching = true;
    std::string error;
    double temperature = 0.0;
    double feelsLike = 0.0;
    double humidity = 0.0;
    double rainChance = 0.0;
    double windSpeed = 0.0;
    double windDirDeg = 0.0;
    double high = 0.0;
    double low = 0.0;
    int weatherCode = -1;
    bool isDay = true;
    std::string updated; // local HH:MM of last successful fetch
};

// One background polling thread per (latitude, longitude, units) combination.
class WeatherBackend {
public:
    WeatherBackend(double lat, double lon, bool imperial, int refreshMinutes);
    ~WeatherBackend();

    WeatherData snapshot();
    void requestRefresh();

    static std::shared_ptr<WeatherBackend> acquire(double lat, double lon, bool imperial, int refreshMinutes);

private:
    void loop();
    bool fetchOnce();

    double lat_;
    double lon_;
    bool imperial_;
    int refreshMinutes_;

    std::mutex mutex_;
    std::condition_variable cv_;
    WeatherData data_;
    std::atomic<bool> running_{true};
    bool refreshRequested_ = false;
    std::thread thread_;
};

// Measure=Weather (or Measure=Plugin, Plugin=TradWeather)
//   Latitude=-23.0   Longitude=30.5   Units=metric|imperial   RefreshMinutes=10
//   Type=Temperature|FeelsLike|Condition|Humidity|RainChance|WindSpeed|
//        WindDirection|WindDegrees|High|Low|TempUnit|SpeedUnit|Updated|Status|Code|IsDay
class WeatherMeasure : public BaseMeasure {
protected:
    void onLoad(const IniLexer& skin, const std::string& section) override;
    void onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) override;

private:
    std::string section_;
    std::string type_;
    bool imperial_ = false;
    std::shared_ptr<WeatherBackend> backend_;
};
