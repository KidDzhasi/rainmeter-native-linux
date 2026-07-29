#pragma once
#include <string>
#include "nanovg.h"

class UIWidget {
protected:
    float x, y, width, height;
    bool isHovered = false;
    bool isClicked = false;

public:
    UIWidget(float x, float y, float w, float h) : x(x), y(y), width(w), height(h) {}
    virtual ~UIWidget() = default;

    bool Contains(float mouseX, float mouseY) const {
        return (mouseX >= x && mouseX <= x + width &&
                mouseY >= y && mouseY <= y + height);
    }

    virtual void OnMouseMove(float mouseX, float mouseY) {
        isHovered = Contains(mouseX, mouseY);
    }
    virtual void OnMousePress(float mouseX, float mouseY) {
        if (isHovered) isClicked = true;
    }
    virtual void OnMouseRelease() {
        isClicked = false;
    }
    
    virtual void Draw(NVGcontext* vg) = 0; 
};
