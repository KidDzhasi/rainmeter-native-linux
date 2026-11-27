#include "NowPlayingMeasure.hpp"
#include <gio/gio.h>
#include <iostream>
#include <chrono>
#include <cstdlib>

namespace {
// Helper to safely lower-case a string for playerType comparison
void toLower(std::string& s) {
    for (char& c : s) {
        if (c >= 'A' && c <= 'Z') {
            c = static_cast<char>(c - 'A' + 'a');
        }
    }
}
}

NowPlayingBackend& NowPlayingBackend::getInstance() {
    static NowPlayingBackend instance;
    return instance;
}

NowPlayingBackend::NowPlayingBackend() {
    thread_ = std::thread(&NowPlayingBackend::workerThread, this);
}

NowPlayingBackend::~NowPlayingBackend() {
    running_ = false;
    if (thread_.joinable()) {
        thread_.join();
    }
}

MprisTrackInfo NowPlayingBackend::getTrackInfo() {
    std::lock_guard<std::mutex> lock(mutex_);
    return currentTrack_;
}

void NowPlayingBackend::sendCommand(const std::string& command) {
    std::string targetPlayer;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        targetPlayer = currentTrack_.activePlayer;
    }

    GError* error = nullptr;
    GDBusConnection* conn = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
    if (!conn) {
        if (error) g_error_free(error);
        return;
    }

    if (targetPlayer.empty()) {
        GVariant* namesResult = g_dbus_connection_call_sync(
            conn, "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "ListNames", nullptr,
            G_VARIANT_TYPE("(as)"), G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
        );
        if (namesResult) {
            GVariantIter* iter;
            g_variant_get(namesResult, "(as)", &iter);
            gchar* name;
            while (g_variant_iter_loop(iter, "s", &name)) {
                std::string sname(name);
                if (sname.find("org.mpris.MediaPlayer2.") == 0) {
                    targetPlayer = sname;
                    break;
                }
            }
            g_variant_iter_free(iter);
            g_variant_unref(namesResult);
        }
    }

    if (targetPlayer.empty()) {
        g_object_unref(conn);
        return;
    }

    std::string cmd = command;
    while (!cmd.empty() && (cmd.front() == '"' || cmd.front() == ' ')) cmd.erase(0, 1);
    while (!cmd.empty() && (cmd.back() == '"' || cmd.back() == ' ')) cmd.pop_back();
    std::string lcmd = cmd;
    toLower(lcmd);

    std::string method = "";
    if (lcmd == "playpause") method = "PlayPause";
    else if (lcmd == "next") method = "Next";
    else if (lcmd == "previous" || lcmd == "prev") method = "Previous";
    else if (lcmd == "play") method = "Play";
    else if (lcmd == "pause") method = "Pause";
    else if (lcmd == "stop") method = "Stop";

    if (!method.empty()) {
        GVariant* result = g_dbus_connection_call_sync(
            conn,
            targetPlayer.c_str(),
            "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2.Player",
            method.c_str(),
            nullptr,
            nullptr,
            G_DBUS_CALL_FLAGS_NONE,
            -1,
            nullptr,
            nullptr
        );
        if (result) g_variant_unref(result);
    } else if (lcmd == "shuffle") {
        GVariant* curVal = g_dbus_connection_call_sync(
            conn, targetPlayer.c_str(), "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties", "Get",
            g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "Shuffle"),
            G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
        );
        bool nextShuffle = true;
        if (curVal) {
            GVariant* inner = nullptr;
            g_variant_get(curVal, "(v)", &inner);
            if (inner && g_variant_is_of_type(inner, G_VARIANT_TYPE_BOOLEAN)) {
                nextShuffle = !g_variant_get_boolean(inner);
            }
            if (inner) g_variant_unref(inner);
            g_variant_unref(curVal);
        }
        GVariant* res = g_dbus_connection_call_sync(
            conn, targetPlayer.c_str(), "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties", "Set",
            g_variant_new("(ssv)", "org.mpris.MediaPlayer2.Player", "Shuffle", g_variant_new_boolean(nextShuffle)),
            nullptr, G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
        );
        if (res) g_variant_unref(res);
    } else if (lcmd == "repeat") {
        GVariant* res = g_dbus_connection_call_sync(
            conn, targetPlayer.c_str(), "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties", "Set",
            g_variant_new("(ssv)", "org.mpris.MediaPlayer2.Player", "LoopStatus", g_variant_new_string("Playlist")),
            nullptr, G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
        );
        if (res) g_variant_unref(res);
    }
    g_object_unref(conn);
}

void NowPlayingBackend::workerThread() {
    GError* error = nullptr;
    GDBusConnection* conn = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
    if (!conn) {
        if (error) g_error_free(error);
        return; // silently fail DBus
    }

    std::string lastArtUrl = "";

    while (running_) {
        MprisTrackInfo info;
        
        // 1. List names to find all MPRIS players and pick the best active one
        GVariant* namesResult = g_dbus_connection_call_sync(
            conn,
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "ListNames",
            nullptr,
            G_VARIANT_TYPE("(as)"),
            G_DBUS_CALL_FLAGS_NONE,
            -1,
            nullptr,
            nullptr
        );

        std::string activePlayer;
        int bestState = -1; // 1 = Playing (best), 2 = Paused, 0 = Stopped
        if (namesResult) {
            GVariantIter* iter;
            g_variant_get(namesResult, "(as)", &iter);
            gchar* name;
            while (g_variant_iter_loop(iter, "s", &name)) {
                std::string sname(name);
                if (sname.find("org.mpris.MediaPlayer2.") == 0) {
                    int st = 0;
                    GVariant* statusResult = g_dbus_connection_call_sync(
                        conn, sname.c_str(), "/org/mpris/MediaPlayer2",
                        "org.freedesktop.DBus.Properties", "Get",
                        g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "PlaybackStatus"),
                        G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
                    );
                    if (statusResult) {
                        GVariant* inner = nullptr;
                        g_variant_get(statusResult, "(v)", &inner);
                        if (inner && g_variant_is_of_type(inner, G_VARIANT_TYPE_STRING)) {
                            std::string s(g_variant_get_string(inner, nullptr));
                            if (s == "Playing") st = 1;
                            else if (s == "Paused") st = 2;
                        }
                        if (inner) g_variant_unref(inner);
                        g_variant_unref(statusResult);
                    }
                    if (st == 1) {
                        activePlayer = sname;
                        bestState = 1;
                        break;
                    } else if (st == 2 && bestState != 1) {
                        activePlayer = sname;
                        bestState = 2;
                    } else if (activePlayer.empty()) {
                        activePlayer = sname;
                        bestState = st;
                    }
                }
            }
            g_variant_iter_free(iter);
            g_variant_unref(namesResult);
        }

        if (!activePlayer.empty()) {
            info.activePlayer = activePlayer;
            info.state = (bestState >= 0) ? bestState : 0;

            // 3. Query Metadata (even when Paused or Stopped, and preserve last known cover art/title if still active)
            if (true) {
                GVariant* metaResult = g_dbus_connection_call_sync(
                    conn, activePlayer.c_str(), "/org/mpris/MediaPlayer2",
                    "org.freedesktop.DBus.Properties", "Get",
                    g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "Metadata"),
                    G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
                );

                if (metaResult) {
                    GVariant* inner = nullptr;
                    g_variant_get(metaResult, "(v)", &inner);
                    if (inner) {
                        GVariantIter* dictIter;
                        g_variant_get(inner, "a{sv}", &dictIter);
                        gchar* key;
                        GVariant* value;
                        
                        while (g_variant_iter_loop(dictIter, "{sv}", &key, &value)) {
                            std::string skey(key);
                            if (skey == "xesam:title" && g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) {
                                info.title = g_variant_get_string(value, nullptr);
                            } else if (skey == "xesam:artist" && g_variant_is_of_type(value, G_VARIANT_TYPE_ARRAY)) {
                                GVariantIter* arrayIter;
                                g_variant_get(value, "as", &arrayIter);
                                gchar* artistName;
                                if (g_variant_iter_loop(arrayIter, "s", &artistName)) {
                                    info.artist = artistName;
                                }
                                g_variant_iter_free(arrayIter);
                            } else if (skey == "xesam:album" && g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) {
                                info.album = g_variant_get_string(value, nullptr);
                            } else if (skey == "mpris:artUrl" && g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) {
                                std::string artUrl = g_variant_get_string(value, nullptr);
                                auto urlDecode = [](const std::string& str) {
                                    std::string res;
                                    res.reserve(str.size());
                                    for (std::size_t i = 0; i < str.size(); ++i) {
                                        if (str[i] == '%' && i + 2 < str.size()) {
                                            int hex = 0;
                                            if (std::sscanf(str.substr(i + 1, 2).c_str(), "%x", &hex) == 1) {
                                                res += static_cast<char>(hex);
                                                i += 2;
                                                continue;
                                            }
                                        }
                                        res += str[i];
                                    }
                                    return res;
                                };
                                if (artUrl.rfind("file://", 0) == 0) {
                                    std::string localArt = urlDecode(artUrl.substr(7));
                                    info.coverUrl = "/tmp/rainmeter_cover.png";
                                    if (!localArt.empty()) {
                                        std::string cpCmd = "cp -f \"" + localArt + "\" /tmp/rainmeter_cover.png 2>/dev/null";
                                        int r = system(cpCmd.c_str());
                                        (void)r;
                                    }
                                } else if (!artUrl.empty()) {
                                    info.coverUrl = "/tmp/rainmeter_cover.png";
                                    if (artUrl != lastArtUrl && (artUrl.rfind("http://", 0) == 0 || artUrl.rfind("https://", 0) == 0)) {
                                        lastArtUrl = artUrl;
                                        std::string cmd = "curl -sL \"" + artUrl + "\" -o /tmp/rainmeter_cover.png 2>/dev/null";
                                        int r = system(cmd.c_str());
                                        (void)r;
                                    }
                                }
                            } else if (skey == "mpris:length") {
                                if (g_variant_is_of_type(value, G_VARIANT_TYPE_UINT64)) {
                                    info.duration = static_cast<double>(g_variant_get_uint64(value)) / 1000000.0;
                                } else if (g_variant_is_of_type(value, G_VARIANT_TYPE_INT64)) {
                                    info.duration = static_cast<double>(g_variant_get_int64(value)) / 1000000.0;
                                }
                            }
                        }
                        g_variant_iter_free(dictIter);
                        g_variant_unref(inner);
                    }
                    g_variant_unref(metaResult);
                }
                if (info.coverUrl.empty() && std::getenv("HOME") != nullptr) {
                    if (FILE* f = std::fopen("/tmp/rainmeter_cover.png", "rb")) {
                        std::fclose(f);
                        info.coverUrl = "/tmp/rainmeter_cover.png";
                    }
                }
                
                // Query Position
                GVariant* posResult = g_dbus_connection_call_sync(
                    conn, activePlayer.c_str(), "/org/mpris/MediaPlayer2",
                    "org.freedesktop.DBus.Properties", "Get",
                    g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "Position"),
                    G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
                );
                
                if (posResult) {
                    GVariant* inner = nullptr;
                    g_variant_get(posResult, "(v)", &inner);
                    if (inner) {
                        if (g_variant_is_of_type(inner, G_VARIANT_TYPE_INT64)) {
                            info.position = static_cast<double>(g_variant_get_int64(inner)) / 1000000.0;
                        } else if (g_variant_is_of_type(inner, G_VARIANT_TYPE_UINT64)) {
                            info.position = static_cast<double>(g_variant_get_uint64(inner)) / 1000000.0;
                        }
                        g_variant_unref(inner);
                    }
                    g_variant_unref(posResult);
                }

                if (info.duration > 0.0) {
                    info.progress = std::clamp((info.position / info.duration) * 100.0, 0.0, 100.0);
                } else {
                    info.progress = 0.0;
                }

                if (info.title.empty()) info.title = "Unknown Title";
                if (info.artist.empty()) info.artist = "Unknown Artist";
                if (info.album.empty()) info.album = "Single";
            } else {
                info.title = "Media Paused / Stopped";
                info.artist = "Click Play to Resume";
                info.album = "Trad Desktop Media";
            }
        } else {
            info.state = 0;
            info.title = "No Media Playing";
            info.artist = "Start Spotify, Browser, or Music App";
            info.album = "Trad Desktop Media";
            info.coverUrl = "";
        }

        {
            std::lock_guard<std::mutex> lock(mutex_);
            currentTrack_ = info;
        }

        // Back off D-Bus polling when no media is actively playing to save CPU on low-end PCs
        const int sleepMs = (info.state == 1) ? 1000 : (activePlayer.empty() ? 2500 : 1500);
        std::this_thread::sleep_for(std::chrono::milliseconds(sleepMs));
    }

    g_object_unref(conn);
}

void NowPlayingMeasure::onLoad(const IniLexer& skin, const std::string& section) {
    name_ = section;
    playerType_ = skin.getOr(section, "PlayerType", "");
    std::string ptype = playerType_;
    toLower(ptype);
    if (ptype == "progress") {
        maxValue_ = 100.0;
    }
}

void NowPlayingMeasure::onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) {
    (void)executeBangs;
    if (dynamicVariables_) {
        playerType_ = skin.getOr(name_, "PlayerType", playerType_);
    }

    MprisTrackInfo info = NowPlayingBackend::getInstance().getTrackInfo();
    
    std::string ptype = playerType_;
    toLower(ptype);

    auto formatTime = [](double sec) -> std::string {
        if (sec < 0.0 || !std::isfinite(sec)) sec = 0.0;
        int totalSec = static_cast<int>(sec);
        int mins = totalSec / 60;
        int secs = totalSec % 60;
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%d:%02d", mins, secs);
        return buf;
    };

    if (ptype == "title") {
        current_ = info.title;
    } else if (ptype == "artist") {
        current_ = info.artist;
    } else if (ptype == "album") {
        current_ = info.album;
    } else if (ptype == "cover") {
        current_ = info.coverUrl;
    } else if (ptype == "state") {
        numeric_ = info.state;
        current_ = std::to_string(static_cast<long long>(numeric_));
    } else if (ptype == "isplaying") {
        numeric_ = (info.state == 1) ? 1.0 : 0.0;
        current_ = (info.state == 1) ? "1" : "0";
    } else if (ptype == "ispaused") {
        numeric_ = (info.state == 1) ? 0.0 : 1.0;
        current_ = (info.state == 1) ? "0" : "1";
    } else if (ptype == "statebutton" || ptype == "playpauseicon") {
        numeric_ = info.state;
        current_ = (info.state == 1) ? "||" : "▶";
    } else if (ptype == "progress") {
        maxValue_ = 100.0;
        numeric_ = info.progress;
        char buf[64];
        std::snprintf(buf, sizeof(buf), "%.1f", numeric_);
        current_ = buf;
    } else if (ptype == "position") {
        maxValue_ = std::max(1.0, info.duration);
        numeric_ = info.position;
        current_ = formatTime(info.position);
    } else if (ptype == "duration") {
        numeric_ = info.duration;
        current_ = formatTime(info.duration);
    }
}
