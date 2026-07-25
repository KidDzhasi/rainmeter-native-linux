#pragma once

#include <string>
#include <string_view>

namespace Utils {

struct Color {
    double r = 0.0;
    double g = 0.0;
    double b = 0.0;
    double a = 255.0;
};

// Parses a Rainmeter color string (HEX or R,G,B,A) into a raw (0 - 255) RGBA Color object.
Color ParseColor(std::string_view spec);

} // namespace Utils
