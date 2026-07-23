#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

#include <wayland-client.h>

#include "wlr-layer-shell-unstable-v1-client-protocol.h"

class CairoRenderer;

// LayerShellWindow presents a Cairo-rendered surface directly onto the
// desktop using the wlr-layer-shell protocol.
//
// Responsibilities:
//   * connect to the Wayland display and bind the required globals
//     (wl_compositor, wl_shm, zwlr_layer_shell_v1) via the registry;
//   * create a layer surface on the BOTTOM layer so it sits on the desktop
//     background, beneath normal application windows;
//   * allocate a wl_shm buffer, copy pixel data from a CairoRenderer's
//     image surface into it, attach it and commit;
//   * run the Wayland event loop to keep the window alive.
class LayerShellWindow {
public:
  LayerShellWindow() = default;
  ~LayerShellWindow();

  LayerShellWindow(const LayerShellWindow &) = delete;
  LayerShellWindow &operator=(const LayerShellWindow &) = delete;

  // Connects to the Wayland display and binds the required globals.
  // Returns false if the display cannot be opened or a required global
  // (compositor, shm, or layer shell) is missing.
  bool connect();

  // Creates a BOTTOM-layer surface of the requested size, anchored to the
  // top-left of the output, and performs the configure handshake.
  bool initLayerSurface(int width, int height,
                        const std::string &scope = "rainmeter-native");

  // Copies the CairoRenderer's ARGB32 pixels into a freshly-allocated
  // wl_shm buffer, attaches it to the surface, and commits the frame.
  void render(const CairoRenderer &renderer);

  // Runs a wl_display_dispatch loop until the surface is closed.
  void run();

  // Processes any pending Wayland events without blocking, then flushes
  // outgoing requests. Returns false once the surface has been closed or
  // the connection is broken. Used to drive a tick-based render loop.
  bool dispatchPending();

  bool connected() const noexcept { return display_ != nullptr; }
  bool closed() const noexcept { return closed_; }
  int width() const noexcept { return width_; }
  int height() const noexcept { return height_; }

  // --- Registry / listener plumbing (public so the C trampolines in the
  //     implementation can reach members; not part of the intended API). ---
  void handleGlobal(wl_registry *registry, uint32_t name, const char *interface,
                    uint32_t version);
  void handleLayerConfigure(zwlr_layer_surface_v1 *surface, uint32_t serial,
                            uint32_t width, uint32_t height);
  void handleLayerClosed();

private:
  void disconnect();

  wl_display *display_ = nullptr;
  wl_registry *registry_ = nullptr;
  wl_compositor *compositor_ = nullptr;
  wl_shm *shm_ = nullptr;
  zwlr_layer_shell_v1 *layerShell_ = nullptr;

  wl_surface *surface_ = nullptr;
  zwlr_layer_surface_v1 *layerSurface_ = nullptr;
  wl_buffer *buffer_ = nullptr; // persistent frame buffer

  int width_ = 0;
  int height_ = 0;

  bool configured_ = false;
  bool closed_ = false;
};
