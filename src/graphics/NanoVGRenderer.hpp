#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>
#include <array>

#include "nanovg.h"

class NanoVGRenderer {
public:
  enum class TextAlign { Left, Center, Right, CenterCenter };

  struct TextMetrics {
    double width = 0.0;
    double height = 0.0;
  };

  struct Color {
    double r = 0.0;
    double g = 0.0;
    double b = 0.0;
    double a = 1.0;
    static Color parse(std::string_view spec);
  };

  NanoVGRenderer() = default;
  ~NanoVGRenderer();

  NanoVGRenderer(const NanoVGRenderer &) = delete;
  NanoVGRenderer &operator=(const NanoVGRenderer &) = delete;

  bool beginEGL(int width, int height);
  
  void beginFrame(int width, int height, float pixelRatio);
  void endFrame();

  void clear(const Color &color);
  void fillRect(double x, double y, double w, double h, const Color &color);
  void strokeRect(double x, double y, double w, double h, double lineWidth, const Color &color);
  void drawEllipse(double x, double y, double w, double h, const Color &fill, const Color &stroke, double lineWidth);
  void drawLine(double x1, double y1, double x2, double y2, double lineWidth, const Color &color);

  struct ImageMetrics {
    bool success = false;
    double width = 0.0;
    double height = 0.0;
  };

  ImageMetrics drawImage(const std::string &path, double x, double y, double w = 0, double h = 0, int preserveAspectRatio = 0);
  void drawBar(double x, double y, double w, double h, double percent, const Color &barColor, const Color &bgColor);
  
  TextMetrics drawText(const std::string &text, double x, double y,
                       const std::string &fontFace, double fontSize,
                       const Color &color, TextAlign align = TextAlign::Left);

  static std::string substituteText(const std::string &text, const std::string &value);
  static std::string substituteText(const std::string &text, const std::vector<std::string> &values);
  void registerFontDirectory(const std::string &fontsDir);

  int width() const noexcept { return width_; }
  int height() const noexcept { return height_; }
  bool valid() const noexcept { return vg_ != nullptr; }

  // Set current transformation matrix (expects float[6])
  void setTransform(const std::array<float, 6>& matrix);
  void save();
  void restore();

private:
  void reset();
  NVGcolor toNVGColor(const Color& c) const;

  NVGcontext* vg_ = nullptr;
  int width_ = 0;
  int height_ = 0;
};
