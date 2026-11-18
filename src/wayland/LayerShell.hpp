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
#include "xdg-shell-client-protocol.h"
#include "xdg-decoration-unstable-v1-client-protocol.h"
#include "fractional-scale-v1-client-protocol.h"
#include "viewporter-client-protocol.h"
#include "xdg-output-unstable-v1-client-protocol.h"

typedef struct _XDisplay Display;
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

  // Dynamically moves and resizes the surface.
  void moveAndResize(int x, int y, int width, int height);

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

  void setPositionCallback(std::function<void(int x, int y)> cb) {
    positionCb_ = std::move(cb);
  }

  // Runs a wl_display_dispatch loop until the surface is closed.
  void run();

  // Processes any pending Wayland events without blocking, then flushes
  // outgoing requests. Returns false once the surface has been closed or
  // the connection is broken. Used to drive a tick-based render loop.
  bool dispatchPending();

  bool connected() const noexcept { return display_ != nullptr || xDisplay_ != nullptr; }
  bool closed() const noexcept { return closed_; }
  int width() const noexcept { return width_; }
  int height() const noexcept { return height_; }
  
  int getMonitorCount() const noexcept { return static_cast<int>(outputs_.size()); }
  int getScreenX(int monitorIndex) const noexcept;
  int getScreenY(int monitorIndex) const noexcept;
  int getScreenWidth(int monitorIndex) const noexcept;
  int getScreenHeight(int monitorIndex) const noexcept;
  double getScreenScale(int monitorIndex) const noexcept;
  double getSurfaceScale() const noexcept { return surfaceScale_; }

  // --- Registry / listener plumbing (public so the C trampolines in the
  //     implementation can reach members; not part of the intended API). ---
  void handleGlobal(wl_registry *registry, uint32_t name, const char *interface,
                    uint32_t version);
  void handleLayerConfigure(zwlr_layer_surface_v1 *surface, uint32_t serial,
                            uint32_t width, uint32_t height);
  void handleLayerClosed();
  void handleXdgSurfaceConfigure(xdg_surface *surface, uint32_t serial);
  void handleXdgToplevelConfigure(int32_t width, int32_t height);
  void handleXdgToplevelClose();

  // Seat/Pointer events
  void handleSeatCapabilities(wl_seat *seat, uint32_t caps);
  void handlePointerEnter(double x, double y);
  void handlePointerMotion(double x, double y);
  void handlePointerButton(uint32_t button, uint32_t state);

  void handleOutputGeometry(wl_output *output, int x, int y);
  void handleOutputMode(wl_output *output, uint32_t flags, int width, int height);
  void handleOutputScale(wl_output *output, int32_t factor);
  void handleXdgOutputLogicalPosition(struct zxdg_output_v1 *xdgOutput, int32_t x, int32_t y);
  void handleXdgOutputLogicalSize(struct zxdg_output_v1 *xdgOutput, int32_t width, int32_t height);
  void handlePreferredFractionalScale(uint32_t scale120);

private:
  void disconnect();
  bool initEGL();
  bool initX11Surface(int width, int height, int windowX, int windowY,
                      const std::string &scope);
  void updateBufferScaleAndViewport();

  wl_display *display_ = nullptr;
  wl_registry *registry_ = nullptr;
  wl_compositor *compositor_ = nullptr;
  zwlr_layer_shell_v1 *layerShell_ = nullptr;
  struct xdg_wm_base *xdgWmBase_ = nullptr;
  struct zxdg_decoration_manager_v1 *xdgDecorationManager_ = nullptr;
  struct wp_fractional_scale_manager_v1 *fractionalScaleManager_ = nullptr;
  struct wp_viewporter *viewporter_ = nullptr;
  struct zxdg_output_manager_v1 *xdgOutputManager_ = nullptr;
  wl_seat *seat_ = nullptr;
  wl_pointer *pointer_ = nullptr;
  
  struct OutputInfo {
      wl_output *output = nullptr;
      struct zxdg_output_v1 *xdgOutput = nullptr;
      int x = 0;
      int y = 0;
      int width = 0;
      int height = 0;
      int logicalWidth = 0;
      int logicalHeight = 0;
      int scale = 1;
      double fractionalScale = 1.0;
  };
  std::vector<OutputInfo> outputs_;

  wl_surface *surface_ = nullptr;
  zwlr_layer_surface_v1 *layerSurface_ = nullptr;
  struct xdg_surface *xdgSurface_ = nullptr;
  struct xdg_toplevel *xdgToplevel_ = nullptr;
  struct zxdg_toplevel_decoration_v1 *xdgToplevelDecoration_ = nullptr;
  struct wp_fractional_scale_v1 *fractionalScale_ = nullptr;
  struct wp_viewport *viewport_ = nullptr;
  int pendingXdgWidth_ = 0;
  int pendingXdgHeight_ = 0;
  double surfaceScale_ = 1.0;

  // X11 / XWayland fallback state
  bool useX11_ = false;
  Display *xDisplay_ = nullptr;
  unsigned long xWindow_ = 0;
  unsigned long xColormap_ = 0;
  unsigned long wmDeleteMessage_ = 0;
  int xWindowX_ = 0;
  int xWindowY_ = 0;
  bool xButtonDown_ = false;
  bool xDragging_ = false;
  int xDragStartRootX_ = 0;
  int xDragStartRootY_ = 0;
  int xDragStartWinX_ = 0;
  int xDragStartWinY_ = 0;
  
  wl_egl_window *eglWindow_ = nullptr;
  EGLDisplay eglDisplay_ = EGL_NO_DISPLAY;
  EGLContext eglContext_ = EGL_NO_CONTEXT;
  EGLSurface eglSurface_ = EGL_NO_SURFACE;

  int width_ = 0;
  int height_ = 0;

  double pointerX_ = 0.0;
  double pointerY_ = 0.0;
  std::function<void(double, double, uint32_t)> mouseCb_;
  std::function<void(int, int)> positionCb_;

  bool configured_ = false;
  bool closed_ = false;
};
