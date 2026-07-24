#include "TransformManager.hpp"
#include <sstream>
#include <vector>

TransformManager::TransformManager() : transform_(1.0f) {}

void TransformManager::parse(const std::string& matrixString) {
    if (matrixString.empty()) {
        reset();
        return;
    }
    
    std::vector<float> values;
    std::stringstream ss(matrixString);
    std::string item;
    while (std::getline(ss, item, ';')) {
        try {
            values.push_back(std::stof(item));
        } catch (...) {
            reset();
            return;
        }
    }
    
    if (values.size() == 6) {
        transform_[0][0] = values[0]; // a
        transform_[0][1] = values[1]; // b
        transform_[0][2] = 0.0f;
        
        transform_[1][0] = values[2]; // c
        transform_[1][1] = values[3]; // d
        transform_[1][2] = 0.0f;
        
        transform_[2][0] = values[4]; // tx
        transform_[2][1] = values[5]; // ty
        transform_[2][2] = 1.0f;
    } else {
        reset();
    }
}

std::array<float, 6> TransformManager::toNanoVG() const {
    return {
        transform_[0][0], transform_[0][1], 
        transform_[1][0], transform_[1][1], 
        transform_[2][0], transform_[2][1]
    };
}

void TransformManager::reset() {
    transform_ = glm::mat3(1.0f);
}
