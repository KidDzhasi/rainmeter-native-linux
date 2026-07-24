#include "LayerShell.hpp"

#include <cstring>
#include <ctime>
#include <iostream>

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#include "graphics/CairoRenderer.hpp"

namespace {

// Creates an anonymous, unlinked file suitable for wl_shm, sized to `size`.
// Returns a file descriptor, or -1 on failure.
int createAnonymousFile(std::size_t size) {
  int fd = memfd_create("rainmeter-native-shm", MFD_CLOEXEC | MFD_ALLOW_SEALING);
  if (fd < 0) {
    std::cerr << "LayerShellWindow: memfd_create failed\n";
    return -1;
  }

  if (ftruncate(fd, static_cast<off_t>(size)) < 0) {
    std::cerr << "LayerShellWindow: ftruncate failed\n";
    close(fd);
    return -1;
  }
  return fd;
}

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
    std::cerr << "LayerShellWindow: failed to connect to a Wayland display "
                 "(is WAYLAND_DISPLAY set?)\n";
    return false;
  }

  registry_ = wl_display_get_registry(display_);
  wl_registry_add_listener(registry_, &kRegistryListener, this);

  // Roundtrip so the registry reports its globals and we bind them.
  wl_display_roundtrip(display_);

  if (compositor_ == nullptr) {
    std::cerr << "LayerShellWindow: wl_compositor global not found\n";
    return false;
  }
  if (shm_ == nullptr) {
    std::cerr << "LayerShellWindow: wl_shm global not found\n";
    return false;
  }
  if (layerShell_ == nullptr) {
    std::cerr << "LayerShellWindow: compositor does not support "
                 "wlr-layer-shell\n";
    return false;
  }
  return true;
}

void LayerShellWindow::handleGlobal(wl_registry *registry, uint32_t name,
                                    const char *interface, uint32_t version) {
  if (std::strcmp(interface, wl_compositor_interface.name) == 0) {
    compositor_ = static_cast<wl_compositor *>(wl_registry_bind(
        registry, name, &wl_compositor_interface, version < 4 ? version : 4));
  } else if (std::strcmp(interface, wl_shm_interface.name) == 0) {
    shm_ = static_cast<wl_shm *>(
        wl_registry_bind(registry, name, &wl_shm_interface, 1));
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

bool LayerShellWindow::initLayerSurface(int width, int height,
                                        const std::string &scope) {
  if (compositor_ == nullptr || layerShell_ == nullptr) {
    return false;
  }
  width_ = width;
  height_ = height;

  surface_ = wl_compositor_create_surface(compositor_);

  // BOTTOM layer: sits above the desktop wallpaper but below normal windows.
  // Anchored to the top-right corner with a 50px margin so it doesn't
  // overlap desktop icons (which are typically on the left).
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
                                       ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
  // 50px top, 50px right, 0 bottom, 0 left.
  zwlr_layer_surface_v1_set_margin(layerSurface_, 50, 50, 0, 0);

  // Initial commit without a buffer; compositor replies with configure.
  wl_surface_commit(surface_);
  wl_display_roundtrip(display_);

  return configured_;
}

void LayerShellWindow::handleLayerConfigure(zwlr_layer_surface_v1 *surface,
                                            uint32_t serial, uint32_t width,
                                            uint32_t height) {
  if (width > 0) {
    width_ = static_cast<int>(width);
  }
  if (height > 0) {
    height_ = static_cast<int>(height);
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
  // state 1 = pressed, 0 = released
  if (state == 0 && mouseCb_) {
    mouseCb_(pointerX_, pointerY_, button);
  }
}

void LayerShellWindow::render(const CairoRenderer &renderer) {
  if (!configured_ || surface_ == nullptr || shm_ == nullptr) {
    return;
  }

  const unsigned char *src = renderer.pixels();
  if (src == nullptr) {
    std::cerr << "LayerShellWindow: renderer has no pixel data\n";
    return;
  }
  
  if (width_ <= 0 || height_ <= 0) {
    return;
  }
  const int srcStride = renderer.stride();
  const int dstStride = width_ * 4;
  const std::size_t size = static_cast<std::size_t>(dstStride) * height_;

  // Allocate a shared-memory buffer for this frame.
  int fd = createAnonymousFile(size);
  if (fd < 0) {
    std::cerr << "LayerShellWindow: failed to create shm file\n";
    return;
  }

  void *dst = mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (dst == MAP_FAILED) {
    std::cerr << "LayerShellWindow: mmap failed\n";
    close(fd);
    return;
  }

  // Copy the Cairo image data into the shm buffer, row by row (the source
  // and destination strides may differ).
  auto *dstBytes = static_cast<unsigned char *>(dst);
  const int copyBytes = (srcStride < dstStride) ? srcStride : dstStride;
  for (int y = 0; y < height_; ++y) {
    std::memcpy(dstBytes + static_cast<std::size_t>(y) * dstStride,
                src + static_cast<std::size_t>(y) * srcStride, copyBytes);
  }

  wl_shm_pool *pool = wl_shm_create_pool(shm_, fd, static_cast<int32_t>(size));

  // Replace any previous frame buffer with the new one. For a static
  // desktop background we keep a single persistent buffer alive rather than
  // recycling it via the release event.
  if (buffer_ != nullptr) {
    wl_buffer_destroy(buffer_);
  }
  buffer_ = wl_shm_pool_create_buffer(pool, 0, width_, height_, dstStride,
                                      WL_SHM_FORMAT_ARGB8888);
  wl_shm_pool_destroy(pool);

  // The buffer keeps the mapping alive on the compositor side; we can
  // unmap and close our fd now that the pool holds a reference.
  munmap(dst, size);
  close(fd);

  wl_surface_attach(surface_, buffer_, 0, 0);
  wl_surface_damage_buffer(surface_, 0, 0, width_, height_);
  wl_surface_commit(surface_);
  wl_display_flush(display_);
}

void LayerShellWindow::run() {
  while (!closed_ && wl_display_dispatch(display_) != -1) {
    // Event loop; the compositor drives redraws and input via events.
  }
}

bool LayerShellWindow::dispatchPending() {
  if (display_ == nullptr || closed_) {
    return false;
  }
  // Drain queued events without blocking, then flush our outgoing requests.
  if (wl_display_dispatch_pending(display_) == -1) {
    return false;
  }
  wl_display_flush(display_);
  return !closed_;
}

void LayerShellWindow::disconnect() {
  if (buffer_ != nullptr) {
    wl_buffer_destroy(buffer_);
    buffer_ = nullptr;
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
  if (shm_ != nullptr) {
    wl_shm_destroy(shm_);
    shm_ = nullptr;
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
