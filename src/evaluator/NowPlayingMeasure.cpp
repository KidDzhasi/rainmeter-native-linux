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
    // Basic implementation for PlayPause/Next/Previous
    // We could use GDBus for this too, but for now we fallback or implement standard calls
    std::lock_guard<std::mutex> lock(mutex_);
    if (currentTrack_.activePlayer.empty()) return;

    GError* error = nullptr;
    GDBusConnection* conn = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
    if (!conn) {
        if (error) g_error_free(error);
        return;
    }

    std::string method = "";
    if (command == "PlayPause") method = "PlayPause";
    else if (command == "Next") method = "Next";
    else if (command == "Previous") method = "Previous";
    // SetPosition is more complex, skipped for brevity in this simplified direct DBus port

    if (!method.empty()) {
        GVariant* result = g_dbus_connection_call_sync(
            conn,
            currentTrack_.activePlayer.c_str(),
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
        
        // 1. List names to find an active player
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
        if (namesResult) {
            GVariantIter* iter;
            g_variant_get(namesResult, "(as)", &iter);
            gchar* name;
            while (g_variant_iter_loop(iter, "s", &name)) {
                std::string sname(name);
                if (sname.find("org.mpris.MediaPlayer2.") == 0) {
                    activePlayer = sname;
                    break;
                }
            }
            g_variant_iter_free(iter);
            g_variant_unref(namesResult);
        }

        if (!activePlayer.empty()) {
            info.activePlayer = activePlayer;
            
            // 2. Query PlaybackStatus
            GVariant* statusResult = g_dbus_connection_call_sync(
                conn, activePlayer.c_str(), "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties", "Get",
                g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "PlaybackStatus"),
                G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, -1, nullptr, nullptr
            );

            if (statusResult) {
                GVariant* inner = nullptr;
                g_variant_get(statusResult, "(v)", &inner);
                if (inner) {
                    const gchar* statusStr = g_variant_get_string(inner, nullptr);
                    if (statusStr) {
                        std::string s(statusStr);
                        if (s == "Playing") info.state = 1;
                        else if (s == "Paused") info.state = 2;
                        else info.state = 0;
                    }
                    g_variant_unref(inner);
                }
                g_variant_unref(statusResult);
            }

            // 3. Query Metadata
            if (info.state != 0) {
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
                        
                        std::string lengthStr;
                        while (g_variant_iter_loop(dictIter, "{sv}", &key, &value)) {
                            std::string skey(key);
                            if (skey == "xesam:title" && g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) {
                                info.title = g_variant_get_string(value, nullptr);
                            } else if (skey == "xesam:artist" && g_variant_is_of_type(value, G_VARIANT_TYPE_ARRAY)) {
                                GVariantIter* arrayIter;
                                g_variant_get(value, "as", &arrayIter);
                                gchar* artistName;
                                if (g_variant_iter_loop(arrayIter, "s", &artistName)) {
                                    info.artist = artistName; // Just take the first artist
                                }
                                g_variant_iter_free(arrayIter);
                            } else if (skey == "xesam:album" && g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) {
                                info.album = g_variant_get_string(value, nullptr);
                            } else if (skey == "mpris:artUrl" && g_variant_is_of_type(value, G_VARIANT_TYPE_STRING)) {
                                std::string artUrl = g_variant_get_string(value, nullptr);
                                info.coverUrl = "/tmp/rainmeter_cover.png";
                                
                                if (!artUrl.empty() && artUrl != lastArtUrl) {
                                    lastArtUrl = artUrl;
                                    std::string cmd;
                                    if (artUrl.rfind("file://", 0) == 0) {
                                        std::string localPath = artUrl.substr(7);
                                        cmd = "convert \"" + localPath + "\" -resize 256x256 /tmp/rainmeter_cover.png 2>/dev/null";
                                    } else if (artUrl.rfind("http://", 0) == 0 || artUrl.rfind("https://", 0) == 0) {
                                        cmd = "curl -s \"" + artUrl + "\" | convert - -resize 256x256 /tmp/rainmeter_cover.png 2>/dev/null";
                                    }
                                    if (!cmd.empty()) {
                                        system(cmd.c_str());
                                    }
                                }
                            } else if (skey == "mpris:length" && g_variant_is_of_type(value, G_VARIANT_TYPE_UINT64)) {
                                info.duration = static_cast<double>(g_variant_get_uint64(value)) / 1000000.0;
                            }
                        }
                        g_variant_iter_free(dictIter);
                        g_variant_unref(inner);
                    }
                    g_variant_unref(metaResult);
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
                        info.position = static_cast<double>(g_variant_get_int64(inner)) / 1000000.0;
                        g_variant_unref(inner);
                    }
                    g_variant_unref(posResult);
                }

                if (info.duration > 0.0) {
                    info.progress = (info.position / info.duration) * 100.0;
                } else {
                    info.progress = 0.0;
                }

                if (info.title.empty()) info.title = "Unknown Title";
                if (info.artist.empty()) info.artist = "Unknown Artist";
            }
        } else {
            info.state = 0;
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

    g_object_unref(conn);
}

void NowPlayingMeasure::onLoad(const IniLexer& skin, const std::string& section) {
    name_ = section;
    playerType_ = skin.getOr(section, "PlayerType", "");
}

void NowPlayingMeasure::onUpdate(const IniLexer& skin, std::function<void(const std::string&)> executeBangs) {
    if (dynamicVariables_) {
        playerType_ = skin.getOr(name_, "PlayerType", playerType_);
    }

    MprisTrackInfo info = NowPlayingBackend::getInstance().getTrackInfo();
    
    std::string ptype = playerType_;
    toLower(ptype);

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
    } else if (ptype == "progress" || ptype == "position") {
        numeric_ = info.progress;
        
        char buf[64];
        std::snprintf(buf, sizeof(buf), "%.1f", numeric_);
        current_ = buf;
    }
}
