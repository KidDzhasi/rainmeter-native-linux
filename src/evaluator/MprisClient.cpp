#include "MprisClient.hpp"
#include <array>
#include <memory>
#include <cstdio>
#include <iostream>
#include <chrono>
#include <cstdlib>

std::string execShell(const char* cmd) {
    std::array<char, 128> buffer;
    std::string result;
    struct PcloseDeleter {
        void operator()(FILE* f) const { pclose(f); }
    };
    std::unique_ptr<FILE, PcloseDeleter> pipe(popen(cmd, "r"));
    if (!pipe) return "";
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    if (!result.empty() && result.back() == '\n') {
        result.pop_back();
    }
    return result;
}

MprisClient::MprisClient() {
    thread_ = std::thread(&MprisClient::workerThread, this);
}

MprisClient::~MprisClient() {
    running_ = false;
    if (thread_.joinable()) {
        thread_.join();
    }
}

TrackInfo MprisClient::getTrackInfo() {
    std::lock_guard<std::mutex> lock(mutex_);
    return currentTrack_;
}

void MprisClient::sendCommand(const std::string& command) {
    if (command == "PlayPause") execShell("playerctl play-pause");
    else if (command == "Next") execShell("playerctl next");
    else if (command == "Previous") execShell("playerctl previous");
    else if (command.rfind("SetPosition ", 0) == 0) {
        std::string numStr = command.substr(12);
        double percent = 0.0;
        try { percent = std::stod(numStr); } catch(...) {}
        
        std::lock_guard<std::mutex> lock(mutex_);
        if (currentTrack_.duration > 0.0) {
            double targetSeconds = (percent / 100.0) * currentTrack_.duration;
            execShell(("playerctl position " + std::to_string(targetSeconds)).c_str());
        }
    }
}

void MprisClient::workerThread() {
    std::string lastArtUrl = "";
    while (running_) {
        TrackInfo info;
        std::string status = execShell("playerctl status 2>/dev/null");
        
        if (status == "Playing") info.state = 1;
        else if (status == "Paused") info.state = 2;
        else info.state = 0;

        if (info.state != 0) {
            info.title = execShell("playerctl metadata title 2>/dev/null");
            info.artist = execShell("playerctl metadata artist 2>/dev/null");
            info.album = execShell("playerctl metadata album 2>/dev/null");
            
            std::string lengthStr = execShell("playerctl metadata mpris:length 2>/dev/null");
            std::string positionStr = execShell("playerctl position 2>/dev/null");

            if (!lengthStr.empty()) {
                try {
                    info.duration = std::stod(lengthStr) / 1000000.0;
                } catch (...) { info.duration = 0.0; }
            }
            if (!positionStr.empty()) {
                try {
                    info.position = std::stod(positionStr);
                } catch (...) { info.position = 0.0; }
            }
            if (info.duration > 0.0) {
                info.progress = (info.position / info.duration) * 100.0;
            } else {
                info.progress = 0.0;
            }

            std::string artUrl = execShell("playerctl metadata mpris:artUrl 2>/dev/null");
            info.coverUrl = "/tmp/rainmeter_cover.png";

            // FORCE CONVERT IMAGE TO STANDARD PNG VIA IMAGEMAGICK
            if (!artUrl.empty() && artUrl != lastArtUrl) {
                lastArtUrl = artUrl;
                std::string cmd;
                if (artUrl.rfind("file://", 0) == 0) {
                    std::string localPath = artUrl.substr(7);
                    cmd = "convert "" + localPath + "" -resize 256x256 /tmp/rainmeter_cover.png 2>/dev/null";
                } else if (artUrl.rfind("http://", 0) == 0 || artUrl.rfind("https://", 0) == 0) {
                    cmd = "curl -s "" + artUrl + "" | convert - -resize 256x256 /tmp/rainmeter_cover.png 2>/dev/null";
                }
                if (!cmd.empty()) {
                    system(cmd.c_str());
                }
            }
            
            if (info.title.empty()) info.title = "Unknown Title";
            if (info.artist.empty()) info.artist = "Unknown Artist";
        } else {
            info.title = "No Media Playing";
            info.artist = "";
            info.coverUrl = "";
        }

        {
            std::lock_guard<std::mutex> lock(mutex_);
            currentTrack_ = info;
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }
}
