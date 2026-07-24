#pragma once

#include <string>
#include <glm/glm.hpp>
#include <array>

class TransformManager {
public:
    TransformManager();
    
    // Parse Rainmeter format: a;b;c;d;tx;ty
    void parse(const std::string& matrixString);
    
    // Return NanoVG transform matrix: [a, b, c, d, e, f]
    std::array<float, 6> toNanoVG() const;
    
    // Reset to identity
    void reset();

private:
    glm::mat3 transform_;
};
