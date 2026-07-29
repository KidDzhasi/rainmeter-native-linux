#pragma once
#include <vector>
#include <memory>
#include "UIWidget.hpp"
#include "nanovg.h"

class UIManager {
private:
    std::vector<std::shared_ptr<UIWidget>> widgets;

    UIManager() = default;

public:
    static UIManager& GetInstance() {
        static UIManager instance;
        return instance;
    }

    void AddWidget(std::shared_ptr<UIWidget> widget) {
        widgets.push_back(widget);
    }

    void OnMouseMove(float x, float y) {
        for (auto& w : widgets) {
            w->OnMouseMove(x, y);
        }
    }

    void OnMousePress(float x, float y) {
        for (auto& w : widgets) {
            w->OnMousePress(x, y);
        }
    }

    void OnMouseRelease() {
        for (auto& w : widgets) {
            w->OnMouseRelease();
        }
    }

    void Draw(NVGcontext* vg) {
        for (auto& w : widgets) {
            w->Draw(vg);
        }
    }
};
