#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include <cairo/cairo.h>

// CairoRenderer draws skin elements (backgrounds, text meters) using
// Cairo for 2D vector graphics and Pango for text layout.
//
// The renderer operates on a caller-owned ARGB32 pixel buffer, which is
// what a Wayland shared-memory buffer provides. This keeps the graphics
// layer independent of the compositor connection: LayerShell allocates
// the buffer, CairoRenderer paints into it.
class CairoRenderer {
public:
  // Horizontal alignment for String meters (Rainmeter's StringAlign key).
  enum class TextAlign { Left, Center, Right, CenterCenter };

  // Pixel dimensions of a piece of drawn text, returned by drawText so the
  // caller can lay out subsequent relative-positioned meters.
  struct TextMetrics {
    double width = 0.0;
    double height = 0.0;
  };

  // Simple RGBA color, components in [0, 255]. Matches Rainmeter's
  // "R,G,B,A" color notation.
  struct Color {

    double r = 0.0;
    double g = 0.0;
    double b = 0.0;
    double a = 1.0;

    // Parses a Rainmeter color string. Supports "R,G,B", "R,G,B,A", "RRGGBB",
    // "RRGGBBAA", and "#RRGGBB". Components are clamped to 0.0-1.0. Returns
    // fully transparent black if parsing fails.
    static Color parse(std::string_view spec);
  };

  CairoRenderer() = default;
  ~CairoRenderer();

  CairoRenderer(const CairoRenderer &) = delete;
  CairoRenderer &operator=(const CairoRenderer &) = delete;

  // Binds the renderer to an externally-owned ARGB32 buffer of the given
  // dimensions. `stride` is the byte length of one pixel row (typically
  // width * 4). Returns false if a Cairo surface could not be created.
  bool begin(unsigned char *pixels, int width, int height, int stride);

  // Alternatively, create a self-owned image surface (used for headless
  // rendering / PNG export when there is no Wayland buffer).
  bool beginImage(int width, int height);

  // Clears the whole surface to the given color.
  void clear(const Color &color);

  // Fills a rectangle.
  void fillRect(double x, double y, double w, double h, const Color &color);

  // Strokes a rectangle outline.
  void strokeRect(double x, double y, double w, double h, double lineWidth,
                  const Color &color);

  // Draws an ellipse inscribed in the given box, with optional fill and
  // stroke. Pass a fully-transparent color to skip either.
  void drawEllipse(double x, double y, double w, double h, const Color &fill,
                   const Color &stroke, double lineWidth);

  // Draws a straight line between two points.
  void drawLine(double x1, double y1, double x2, double y2, double lineWidth,
                const Color &color);

  struct ImageMetrics {
    bool success = false;
    double width = 0.0;
    double height = 0.0;
  };

  // Renders a PNG image loaded from disk at (x, y), scaled to (w, h) if both
  // are > 0 (otherwise drawn at native size). Returns success and the final
  // drawn dimensions.
  ImageMetrics drawImage(const std::string &path, double x, double y, double w = 0,
                         double h = 0, int preserveAspectRatio = 0);

  // Draws a horizontal progress bar. `percent` is 0-100. The filled portion
  // uses `barColor`; the remainder uses `bgColor`.
  void drawBar(double x, double y, double w, double h, double percent,
               const Color &barColor, const Color &bgColor);

  // Draws a line of text using Pango. `x`/`y` are the anchor of the text
  // block; `align` shifts it horizontally relative to that anchor (Left =
  // anchor is the left edge, Center = the middle, Right = the right edge).
  // Returns the measured pixel width/height of the rendered text so callers
  // can position later relative-coordinate meters.
  //   fontFace: e.g. "Trebuchet MS"
  //   fontSize: point size
  TextMetrics drawText(const std::string &text, double x, double y,
                       const std::string &fontFace, double fontSize,
                       const Color &color, TextAlign align = TextAlign::Left);

  // Substitutes a meter's variable token into a Text template. Replaces all
  // occurrences of "%1" with `value` (the live output of the meter's
  // MeasureName), matching Rainmeter's String meter semantics.
  static std::string substituteText(const std::string &text,
                                    const std::string &value);

  // Substitutes multiple meter values into a Text template. Replaces "%1"
  // with values[0], "%2" with values[1], and so on (matching Rainmeter's
  // MeasureName / MeasureName2 / ... String meter semantics). Tokens with
  // no corresponding value are replaced with an empty string.
  static std::string substituteText(const std::string &text,
                                    const std::vector<std::string> &values);

  // Registers all .ttf/.otf font files found in `fontsDir` (e.g. a skin's
  // resolved @Resources/Fonts directory) with the application's fontconfig
  // instance, so Pango can locate custom fonts by family name. Missing or
  // empty directories are ignored. Safe to call multiple times.
  static void registerFontDirectory(const std::string &fontsDir);

  // Flushes pending drawing operations to the underlying buffer.
  void flush();

  // Writes the current surface contents to a PNG file (for verification).
  // Returns false on failure.
  bool writePng(const std::string &path);

  int width() const noexcept { return width_; }
  int height() const noexcept { return height_; }
  bool valid() const noexcept { return surface_ != nullptr && cr_ != nullptr; }

  // Raw access to the underlying ARGB32 pixel data. Valid after a
  // successful begin()/beginImage(); returns nullptr otherwise. Callers
  // should flush() before reading. Used to copy frames into a Wayland
  // shared-memory buffer.
  unsigned char *pixels() const;
  int stride() const;

private:
  void reset();

  cairo_surface_t *surface_ = nullptr;
  cairo_t *cr_ = nullptr;
  int width_ = 0;
  int height_ = 0;
};
