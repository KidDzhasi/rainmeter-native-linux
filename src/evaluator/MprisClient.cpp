#include "MprisClient.hpp"
#include <gio/gio.h>
#include <iostream>

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
  std::string activePlayer;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    activePlayer = currentTrack_.activePlayer;
  }
  if (activePlayer.empty()) return;
  
  GError* error = nullptr;
  GDBusConnection* connection = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
  if (!connection) {
    if (error) g_error_free(error);
    return;
  }
  
  // Fire and forget asynchronous call
  g_dbus_connection_call(connection,
     activePlayer.c_str(), "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player",
     command.c_str(), nullptr, nullptr, G_DBUS_CALL_FLAGS_NONE, 1000, nullptr, nullptr, nullptr);
     
  g_object_unref(connection);
}

void MprisClient::workerThread() {
  GError* error = nullptr;
  GDBusConnection* connection = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
  if (!connection) {
    if (error) {
       std::cerr << "MprisClient: D-Bus connection failed: " << error->message << "\n";
       g_error_free(error);
    }
    return;
  }
  
  while (running_) {
    for (int i=0; i<10 && running_; ++i) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    if (!running_) break;
    
    // Find active player
    GVariant* namesReply = g_dbus_connection_call_sync(connection,
        "org.freedesktop.DBus", "/", "org.freedesktop.DBus", "ListNames",
        nullptr, G_VARIANT_TYPE("(as)"), G_DBUS_CALL_FLAGS_NONE, 1000, nullptr, nullptr);
        
    std::string activePlayer;
    if (namesReply) {
       GVariantIter* iter;
       g_variant_get(namesReply, "(as)", &iter);
       char* name;
       while (g_variant_iter_loop(iter, "s", &name)) {
         std::string sname(name);
         if (sname.find("org.mpris.MediaPlayer2.") == 0) {
            activePlayer = sname;
            // Stop at first MPRIS player
            break;
         }
       }
       g_variant_iter_free(iter);
       g_variant_unref(namesReply);
    }
    
    TrackInfo info;
    info.activePlayer = activePlayer;
    
    if (!activePlayer.empty()) {
       gint64 length = 0;
       
       GVariant* propsReply = g_dbus_connection_call_sync(connection,
          activePlayer.c_str(), "/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties",
          "GetAll", g_variant_new("(s)", "org.mpris.MediaPlayer2.Player"), 
          G_VARIANT_TYPE("(a{sv})"), G_DBUS_CALL_FLAGS_NONE, 1000, nullptr, nullptr);
          
       if (propsReply) {
          GVariant* dict = g_variant_get_child_value(propsReply, 0);
          GVariantIter iter;
          g_variant_iter_init(&iter, dict);
          char* key;
          GVariant* val;
          while (g_variant_iter_loop(&iter, "{sv}", &key, &val)) {
             std::string skey(key);
             if (skey == "PlaybackStatus") {
                const char* status = g_variant_get_string(val, nullptr);
                if (status) {
                   if (std::string(status) == "Playing") info.state = 1;
                   else if (std::string(status) == "Paused") info.state = 2;
                   else info.state = 0;
                }
             } else if (skey == "Metadata") {
                GVariantIter mIter;
                g_variant_iter_init(&mIter, val);
                char* mKey;
                GVariant* mVal;
                while (g_variant_iter_loop(&mIter, "{sv}", &mKey, &mVal)) {
                   std::string smKey(mKey);
                   if (smKey == "xesam:title") {
                      const char* s = g_variant_get_string(mVal, nullptr);
                      if (s) info.title = s;
                   } else if (smKey == "xesam:artist") {
                      if (g_variant_is_of_type(mVal, G_VARIANT_TYPE("as"))) {
                          GVariantIter aIter;
                          g_variant_iter_init(&aIter, mVal);
                          char* artist;
                          if (g_variant_iter_loop(&aIter, "s", &artist)) {
                             info.artist = artist;
                          }
                      }
                   } else if (smKey == "xesam:album") {
                      const char* s = g_variant_get_string(mVal, nullptr);
                      if (s) info.album = s;
                   } else if (smKey == "mpris:artUrl") {
                      const char* s = g_variant_get_string(mVal, nullptr);
                      if (s) {
                          info.coverUrl = s;
                          if (info.coverUrl.find("file://") == 0) {
                              info.coverUrl = info.coverUrl.substr(7);
                          }
                      }
                   } else if (smKey == "mpris:length") {
                      length = g_variant_get_int64(mVal);
                   }
                }
             }
          }
          g_variant_unref(dict);
          g_variant_unref(propsReply);
       }
       
       GVariant* posReply = g_dbus_connection_call_sync(connection,
          activePlayer.c_str(), "/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties",
          "Get", g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "Position"),
          G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, 1000, nullptr, nullptr);
          
       gint64 position = 0;
       if (posReply) {
          GVariant* v = g_variant_get_child_value(posReply, 0);
          GVariant* inner = g_variant_get_variant(v);
          if (inner && g_variant_is_of_type(inner, G_VARIANT_TYPE_INT64)) {
             position = g_variant_get_int64(inner);
          }
          if (inner) g_variant_unref(inner);
          g_variant_unref(v);
          g_variant_unref(posReply);
       }
       
       if (length > 0) {
          info.progress = (static_cast<double>(position) / length) * 100.0;
       }
    }
    
    {
      std::lock_guard<std::mutex> lock(mutex_);
      currentTrack_ = info;
    }
  }
  g_object_unref(connection);
}
