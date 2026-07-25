#include "NanoVGRenderer.hpp"

#include <charconv>
#include <filesystem>
#include <unordered_map>
#include <algorithm>
#include <iostream>

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
    width_ = 0;
    height_ = 0;
}

NVGcolor NanoVGRenderer::toNVGColor(const Color& c) const {
    float a = static_cast<float>(c.a) / 255.0f;
    float r = (static_cast<float>(c.r) / 255.0f) * a;
    float g = (static_cast<float>(c.g) / 255.0f) * a;
    float b = (static_cast<float>(c.b) / 255.0f) * a;
    return nvgRGBAf(r, g, b, a);
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

void NanoVGRenderer::drawLine(double x1, double y1, double x2, double y2, double lineWidth, const Color &color) {
    if (!valid()) return;
    nvgBeginPath(vg_);
    nvgMoveTo(vg_, x1, y1);
    nvgLineTo(vg_, x2, y2);
    nvgStrokeColor(vg_, toNVGColor(color));
    nvgStrokeWidth(vg_, lineWidth);
    nvgStroke(vg_);
}

static std::unordered_map<std::string, int> s_imageCache;

NanoVGRenderer::ImageMetrics NanoVGRenderer::drawImage(const std::string &path, double x, double y, double w, double h, int preserveAspectRatio) {
    if (!valid()) return {};

    int img = 0;
    auto it = s_imageCache.find(path);
    if (it != s_imageCache.end()) {
        img = it->second;
    } else {
        img = nvgCreateImage(vg_, path.c_str(), 0);
        if (img == 0) return {};
        s_imageCache[path] = img;
    }

    int iw = 0, ih = 0;
    nvgImageSize(vg_, img, &iw, &ih);

    double finalW = (w > 0) ? w : iw;
    double finalH = (h > 0) ? h : ih;

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
                nvgIntersectScissor(vg_, x, y, w, h);
            }
            imgPaint = nvgImagePattern(vg_, drawX, drawY, drawW, drawH, 0.0f, img, 1.0f);
            nvgBeginPath(vg_);
            nvgRect(vg_, drawX, drawY, drawW, drawH);
            nvgFillPaint(vg_, imgPaint);
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

NanoVGRenderer::TextMetrics NanoVGRenderer::drawText(const std::string &text, double x, double y, const std::string &fontFace, double fontSize, const Color &color, TextAlign align) {
    TextMetrics metrics;
    if (!valid()) return metrics;

    std::string searchFace = toLowerString(fontFace);
    std::string resolvedFace = "sans";
    auto it = s_fontFamilyMap.find(searchFace);
    if (it != s_fontFamilyMap.end()) {
        resolvedFace = it->second;
    }

    nvgFontSize(vg_, fontSize);
    nvgFontFace(vg_, resolvedFace.c_str());
    nvgFillColor(vg_, toNVGColor(color));

    int nvgAlign = NVG_ALIGN_TOP;
    if (align == TextAlign::Left) nvgAlign |= NVG_ALIGN_LEFT;
    else if (align == TextAlign::Center) nvgAlign |= NVG_ALIGN_CENTER;
    else if (align == TextAlign::Right) nvgAlign |= NVG_ALIGN_RIGHT;
    else if (align == TextAlign::CenterCenter) nvgAlign = NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE;

    nvgTextAlign(vg_, nvgAlign);

    float bounds[4];
    nvgTextBounds(vg_, x, y, text.c_str(), nullptr, bounds);
    
    metrics.width = bounds[2] - bounds[0];
    metrics.height = bounds[3] - bounds[1];

    nvgText(vg_, x, y, text.c_str(), nullptr);
    
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
