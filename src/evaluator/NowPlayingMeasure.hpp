#pragma once

#include "BaseMeasure.hpp"
#include <string>
#include <mutex>
#include <thread>
#include <atomic>

struct MprisTrackInfo {
    std::string title;
    std::string artist;
    std::string album;
    std::string coverUrl;
    int state = 0; // 0 = stopped, 1 = playing, 2 = paused
    double progress = 0.0;
    double position = 0.0;
    double duration = 0.0;
    std::string activePlayer;
};

class NowPlayingBackend {
public:
    static NowPlayingBackend& getInstance();
    
    MprisTrackInfo getTrackInfo();
    void sendCommand(const std::string& command);

private:
    NowPlayingBackend();
    ~NowPlayingBackend();
    
    void workerThread();

    std::mutex mutex_;
    MprisTrackInfo currentTrack_;
    std::atomic<bool> running_{true};
    std::thread thread_;
};

class NowPlayingMeasure : public BaseMeasure {
public:
    NowPlayingMeasure() = default;
    ~NowPlayingMeasure() override = default;

protected:
    void onLoad(const IniLexer& skin, const std::string& section) override;
    void onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) override;

private:
    std::string playerType_;
    std::string name_;
};
