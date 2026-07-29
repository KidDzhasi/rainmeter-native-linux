#pragma once
#include "UIWidget.hpp"
#include <functional>

class UIButton : public UIWidget {
private:
    std::string label;
    std::function<void()> onClickCallback;

public:
    UIButton(float x, float y, float w, float h, std::string text) 
        : UIWidget(x, y, w, h), label(text) {}

    void SetCallback(std::function<void()> callback) {
        onClickCallback = callback;
    }

    void OnMouseRelease() override {
        if (isClicked && isHovered && onClickCallback) {
            onClickCallback(); 
        }
        UIWidget::OnMouseRelease();
    }

    void Draw(NVGcontext* vg) override {
        NVGcolor bgColor = nvgRGBA(30, 30, 30, 255); 
        if (isClicked) bgColor = nvgRGBA(100, 220, 255, 255); 
        else if (isHovered) bgColor = nvgRGBA(60, 60, 60, 255); 

        nvgBeginPath(vg);
        nvgRoundedRect(vg, x, y, width, height, 6.0f);
        nvgFillColor(vg, bgColor);
        nvgFill(vg);

        nvgFillColor(vg, nvgRGBA(255, 255, 255, 255));
        nvgFontSize(vg, 16.0f);
        nvgFontFace(vg, "Rajdhani"); 
        nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgText(vg, x + (width / 2.0f), y + (height / 2.0f), label.c_str(), NULL);
    }
};
