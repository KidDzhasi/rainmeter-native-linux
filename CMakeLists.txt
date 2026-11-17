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
pkg_check_modules(X11 REQUIRED x11)
pkg_check_modules(XRANDR REQUIRED xrandr)
pkg_check_modules(EGL REQUIRED egl)
pkg_check_modules(EPOXY REQUIRED epoxy)
pkg_check_modules(FONTCONFIG REQUIRED fontconfig)
pkg_check_modules(LIBZIP REQUIRED libzip)
pkg_check_modules(LIBCURL REQUIRED libcurl)
pkg_check_modules(GIO REQUIRED gio-2.0)
pkg_search_module(LUA REQUIRED lua lua5.3 lua5.4)
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

# --- Wayland protocol code generation (xdg-shell) ---
pkg_check_modules(WAYLAND_PROTOCOLS QUIET wayland-protocols)
if(WAYLAND_PROTOCOLS_FOUND)
    pkg_get_variable(WAYLAND_PROTOCOLS_DIR wayland-protocols pkgdatadir)
else()
    set(WAYLAND_PROTOCOLS_DIR "/usr/share/wayland-protocols")
endif()

set(XDG_SHELL_XML
    "${WAYLAND_PROTOCOLS_DIR}/stable/xdg-shell/xdg-shell.xml")
set(XDG_SHELL_HEADER
    "${PROTO_DIR}/xdg-shell-client-protocol.h")
set(XDG_SHELL_SOURCE
    "${PROTO_DIR}/xdg-shell-protocol.c")

add_custom_command(
    OUTPUT "${XDG_SHELL_HEADER}"
    COMMAND ${WAYLAND_SCANNER} client-header "${XDG_SHELL_XML}"
            "${XDG_SHELL_HEADER}"
    DEPENDS "${XDG_SHELL_XML}"
    VERBATIM)

add_custom_command(
    OUTPUT "${XDG_SHELL_SOURCE}"
    COMMAND ${WAYLAND_SCANNER} private-code "${XDG_SHELL_XML}"
            "${XDG_SHELL_SOURCE}"
    DEPENDS "${XDG_SHELL_XML}"
    VERBATIM)

# --- Wayland protocol code generation (xdg-decoration) ---
set(XDG_DECORATION_XML
    "${WAYLAND_PROTOCOLS_DIR}/unstable/xdg-decoration/xdg-decoration-unstable-v1.xml")
set(XDG_DECORATION_HEADER
    "${PROTO_DIR}/xdg-decoration-unstable-v1-client-protocol.h")
set(XDG_DECORATION_SOURCE
    "${PROTO_DIR}/xdg-decoration-unstable-v1-protocol.c")

add_custom_command(
    OUTPUT "${XDG_DECORATION_HEADER}"
    COMMAND ${WAYLAND_SCANNER} client-header "${XDG_DECORATION_XML}"
            "${XDG_DECORATION_HEADER}"
    DEPENDS "${XDG_DECORATION_XML}"
    VERBATIM)

add_custom_command(
    OUTPUT "${XDG_DECORATION_SOURCE}"
    COMMAND ${WAYLAND_SCANNER} private-code "${XDG_DECORATION_XML}"
            "${XDG_DECORATION_SOURCE}"
    DEPENDS "${XDG_DECORATION_XML}"
    VERBATIM)

# --- Wayland protocol code generation (fractional-scale, viewporter, xdg-output) ---
set(FRACTIONAL_SCALE_XML
    "${WAYLAND_PROTOCOLS_DIR}/staging/fractional-scale/fractional-scale-v1.xml")
set(FRACTIONAL_SCALE_HEADER
    "${PROTO_DIR}/fractional-scale-v1-client-protocol.h")
set(FRACTIONAL_SCALE_SOURCE
    "${PROTO_DIR}/fractional-scale-v1-protocol.c")

add_custom_command(
    OUTPUT "${FRACTIONAL_SCALE_HEADER}"
    COMMAND ${WAYLAND_SCANNER} client-header "${FRACTIONAL_SCALE_XML}"
            "${FRACTIONAL_SCALE_HEADER}"
    DEPENDS "${FRACTIONAL_SCALE_XML}"
    VERBATIM)

add_custom_command(
    OUTPUT "${FRACTIONAL_SCALE_SOURCE}"
    COMMAND ${WAYLAND_SCANNER} private-code "${FRACTIONAL_SCALE_XML}"
            "${FRACTIONAL_SCALE_SOURCE}"
    DEPENDS "${FRACTIONAL_SCALE_XML}"
    VERBATIM)

set(VIEWPORTER_XML
    "${WAYLAND_PROTOCOLS_DIR}/stable/viewporter/viewporter.xml")
set(VIEWPORTER_HEADER
    "${PROTO_DIR}/viewporter-client-protocol.h")
set(VIEWPORTER_SOURCE
    "${PROTO_DIR}/viewporter-protocol.c")

add_custom_command(
    OUTPUT "${VIEWPORTER_HEADER}"
    COMMAND ${WAYLAND_SCANNER} client-header "${VIEWPORTER_XML}"
            "${VIEWPORTER_HEADER}"
    DEPENDS "${VIEWPORTER_XML}"
    VERBATIM)

add_custom_command(
    OUTPUT "${VIEWPORTER_SOURCE}"
    COMMAND ${WAYLAND_SCANNER} private-code "${VIEWPORTER_XML}"
            "${VIEWPORTER_SOURCE}"
    DEPENDS "${VIEWPORTER_XML}"
    VERBATIM)

set(XDG_OUTPUT_XML
    "${WAYLAND_PROTOCOLS_DIR}/unstable/xdg-output/xdg-output-unstable-v1.xml")
set(XDG_OUTPUT_HEADER
    "${PROTO_DIR}/xdg-output-unstable-v1-client-protocol.h")
set(XDG_OUTPUT_SOURCE
    "${PROTO_DIR}/xdg-output-unstable-v1-protocol.c")

add_custom_command(
    OUTPUT "${XDG_OUTPUT_HEADER}"
    COMMAND ${WAYLAND_SCANNER} client-header "${XDG_OUTPUT_XML}"
            "${XDG_OUTPUT_HEADER}"
    DEPENDS "${XDG_OUTPUT_XML}"
    VERBATIM)

add_custom_command(
    OUTPUT "${XDG_OUTPUT_SOURCE}"
    COMMAND ${WAYLAND_SCANNER} private-code "${XDG_OUTPUT_XML}"
            "${XDG_OUTPUT_SOURCE}"
    DEPENDS "${XDG_OUTPUT_XML}"
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
list(REMOVE_ITEM RAINMETER_NATIVE_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/src/tools/rmskin_unpacker.cpp")

add_executable(rainmeter-native
    ${RAINMETER_NATIVE_SOURCES}
    src/evaluator/ScriptEnvironment.cpp
    src/evaluator/SysfsParser.cpp
    src/wayland/LayerShell.cpp
    src/evaluator/LinuxPowerPlugin.cpp
    src/evaluator/LinuxAudioLevel.cpp
    ${nanovg_SOURCE_DIR}/src/nanovg.c
    ${LAYER_SHELL_SOURCE}
    ${LAYER_SHELL_HEADER}
    ${XDG_SHELL_SOURCE}
    ${XDG_SHELL_HEADER}
    ${XDG_DECORATION_SOURCE}
    ${XDG_DECORATION_HEADER}
    ${FRACTIONAL_SCALE_SOURCE}
    ${FRACTIONAL_SCALE_HEADER}
    ${VIEWPORTER_SOURCE}
    ${VIEWPORTER_HEADER}
    ${XDG_OUTPUT_SOURCE}
    ${XDG_OUTPUT_HEADER})

# Allow includes relative to the src tree and the generated protocol headers.
target_include_directories(rainmeter-native PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    "${PROTO_DIR}"
    "${nanovg_SOURCE_DIR}/src"
    "${glm_SOURCE_DIR}"
    ${WAYLAND_CLIENT_INCLUDE_DIRS}
    ${WAYLAND_EGL_INCLUDE_DIRS}
    ${X11_INCLUDE_DIRS}
    ${XRANDR_INCLUDE_DIRS}
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
    ${X11_CFLAGS_OTHER}
    ${XRANDR_CFLAGS_OTHER}
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
    ${X11_LIBRARIES}
    ${XRANDR_LIBRARIES}
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

# --- RMSKIN Unpacker Utility ---
add_executable(rmskin-unpacker 
    src/tools/rmskin_unpacker.cpp
    src/parser/IniLexer.cpp
    src/parser/EnvironmentManager.cpp)
target_compile_options(rmskin-unpacker PRIVATE -Wall -Wextra)
