#include "LayerShell.hpp"

#include <cstring>
#include <ctime>
#include <iostream>

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
void pointerEnter(void *data, wl_pointer * /*pointer*/, uint32_t /*serial*/,
                  wl_surface * /*surface*/, wl_fixed_t surface_x,
                  wl_fixed_t surface_y) {
  static_cast<LayerShellWindow *>(data)->handlePointerEnter(
      wl_fixed_to_double(surface_x), wl_fixed_to_double(surface_y));
}
void pointerLeave(void * /*data*/, wl_pointer * /*pointer*/,
                  uint32_t /*serial*/, wl_surface * /*surface*/) {}
void pointerMotion(void *data, wl_pointer * /*pointer*/, uint32_t /*time*/,
                   wl_fixed_t surface_x, wl_fixed_t surface_y) {
  static_cast<LayerShellWindow *>(data)->handlePointerMotion(
      wl_fixed_to_double(surface_x), wl_fixed_to_double(surface_y));
}
void pointerButton(void *data, wl_pointer * /*pointer*/, uint32_t /*serial*/,
                   uint32_t /*time*/, uint32_t button, uint32_t state) {
  static_cast<LayerShellWindow *>(data)->handlePointerButton(button, state);
}
void pointerAxis(void * /*data*/, wl_pointer * /*pointer*/, uint32_t /*time*/,
                 uint32_t /*axis*/, wl_fixed_t /*value*/) {}
// These are available in newer protocol versions, but we define nullops if we bind a higher version.
void pointerFrame(void * /*data*/, wl_pointer * /*pointer*/) {}
void pointerAxisSource(void * /*data*/, wl_pointer * /*pointer*/, uint32_t /*axis_source*/) {}
void pointerAxisStop(void * /*data*/, wl_pointer * /*pointer*/, uint32_t /*time*/, uint32_t /*axis*/) {}
void pointerAxisDiscrete(void * /*data*/, wl_pointer * /*pointer*/, uint32_t /*axis*/, int32_t /*discrete*/) {}

const wl_pointer_listener kPointerListener = {
    .enter = pointerEnter,
    .leave = pointerLeave,
    .motion = pointerMotion,
    .button = pointerButton,
    .axis = pointerAxis,
    .frame = pointerFrame,
    .axis_source = pointerAxisSource,
    .axis_stop = pointerAxisStop,
    .axis_discrete = pointerAxisDiscrete,
};

} // namespace

LayerShellWindow::~LayerShellWindow() { disconnect(); }

bool LayerShellWindow::connect() {
  display_ = wl_display_connect(nullptr);
  if (display_ == nullptr) {
    std::cerr << "LayerShellWindow: failed to connect to a Wayland display\n";
    return false;
  }

  registry_ = wl_display_get_registry(display_);
  wl_registry_add_listener(registry_, &kRegistryListener, this);

  wl_display_roundtrip(display_);

  if (compositor_ == nullptr) {
    std::cerr << "LayerShellWindow: wl_compositor global not found\n";
    return false;
  }
  if (layerShell_ == nullptr) {
    std::cerr << "LayerShellWindow: compositor does not support wlr-layer-shell\n";
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
  } else if (std::strcmp(interface, wl_seat_interface.name) == 0) {
    seat_ = static_cast<wl_seat *>(
        wl_registry_bind(registry, name, &wl_seat_interface, version < 5 ? version : 5));
    wl_seat_add_listener(seat_, &kSeatListener, this);
  }
}

bool LayerShellWindow::initLayerSurface(int width, int height, int windowX, int windowY, const std::string &scope) {
  if (compositor_ == nullptr || layerShell_ == nullptr) {
    return false;
  }
  width_ = width;
  height_ = height;

  surface_ = wl_compositor_create_surface(compositor_);

  layerSurface_ = zwlr_layer_shell_v1_get_layer_surface(
      layerShell_, surface_, nullptr, ZWLR_LAYER_SHELL_V1_LAYER_BOTTOM,
      scope.c_str());
  if (layerSurface_ == nullptr) {
    std::cerr << "LayerShellWindow: failed to create layer surface\n";
    return false;
  }

  zwlr_layer_surface_v1_add_listener(layerSurface_, &kLayerSurfaceListener,
                                     this);
  zwlr_layer_surface_v1_set_size(layerSurface_, static_cast<uint32_t>(width),
                                 static_cast<uint32_t>(height));
  zwlr_layer_surface_v1_set_anchor(layerSurface_,
                                   ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP |
                                       ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT);
  zwlr_layer_surface_v1_set_margin(layerSurface_, windowY, 0, 0, windowX);
  zwlr_layer_surface_v1_set_keyboard_interactivity(layerSurface_, 0);

  // Initialize EGL and create wl_egl_window before first commit
  if (!initEGL()) {
    std::cerr << "LayerShellWindow: failed to initialize EGL\n";
    return false;
  }

  wl_surface_commit(surface_);
  wl_display_roundtrip(display_);

  return configured_;
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

  return true;
}

void LayerShellWindow::resize(int width, int height) {
    if (width == width_ && height == height_) return;
    
    if (layerSurface_) {
        zwlr_layer_surface_v1_set_size(layerSurface_, width, height);
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
        eglSwapBuffers(eglDisplay_, eglSurface_);
    }
}

void LayerShellWindow::handleLayerConfigure(zwlr_layer_surface_v1 *surface,
                                            uint32_t serial, uint32_t width,
                                            uint32_t height) {
  if (width > 0) width_ = static_cast<int>(width);
  if (height > 0) height_ = static_cast<int>(height);
  
  if (eglWindow_) {
      wl_egl_window_resize(eglWindow_, width_, height_, 0, 0);
  }

  zwlr_layer_surface_v1_ack_configure(surface, serial);
  configured_ = true;
}

void LayerShellWindow::handleLayerClosed() { closed_ = true; }

void LayerShellWindow::handleSeatCapabilities(wl_seat *seat, uint32_t caps) {
  if ((caps & WL_SEAT_CAPABILITY_POINTER) && pointer_ == nullptr) {
    pointer_ = wl_seat_get_pointer(seat);
    wl_pointer_add_listener(pointer_, &kPointerListener, this);
  } else if (!(caps & WL_SEAT_CAPABILITY_POINTER) && pointer_ != nullptr) {
    wl_pointer_release(pointer_);
    pointer_ = nullptr;
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

void LayerShellWindow::run() {
  while (!closed_ && wl_display_dispatch(display_) != -1) {}
}

bool LayerShellWindow::dispatchPending() {
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
  }
  if (eglWindow_ != nullptr) {
      wl_egl_window_destroy(eglWindow_);
      eglWindow_ = nullptr;
  }
  if (layerSurface_ != nullptr) {
    zwlr_layer_surface_v1_destroy(layerSurface_);
    layerSurface_ = nullptr;
  }
  if (surface_ != nullptr) {
    wl_surface_destroy(surface_);
    surface_ = nullptr;
  }
  if (pointer_ != nullptr) {
    wl_pointer_release(pointer_);
    pointer_ = nullptr;
  }
  if (seat_ != nullptr) {
    wl_seat_release(seat_);
    seat_ = nullptr;
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
