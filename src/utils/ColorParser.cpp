#include "ColorParser.hpp"

#include <charconv>
#include <vector>
#include <cstdint>

namespace Utils {

Color ParseColor(std::string_view spec) {
    while (!spec.empty() && (spec.front() == ' ' || spec.front() == '\t')) spec.remove_prefix(1);
    while (!spec.empty() && (spec.back() == ' ' || spec.back() == '\t')) spec.remove_suffix(1);
    if (spec.empty()) return Color{};

    std::vector<std::string_view> tokens;
    std::size_t start = 0;
    while (start <= spec.size() && tokens.size() < 4) {
        std::size_t comma = spec.find(',', start);
        std::string_view token = (comma == std::string_view::npos) ? spec.substr(start) : spec.substr(start, comma - start);
        while (!token.empty() && (token.front() == ' ' || token.front() == '\t')) token.remove_prefix(1);
        while (!token.empty() && (token.back() == ' ' || token.back() == '\t')) token.remove_suffix(1);
        tokens.push_back(token);
        if (comma == std::string_view::npos) break;
        start = comma + 1;
    }

    if (tokens.empty()) return Color{};

    auto parseHex = [](std::string_view hexStr, Color& c) -> bool {
        if (!hexStr.empty() && hexStr.front() == '#') hexStr.remove_prefix(1);
        if (hexStr.size() == 6 || hexStr.size() == 8) {
            uint32_t val = 0;
            auto [ptr, ec] = std::from_chars(hexStr.data(), hexStr.data() + hexStr.size(), val, 16);
            if (ec == std::errc()) {
                if (hexStr.size() == 6) {
                    c.r = (val >> 16) & 0xFF;
                    c.g = (val >> 8) & 0xFF;
                    c.b = val & 0xFF;
                    c.a = 255.0;
                } else {
                    c.a = val & 0xFF;
                    c.r = (val >> 24) & 0xFF;
                    c.g = (val >> 16) & 0xFF;
                    c.b = (val >> 8) & 0xFF;
                }
                return true;
            }
        }
        return false;
    };

    Color c;
    if (parseHex(tokens[0], c)) {
        if (tokens.size() > 1) {
            int overrideAlpha = 255;
            auto [ptr, ec] = std::from_chars(tokens[1].data(), tokens[1].data() + tokens[1].size(), overrideAlpha);
            if (ec == std::errc()) {
                c.a = overrideAlpha;
            }
        }
        return c;
    }

    std::vector<int> components;
    for (auto token : tokens) {
        int value = 0;
        if (!token.empty()) std::from_chars(token.data(), token.data() + token.size(), value);
        components.push_back(value);
    }

    if (components.size() >= 3) {
        c.a = (components.size() >= 4) ? components[3] : 255.0;
        c.r = components[0];
        c.g = components[1];
        c.b = components[2];
    }
    return c;
}

} // namespace Utils
