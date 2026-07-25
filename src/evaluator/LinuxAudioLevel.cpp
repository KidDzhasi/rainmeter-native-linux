#include "LinuxAudioLevel.hpp"
#include "parser/IniLexer.hpp"
#include <cmath>
#include <complex>
#include <algorithm>
#include <pulse/simple.h>
#include <pulse/error.h>
#include <iostream>

namespace {
    std::unordered_map<std::string, std::weak_ptr<LinuxAudioLevel>> parentRegistry;
    std::mutex registryMutex;
    
    std::string toLower(const std::string& s) {
        std::string out = s;
        for(char& c : out) if(c >= 'A' && c <= 'Z') c = c - 'A' + 'a';
        return out;
    }
    
    // Basic Cooley-Tukey FFT (recursive)
    void fft(std::vector<std::complex<float>>& a) {
        int n = a.size();
        if (n <= 1) return;
        
        std::vector<std::complex<float>> a0(n/2), a1(n/2);
        for (int i = 0; 2*i < n; i++) {
            a0[i] = a[2*i];
            a1[i] = a[2*i+1];
        }
        
        fft(a0);
        fft(a1);
        
        float angle = -2 * M_PI / n;
        std::complex<float> w(1), wn(std::cos(angle), std::sin(angle));
        
        for (int i = 0; 2*i < n; i++) {
            a[i] = a0[i] + w * a1[i];
            a[i + n/2] = a0[i] - w * a1[i];
            w *= wn;
        }
    }
}

LinuxAudioLevel::~LinuxAudioLevel() {
    running_ = false;
    if (captureThread_.joinable()) {
        captureThread_.join();
    }
    if (pa_) {
        pa_simple_free(pa_);
        pa_ = nullptr;
    }
}

std::shared_ptr<LinuxAudioLevel> LinuxAudioLevel::getParent(const std::string& name) {
    std::lock_guard<std::mutex> lock(registryMutex);
    auto it = parentRegistry.find(toLower(name));
    if (it != parentRegistry.end()) {
        return it->second.lock();
    }
    return nullptr;
}

void LinuxAudioLevel::registerParent(const std::string& name, std::shared_ptr<LinuxAudioLevel> parent) {
    std::lock_guard<std::mutex> lock(registryMutex);
    parentRegistry[toLower(name)] = parent;
}

void LinuxAudioLevel::loadFrom(const IniLexer& skin, const std::string& section) {
    sectionName_ = section;
    parentName_ = skin.getOr(section, "Parent", "");
    
    if (parentName_.empty()) {
        isParent_ = true;
        // FFTSize must be power of 2, default 1024
        fftSize_ = std::stoi(skin.getOr(section, "FFTSize", "1024"));
        if (fftSize_ <= 0 || (fftSize_ & (fftSize_-1)) != 0) fftSize_ = 1024; 
        
        bands_ = std::stoi(skin.getOr(section, "Bands", "10"));
        attack_ = std::stod(skin.getOr(section, "FFTAttack", "50.0"));
        decay_ = std::stod(skin.getOr(section, "FFTDecay", "300.0"));
        sensitivity_ = std::stod(skin.getOr(section, "Sensitivity", "35.0"));
        
        bandValues_.resize(bands_, 0.0);
        
        // Start capture thread
        running_ = true;
        captureThread_ = std::thread(&LinuxAudioLevel::captureLoop, this);
    } else {
        isParent_ = false;
        parent_ = getParent(parentName_);
        type_ = skin.getOr(section, "Type", "Band");
        type_ = toLower(type_);
        bandIdx_ = std::stoi(skin.getOr(section, "BandIdx", "0"));
    }
}

void LinuxAudioLevel::captureLoop() {
    pa_sample_spec ss;
    ss.format = PA_SAMPLE_FLOAT32LE;
    ss.rate = 44100;
    ss.channels = 1;
    
    int error;
    // Pass NULL for default recording device, which might be a mic. 
    // Ideally we want the default sink monitor for loopback audio.
    // PulseAudio has "@DEFAULT_SINK@.monitor", but some setups might just use NULL for the default input.
    pa_ = pa_simple_new(NULL, "rainmeter", PA_STREAM_RECORD, "@DEFAULT_SINK@.monitor", "AudioLevel", &ss, NULL, NULL, &error);
    if (!pa_) {
        std::cerr << "Failed to open @DEFAULT_SINK@.monitor, falling back to default source. Error: " << pa_strerror(error) << "\n";
        pa_ = pa_simple_new(NULL, "rainmeter", PA_STREAM_RECORD, NULL, "AudioLevel", &ss, NULL, NULL, &error);
    }
    
    if (!pa_) {
        std::cerr << "pa_simple_new() failed: " << pa_strerror(error) << "\n";
        return;
    }
    
    std::vector<float> pcm(fftSize_);
    
    while (running_) {
        if (pa_simple_read(pa_, pcm.data(), pcm.size() * sizeof(float), &error) < 0) {
            std::cerr << "pa_simple_read() failed: " << pa_strerror(error) << "\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }
        
        computeFFT(pcm);
    }
}

void LinuxAudioLevel::computeFFT(const std::vector<float>& pcm) {
    // 1. Calculate RMS
    double sum = 0;
    for(float v : pcm) sum += v * v;
    double currentRms = std::sqrt(sum / pcm.size());
    // Apply sensitivity mapping
    currentRms *= (sensitivity_ / 10.0);
    currentRms = std::clamp(currentRms, 0.0, 1.0);
    
    // 2. Perform FFT
    std::vector<std::complex<float>> data(fftSize_);
    for(int i = 0; i < fftSize_; i++) {
        // Hanning window
        float multiplier = 0.5f * (1.0f - std::cos(2.0f * M_PI * i / (fftSize_ - 1)));
        data[i] = std::complex<float>(pcm[i] * multiplier, 0);
    }
    
    fft(data);
    
    // 3. Process into bands
    std::vector<double> currentBands(bands_, 0.0);
    
    // We only care about the first half of the FFT (positive frequencies)
    int maxBin = fftSize_ / 2;
    int binsPerBand = std::max(1, maxBin / bands_);
    
    for(int b = 0; b < bands_; b++) {
        double bandSum = 0;
        int startBin = b * binsPerBand;
        int endBin = std::min(maxBin, (b + 1) * binsPerBand);
        int count = 0;
        
        for(int i = startBin; i < endBin; i++) {
            bandSum += std::abs(data[i]);
            count++;
        }
        
        double magnitude = count > 0 ? (bandSum / count) : 0.0;
        
        // Normalize magnitude (approximate heuristic scaling)
        magnitude = magnitude * (sensitivity_ / 10.0) * 2.0; 
        
        currentBands[b] = std::clamp(magnitude, 0.0, 1.0);
    }
    
    // 4. Apply Attack/Decay
    std::lock_guard<std::mutex> lock(dataMutex_);
    
    // Smooth RMS
    if (currentRms > rmsValue_) {
        rmsValue_ += (currentRms - rmsValue_) * std::clamp(1.0 - (attack_ / 1000.0), 0.1, 1.0);
    } else {
        rmsValue_ -= (rmsValue_ - currentRms) * std::clamp(1.0 - (decay_ / 1000.0), 0.1, 1.0);
    }
    rmsValue_ = std::clamp(rmsValue_, 0.0, 1.0);
    
    // Smooth Bands
    for(int b = 0; b < bands_; b++) {
        if (currentBands[b] > bandValues_[b]) {
            bandValues_[b] += (currentBands[b] - bandValues_[b]) * std::clamp(1.0 - (attack_ / 1000.0), 0.1, 1.0);
        } else {
            bandValues_[b] -= (bandValues_[b] - currentBands[b]) * std::clamp(1.0 - (decay_ / 1000.0), 0.1, 1.0);
        }
        bandValues_[b] = std::clamp(bandValues_[b], 0.0, 1.0);
    }
}

void LinuxAudioLevel::update() {
    if (isParent_) {
        std::lock_guard<std::mutex> lock(dataMutex_);
        currentNumeric_ = rmsValue_;
    } else {
        auto p = parent_.lock();
        if (!p) {
            // Might have been registered later
            p = getParent(parentName_);
            if (p) parent_ = p;
        }
        if (p) {
            std::lock_guard<std::mutex> lock(p->dataMutex_);
            if (type_ == "band") {
                if (bandIdx_ >= 0 && bandIdx_ < p->bands_) {
                    currentNumeric_ = p->bandValues_[bandIdx_];
                }
            } else if (type_ == "rms") {
                currentNumeric_ = p->rmsValue_;
            }
        }
    }
    
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%.3f", currentNumeric_);
    currentString_ = buf;
}

double LinuxAudioLevel::numericValue() const { return currentNumeric_; }
std::string LinuxAudioLevel::stringValue() const { return currentString_; }
