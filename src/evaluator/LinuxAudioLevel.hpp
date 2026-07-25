#pragma once

#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <memory>
#include <unordered_map>

class IniLexer;
struct pa_simple;

class LinuxAudioLevel {
public:
    LinuxAudioLevel() = default;
    ~LinuxAudioLevel();

    void loadFrom(const IniLexer& skin, const std::string& section);
    void update();

    double numericValue() const;
    std::string stringValue() const;
    
    // Global registry for parent-child relationship
    static std::shared_ptr<LinuxAudioLevel> getParent(const std::string& name);
    static void registerParent(const std::string& name, std::shared_ptr<LinuxAudioLevel> parent);

private:
    std::string sectionName_;
    std::string parentName_;
    bool isParent_ = true;
    std::weak_ptr<LinuxAudioLevel> parent_;
    
    // Parent configuration
    int fftSize_ = 1024;
    int bands_ = 10;
    double attack_ = 50.0;
    double decay_ = 300.0;
    double sensitivity_ = 35.0;
    
    // Child configuration
    std::string type_;
    int bandIdx_ = 0;
    
    // Processed data
    double currentNumeric_ = 0.0;
    std::string currentString_;
    
    // Audio backend (Parent only)
    std::vector<double> bandValues_;
    double rmsValue_ = 0.0;
    
    pa_simple* pa_ = nullptr;
    std::thread captureThread_;
    std::atomic<bool> running_{false};
    std::mutex dataMutex_;
    
    void captureLoop();
    void computeFFT(const std::vector<float>& pcm);
};
