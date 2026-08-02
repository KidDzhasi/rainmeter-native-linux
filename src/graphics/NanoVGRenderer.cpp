#include "NanoVGRenderer.hpp"

#include <charconv>
#include <filesystem>
#include <unordered_map>
#include <algorithm>
#include "stb_image.h"

#include <iostream>
#include <cmath>

// NanoVG GL3 implementation
#define NANOVG_GL3_IMPLEMENTATION
#include <epoxy/gl.h>
#include "nanovg_gl.h"

static std::unordered_map<std::string, std::string> s_fontFamilyMap;

static std::string toLowerString(const std::string& str) {
  std::string out = str;
  for (char& c : out) c = std::tolower(static_cast<unsigned char>(c));
  return out;
}



NanoVGRenderer::~NanoVGRenderer() { reset(); }

void NanoVGRenderer::reset() {
    if (vg_) {
        nvgDeleteGL3(vg_);
        vg_ = nullptr;
    }
    imageCache_.clear();
    width_ = 0;
    height_ = 0;
}

NVGcolor NanoVGRenderer::toNVGColor(const Color& c) const {
    return nvgRGBA(
        static_cast<unsigned char>(c.r),
        static_cast<unsigned char>(c.g),
        static_cast<unsigned char>(c.b),
        static_cast<unsigned char>(c.a)
    );
}

bool NanoVGRenderer::beginEGL(int width, int height) {
    reset();
    
    vg_ = nvgCreateGL3(NVG_ANTIALIAS | NVG_STENCIL_STROKES);
    if (!vg_) {
        std::cerr << "Failed to create NVG context\n";
        return false;
    }

    int font = nvgCreateFont(vg_, "sans", "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf");
    if (font == -1) {
        font = nvgCreateFont(vg_, "sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf");
    }
    if (font != -1) {
        s_fontFamilyMap["sans"] = "sans";
    }

    width_ = width;
    height_ = height;
    return true;
}

void NanoVGRenderer::beginFrame(int width, int height, float pixelRatio) {
    if (vg_) {
        width_ = width;
        height_ = height;
        glViewport(0, 0, width, height);
        glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
        glEnable(GL_BLEND);
        glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
        nvgBeginFrame(vg_, width, height, pixelRatio);
    }
}

void NanoVGRenderer::endFrame() {
    if (vg_) {
        nvgEndFrame(vg_);
    }
}

void NanoVGRenderer::clear(const Color &color) {
    if (!valid()) return;
    float a = static_cast<float>(color.a) / 255.0f;
    glClearColor((static_cast<float>(color.r) / 255.0f) * a,
                 (static_cast<float>(color.g) / 255.0f) * a,
                 (static_cast<float>(color.b) / 255.0f) * a,
                 a);
    glClear(GL_COLOR_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
}

void NanoVGRenderer::clearRect(double x, double y, double w, double h) {
    if (!valid()) return;
    nvgSave(vg_);
    nvgGlobalCompositeOperation(vg_, NVG_COPY);
    nvgBeginPath(vg_);
    nvgRect(vg_, x, y, w, h);
    nvgFillColor(vg_, nvgRGBA(0, 0, 0, 0));
    nvgFill(vg_);
    nvgRestore(vg_);
}

void NanoVGRenderer::fillRect(double x, double y, double w, double h, const Color &color) {
    if (!valid()) return;
    nvgBeginPath(vg_);
    nvgRect(vg_, x, y, w, h);
    nvgFillColor(vg_, toNVGColor(color));
    nvgFill(vg_);
}

void NanoVGRenderer::strokeRect(double x, double y, double w, double h, double lineWidth, const Color &color) {
    if (!valid()) return;
    nvgBeginPath(vg_);
    nvgRect(vg_, x, y, w, h);
    nvgStrokeColor(vg_, toNVGColor(color));
    nvgStrokeWidth(vg_, lineWidth);
    nvgStroke(vg_);
}

void NanoVGRenderer::drawRectangle(double x, double y, double w, double h, double cornerRadius, const Color &fill, const Color &stroke, double lineWidth) {
    if (!valid() || w <= 0 || h <= 0) return;
    nvgBeginPath(vg_);
    if (cornerRadius > 0) {
        nvgRoundedRect(vg_, x, y, w, h, cornerRadius);
    } else {
        nvgRect(vg_, x, y, w, h);
    }
    
    if (fill.a > 0.0) {
        nvgFillColor(vg_, toNVGColor(fill));
        nvgFill(vg_);
    }
    if (stroke.a > 0.0 && lineWidth > 0) {
        nvgStrokeColor(vg_, toNVGColor(stroke));
        nvgStrokeWidth(vg_, lineWidth);
        nvgStroke(vg_);
    }
}

void NanoVGRenderer::drawEllipse(double x, double y, double w, double h, const Color &fill, const Color &stroke, double lineWidth) {
    if (!valid() || w <= 0 || h <= 0) return;
    double cx = x + w / 2.0;
    double cy = y + h / 2.0;
    double rx = w / 2.0;
    double ry = h / 2.0;

    nvgBeginPath(vg_);
    nvgEllipse(vg_, cx, cy, rx, ry);
    
    if (fill.a > 0.0) {
        nvgFillColor(vg_, toNVGColor(fill));
        nvgFill(vg_);
    }
    if (stroke.a > 0.0) {
        nvgStrokeColor(vg_, toNVGColor(stroke));
        nvgStrokeWidth(vg_, lineWidth);
        nvgStroke(vg_);
    }
}

void NanoVGRenderer::drawAdvancedMeter(double x, double y, double w, double h, double radius, double angle_deg, const Color &color) {
    if (!valid() || w <= 0 || h <= 0) return;
    
    nvgSave(vg_);

    if (angle_deg != 0.0) {
        double angle_rad = angle_deg * (M_PI / 180.0);
        nvgTranslate(vg_, x + w / 2.0, y + h / 2.0);
        nvgRotate(vg_, angle_rad);
        nvgTranslate(vg_, -(x + w / 2.0), -(y + h / 2.0));
    }

    nvgBeginPath(vg_);
    
    if (radius > 0) {
        double max_radius = std::min(w / 2.0, h / 2.0);
        if (radius > max_radius) radius = max_radius;
        nvgRoundedRect(vg_, x, y, w, h, radius);
    } else {
        nvgRect(vg_, x, y, w, h);
    }

    nvgFillColor(vg_, toNVGColor(color));
    nvgFill(vg_);

    nvgRestore(vg_);
}

void NanoVGRenderer::drawLine(double x1, double y1, double x2, double y2, double lineWidth, const Color &color) {
    if (!valid()) return;
    nvgBeginPath(vg_);
    nvgMoveTo(vg_, x1, y1);
    nvgLineTo(vg_, x2, y2);
    nvgStrokeColor(vg_, toNVGColor(color));
    nvgStrokeWidth(vg_, lineWidth);
    nvgStroke(vg_);
}

void NanoVGRenderer::drawRoundline(double x, double y, double w, double h, double startAngle, double rotationAngle, double lineLength, double lineStart, const Color &color, bool solid) {
    if (!valid()) return;

    double cx = w / 2.0;
    double cy = h / 2.0;
    double radius = lineLength != 0.0 ? lineLength : (std::min(w, h) / 2.0);

    nvgSave(vg_);
    nvgTranslate(vg_, x, y);

    nvgBeginPath(vg_);

    if (solid) {
        int dir = rotationAngle >= 0 ? NVG_CW : NVG_CCW;
        nvgArc(vg_, cx, cy, radius, startAngle, startAngle + rotationAngle, dir);
        
        if (lineStart > 0.0) {
            int oppDir = rotationAngle >= 0 ? NVG_CCW : NVG_CW;
            nvgLineTo(vg_, cx + std::cos(startAngle + rotationAngle) * lineStart, cy + std::sin(startAngle + rotationAngle) * lineStart);
            nvgArc(vg_, cx, cy, lineStart, startAngle + rotationAngle, startAngle, oppDir);
        } else {
            nvgLineTo(vg_, cx, cy);
        }
        
        nvgClosePath(vg_);
        nvgFillColor(vg_, toNVGColor(color));
        nvgFill(vg_);
    } else {
        double currentAngle = startAngle + rotationAngle;
        double x1 = cx + std::cos(currentAngle) * lineStart;
        double y1 = cy + std::sin(currentAngle) * lineStart;
        double x2 = cx + std::cos(currentAngle) * radius;
        double y2 = cy + std::sin(currentAngle) * radius;
        
        nvgMoveTo(vg_, x1, y1);
        nvgLineTo(vg_, x2, y2);
        
        nvgStrokeColor(vg_, toNVGColor(color));
        nvgStrokeWidth(vg_, 1.0f);
        nvgStroke(vg_);
    }

    nvgRestore(vg_);
}

NanoVGRenderer::ImageMetrics NanoVGRenderer::drawImage(const std::string &path, double x, double y, double w, double h, int preserveAspectRatio) {
    if (!valid()) return {};

    auto trimPath = [](const std::string& s) {
        size_t start = s.find_first_not_of(" \t\r\n\v\f");
        if (start == std::string::npos) return std::string();
        size_t end = s.find_last_not_of(" \t\r\n\v\f");
        return s.substr(start, end - start + 1);
    };
    std::string cleanPath = trimPath(path);

    std::error_code ec;
    auto current_mtime = std::filesystem::last_write_time(cleanPath, ec);
    if (ec) return {}; // file doesn't exist

    int img = 0;
    auto it = imageCache_.find(cleanPath);
    if (it != imageCache_.end()) {
        if (it->second.mtime != current_mtime) {
            std::cout << "[ImageMeter] Hot-reloading via stbi: [" << cleanPath << "]" << std::endl;
            if (it->second.img != 0) {
                nvgDeleteImage(vg_, it->second.img);
                it->second.img = 0;
            }
            it->second.hasFailed = false;
            
            int w, h, n;
            unsigned char *data = stbi_load(cleanPath.c_str(), &w, &h, &n, 4);
            if (!data) {
                std::cerr << "[ImageMeter] stbi_load failed for [" << cleanPath << "]: " << stbi_failure_reason() << std::endl;
                it->second.hasFailed = true;
                it->second.mtime = current_mtime;
                return {};
            }
            it->second.img = nvgCreateImageRGBA(vg_, w, h, 0, data);
            stbi_image_free(data);

            if (it->second.img == 0) {
                std::cerr << "[ImageMeter] Failed to push RGBA to NanoVG: [" << cleanPath << "]" << std::endl;
                it->second.hasFailed = true;
                it->second.mtime = current_mtime;
                return {};
            }
            it->second.mtime = current_mtime;
        } else if (it->second.hasFailed) {
            return {};
        }
        img = it->second.img;
    } else {
        std::cout << "[ImageMeter] Attempting stbi_load: [" << cleanPath << "]" << std::endl;
        
        int w, h, n;
        unsigned char *data = stbi_load(cleanPath.c_str(), &w, &h, &n, 4);
        if (!data) {
            std::cerr << "[ImageMeter] stbi_load failed for [" << cleanPath << "]: " << stbi_failure_reason() << std::endl;
            imageCache_[cleanPath] = {0, current_mtime, true};
            return {};
        }
        img = nvgCreateImageRGBA(vg_, w, h, 0, data);
        stbi_image_free(data);

        if (img == 0) {
            std::cerr << "[ImageMeter] Failed to push RGBA to NanoVG: [" << cleanPath << "]" << std::endl;
            imageCache_[cleanPath] = {0, current_mtime, true};
            return {};
        }
        imageCache_[cleanPath] = {img, current_mtime, false};
    }

    int iw = 0, ih = 0;
    nvgImageSize(vg_, img, &iw, &ih);

    double finalW = (w > 0) ? w : iw;
    double finalH = (h > 0) ? h : ih;

    // 1. Save the global state
    nvgSave(vg_);

    if (w > 0 && h > 0 && iw > 0 && ih > 0) {
        NVGpaint imgPaint;
        if (preserveAspectRatio == 0) {
            imgPaint = nvgImagePattern(vg_, x, y, w, h, 0.0f, img, 1.0f);
            nvgBeginPath(vg_);
            nvgRect(vg_, x, y, w, h);
            nvgFillPaint(vg_, imgPaint);
            nvgFill(vg_);
        } else {
            double scaleX = w / iw;
            double scaleY = h / ih;
            double scale = (preserveAspectRatio == 1) ? std::min(scaleX, scaleY) : std::max(scaleX, scaleY);
            
            double drawW = iw * scale;
            double drawH = ih * scale;
            double drawX = x + (w - drawW) / 2.0;
            double drawY = y + (h - drawH) / 2.0;

            if (preserveAspectRatio == 2) {
                // 2. Apply the bounding box mask based on the INI W and H variables
                nvgScissor(vg_, x, y, w, h);
            }
            imgPaint = nvgImagePattern(vg_, drawX, drawY, drawW, drawH, 0.0f, img, 1.0f);
            nvgBeginPath(vg_);
            nvgRect(vg_, drawX, drawY, drawW, drawH);
            nvgFillPaint(vg_, imgPaint);
            // 3. Draw the meter (nvgText or nvgImagePattern/nvgFill)
            nvgFill(vg_);
        }
    } else if (w > 0 && iw > 0 && h <= 0) {
        double scale = w / iw;
        finalH = ih * scale;
        NVGpaint imgPaint = nvgImagePattern(vg_, x, y, w, finalH, 0.0f, img, 1.0f);
        nvgBeginPath(vg_);
        nvgRect(vg_, x, y, w, finalH);
        nvgFillPaint(vg_, imgPaint);
        nvgFill(vg_);
    } else if (h > 0 && ih > 0 && w <= 0) {
        double scale = h / ih;
        finalW = iw * scale;
        NVGpaint imgPaint = nvgImagePattern(vg_, x, y, finalW, h, 0.0f, img, 1.0f);
        nvgBeginPath(vg_);
        nvgRect(vg_, x, y, finalW, h);
        nvgFillPaint(vg_, imgPaint);
        nvgFill(vg_);
    } else {
        NVGpaint imgPaint = nvgImagePattern(vg_, x, y, iw, ih, 0.0f, img, 1.0f);
        nvgBeginPath(vg_);
        nvgRect(vg_, x, y, iw, ih);
        nvgFillPaint(vg_, imgPaint);
        nvgFill(vg_);
    }

    // 4. Immediately restore the state
    nvgRestore(vg_);
    
    return {true, finalW, finalH};
}

void NanoVGRenderer::drawBar(double x, double y, double w, double h, double percent, const Color &barColor, const Color &bgColor, bool horizontal) {
    if (!valid() || w <= 0 || h <= 0) return;
    double frac = std::clamp(percent, 0.0, 1.0);
    if (bgColor.a > 0.0) fillRect(x, y, w, h, bgColor);
    if (frac > 0.0) {
        if (horizontal) {
            fillRect(x, y, w * frac, h, barColor);
        } else {
            double barH = h * frac;
            fillRect(x, y + h - barH, w, barH, barColor);
        }
    }
}

NanoVGRenderer::TextMetrics NanoVGRenderer::drawText(const std::string &text, double x, double y, const std::string &fontFace, double fontSize, const Color &color, TextAlign align, double angle, const TextEffect* effect, double maxWidth, double maxHeight, int clipString) {
    TextMetrics metrics;
    if (!valid()) return metrics;

    // ---------------------------------------------------------------
    // STEP 1: Font Setup — must happen before any measurement.
    // ---------------------------------------------------------------
    std::string searchFace = toLowerString(fontFace);
    std::string resolvedFace = "sans";
    auto it = s_fontFamilyMap.find(searchFace);
    if (it != s_fontFamilyMap.end()) {
        resolvedFace = it->second;
    }

    // Rainmeter specifies FontSize in typographic points; NanoVG expects
    // pixels.  Convert using the standard 96-DPI factor (pt * 96/72).
    float pixelSize = static_cast<float>(fontSize) * (96.0f / 72.0f);
    if (pixelSize < 1.0f) pixelSize = 1.0f;

    nvgFontFace(vg_, resolvedFace.c_str());
    nvgFontSize(vg_, pixelSize);

    int nvgAlign = NVG_ALIGN_TOP;
    if (align == TextAlign::Left) nvgAlign |= NVG_ALIGN_LEFT;
    else if (align == TextAlign::Center) nvgAlign |= NVG_ALIGN_CENTER;
    else if (align == TextAlign::Right) nvgAlign |= NVG_ALIGN_RIGHT;
    else if (align == TextAlign::CenterCenter) nvgAlign = NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE;

    nvgTextAlign(vg_, nvgAlign);

    // ---------------------------------------------------------------
    // STEP 2: Sanitise the display string.
    // ---------------------------------------------------------------
    std::string textToDraw = text;
    auto replaceAll = [](std::string& str, const std::string& from, const std::string& to) {
        size_t start_pos = 0;
        while((start_pos = str.find(from, start_pos)) != std::string::npos) {
            str.replace(start_pos, from.length(), to);
            start_pos += to.length();
        }
    };
    replaceAll(textToDraw, "⏮", "<<");
    replaceAll(textToDraw, "⏭", ">>");
    replaceAll(textToDraw, "♥", "+");
    replaceAll(textToDraw, "♡", "+");
    replaceAll(textToDraw, "⏸", "||");
    replaceAll(textToDraw, "▶", ">");
    replaceAll(textToDraw, "⏵", ">");
    replaceAll(textToDraw, "■", "[]");

    // ---------------------------------------------------------------
    // STEP 3: Truncate if ClipString=1
    // ---------------------------------------------------------------
    if (clipString == 1 && maxWidth > 0) {
        float bounds[4] = {0};
        nvgTextBounds(vg_, 0.0f, 0.0f, textToDraw.c_str(), nullptr, bounds);
        if (bounds[2] - bounds[0] > maxWidth) {
            std::string ellipsis = "...";
            while (!textToDraw.empty()) {
                // Pop one UTF-8 character
                while (!textToDraw.empty()) {
                    unsigned char c = textToDraw.back();
                    textToDraw.pop_back();
                    if ((c & 0xC0) != 0x80) break;
                }
                std::string tryText = textToDraw + ellipsis;
                nvgTextBounds(vg_, 0.0f, 0.0f, tryText.c_str(), nullptr, bounds);
                if (bounds[2] - bounds[0] <= maxWidth) {
                    textToDraw = tryText;
                    break;
                }
            }
            if (textToDraw.empty()) textToDraw = ellipsis;
        }
    }

    // ---------------------------------------------------------------
    // STEP 4: Measure the string locally at (0, 0).
    // ---------------------------------------------------------------
    float bounds[4] = {0, 0, 0, 0};
    nvgSave(vg_);
        if (clipString == 2 && maxWidth > 0) {
        nvgTextBoxBounds(vg_, 0.0f, 0.0f, maxWidth, textToDraw.c_str(), nullptr, bounds);
    } else {
        nvgTextBounds(vg_, 0.0f, 0.0f, textToDraw.c_str(), nullptr, bounds);
    }

    float measuredW = bounds[2] - bounds[0];
    float measuredH = bounds[3] - bounds[1];

    if (measuredW < 1.0f) measuredW = pixelSize * static_cast<float>(textToDraw.size());
    if (measuredH < 1.0f) measuredH = pixelSize;
    if (clipString == 2 && maxHeight > 0 && measuredH > maxHeight) measuredH = maxHeight;

    metrics.width  = measuredW;
    metrics.height = measuredH;

    // Helper lambda for the shadow pass (since it needs an offset from the layout)
    auto renderShadowPass = [&](float offset_x, float offset_y) {
        // 1. Save the global state
        nvgSave(vg_);
        nvgTranslate(vg_, static_cast<float>(x) + offset_x, static_cast<float>(y) + offset_y);
        if (angle != 0.0) nvgRotate(vg_, static_cast<float>(angle));
        
        nvgSave(vg_);
        if (clipString == 2 && maxWidth > 0) {
            if (maxHeight > 0) {
                // 2. Apply the bounding box mask based on the INI W and H variables
                nvgScissor(vg_, 0, 0, maxWidth, maxHeight);
            }
            // 3. Draw the meter (nvgText or nvgImagePattern/nvgFill)
            nvgTextBox(vg_, 0, 0, maxWidth, textToDraw.c_str(), nullptr);
        } else {
            // 3. Draw the meter (nvgText or nvgImagePattern/nvgFill)
            nvgText(vg_, 0, 0, textToDraw.c_str(), nullptr);
        }
        
        // 4. Immediately restore the state
        nvgRestore(vg_);
    };

    if (effect && effect->shadowEnabled) {
        nvgSave(vg_);
        nvgFontBlur(vg_, effect->shadowBlur);
        nvgFillColor(vg_, toNVGColor(effect->shadowColor));
        renderShadowPass(static_cast<float>(effect->shadowX), static_cast<float>(effect->shadowY));
        nvgRestore(vg_);
    }

    // ---------------------------------------------------------------
    // STEP 4 & 5: Translate first, build local paint, and draw.
    // ---------------------------------------------------------------
    // 1. Save the global state
    nvgSave(vg_);
    nvgTranslate(vg_, static_cast<float>(x), static_cast<float>(y));
    if (angle != 0.0) nvgRotate(vg_, static_cast<float>(angle));

    nvgBeginPath(vg_);

    if (effect && effect->gradientEnabled) {
        float cx = (bounds[0] + bounds[2]) * 0.5f;
        float cy = (bounds[1] + bounds[3]) * 0.5f;

        float angle_rad = effect->gradientAngle * (M_PI / 180.0f);

        float L = std::abs(measuredW * std::cos(angle_rad)) + std::abs(measuredH * std::sin(angle_rad));
        if (L < 1.0f) L = std::max(measuredW, measuredH);

        float sx = cx - (L * 0.5f) * std::cos(angle_rad);
        float sy = cy - (L * 0.5f) * std::sin(angle_rad);
        float ex = cx + (L * 0.5f) * std::cos(angle_rad);
        float ey = cy + (L * 0.5f) * std::sin(angle_rad);
        
        if (effect->gradientAngle == 0.0) {
            sx = bounds[0];
            ex = bounds[2];
            sy = bounds[1];
            ey = bounds[1];
        } else if (effect->gradientAngle == 90.0) {
            sx = bounds[0];
            ex = bounds[0];
            sy = bounds[1];
            ey = bounds[3];
        }

        NVGpaint paint = nvgLinearGradient(vg_, sx, sy, ex, ey,
            toNVGColor(effect->gradientStartColor),
            toNVGColor(effect->gradientEndColor));
        
        nvgFillPaint(vg_, paint);

        // INVISIBLE FLUSH: Force Wayland/OpenGL to bind the gradient uniform 
        // before nvgText executes, working around a known shader state bug.
        nvgBeginPath(vg_);
        nvgRect(vg_, 0, 0, 0, 0);
        nvgFill(vg_);
    } else {
        nvgFillColor(vg_, toNVGColor(color));
    }

    nvgSave(vg_);
        if (clipString == 2 && maxWidth > 0) {
        if (maxHeight > 0) {
            // 2. Apply the bounding box mask based on the INI W and H variables
            nvgScissor(vg_, 0, 0, maxWidth, maxHeight);
        }
        // 3. Draw the meter (nvgText or nvgImagePattern/nvgFill)
        nvgTextBox(vg_, 0, 0, maxWidth, textToDraw.c_str(), nullptr);
    } else {
        // 3. Draw the meter (nvgText or nvgImagePattern/nvgFill)
        nvgText(vg_, 0, 0, textToDraw.c_str(), nullptr);
    }
    
    // 4. Immediately restore the state
    nvgRestore(vg_);

    return metrics;
}

std::string NanoVGRenderer::substituteText(const std::string &text, const std::string &value) {
    return substituteText(text, std::vector<std::string>{value});
}

std::string NanoVGRenderer::substituteText(const std::string &text, const std::vector<std::string> &values) {
    std::string result;
    result.reserve(text.size());
    for (std::size_t i = 0; i < text.size();) {
        if (text[i] == '%' && i + 1 < text.size() && text[i + 1] >= '1' && text[i + 1] <= '9') {
            std::size_t j = i + 1;
            std::size_t index = 0;
            while (j < text.size() && text[j] >= '0' && text[j] <= '9') {
                index = index * 10 + static_cast<std::size_t>(text[j] - '0');
                ++j;
            }
            if (index >= 1 && index <= values.size()) {
                result += values[index - 1];
            }
            i = j;
        } else {
            result += text[i];
            ++i;
        }
    }
    return result;
}

void NanoVGRenderer::registerFontDirectory(const std::string &fontsDir) {
    if (!valid() || fontsDir.empty()) return;
    std::error_code ec;
    if (!std::filesystem::is_directory(fontsDir, ec)) return;

    for (const auto &entry : std::filesystem::directory_iterator(fontsDir, ec)) {
        if (!entry.is_regular_file(ec)) continue;
        std::string ext = entry.path().extension().string();
        for (char &c : ext) if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
        if (ext == ".ttf" || ext == ".otf") {
            std::string stem = entry.path().stem().string();
            std::string fontName = toLowerString(stem);
            
            if (nvgFindFont(vg_, fontName.c_str()) == -1) {
                int font = nvgCreateFont(vg_, fontName.c_str(), entry.path().string().c_str());
                if (font >= 0) {
                    s_fontFamilyMap[fontName] = fontName;
                }
            }
        }
    }
}

void NanoVGRenderer::setTransform(const std::array<float, 6>& matrix) {
    if (!valid()) return;
    nvgTransform(vg_, matrix[0], matrix[1], matrix[2], matrix[3], matrix[4], matrix[5]);
}

void NanoVGRenderer::save() {
    if (vg_) nvgSave(vg_);
}

void NanoVGRenderer::restore() {
    if (vg_) nvgRestore(vg_);
}

void NanoVGRenderer::resetScissor() {
    if (vg_) nvgResetScissor(vg_);
}
