# rainmeter-native

A native Linux rendering engine for Rainmeter skins. Built from the ground up with C++20, this project allows Linux users to parse, render, and interact with complex Rainmeter suites natively on their desktops without relying on WINE or Windows virtual machines.

## Features

* **Native Windowing:** Utilizes Wayland and LayerShell to draw true desktop widgets that sit underneath your active windows.
* **High-Fidelity Rendering:** Powered by Cairo for vector/raster graphics and Pango for advanced text formatting and layout.
* **Custom Lexer & Parser:** Reads standard Windows Rainmeter `.ini` and `.thm` files and dynamically translates Windows-style configurations to Linux equivalents.
* **Smart Path Resolution:** Features a case-insensitive virtual filesystem resolver to handle poorly-cased DevinatArt skins perfectly on literal Linux filesystems.
* **Mock Plugin Manager:** Intercepts calls to Windows-specific plugins (like `AudioLevel` or `WebParser`) to prevent crashes, allowing heavy suites like ScreenStyler to render successfully even if the underlying data isn't available.

## Prerequisites

To build and run `rainmeter-native`, you will need a C++20 compatible compiler, CMake, and a few core development libraries. 

For Debian/Ubuntu-based distributions (like Pop!_OS), you can install the required dependencies using `apt`:

```bash
sudo apt update
sudo apt install build-essential cmake pkg-config \
    libwayland-dev wayland-protocols \
    libcairo2-dev libpango1.0-dev libfontconfig1-dev
