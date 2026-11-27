#include <functional>
#ifndef GLOBAL_STATE_FIX
#define GLOBAL_STATE_FIX
#include <string>
#include "evaluator/CommandProcessor.hpp"
std::function<void()> g_RequestKeyboardFocus;
std::function<void()> g_ReleaseKeyboardFocus;
#endif
#include "LayerShell.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <mutex>

#include <X11/Xatom.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xrandr.h>

namespace {

// --- Registry listener trampolines ---
void registryGlobal(void *data, wl_registry *registry, uint32_t name,
                    const char *interface, uint32_t version) {
  static_cast<LayerShellWindow *>(data)->handleGlobal(registry, name, interface,
                                                      version);
}

void registryGlobalRemove(void * /*data*/, wl_registry * /*registry*/,
                          uint32_t /*name*/) {}

const wl_registry_listener kRegistryListener = {
    .global = registryGlobal,
    .global_remove = registryGlobalRemove,
};

// --- Layer surface listener trampolines ---
void layerConfigure(void *data, zwlr_layer_surface_v1 *surface, uint32_t serial,
                    uint32_t width, uint32_t height) {
  static_cast<LayerShellWindow *>(data)->handleLayerConfigure(surface, serial,
                                                              width, height);
}

void layerClosed(void *data, zwlr_layer_surface_v1 * /*surface*/) {
  static_cast<LayerShellWindow *>(data)->handleLayerClosed();
}

const zwlr_layer_surface_v1_listener kLayerSurfaceListener = {
    .configure = layerConfigure,
    .closed = layerClosed,
};

// --- XDG shell listener trampolines ---
void xdgWmBasePing(void * /*data*/, struct xdg_wm_base *xdgWmBase,
                   uint32_t serial) {
  xdg_wm_base_pong(xdgWmBase, serial);
}

const struct xdg_wm_base_listener kXdgWmBaseListener = {
    .ping = xdgWmBasePing,
};

void xdgSurfaceConfigure(void *data, struct xdg_surface *surface,
                         uint32_t serial) {
  static_cast<LayerShellWindow *>(data)->handleXdgSurfaceConfigure(surface,
                                                                   serial);
}

const struct xdg_surface_listener kXdgSurfaceListener = {
    .configure = xdgSurfaceConfigure,
};

void xdgToplevelConfigure(void *data, struct xdg_toplevel * /*toplevel*/,
                          int32_t width, int32_t height,
                          struct wl_array * /*states*/) {
  static_cast<LayerShellWindow *>(data)->handleXdgToplevelConfigure(width,
                                                                    height);
}

void xdgToplevelClose(void *data, struct xdg_toplevel * /*toplevel*/) {
  static_cast<LayerShellWindow *>(data)->handleXdgToplevelClose();
}

const struct xdg_toplevel_listener kXdgToplevelListener = {
    .configure = xdgToplevelConfigure,
    .close = xdgToplevelClose,
};

void xdgToplevelDecorationConfigure(
    void * /*data*/, struct zxdg_toplevel_decoration_v1 * /*decoration*/,
    uint32_t /*mode*/) {}

const struct zxdg_toplevel_decoration_v1_listener
    kXdgToplevelDecorationListener = {
        .configure = xdgToplevelDecorationConfigure,
};

// --- Seat listener trampolines ---
void seatCapabilities(void *data, wl_seat *seat, uint32_t caps) {
  static_cast<LayerShellWindow *>(data)->handleSeatCapabilities(seat, caps);
}
void seatName(void * /*data*/, wl_seat * /*seat*/, const char * /*name*/) {}

const wl_seat_listener kSeatListener = {
    .capabilities = seatCapabilities,
    .name = seatName,
};

// --- Pointer listener trampolines ---
const struct wl_pointer_listener kPointerListener = {
    .enter = [](void *data, wl_pointer *, uint32_t, wl_surface *, wl_fixed_t x,
                wl_fixed_t y) {
      static_cast<LayerShellWindow *>(data)->handlePointerEnter(
          wl_fixed_to_double(x), wl_fixed_to_double(y));
    },
    .leave = [](void *, wl_pointer *, uint32_t, wl_surface *) {},
    .motion = [](void *data, wl_pointer *, uint32_t, wl_fixed_t x,
                 wl_fixed_t y) {
      static_cast<LayerShellWindow *>(data)->handlePointerMotion(
          wl_fixed_to_double(x), wl_fixed_to_double(y));
    },
    .button = [](void *data, wl_pointer *, uint32_t, uint32_t, uint32_t button,
                 uint32_t state) {
      static_cast<LayerShellWindow *>(data)->handlePointerButton(button, state);
    },
    .axis = [](void *, wl_pointer *, uint32_t, uint32_t, wl_fixed_t) {},
    .frame = [](void *, wl_pointer *) {},
    .axis_source = [](void *, wl_pointer *, uint32_t) {},
    .axis_stop = [](void *, wl_pointer *, uint32_t, uint32_t) {},
    .axis_discrete = [](void *, wl_pointer *, uint32_t, int32_t) {},
};

const struct wl_output_listener kOutputListener = {
    .geometry = [](void *data, wl_output *output, int32_t x, int32_t y, int32_t, int32_t, int32_t, const char *, const char *, int32_t) {
        static_cast<LayerShellWindow *>(data)->handleOutputGeometry(output, x, y);
    },
    .mode = [](void *data, wl_output *output, uint32_t flags, int32_t width, int32_t height, int32_t) {
        static_cast<LayerShellWindow *>(data)->handleOutputMode(output, flags, width, height);
    },
    .done = [](void *, wl_output *) {},
    .scale = [](void *data, wl_output *output, int32_t factor) {
        static_cast<LayerShellWindow *>(data)->handleOutputScale(output, factor);
    },
};

const struct zxdg_output_v1_listener kXdgOutputListener = {
    .logical_position = [](void *data, struct zxdg_output_v1 *xdgOutput, int32_t x, int32_t y) {
        static_cast<LayerShellWindow *>(data)->handleXdgOutputLogicalPosition(xdgOutput, x, y);
    },
    .logical_size = [](void *data, struct zxdg_output_v1 *xdgOutput, int32_t width, int32_t height) {
        static_cast<LayerShellWindow *>(data)->handleXdgOutputLogicalSize(xdgOutput, width, height);
    },
    .done = [](void *, struct zxdg_output_v1 *) {},
    .name = [](void *, struct zxdg_output_v1 *, const char *) {},
    .description = [](void *, struct zxdg_output_v1 *, const char *) {},
};

const struct wp_fractional_scale_v1_listener kFractionalScaleListener = {
    .preferred_scale = [](void *data, struct wp_fractional_scale_v1 *, uint32_t scale120) {
        static_cast<LayerShellWindow *>(data)->handlePreferredFractionalScale(scale120);
    },
};


// --- NATIVE KEYBOARD INPUT STUBS ---
#ifndef IOSTREAM_INCLUDED
#define IOSTREAM_INCLUDED
#include <iostream>
#endif

#include <linux/input-event-codes.h>




// Lightweight translator for raw Wayland hardware keys
char getCharFromKey(uint32_t key) {
    if (key >= KEY_1 && key <= KEY_9) return '1' + (key - KEY_1);
    if (key == KEY_0) return '0';
    if (key >= KEY_Q && key <= KEY_P) return "qwertyuiop"[key - KEY_Q];
    if (key >= KEY_A && key <= KEY_L) return "asdfghjkl"[key - KEY_A];
    if (key >= KEY_Z && key <= KEY_M) return "zxcvbnm"[key - KEY_Z];
    if (key == KEY_SPACE) return ' ';
    return 0;
}

void keyboardKeymap(void *data, wl_keyboard *keyboard, uint32_t format, int32_t fd, uint32_t size) {}
void keyboardEnter(void *data, wl_keyboard *keyboard, uint32_t serial, wl_surface *surface, wl_array *keys) {}
void keyboardLeave(void *data, wl_keyboard *keyboard, uint32_t serial, wl_surface *surface) {}
void keyboardKey(void *data, wl_keyboard *keyboard, uint32_t serial, uint32_t time, uint32_t key, uint32_t state) {
    if (state == 1 && g_InputState.active) { 
        if (key == KEY_BACKSPACE && !g_InputState.buffer.empty()) {
            g_InputState.buffer.pop_back();
        } else if (key == KEY_ESC) {
            g_InputState.buffer = "";
            g_InputState.active = false;
            if (g_ReleaseKeyboardFocus) g_ReleaseKeyboardFocus();
        } else if (key == KEY_ENTER) {
            std::string cmd = g_InputState.command;
            size_t pos = cmd.find("$UserInput$");
            if (pos != std::string::npos) {
                cmd.replace(pos, 11, g_InputState.buffer);
            }
            g_InputState.pendingCommand = cmd;
            g_InputState.buffer = "";
            g_InputState.active = false;
            if (g_ReleaseKeyboardFocus) g_ReleaseKeyboardFocus();
        } else {
            char c = getCharFromKey(key);
            if (c != 0) g_InputState.buffer += c;
        }
        std::cout << "[TYPING] Live Buffer: " << g_InputState.buffer << std::endl;
    }
}
void keyboardModifiers(void *data, wl_keyboard *keyboard, uint32_t serial, uint32_t mods_dep, uint32_t mods_lat, uint32_t mods_lock, uint32_t group) {}
void keyboardRepeatInfo(void *data, wl_keyboard *keyboard, int32_t rate, int32_t delay) {}

const wl_keyboard_listener kKeyboardListener = {
    .keymap = keyboardKeymap,
    .enter = keyboardEnter,
    .leave = keyboardLeave,
    .key = keyboardKey,
    .modifiers = keyboardModifiers,
    .repeat_info = keyboardRepeatInfo,
};
// -----------------------------------

} // namespace

LayerShellWindow::~LayerShellWindow() { disconnect(); }

bool LayerShellWindow::connect() {
  display_ = wl_display_connect(nullptr);
  if (display_ != nullptr) {
    registry_ = wl_display_get_registry(display_);
    wl_registry_add_listener(registry_, &kRegistryListener, this);

    wl_display_roundtrip(display_);
    if (xdgOutputManager_ != nullptr) {
      for (auto &info : outputs_) {
        if (info.output != nullptr && info.xdgOutput == nullptr) {
          info.xdgOutput = zxdg_output_manager_v1_get_xdg_output(
              xdgOutputManager_, info.output);
          if (info.xdgOutput) {
            zxdg_output_v1_add_listener(info.xdgOutput, &kXdgOutputListener,
                                        this);
          }
        }
      }
    }
    // Second roundtrip to ensure we receive the bound output geometry events
    wl_display_roundtrip(display_);
    std::sort(outputs_.begin(), outputs_.end(),
              [](const OutputInfo &a, const OutputInfo &b) {
                if (a.x != b.x) return a.x < b.x;
                return a.y < b.y;
              });
  }

  // If the compositor supports wlr-layer-shell (e.g. wlroots, KDE, or GNOME
  // with a Mutter Layer-Shell patch), use native Wayland layer-shell.
  if (compositor_ != nullptr && layerShell_ != nullptr) {
    useX11_ = false;
    return true;
  }

  // Otherwise (e.g. standard GNOME Mutter without wlr-layer-shell), prefer the
  // X11/XWayland fallback unless RAINMETER_WAYLAND_XDG=1 is explicitly set.
  const char *forceWaylandXdg = std::getenv("RAINMETER_WAYLAND_XDG");
  if (!forceWaylandXdg || std::strcmp(forceWaylandXdg, "1") != 0) {
    static std::once_flag xInitFlag;
    std::call_once(xInitFlag, []() { XInitThreads(); });

    xDisplay_ = XOpenDisplay(nullptr);
    if (xDisplay_ != nullptr) {
      useX11_ = true;
      int screen = DefaultScreen(xDisplay_);
      Window root = RootWindow(xDisplay_, screen);
      int nmon = 0;
      XRRMonitorInfo *mons = XRRGetMonitors(xDisplay_, root, True, &nmon);
      if (mons && nmon > 0) {
        for (auto &oldInfo : outputs_) {
          if (oldInfo.xdgOutput != nullptr) {
            zxdg_output_v1_destroy(oldInfo.xdgOutput);
            oldInfo.xdgOutput = nullptr;
          }
        }
        outputs_.clear();
        for (int i = 0; i < nmon; ++i) {
          OutputInfo info;
          info.x = mons[i].x;
          info.y = mons[i].y;
          info.width = mons[i].width;
          info.height = mons[i].height;
          info.logicalWidth = mons[i].width;
          info.logicalHeight = mons[i].height;
          info.scale = 1;
          info.fractionalScale = 1.0;
          outputs_.push_back(info);
        }
        XRRFreeMonitors(mons);
        std::sort(outputs_.begin(), outputs_.end(),
                  [](const OutputInfo &a, const OutputInfo &b) {
                    if (a.x != b.x) return a.x < b.x;
                    return a.y < b.y;
                  });
      } else if (outputs_.empty()) {
        OutputInfo info;
        info.output = nullptr;
        info.width = DisplayWidth(xDisplay_, screen);
        info.height = DisplayHeight(xDisplay_, screen);
        info.logicalWidth = info.width;
        info.logicalHeight = info.height;
        outputs_.push_back(info);
      }
      return true;
    }
  }

  if (compositor_ == nullptr) {
    std::cerr << "LayerShellWindow: wl_compositor global not found\n";
    return false;
  }
  if (layerShell_ == nullptr && xdgWmBase_ == nullptr) {
    std::cerr << "LayerShellWindow: compositor supports neither wlr-layer-shell nor xdg-shell\n";
    return false;
  }
  return true;
}

void LayerShellWindow::handleGlobal(wl_registry *registry, uint32_t name,
                                    const char *interface, uint32_t version) {
  if (std::strcmp(interface, wl_compositor_interface.name) == 0) {
    compositor_ = static_cast<wl_compositor *>(wl_registry_bind(
        registry, name, &wl_compositor_interface, version < 4 ? version : 4));
  } else if (std::strcmp(interface, zwlr_layer_shell_v1_interface.name) == 0) {
    layerShell_ = static_cast<zwlr_layer_shell_v1 *>(
        wl_registry_bind(registry, name, &zwlr_layer_shell_v1_interface,
                         version < 4 ? version : 4));
  } else if (std::strcmp(interface, xdg_wm_base_interface.name) == 0) {
    xdgWmBase_ = static_cast<xdg_wm_base *>(
        wl_registry_bind(registry, name, &xdg_wm_base_interface, 1));
    xdg_wm_base_add_listener(xdgWmBase_, &kXdgWmBaseListener, this);
  } else if (std::strcmp(interface, zxdg_decoration_manager_v1_interface.name) == 0) {
    xdgDecorationManager_ = static_cast<zxdg_decoration_manager_v1 *>(
        wl_registry_bind(registry, name, &zxdg_decoration_manager_v1_interface, 1));
  } else if (std::strcmp(interface, wp_fractional_scale_manager_v1_interface.name) == 0) {
    fractionalScaleManager_ = static_cast<wp_fractional_scale_manager_v1 *>(
        wl_registry_bind(registry, name, &wp_fractional_scale_manager_v1_interface, 1));
  } else if (std::strcmp(interface, wp_viewporter_interface.name) == 0) {
    viewporter_ = static_cast<wp_viewporter *>(
        wl_registry_bind(registry, name, &wp_viewporter_interface, 1));
  } else if (std::strcmp(interface, zxdg_output_manager_v1_interface.name) == 0) {
    xdgOutputManager_ = static_cast<zxdg_output_manager_v1 *>(
        wl_registry_bind(registry, name, &zxdg_output_manager_v1_interface,
                         version < 3 ? version : 3));
  } else if (std::strcmp(interface, wl_seat_interface.name) == 0) {
    seat_ = static_cast<wl_seat *>(
        wl_registry_bind(registry, name, &wl_seat_interface, version < 5 ? version : 5));
    wl_seat_add_listener(seat_, &kSeatListener, this);
  } else if (std::strcmp(interface, wl_output_interface.name) == 0) {
    wl_output *output = static_cast<wl_output *>(
        wl_registry_bind(registry, name, &wl_output_interface, version < 3 ? version : 3));
    OutputInfo info;
    info.output = output;
    outputs_.push_back(info);
    wl_output_add_listener(output, &kOutputListener, this);
  }
}

int LayerShellWindow::getScreenX(int monitorIndex) const noexcept {
    if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
        return outputs_[monitorIndex].x;
    }
    return 0;
}

int LayerShellWindow::getScreenY(int monitorIndex) const noexcept {
    if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
        return outputs_[monitorIndex].y;
    }
    return 0;
}

int LayerShellWindow::getScreenWidth(int monitorIndex) const noexcept {
    if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
        if (outputs_[monitorIndex].logicalWidth > 0) {
            return outputs_[monitorIndex].logicalWidth;
        }
        return outputs_[monitorIndex].width;
    }
    return 1920; // fallback
}

int LayerShellWindow::getScreenHeight(int monitorIndex) const noexcept {
    if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
        if (outputs_[monitorIndex].logicalHeight > 0) {
            return outputs_[monitorIndex].logicalHeight;
        }
        return outputs_[monitorIndex].height;
    }
    return 1080; // fallback
}

double LayerShellWindow::getScreenScale(int monitorIndex) const noexcept {
    if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
        if (outputs_[monitorIndex].fractionalScale > 0.0) {
            return outputs_[monitorIndex].fractionalScale;
        }
        return static_cast<double>(outputs_[monitorIndex].scale);
    }
    return 1.0;
}

bool LayerShellWindow::initLayerSurface(int width, int height, int windowX, int windowY, int monitorIndex, uint32_t anchor, const std::string &scope) {
  if (useX11_) {
    return initX11Surface(width, height, windowX, windowY, scope);
  }
  if (compositor_ == nullptr || (layerShell_ == nullptr && xdgWmBase_ == nullptr)) {
    return false;
  }
  width_ = width;
  height_ = height;

  surface_ = wl_compositor_create_surface(compositor_);

  if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
    surfaceScale_ = getScreenScale(monitorIndex);
  }
  if (viewporter_) {
    viewport_ = wp_viewporter_get_viewport(viewporter_, surface_);
  }
  if (fractionalScaleManager_) {
    fractionalScale_ = wp_fractional_scale_manager_v1_get_fractional_scale(
        fractionalScaleManager_, surface_);
    if (fractionalScale_) {
      wp_fractional_scale_v1_add_listener(fractionalScale_,
                                          &kFractionalScaleListener, this);
    }
  }

  if (layerShell_) {
    wl_output *targetOutput = nullptr;
    if (monitorIndex >= 0 && monitorIndex < static_cast<int>(outputs_.size())) {
      targetOutput = outputs_[monitorIndex].output;
    }

    layerSurface_ = zwlr_layer_shell_v1_get_layer_surface(
        layerShell_, surface_, targetOutput, ZWLR_LAYER_SHELL_V1_LAYER_BOTTOM,
        scope.c_str());
    if (layerSurface_ == nullptr) {
      std::cerr << "LayerShellWindow: failed to create layer surface\n";
      return false;
    }

    zwlr_layer_surface_v1_add_listener(layerSurface_, &kLayerSurfaceListener,
                                       this);
    zwlr_layer_surface_v1_set_size(layerSurface_, static_cast<uint32_t>(width),
                                   static_cast<uint32_t>(height));

    // Anchor to top-left and apply X/Y as margins for global screen positioning
    zwlr_layer_surface_v1_set_anchor(layerSurface_, ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT);
    zwlr_layer_surface_v1_set_margin(layerSurface_, windowY, 0, 0, windowX);

    g_RequestKeyboardFocus = [this]() {
        if (layerSurface_ && surface_) {
            // Force Wayland to elevate the widget and grant keyboard focus!
            zwlr_layer_surface_v1_set_keyboard_interactivity(layerSurface_, 1);
            // Stay on bottom layer
            wl_surface_commit(surface_);
        }
    };
    g_ReleaseKeyboardFocus = [this]() {
        if (layerSurface_ && surface_) {
            // Drop the widget back to the background layer safely
            zwlr_layer_surface_v1_set_keyboard_interactivity(layerSurface_, 0);
            // Stay on bottom layer
            wl_surface_commit(surface_);
        }
    };

    // Always anchor to top-left so that WindowX and WindowY absolute coordinates work as margins
    zwlr_layer_surface_v1_set_anchor(layerSurface_, ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT);
    zwlr_layer_surface_v1_set_margin(layerSurface_, windowY, 0, 0, windowX);
    zwlr_layer_surface_v1_set_keyboard_interactivity(layerSurface_, 0);
  } else if (xdgWmBase_) {
    // GNOME Mutter Fallback
    xdgSurface_ = xdg_wm_base_get_xdg_surface(xdgWmBase_, surface_);
    if (xdgSurface_ == nullptr) {
      std::cerr << "LayerShellWindow: failed to create xdg_surface\n";
      return false;
    }
    xdgToplevel_ = xdg_surface_get_toplevel(xdgSurface_);
    if (xdgToplevel_ == nullptr) {
      std::cerr << "LayerShellWindow: failed to create xdg_toplevel\n";
      return false;
    }

    // This tag allows our future GNOME extension to intercept the widget
    xdg_toplevel_set_app_id(xdgToplevel_, "rainmeter-native-widget");
    if (!scope.empty()) {
      xdg_toplevel_set_title(xdgToplevel_, scope.c_str());
    }

    // Negotiate Client-Side Decorations (CSD) so the compositor does not draw
    // server-side borders around the widget.
    if (xdgDecorationManager_) {
      xdgToplevelDecoration_ =
          zxdg_decoration_manager_v1_get_toplevel_decoration(
              xdgDecorationManager_, xdgToplevel_);
      if (xdgToplevelDecoration_) {
        zxdg_toplevel_decoration_v1_add_listener(
            xdgToplevelDecoration_, &kXdgToplevelDecorationListener, this);
        zxdg_toplevel_decoration_v1_set_mode(
            xdgToplevelDecoration_,
            ZXDG_TOPLEVEL_DECORATION_V1_MODE_CLIENT_SIDE);
      }
    }

    xdg_surface_add_listener(xdgSurface_, &kXdgSurfaceListener, this);
    xdg_toplevel_add_listener(xdgToplevel_, &kXdgToplevelListener, this);
  } else {
    std::cerr << "Fatal: Compositor supports neither wlr-layer-shell nor xdg-shell\n";
    return false;
  }

  // Initialize EGL and create wl_egl_window before first commit
  if (!initEGL()) {
    std::cerr << "LayerShellWindow: failed to initialize EGL\n";
    return false;
  }

  wl_surface_commit(surface_);
  wl_display_roundtrip(display_);

  return configured_;
}

bool LayerShellWindow::initX11Surface(int width, int height, int windowX,
                                      int windowY, const std::string &scope) {
  if (xDisplay_ == nullptr) {
    return false;
  }
  width_ = width;
  height_ = height;
  xWindowX_ = windowX;
  xWindowY_ = windowY;

  int screen = DefaultScreen(xDisplay_);
  Window root = RootWindow(xDisplay_, screen);

#ifdef EGL_PLATFORM_X11_EXT
  if (epoxy_has_egl_extension(EGL_NO_DISPLAY, "EGL_EXT_platform_base")) {
    eglDisplay_ =
        eglGetPlatformDisplayEXT(EGL_PLATFORM_X11_EXT, xDisplay_, nullptr);
  }
#endif
  if (eglDisplay_ == EGL_NO_DISPLAY) {
    eglDisplay_ = eglGetDisplay(reinterpret_cast<EGLNativeDisplayType>(xDisplay_));
  }
  if (eglDisplay_ == EGL_NO_DISPLAY) {
    std::cerr << "LayerShellWindow: failed to get X11 EGL display\n";
    return false;
  }

  EGLint major = 0, minor = 0;
  if (!eglInitialize(eglDisplay_, &major, &minor)) {
    std::cerr << "LayerShellWindow: failed to initialize X11 EGL\n";
    return false;
  }
  if (!eglBindAPI(EGL_OPENGL_API)) {
    return false;
  }

  XVisualInfo vinfo{};
  bool hasArgbVisual =
      XMatchVisualInfo(xDisplay_, screen, 32, TrueColor, &vinfo) != 0;

  EGLint configAttribs[] = {
      EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
      EGL_RED_SIZE, 8,
      EGL_GREEN_SIZE, 8,
      EGL_BLUE_SIZE, 8,
      EGL_ALPHA_SIZE, 8,
      EGL_STENCIL_SIZE, 8,
      EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT,
      EGL_NONE
  };

  EGLConfig configs[64];
  EGLint numConfigs = 0;
  if (!eglChooseConfig(eglDisplay_, configAttribs, configs, 64, &numConfigs) ||
      numConfigs == 0) {
    std::cerr << "LayerShellWindow: no matching X11 EGLConfig found\n";
    return false;
  }

  EGLConfig chosenConfig = configs[0];
  if (hasArgbVisual) {
    for (EGLint i = 0; i < numConfigs; ++i) {
      EGLint visualId = 0;
      if (eglGetConfigAttrib(eglDisplay_, configs[i], EGL_NATIVE_VISUAL_ID,
                             &visualId) &&
          static_cast<VisualID>(visualId) == vinfo.visualid) {
        chosenConfig = configs[i];
        break;
      }
    }
  } else {
    EGLint visualId = 0;
    eglGetConfigAttrib(eglDisplay_, chosenConfig, EGL_NATIVE_VISUAL_ID,
                       &visualId);
    XVisualInfo tmpl{};
    tmpl.visualid = static_cast<VisualID>(visualId);
    int n = 0;
    XVisualInfo *vi = XGetVisualInfo(xDisplay_, VisualIDMask, &tmpl, &n);
    if (vi && n > 0) {
      vinfo = vi[0];
      XFree(vi);
    } else {
      return false;
    }
  }

  xColormap_ = XCreateColormap(xDisplay_, root, vinfo.visual, AllocNone);

  // IMPORTANT: On GNOME Mutter, override_redirect = True puts windows into
  // META_LAYER_OVERRIDE_REDIRECT (top_window_group, above all normal windows).
  // Keeping override_redirect = False allows Mutter to honor
  // _NET_WM_WINDOW_TYPE_DESKTOP and _NET_WM_STATE_BELOW so the widget stays
  // in META_LAYER_DESKTOP beneath all normal windows.
  const char *orEnv = std::getenv("RAINMETER_X11_OVERRIDE_REDIRECT");
  Bool useOverrideRedirect =
      (orEnv && std::strcmp(orEnv, "1") == 0) ? True : False;

  XSetWindowAttributes swa{};
  swa.colormap = xColormap_;
  swa.background_pixel = 0;
  swa.border_pixel = 0;
  swa.override_redirect = useOverrideRedirect;
  swa.event_mask = ExposureMask | ButtonPressMask | ButtonReleaseMask |
                   PointerMotionMask | EnterWindowMask | KeyPressMask |
                   KeyReleaseMask | StructureNotifyMask;

  xWindow_ = XCreateWindow(
      xDisplay_, root, windowX, windowY, static_cast<unsigned int>(width),
      static_cast<unsigned int>(height), 0, vinfo.depth, InputOutput,
      vinfo.visual,
      CWColormap | CWBackPixel | CWBorderPixel | CWOverrideRedirect |
          CWEventMask,
      &swa);
  if (!xWindow_) {
    std::cerr << "LayerShellWindow: XCreateWindow failed\n";
    return false;
  }

  // Borderless Motif hint
  struct MotifWmHints {
    unsigned long flags;
    unsigned long functions;
    unsigned long decorations;
    long input_mode;
    unsigned long status;
  } motifHints = {2UL, 0UL, 0UL, 0L, 0UL};
  Atom motifAtom = XInternAtom(xDisplay_, "_MOTIF_WM_HINTS", False);
  XChangeProperty(xDisplay_, xWindow_, motifAtom, motifAtom, 32,
                  PropModeReplace,
                  reinterpret_cast<unsigned char *>(&motifHints), 5);

  // Set EWMH desktop window type so XWayland / Mutter places it in
  // META_LAYER_DESKTOP (beneath all normal windows, on the desktop background).
  Atom wmWindowType = XInternAtom(xDisplay_, "_NET_WM_WINDOW_TYPE", False);
  Atom wmWindowTypeDesktop =
      XInternAtom(xDisplay_, "_NET_WM_WINDOW_TYPE_DESKTOP", False);
  XChangeProperty(xDisplay_, xWindow_, wmWindowType, XA_ATOM, 32,
                  PropModeReplace,
                  reinterpret_cast<unsigned char *>(&wmWindowTypeDesktop), 1);

  // Set EWMH states (below, sticky across workspaces, skip taskbar & pager)
  Atom wmState = XInternAtom(xDisplay_, "_NET_WM_STATE", False);
  Atom wmStateBelow = XInternAtom(xDisplay_, "_NET_WM_STATE_BELOW", False);
  Atom wmStateSticky = XInternAtom(xDisplay_, "_NET_WM_STATE_STICKY", False);
  Atom wmStateSkipTaskbar =
      XInternAtom(xDisplay_, "_NET_WM_STATE_SKIP_TASKBAR", False);
  Atom wmStateSkipPager =
      XInternAtom(xDisplay_, "_NET_WM_STATE_SKIP_PAGER", False);
  Atom states[4] = {wmStateBelow, wmStateSticky, wmStateSkipTaskbar,
                    wmStateSkipPager};
  XChangeProperty(xDisplay_, xWindow_, wmState, XA_ATOM, 32, PropModeReplace,
                  reinterpret_cast<unsigned char *>(states), 4);

  // Pin to all workspaces (0xFFFFFFFF)
  unsigned long allDesktops = 0xFFFFFFFFUL;
  Atom wmDesktop = XInternAtom(xDisplay_, "_NET_WM_DESKTOP", False);
  XChangeProperty(xDisplay_, xWindow_, wmDesktop, XA_CARDINAL, 32,
                  PropModeReplace,
                  reinterpret_cast<unsigned char *>(&allDesktops), 1);

  // Prevent window from stealing focus or raising when clicked
  XWMHints wmHints{};
  wmHints.flags = InputHint;
  wmHints.input = False;
  XSetWMHints(xDisplay_, xWindow_, &wmHints);

  XSizeHints sizeHints{};
  sizeHints.flags = USPosition | PPosition | USSize | PSize;
  sizeHints.x = windowX;
  sizeHints.y = windowY;
  sizeHints.width = width;
  sizeHints.height = height;
  XSetWMNormalHints(xDisplay_, xWindow_, &sizeHints);

  if (!scope.empty()) {
    XStoreName(xDisplay_, xWindow_, scope.c_str());
  }
  XClassHint *classHint = XAllocClassHint();
  if (classHint) {
    char resName[] = "rainmeter-native-widget";
    char resClass[] = "rainmeter-native-widget";
    classHint->res_name = resName;
    classHint->res_class = resClass;
    XSetClassHint(xDisplay_, xWindow_, classHint);
    XFree(classHint);
  }

  wmDeleteMessage_ = XInternAtom(xDisplay_, "WM_DELETE_WINDOW", False);
  XSetWMProtocols(xDisplay_, xWindow_, &wmDeleteMessage_, 1);

  XMapWindow(xDisplay_, xWindow_);
  XMoveWindow(xDisplay_, xWindow_, windowX, windowY);

  // Send EWMH ClientMessages after mapping so Mutter enforces BELOW + STICKY
  // and SKIP_TASKBAR + SKIP_PAGER on the mapped window.
  auto sendWmState = [&](Atom prop1, Atom prop2) {
    XEvent xev{};
    xev.xclient.type = ClientMessage;
    xev.xclient.serial = 0;
    xev.xclient.send_event = True;
    xev.xclient.display = xDisplay_;
    xev.xclient.window = xWindow_;
    xev.xclient.message_type = wmState;
    xev.xclient.format = 32;
    xev.xclient.data.l[0] = 1; // _NET_WM_STATE_ADD
    xev.xclient.data.l[1] = static_cast<long>(prop1);
    xev.xclient.data.l[2] = static_cast<long>(prop2);
    xev.xclient.data.l[3] = 1;
    XSendEvent(xDisplay_, root, False,
               SubstructureRedirectMask | SubstructureNotifyMask, &xev);
  };
  sendWmState(wmStateBelow, wmStateSticky);
  sendWmState(wmStateSkipTaskbar, wmStateSkipPager);

  XLowerWindow(xDisplay_, xWindow_);
  XFlush(xDisplay_);

  g_RequestKeyboardFocus = [this]() {
    if (xDisplay_ && xWindow_) {
      XSetInputFocus(xDisplay_, xWindow_, RevertToParent, CurrentTime);
      XFlush(xDisplay_);
    }
  };
  g_ReleaseKeyboardFocus = [this]() {
    if (xDisplay_ && xWindow_) {
      XLowerWindow(xDisplay_, xWindow_);
      XFlush(xDisplay_);
    }
  };

  EGLint contextAttribs[] = {
      EGL_CONTEXT_MAJOR_VERSION, 3,
      EGL_CONTEXT_MINOR_VERSION, 2,
      EGL_CONTEXT_OPENGL_PROFILE_MASK, EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,
      EGL_NONE
  };
  eglContext_ = eglCreateContext(eglDisplay_, chosenConfig, EGL_NO_CONTEXT,
                                 contextAttribs);
  if (eglContext_ == EGL_NO_CONTEXT) {
    std::cerr << "LayerShellWindow: failed to create X11 EGL context\n";
    return false;
  }

  eglSurface_ = eglCreateWindowSurface(
      eglDisplay_, chosenConfig,
      reinterpret_cast<EGLNativeWindowType>(xWindow_), nullptr);
  if (eglSurface_ == EGL_NO_SURFACE) {
    std::cerr << "LayerShellWindow: failed to create X11 EGL surface\n";
    return false;
  }

  // Bind context once to set non-blocking swap interval (0) so eglSwapBuffers
  // never stalls the engine loop when an app/window is open on another monitor
  // or when two monitors have different refresh timings under Mutter/XWayland.
  if (eglMakeCurrent(eglDisplay_, eglSurface_, eglSurface_, eglContext_) == EGL_TRUE) {
    eglSwapInterval(eglDisplay_, 0);
  }

  configured_ = true;
  return true;
}

bool LayerShellWindow::initEGL() {
  eglDisplay_ = eglGetDisplay((EGLNativeDisplayType)display_);
  if (eglDisplay_ == EGL_NO_DISPLAY) return false;

  EGLint major, minor;
  if (!eglInitialize(eglDisplay_, &major, &minor)) return false;

  if (!eglBindAPI(EGL_OPENGL_API)) return false;

  EGLint configAttribs[] = {
      EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
      EGL_RED_SIZE, 8,
      EGL_GREEN_SIZE, 8,
      EGL_BLUE_SIZE, 8,
      EGL_ALPHA_SIZE, 8,
      EGL_STENCIL_SIZE, 8,
      EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT,
      EGL_NONE
  };

  EGLConfig config;
  EGLint numConfigs;
  if (!eglChooseConfig(eglDisplay_, configAttribs, &config, 1, &numConfigs) || numConfigs == 0) {
      return false;
  }

  EGLint contextAttribs[] = {
      EGL_CONTEXT_MAJOR_VERSION, 3,
      EGL_CONTEXT_MINOR_VERSION, 2,
      EGL_CONTEXT_OPENGL_PROFILE_MASK, EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,
      EGL_NONE
  };

  eglContext_ = eglCreateContext(eglDisplay_, config, EGL_NO_CONTEXT, contextAttribs);
  if (eglContext_ == EGL_NO_CONTEXT) return false;

  eglWindow_ = wl_egl_window_create(surface_, width_, height_);
  if (!eglWindow_) return false;

  eglSurface_ = eglCreateWindowSurface(eglDisplay_, config, (EGLNativeWindowType)eglWindow_, nullptr);
  if (eglSurface_ == EGL_NO_SURFACE) return false;

  if (eglMakeCurrent(eglDisplay_, eglSurface_, eglSurface_, eglContext_) == EGL_TRUE) {
    eglSwapInterval(eglDisplay_, 0);
  }

  return true;
}

void LayerShellWindow::updateBufferScaleAndViewport() {
  if (!surface_ || width_ <= 0 || height_ <= 0) return;
  int fbW = std::max(1, static_cast<int>(std::lround(width_ * surfaceScale_)));
  int fbH = std::max(1, static_cast<int>(std::lround(height_ * surfaceScale_)));
  if (eglWindow_) {
    wl_egl_window_resize(eglWindow_, fbW, fbH, 0, 0);
  }
  if (viewport_) {
    wl_surface_set_buffer_scale(surface_, 1);
    wp_viewport_set_destination(viewport_, width_, height_);
  } else {
    int intScale = std::max(1, static_cast<int>(std::lround(surfaceScale_)));
    wl_surface_set_buffer_scale(surface_, intScale);
  }
}

void LayerShellWindow::resize(int width, int height) {
    if (width == width_ && height == height_) return;
    moveAndResize(xWindowX_, xWindowY_, width, height);
}

void LayerShellWindow::moveAndResize(int x, int y, int width, int height) {
    bool sizeChanged = (width != width_ || height != height_);
    bool posChanged = (x != xWindowX_ || y != xWindowY_);
    if (!sizeChanged && !posChanged) return;

    width_ = width;
    height_ = height;
    xWindowX_ = x;
    xWindowY_ = y;

    if (useX11_ && xDisplay_ && xWindow_) {
        XSizeHints sizeHints{};
        sizeHints.flags = USPosition | PPosition | USSize | PSize;
        sizeHints.x = xWindowX_;
        sizeHints.y = xWindowY_;
        sizeHints.width = width;
        sizeHints.height = height;
        XSetWMNormalHints(xDisplay_, xWindow_, &sizeHints);
        XMoveResizeWindow(xDisplay_, xWindow_, xWindowX_, xWindowY_,
                          static_cast<unsigned int>(width),
                          static_cast<unsigned int>(height));
        XLowerWindow(xDisplay_, xWindow_);
        XFlush(xDisplay_);
    } else if (layerSurface_) {
        zwlr_layer_surface_v1_set_size(layerSurface_, width, height);
        zwlr_layer_surface_v1_set_margin(layerSurface_, xWindowY_, 0, 0, xWindowX_);
        updateBufferScaleAndViewport();
        wl_surface_commit(surface_);
    } else if (xdgToplevel_) {
        updateBufferScaleAndViewport();
        if (xdgSurface_) {
            xdg_surface_set_window_geometry(xdgSurface_, 0, 0, width_, height_);
        }
        wl_surface_commit(surface_);
    }
}

bool LayerShellWindow::makeCurrent() {
    if (eglDisplay_ == EGL_NO_DISPLAY || eglSurface_ == EGL_NO_SURFACE || eglContext_ == EGL_NO_CONTEXT) {
        return false;
    }
    return eglMakeCurrent(eglDisplay_, eglSurface_, eglSurface_, eglContext_) == EGL_TRUE;
}

void LayerShellWindow::swapBuffers() {
    if (eglDisplay_ != EGL_NO_DISPLAY && eglSurface_ != EGL_NO_SURFACE) {
        eglSwapInterval(eglDisplay_, 0);
        eglSwapBuffers(eglDisplay_, eglSurface_);
    }
}

void LayerShellWindow::handleLayerConfigure(zwlr_layer_surface_v1 *surface,
                                            uint32_t serial, uint32_t width,
                                            uint32_t height) {
  if (width > 0) width_ = static_cast<int>(width);
  if (height > 0) height_ = static_cast<int>(height);
  
  updateBufferScaleAndViewport();

  zwlr_layer_surface_v1_ack_configure(surface, serial);
  configured_ = true;
}

void LayerShellWindow::handleLayerClosed() { closed_ = true; }

void LayerShellWindow::handleXdgSurfaceConfigure(xdg_surface *surface,
                                                 uint32_t serial) {
  if (pendingXdgWidth_ > 0) width_ = pendingXdgWidth_;
  if (pendingXdgHeight_ > 0) height_ = pendingXdgHeight_;
  pendingXdgWidth_ = 0;
  pendingXdgHeight_ = 0;

  updateBufferScaleAndViewport();
  if (width_ > 0 && height_ > 0) {
    xdg_surface_set_window_geometry(surface, 0, 0, width_, height_);
  }

  xdg_surface_ack_configure(surface, serial);
  configured_ = true;
}

void LayerShellWindow::handleXdgToplevelConfigure(int32_t width,
                                                  int32_t height) {
  pendingXdgWidth_ = width;
  pendingXdgHeight_ = height;
}

void LayerShellWindow::handleXdgToplevelClose() { closed_ = true; }

void LayerShellWindow::handleSeatCapabilities(wl_seat *seat, uint32_t caps) {
  if ((caps & WL_SEAT_CAPABILITY_POINTER) && pointer_ == nullptr) {
    pointer_ = wl_seat_get_pointer(seat);
    wl_pointer_add_listener(pointer_, &kPointerListener, this);
  } else if (!(caps & WL_SEAT_CAPABILITY_POINTER) && pointer_ != nullptr) {
    wl_pointer_release(pointer_);
    pointer_ = nullptr;
  }

  static wl_keyboard *local_keyboard_ = nullptr;
  if ((caps & WL_SEAT_CAPABILITY_KEYBOARD) && local_keyboard_ == nullptr) {
    local_keyboard_ = wl_seat_get_keyboard(seat);
    wl_keyboard_add_listener(local_keyboard_, &kKeyboardListener, this);
  } else if (!(caps & WL_SEAT_CAPABILITY_KEYBOARD) && local_keyboard_ != nullptr) {
    wl_keyboard_release(local_keyboard_);
    local_keyboard_ = nullptr;
  }
}

void LayerShellWindow::handlePointerEnter(double x, double y) {
  pointerX_ = x;
  pointerY_ = y;
}

void LayerShellWindow::handlePointerMotion(double x, double y) {
  pointerX_ = x;
  pointerY_ = y;
}

void LayerShellWindow::handlePointerButton(uint32_t button, uint32_t state) {
  if (state == 0) {
    std::cout << "[WAYLAND] Mouse click detected at X: " << pointerX_ << ", Y: " << pointerY_ << std::endl;
    if (mouseCb_) {
      mouseCb_(pointerX_, pointerY_, button);
    }
  }
}

void LayerShellWindow::handleOutputGeometry(wl_output *output, int x, int y) {
    for (auto &info : outputs_) {
        if (info.output == output) {
            if (info.x == 0 && info.y == 0) {
                info.x = x;
                info.y = y;
            }
            break;
        }
    }
}

void LayerShellWindow::handleOutputMode(wl_output *output, uint32_t flags, int width, int height) {
    if (flags & WL_OUTPUT_MODE_CURRENT) {
        for (auto &info : outputs_) {
            if (info.output == output) {
                info.width = width;
                info.height = height;
                if (info.logicalWidth > 0) {
                    info.fractionalScale = static_cast<double>(info.width) /
                                           static_cast<double>(info.logicalWidth);
                }
                break;
            }
        }
    }
}

void LayerShellWindow::handleOutputScale(wl_output *output, int32_t factor) {
    if (factor <= 0) return;
    for (auto &info : outputs_) {
        if (info.output == output) {
            info.scale = factor;
            if (info.logicalWidth <= 0) {
                info.fractionalScale = static_cast<double>(factor);
            }
            break;
        }
    }
}

void LayerShellWindow::handleXdgOutputLogicalPosition(
    struct zxdg_output_v1 *xdgOutput, int32_t x, int32_t y) {
    for (auto &info : outputs_) {
        if (info.xdgOutput == xdgOutput) {
            info.x = x;
            info.y = y;
            break;
        }
    }
}

void LayerShellWindow::handleXdgOutputLogicalSize(
    struct zxdg_output_v1 *xdgOutput, int32_t width, int32_t height) {
    for (auto &info : outputs_) {
        if (info.xdgOutput == xdgOutput) {
            info.logicalWidth = width;
            info.logicalHeight = height;
            if (info.width > 0 && width > 0) {
                info.fractionalScale =
                    static_cast<double>(info.width) / static_cast<double>(width);
            }
            break;
        }
    }
}

void LayerShellWindow::handlePreferredFractionalScale(uint32_t scale120) {
    if (scale120 == 0) return;
    surfaceScale_ = static_cast<double>(scale120) / 120.0;
    updateBufferScaleAndViewport();
}

void LayerShellWindow::run() {
  if (useX11_) {
    while (!closed_ && dispatchPending()) {}
    return;
  }
  while (!closed_ && wl_display_dispatch(display_) != -1) {}
}

bool LayerShellWindow::dispatchPending() {
  if (useX11_) {
    if (xDisplay_ == nullptr || closed_) return false;
    while (XPending(xDisplay_) > 0) {
      XEvent ev;
      XNextEvent(xDisplay_, &ev);
      switch (ev.type) {
      case EnterNotify:
        handlePointerEnter(ev.xcrossing.x, ev.xcrossing.y);
        break;
      case MotionNotify:
        while (XCheckTypedWindowEvent(xDisplay_, xWindow_, MotionNotify, &ev)) {}
        handlePointerMotion(ev.xmotion.x, ev.xmotion.y);
        break;
      case ButtonPress:
        handlePointerMotion(ev.xbutton.x, ev.xbutton.y);
        break;
      case ButtonRelease: {
        handlePointerMotion(ev.xbutton.x, ev.xbutton.y);
        uint32_t wlBtn = BTN_LEFT;
        if (ev.xbutton.button == Button2) wlBtn = BTN_MIDDLE;
        else if (ev.xbutton.button == Button3) wlBtn = BTN_RIGHT;
        else if (ev.xbutton.button != Button1) break;
        handlePointerButton(wlBtn, 0U);
        break;
      }
      case MapNotify:
        if (ev.xmap.window == xWindow_) {
          XMoveResizeWindow(xDisplay_, xWindow_, xWindowX_, xWindowY_,
                            static_cast<unsigned int>(width_),
                            static_cast<unsigned int>(height_));
          XLowerWindow(xDisplay_, xWindow_);
          XFlush(xDisplay_);
        }
        break;
      case ConfigureNotify:
        // Keep the widget strictly pinned to its configured desktop position & size
        if (ev.xconfigure.window == xWindow_ &&
            (ev.xconfigure.x != xWindowX_ || ev.xconfigure.y != xWindowY_ ||
             ev.xconfigure.width != width_ || ev.xconfigure.height != height_)) {
          XMoveResizeWindow(xDisplay_, xWindow_, xWindowX_, xWindowY_,
                            static_cast<unsigned int>(width_),
                            static_cast<unsigned int>(height_));
          XLowerWindow(xDisplay_, xWindow_);
          XFlush(xDisplay_);
        }
        break;
      case KeyPress:
      case KeyRelease: {
        if (ev.xkey.keycode >= 8) {
          uint32_t linuxKey = static_cast<uint32_t>(ev.xkey.keycode - 8);
          keyboardKey(this, nullptr, 0, static_cast<uint32_t>(ev.xkey.time),
                      linuxKey, ev.type == KeyPress ? 1U : 0U);
        }
        break;
      }
      case ClientMessage:
        if (static_cast<unsigned long>(ev.xclient.data.l[0]) ==
            wmDeleteMessage_) {
          closed_ = true;
        }
        break;
      default:
        break;
      }
    }
    return !closed_;
  }
  if (display_ == nullptr || closed_) return false;
  if (wl_display_dispatch_pending(display_) == -1) return false;
  wl_display_flush(display_);
  return !closed_;
}

void LayerShellWindow::disconnect() {
  if (eglDisplay_ != EGL_NO_DISPLAY) {
      eglMakeCurrent(eglDisplay_, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
      if (eglSurface_ != EGL_NO_SURFACE) eglDestroySurface(eglDisplay_, eglSurface_);
      if (eglContext_ != EGL_NO_CONTEXT) eglDestroyContext(eglDisplay_, eglContext_);
      eglTerminate(eglDisplay_);
      eglDisplay_ = EGL_NO_DISPLAY;
      eglSurface_ = EGL_NO_SURFACE;
      eglContext_ = EGL_NO_CONTEXT;
  }
  if (eglWindow_ != nullptr) {
      wl_egl_window_destroy(eglWindow_);
      eglWindow_ = nullptr;
  }
  if (xDisplay_ != nullptr) {
    if (xWindow_ != 0) {
      XDestroyWindow(xDisplay_, xWindow_);
      xWindow_ = 0;
    }
    if (xColormap_ != 0) {
      XFreeColormap(xDisplay_, xColormap_);
      xColormap_ = 0;
    }
    XCloseDisplay(xDisplay_);
    xDisplay_ = nullptr;
  }
  if (fractionalScale_ != nullptr) {
    wp_fractional_scale_v1_destroy(fractionalScale_);
    fractionalScale_ = nullptr;
  }
  if (viewport_ != nullptr) {
    wp_viewport_destroy(viewport_);
    viewport_ = nullptr;
  }
  if (xdgToplevelDecoration_ != nullptr) {
    zxdg_toplevel_decoration_v1_destroy(xdgToplevelDecoration_);
    xdgToplevelDecoration_ = nullptr;
  }
  if (xdgToplevel_ != nullptr) {
    xdg_toplevel_destroy(xdgToplevel_);
    xdgToplevel_ = nullptr;
  }
  if (xdgSurface_ != nullptr) {
    xdg_surface_destroy(xdgSurface_);
    xdgSurface_ = nullptr;
  }
  if (layerSurface_ != nullptr) {
    zwlr_layer_surface_v1_destroy(layerSurface_);
    layerSurface_ = nullptr;
  }
  if (surface_ != nullptr) {
    wl_surface_destroy(surface_);
    surface_ = nullptr;
  }
  for (auto &info : outputs_) {
    if (info.xdgOutput != nullptr) {
      zxdg_output_v1_destroy(info.xdgOutput);
      info.xdgOutput = nullptr;
    }
  }
  if (pointer_ != nullptr) {
    wl_pointer_release(pointer_);
    pointer_ = nullptr;
  }
  if (seat_ != nullptr) {
    wl_seat_release(seat_);
    seat_ = nullptr;
  }
  if (xdgOutputManager_ != nullptr) {
    zxdg_output_manager_v1_destroy(xdgOutputManager_);
    xdgOutputManager_ = nullptr;
  }
  if (viewporter_ != nullptr) {
    wp_viewporter_destroy(viewporter_);
    viewporter_ = nullptr;
  }
  if (fractionalScaleManager_ != nullptr) {
    wp_fractional_scale_manager_v1_destroy(fractionalScaleManager_);
    fractionalScaleManager_ = nullptr;
  }
  if (xdgDecorationManager_ != nullptr) {
    zxdg_decoration_manager_v1_destroy(xdgDecorationManager_);
    xdgDecorationManager_ = nullptr;
  }
  if (xdgWmBase_ != nullptr) {
    xdg_wm_base_destroy(xdgWmBase_);
    xdgWmBase_ = nullptr;
  }
  if (layerShell_ != nullptr) {
    zwlr_layer_shell_v1_destroy(layerShell_);
    layerShell_ = nullptr;
  }
  if (compositor_ != nullptr) {
    wl_compositor_destroy(compositor_);
    compositor_ = nullptr;
  }
  if (registry_ != nullptr) {
    wl_registry_destroy(registry_);
    registry_ = nullptr;
  }
  if (display_ != nullptr) {
    wl_display_disconnect(display_);
    display_ = nullptr;
  }
}
