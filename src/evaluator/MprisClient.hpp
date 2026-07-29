#pragma once

#include <string>
#include <mutex>
#include <thread>
#include <atomic>

struct TrackInfo {
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

class MprisClient {
public:
  MprisClient();
  ~MprisClient();

  // Retrieves the most recently polled media state.
  TrackInfo getTrackInfo();

  // Sends a method call (e.g. "PlayPause", "Next") to the active player.
  void sendCommand(const std::string& command);

private:
  void workerThread();
  
  std::mutex mutex_;
  TrackInfo currentTrack_;
  std::atomic<bool> running_{true};
  std::thread thread_;
};
