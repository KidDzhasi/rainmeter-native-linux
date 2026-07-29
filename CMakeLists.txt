cmake_minimum_required(VERSION 3.16)

project(rainmeter-native
    VERSION 0.1.0
    DESCRIPTION "Native Linux Rainmeter rendering engine"
    LANGUAGES C CXX)

# --- C++20 configuration ---
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile commands for tooling (clangd, etc.)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --- Dependencies via pkg-config ---
find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

pkg_check_modules(WAYLAND_CLIENT REQUIRED wayland-client)
pkg_check_modules(WAYLAND_EGL REQUIRED wayland-egl)
pkg_check_modules(EGL REQUIRED egl)
pkg_check_modules(EPOXY REQUIRED epoxy)
pkg_check_modules(FONTCONFIG REQUIRED fontconfig)
pkg_check_modules(LIBZIP REQUIRED libzip)
pkg_check_modules(LIBCURL REQUIRED libcurl)
pkg_check_modules(GIO REQUIRED gio-2.0)
pkg_check_modules(LUA REQUIRED lua5.3)
pkg_check_modules(GLIB2 REQUIRED glib-2.0)
pkg_check_modules(DBUS1 REQUIRED dbus-1)
pkg_check_modules(PULSE REQUIRED libpulse-simple libpulse)


# --- Wayland protocol code generation (wlr-layer-shell) ---
# The wlr-layer-shell protocol is not shipped in wayland-protocols, so it is
# vendored in protocols/. Use wayland-scanner to generate the client glue.
find_program(WAYLAND_SCANNER wayland-scanner REQUIRED)

set(LAYER_SHELL_XML
    "${CMAKE_CURRENT_SOURCE_DIR}/protocols/wlr-layer-shell-unstable-v1.xml")
set(PROTO_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(LAYER_SHELL_HEADER
    "${PROTO_DIR}/wlr-layer-shell-unstable-v1-client-protocol.h")
set(LAYER_SHELL_SOURCE
    "${PROTO_DIR}/wlr-layer-shell-unstable-v1-protocol.c")

file(MAKE_DIRECTORY "${PROTO_DIR}")

add_custom_command(
    OUTPUT "${LAYER_SHELL_HEADER}"
    COMMAND ${WAYLAND_SCANNER} client-header "${LAYER_SHELL_XML}"
            "${LAYER_SHELL_HEADER}"
    DEPENDS "${LAYER_SHELL_XML}"
    VERBATIM)

add_custom_command(
    OUTPUT "${LAYER_SHELL_SOURCE}"
    COMMAND ${WAYLAND_SCANNER} private-code "${LAYER_SHELL_XML}"
            "${LAYER_SHELL_SOURCE}"
    DEPENDS "${LAYER_SHELL_XML}"
    VERBATIM)

# --- NanoVG ---
include(FetchContent)
FetchContent_Declare(
    nanovg
    GIT_REPOSITORY https://github.com/memononen/nanovg.git
    GIT_TAG        master
)
FetchContent_Populate(nanovg)

# --- GLM ---
FetchContent_Declare(
    glm
    GIT_REPOSITORY https://github.com/g-truc/glm.git
    GIT_TAG        master
)
FetchContent_Populate(glm)

# --- Collect all sources under src/ ---
file(GLOB_RECURSE RAINMETER_NATIVE_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

add_executable(rainmeter-native
    ${RAINMETER_NATIVE_SOURCES}
    src/evaluator/LinuxUsageMonitor.cpp
    src/evaluator/LinuxCoreTemp.cpp
    src/evaluator/LinuxPowerPlugin.cpp
    src/evaluator/LinuxAudioLevel.cpp
    ${nanovg_SOURCE_DIR}/src/nanovg.c
    ${LAYER_SHELL_SOURCE}
    ${LAYER_SHELL_HEADER})

# Allow includes relative to the src tree and the generated protocol headers.
target_include_directories(rainmeter-native PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    "${PROTO_DIR}"
    "${nanovg_SOURCE_DIR}/src"
    "${glm_SOURCE_DIR}"
    ${WAYLAND_CLIENT_INCLUDE_DIRS}
    ${WAYLAND_EGL_INCLUDE_DIRS}
    ${EGL_INCLUDE_DIRS}
    ${EPOXY_INCLUDE_DIRS}
    ${FONTCONFIG_INCLUDE_DIRS}
    ${LIBZIP_INCLUDE_DIRS}
    ${LIBCURL_INCLUDE_DIRS}
    ${GIO_INCLUDE_DIRS}
    ${LUA_INCLUDE_DIRS}
    ${GLIB2_INCLUDE_DIRS}
    ${DBUS1_INCLUDE_DIRS}
    ${PULSE_INCLUDE_DIRS})


target_compile_options(rainmeter-native PRIVATE
    ${WAYLAND_CLIENT_CFLAGS_OTHER}
    ${WAYLAND_EGL_CFLAGS_OTHER}
    ${EGL_CFLAGS_OTHER}
    ${EPOXY_CFLAGS_OTHER}
    ${FONTCONFIG_CFLAGS_OTHER}
    ${LIBZIP_CFLAGS_OTHER}
    ${LIBCURL_CFLAGS_OTHER}
    ${GIO_CFLAGS_OTHER}
    ${LUA_CFLAGS_OTHER}
    ${GLIB2_CFLAGS_OTHER}
    ${DBUS1_CFLAGS_OTHER}
    ${PULSE_CFLAGS_OTHER})


target_link_libraries(rainmeter-native PRIVATE
    ${WAYLAND_CLIENT_LIBRARIES}
    ${WAYLAND_EGL_LIBRARIES}
    ${EGL_LIBRARIES}
    ${EPOXY_LIBRARIES}
    ${FONTCONFIG_LIBRARIES}
    m
    ${LIBZIP_LIBRARIES}
    ${LIBCURL_LIBRARIES}
    ${GIO_LIBRARIES}
    ${LUA_LIBRARIES}
    ${GLIB2_LIBRARIES}
    ${DBUS1_LIBRARIES}
    ${PULSE_LIBRARIES}
    Threads::Threads
    rt)
