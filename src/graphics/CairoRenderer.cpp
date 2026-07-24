#include "CairoRenderer.hpp"

#include <charconv>
#include <filesystem>
#include <vector>

#include <fontconfig/fontconfig.h>
#include <fontconfig/fcfreetype.h>
#include <pango/pangocairo.h>
#include <unordered_map>

static std::unordered_map<std::string, std::string> s_fontFamilyMap;

static std::string toLowerString(const std::string& str) {
  std::string out = str;
  for (char& c : out) c = std::tolower(static_cast<unsigned char>(c));
  return out;
}

CairoRenderer::Color CairoRenderer::Color::parse(std::string_view spec) {
  // Trim outer whitespace
  while (!spec.empty() && (spec.front() == ' ' || spec.front() == '\t')) {
    spec.remove_prefix(1);
  }
  while (!spec.empty() && (spec.back() == ' ' || spec.back() == '\t')) {
    spec.remove_suffix(1);
  }

  if (spec.empty()) {
    return Color{};
  }

  // Handle HEX: "RRGGBB" or "RRGGBBAA", optionally starting with "#"
  if (spec.find(',') == std::string_view::npos) {
    std::string_view hexStr = spec;
    if (hexStr.front() == '#') {
      hexStr.remove_prefix(1);
    }
    
    if (hexStr.size() == 6 || hexStr.size() == 8) {
      uint32_t val = 0;
      auto [ptr, ec] = std::from_chars(hexStr.data(), hexStr.data() + hexStr.size(), val, 16);
      if (ec == std::errc()) {
        Color c;
        if (hexStr.size() == 6) {
          c.r = ((val >> 16) & 0xFF) / 255.0;
          c.g = ((val >> 8) & 0xFF) / 255.0;
          c.b = (val & 0xFF) / 255.0;
          c.a = 1.0;
        } else {
          c.r = ((val >> 24) & 0xFF) / 255.0;
          c.g = ((val >> 16) & 0xFF) / 255.0;
          c.b = ((val >> 8) & 0xFF) / 255.0;
          c.a = (val & 0xFF) / 255.0;
        }
        return c;
      }
    }
  }

  // Split on commas into up to four integer components (0-255).
  std::vector<int> components;
  std::size_t start = 0;
  while (start <= spec.size() && components.size() < 4) {
    std::size_t comma = spec.find(',', start);
    std::string_view token = (comma == std::string_view::npos)
                                 ? spec.substr(start)
                                 : spec.substr(start, comma - start);

    // Trim whitespace around the token.
    while (!token.empty() && (token.front() == ' ' || token.front() == '\t')) {
      token.remove_prefix(1);
    }
    while (!token.empty() && (token.back() == ' ' || token.back() == '\t')) {
      token.remove_suffix(1);
    }

    int value = 0;
    if (!token.empty()) {
      std::from_chars(token.data(), token.data() + token.size(), value);
    }
    components.push_back(value);

    if (comma == std::string_view::npos) {
      break;
    }
    start = comma + 1;
  }

  Color c;
  if (components.size() >= 3) {
    c.r = components[0] / 255.0;
    c.g = components[1] / 255.0;
    c.b = components[2] / 255.0;
    c.a = (components.size() >= 4) ? components[3] / 255.0 : 1.0;
  }
  return c;
}

CairoRenderer::~CairoRenderer() { reset(); }

void CairoRenderer::reset() {
  if (cr_ != nullptr) {
    cairo_destroy(cr_);
    cr_ = nullptr;
  }
  if (surface_ != nullptr) {
    cairo_surface_destroy(surface_);
    surface_ = nullptr;
  }
  width_ = 0;
  height_ = 0;
}

bool CairoRenderer::begin(unsigned char *pixels, int width, int height,
                          int stride) {
  reset();
  surface_ = cairo_image_surface_create_for_data(pixels, CAIRO_FORMAT_ARGB32,
                                                 width, height, stride);
  if (cairo_surface_status(surface_) != CAIRO_STATUS_SUCCESS) {
    reset();
    return false;
  }
  cr_ = cairo_create(surface_);
  if (cairo_status(cr_) != CAIRO_STATUS_SUCCESS) {
    reset();
    return false;
  }
  width_ = width;
  height_ = height;
  return true;
}

bool CairoRenderer::beginImage(int width, int height) {
  reset();
  surface_ = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, width, height);
  if (cairo_surface_status(surface_) != CAIRO_STATUS_SUCCESS) {
    reset();
    return false;
  }
  cr_ = cairo_create(surface_);
  if (cairo_status(cr_) != CAIRO_STATUS_SUCCESS) {
    reset();
    return false;
  }
  width_ = width;
  height_ = height;
  return true;
}

void CairoRenderer::clear(const Color &color) {
  if (!valid()) {
    return;
  }
  cairo_save(cr_);
  cairo_set_operator(cr_, CAIRO_OPERATOR_SOURCE);
  cairo_set_source_rgba(cr_, color.r, color.g, color.b, color.a);
  cairo_paint(cr_);
  cairo_restore(cr_);
}

void CairoRenderer::fillRect(double x, double y, double w, double h,
                             const Color &color) {
  if (!valid()) {
    return;
  }
  cairo_set_source_rgba(cr_, color.r, color.g, color.b, color.a);
  cairo_rectangle(cr_, x, y, w, h);
  cairo_fill(cr_);
}

CairoRenderer::TextMetrics
CairoRenderer::drawText(const std::string &text, double x, double y,
                        const std::string &fontFace, double fontSize,
                        const Color &color, TextAlign align) {
  TextMetrics metrics;
  if (!valid()) {
    return metrics;
  }

  PangoLayout *layout = pango_cairo_create_layout(cr_);
  pango_layout_set_text(layout, text.c_str(), -1);

  std::string searchFace = toLowerString(fontFace);
  std::string resolvedFace = fontFace;
  auto it = s_fontFamilyMap.find(searchFace);
  if (it != s_fontFamilyMap.end()) {
    resolvedFace = it->second;
  }

  PangoFontDescription *desc = pango_font_description_new();
  pango_font_description_set_family(desc, resolvedFace.c_str());
  pango_font_description_set_absolute_size(desc, fontSize * PANGO_SCALE);
  pango_layout_set_font_description(layout, desc);
  pango_font_description_free(desc);

  // Measure the rendered extents so we can align and report dimensions.
  int pxWidth = 0;
  int pxHeight = 0;
  pango_cairo_update_layout(cr_, layout);
  pango_layout_get_pixel_size(layout, &pxWidth, &pxHeight);
  metrics.width = static_cast<double>(pxWidth);
  metrics.height = static_cast<double>(pxHeight);

  // Shift the draw origin horizontally based on alignment. `x` is the anchor;
  // Center/Right pull the text block left so the anchor lands at the
  // middle/right edge respectively.
  double drawX = x;
  double drawY = y;
  if (align == TextAlign::Center || align == TextAlign::CenterCenter) {
    drawX = x - metrics.width / 2.0;
  } else if (align == TextAlign::Right) {
    drawX = x - metrics.width;
  }
  
  if (align == TextAlign::CenterCenter) {
    drawY = y - metrics.height / 2.0;
  }

  cairo_save(cr_);
  cairo_set_source_rgba(cr_, color.r, color.g, color.b, color.a);
  cairo_move_to(cr_, drawX, drawY);
  pango_cairo_show_layout(cr_, layout);
  cairo_restore(cr_);

  g_object_unref(layout);
  return metrics;
}

void CairoRenderer::strokeRect(double x, double y, double w, double h,
                               double lineWidth, const Color &color) {
  if (!valid()) {
    return;
  }
  cairo_set_source_rgba(cr_, color.r, color.g, color.b, color.a);
  cairo_set_line_width(cr_, lineWidth);
  cairo_rectangle(cr_, x, y, w, h);
  cairo_stroke(cr_);
}

void CairoRenderer::drawEllipse(double x, double y, double w, double h,
                                const Color &fill, const Color &stroke,
                                double lineWidth) {
  if (!valid() || w <= 0 || h <= 0) {
    return;
  }
  cairo_save(cr_);
  // Map the unit circle to the bounding box via translate + scale.
  cairo_translate(cr_, x + w / 2.0, y + h / 2.0);
  cairo_scale(cr_, w / 2.0, h / 2.0);
  cairo_arc(cr_, 0.0, 0.0, 1.0, 0.0, 2.0 * 3.14159265358979323846);
  cairo_restore(cr_);

  if (fill.a > 0.0) {
    cairo_set_source_rgba(cr_, fill.r, fill.g, fill.b, fill.a);
    cairo_fill_preserve(cr_);
  }
  if (stroke.a > 0.0) {
    cairo_set_source_rgba(cr_, stroke.r, stroke.g, stroke.b, stroke.a);
    cairo_set_line_width(cr_, lineWidth);
    cairo_stroke(cr_);
  } else {
    cairo_new_path(cr_);
  }
}

void CairoRenderer::drawLine(double x1, double y1, double x2, double y2,
                             double lineWidth, const Color &color) {
  if (!valid()) {
    return;
  }
  cairo_set_source_rgba(cr_, color.r, color.g, color.b, color.a);
  cairo_set_line_width(cr_, lineWidth);
  cairo_move_to(cr_, x1, y1);
  cairo_line_to(cr_, x2, y2);
  cairo_stroke(cr_);
}

static std::unordered_map<std::string, cairo_surface_t*> s_imageCache;

CairoRenderer::ImageMetrics CairoRenderer::drawImage(const std::string &path, double x, double y,
                              double w, double h, int preserveAspectRatio) {
  if (!valid()) {
    return {};
  }
  
  cairo_surface_t *image = nullptr;
  auto it = s_imageCache.find(path);
  if (it != s_imageCache.end()) {
    image = it->second;
  } else {
    image = cairo_image_surface_create_from_png(path.c_str());
    if (cairo_surface_status(image) != CAIRO_STATUS_SUCCESS) {
      cairo_surface_destroy(image);
      return {};
    }
    s_imageCache[path] = image;
  }

  const int iw = cairo_image_surface_get_width(image);
  const int ih = cairo_image_surface_get_height(image);

  double finalW = (w > 0) ? w : iw;
  double finalH = (h > 0) ? h : ih;

  cairo_save(cr_);
  cairo_translate(cr_, x, y);

  if (w > 0 && h > 0 && iw > 0 && ih > 0) {
    if (preserveAspectRatio == 0) {
      // 0: Stretch (default)
      cairo_scale(cr_, w / static_cast<double>(iw), h / static_cast<double>(ih));
    } else {
      double scaleX = w / static_cast<double>(iw);
      double scaleY = h / static_cast<double>(ih);
      double scale = 1.0;
      if (preserveAspectRatio == 1) {
        // 1: Fit (scale to fit within W,H without cropping)
        scale = std::min(scaleX, scaleY);
      } else if (preserveAspectRatio == 2) {
        // 2: Fill/Crop (scale to cover W,H, clipping the excess)
        scale = std::max(scaleX, scaleY);
      }
      
      // If we are cropping (Fill), we need to clip to W,H before scaling
      if (preserveAspectRatio == 2) {
        cairo_rectangle(cr_, 0, 0, w, h);
        cairo_clip(cr_);
      }
      
      // Center the image inside the bounding box
      double drawW = iw * scale;
      double drawH = ih * scale;
      cairo_translate(cr_, (w - drawW) / 2.0, (h - drawH) / 2.0);
      cairo_scale(cr_, scale, scale);
    }
  } else if (w > 0 && iw > 0 && h <= 0) {
    // Scale proportionally if only width is given
    double scale = w / static_cast<double>(iw);
    cairo_scale(cr_, scale, scale);
    finalH = ih * scale;
  } else if (h > 0 && ih > 0 && w <= 0) {
    // Scale proportionally if only height is given
    double scale = h / static_cast<double>(ih);
    cairo_scale(cr_, scale, scale);
    finalW = iw * scale;
  }

  cairo_set_source_surface(cr_, image, 0, 0);
  cairo_paint(cr_);
  cairo_restore(cr_);
  
  ImageMetrics metrics;
  metrics.success = true;
  metrics.width = finalW;
  metrics.height = finalH;
  return metrics;
}

void CairoRenderer::drawBar(double x, double y, double w, double h,
                            double percent, const Color &barColor,
                            const Color &bgColor) {
  if (!valid() || w <= 0 || h <= 0) {
    return;
  }
  double frac = percent / 100.0;
  if (frac < 0.0) {
    frac = 0.0;
  }
  if (frac > 1.0) {
    frac = 1.0;
  }

  // Background track.
  if (bgColor.a > 0.0) {
    fillRect(x, y, w, h, bgColor);
  }
  // Filled portion (horizontal, left-to-right).
  fillRect(x, y, w * frac, h, barColor);
}

std::string CairoRenderer::substituteText(const std::string &text,
                                          const std::string &value) {
  return substituteText(text, std::vector<std::string>{value});
}

std::string
CairoRenderer::substituteText(const std::string &text,
                              const std::vector<std::string> &values) {
  std::string result;
  result.reserve(text.size());
  for (std::size_t i = 0; i < text.size();) {
    // Recognize a "%<n>" token where <n> is a run of digits (1-based index).
    if (text[i] == '%' && i + 1 < text.size() && text[i + 1] >= '1' &&
        text[i + 1] <= '9') {
      std::size_t j = i + 1;
      std::size_t index = 0;
      while (j < text.size() && text[j] >= '0' && text[j] <= '9') {
        index = index * 10 + static_cast<std::size_t>(text[j] - '0');
        ++j;
      }
      // %1 -> values[0], %2 -> values[1], ...
      if (index >= 1 && index <= values.size()) {
        result += values[index - 1];
      }
      // Out-of-range tokens collapse to an empty string.
      i = j;
    } else {
      result += text[i];
      ++i;
    }
  }
  return result;
}

void CairoRenderer::registerFontDirectory(const std::string &fontsDir) {
  if (fontsDir.empty()) {
    return;
  }
  std::error_code ec;
  if (!std::filesystem::is_directory(fontsDir, ec)) {
    return; // Missing directory: nothing to register.
  }

  FcConfig *config = FcConfigGetCurrent();
  if (config == nullptr) {
    return;
  }

  // Add every .ttf/.otf file so fontconfig (and thus Pango) can find custom
  // fonts by family name.
  for (const auto &entry : std::filesystem::directory_iterator(fontsDir, ec)) {
    if (!entry.is_regular_file(ec)) {
      continue;
    }
    std::string ext = entry.path().extension().string();
    for (char &c : ext) {
      if (c >= 'A' && c <= 'Z') {
        c = static_cast<char>(c - 'A' + 'a');
      }
    }
    if (ext == ".ttf" || ext == ".otf") {
      const std::string path = entry.path().string();
      const FcChar8* fcPath = reinterpret_cast<const FcChar8 *>(path.c_str());
      FcConfigAppFontAddFile(config, fcPath);

      // Query the font file to extract the true typographical family name.
      FcPattern *pat = FcFreeTypeQuery(fcPath, 0, nullptr, nullptr);
      if (pat != nullptr) {
        FcChar8 *family = nullptr;
        if (FcPatternGetString(pat, FC_FAMILY, 0, &family) == FcResultMatch) {
          std::string familyStr = reinterpret_cast<const char *>(family);
          std::string stem = entry.path().stem().string();
          // Map both the filename (without extension) and the family name itself
          // (lowercased) to the exact case-sensitive family name Pango expects.
          s_fontFamilyMap[toLowerString(stem)] = familyStr;
          s_fontFamilyMap[toLowerString(familyStr)] = familyStr;
        }
        FcPatternDestroy(pat);
      }
    }
  }
}

void CairoRenderer::flush() {
  if (surface_ != nullptr) {
    cairo_surface_flush(surface_);
  }
}

unsigned char *CairoRenderer::pixels() const {
  if (surface_ == nullptr) {
    return nullptr;
  }
  return cairo_image_surface_get_data(surface_);
}

int CairoRenderer::stride() const {
  if (surface_ == nullptr) {
    return 0;
  }
  return cairo_image_surface_get_stride(surface_);
}

bool CairoRenderer::writePng(const std::string &path) {
  if (surface_ == nullptr) {
    return false;
  }
  flush();
  return cairo_surface_write_to_png(surface_, path.c_str()) ==
         CAIRO_STATUS_SUCCESS;
}
