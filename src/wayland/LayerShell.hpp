#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

#include <wayland-client.h>
#include <wayland-egl.h>
#include <epoxy/egl.h>

#include "wlr-layer-shell-unstable-v1-client-protocol.h"
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
                        int windowX = 0, int windowY = 0,
                        int monitorIndex = 0, uint32_t anchor = 0,
                        const std::string &scope = "rainmeter-native");

  // Dynamically resizes the surface.
  void resize(int width, int height);

  // Makes the EGL context current on the calling thread.
  bool makeCurrent();

  // Swaps EGL buffers to present the frame.
  void swapBuffers();

  // Sets a callback to be invoked when a mouse button is released over the
  // surface. Coordinates are relative to the top-left of the surface.
  // button is the Wayland button code (e.g. BTN_LEFT).
  void setMouseCallback(std::function<void(double x, double y, uint32_t button)> cb) {
    mouseCb_ = std::move(cb);
  }

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
  
  int getScreenWidth(int monitorIndex) const noexcept;
  int getScreenHeight(int monitorIndex) const noexcept;

  // --- Registry / listener plumbing (public so the C trampolines in the
  //     implementation can reach members; not part of the intended API). ---
  void handleGlobal(wl_registry *registry, uint32_t name, const char *interface,
                    uint32_t version);
  void handleLayerConfigure(zwlr_layer_surface_v1 *surface, uint32_t serial,
                            uint32_t width, uint32_t height);
  void handleLayerClosed();

  // Seat/Pointer events
  void handleSeatCapabilities(wl_seat *seat, uint32_t caps);
  void handlePointerEnter(double x, double y);
  void handlePointerMotion(double x, double y);
  void handlePointerButton(uint32_t button, uint32_t state);

  void handleOutputMode(wl_output *output, uint32_t flags, int width, int height);

private:
  void disconnect();
  bool initEGL();

  wl_display *display_ = nullptr;
  wl_registry *registry_ = nullptr;
  wl_compositor *compositor_ = nullptr;
  zwlr_layer_shell_v1 *layerShell_ = nullptr;
  wl_seat *seat_ = nullptr;
  wl_pointer *pointer_ = nullptr;
  
  struct OutputInfo {
      wl_output *output;
      int width = 0;
      int height = 0;
  };
  std::vector<OutputInfo> outputs_;

  wl_surface *surface_ = nullptr;
  zwlr_layer_surface_v1 *layerSurface_ = nullptr;
  
  wl_egl_window *eglWindow_ = nullptr;
  EGLDisplay eglDisplay_ = EGL_NO_DISPLAY;
  EGLContext eglContext_ = EGL_NO_CONTEXT;
  EGLSurface eglSurface_ = EGL_NO_SURFACE;

  int width_ = 0;
  int height_ = 0;

  double pointerX_ = 0.0;
  double pointerY_ = 0.0;
  std::function<void(double, double, uint32_t)> mouseCb_;

  bool configured_ = false;
  bool closed_ = false;
};
