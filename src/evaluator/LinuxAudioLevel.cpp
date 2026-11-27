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
    
    // Zero-allocation in-place iterative Cooley-Tukey radix-2 FFT
    void fftInPlace(std::vector<std::complex<float>>& a) {
        const int n = static_cast<int>(a.size());
        if (n <= 1) return;

        for (int i = 1, j = 0; i < n; ++i) {
            int bit = n >> 1;
            for (; j & bit; bit >>= 1) {
                j ^= bit;
            }
            j ^= bit;
            if (i < j) {
                std::swap(a[i], a[j]);
            }
        }

        for (int len = 2; len <= n; len <<= 1) {
            const float angle = -2.0f * static_cast<float>(M_PI) / static_cast<float>(len);
            const std::complex<float> wlen(std::cos(angle), std::sin(angle));
            const int half = len >> 1;
            for (int i = 0; i < n; i += len) {
                std::complex<float> w(1.0f, 0.0f);
                for (int j = 0; j < half; ++j) {
                    const std::complex<float> u = a[i + j];
                    const std::complex<float> v = a[i + j + half] * w;
                    a[i + j] = u + v;
                    a[i + j + half] = u - v;
                    w *= wlen;
                }
            }
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
        targetBandValues_.resize(bands_, 0.0);
        fftBuffer_.resize(fftSize_);

        hanningWindow_.resize(fftSize_);
        for (int i = 0; i < fftSize_; ++i) {
            hanningWindow_[i] = 0.5f * (1.0f - std::cos(2.0f * static_cast<float>(M_PI) * i / std::max(1, fftSize_ - 1)));
        }

        const double sampleRate = 44100.0;
        const double logMin = std::log10(20.0);
        const double logMax = std::log10(16000.0);
        const int maxBin = fftSize_ / 2;
        bandBoundaries_.resize(bands_ + 1);
        for (int b = 0; b <= bands_; ++b) {
            double currentLog = logMin + b * (logMax - logMin) / std::max(1, bands_);
            double currentFreq = std::pow(10.0, currentLog);
            bandBoundaries_[b] = std::clamp(static_cast<int>(std::round(currentFreq * fftSize_ / sampleRate)), 0, maxBin);
        }
        for (int b = 1; b <= bands_; ++b) {
            if (bandBoundaries_[b] <= bandBoundaries_[b - 1]) {
                bandBoundaries_[b] = std::min(maxBin, bandBoundaries_[b - 1] + 1);
            }
        }

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

    const int hopSize = std::max(128, fftSize_ / 2); // 512 samples (~11.6 ms) 50% overlap hop
    pa_buffer_attr bufAttr{};
    bufAttr.maxlength = static_cast<uint32_t>(fftSize_ * sizeof(float) * 2);
    bufAttr.tlength = static_cast<uint32_t>(-1);
    bufAttr.prebuf = static_cast<uint32_t>(-1);
    bufAttr.minreq = static_cast<uint32_t>(-1);
    bufAttr.fragsize = static_cast<uint32_t>(hopSize * sizeof(float));

    int error = 0;
    pa_ = pa_simple_new(NULL, "trad-desktop", PA_STREAM_RECORD, "@DEFAULT_SINK@.monitor", "AudioLevel", &ss, NULL, &bufAttr, &error);
    if (!pa_) {
        std::cerr << "Failed to open @DEFAULT_SINK@.monitor, falling back to default source. Error: " << pa_strerror(error) << "\n";
        pa_ = pa_simple_new(NULL, "trad-desktop", PA_STREAM_RECORD, NULL, "AudioLevel", &ss, NULL, &bufAttr, &error);
    }

    if (!pa_) {
        std::cerr << "pa_simple_new() failed: " << pa_strerror(error) << "\n";
        return;
    }

    std::vector<float> pcmWindow(fftSize_, 0.0f);
    std::vector<float> hopBuf(hopSize, 0.0f);

    while (running_) {
        if (pa_simple_read(pa_, hopBuf.data(), hopBuf.size() * sizeof(float), &error) < 0) {
            std::cerr << "pa_simple_read() failed: " << pa_strerror(error) << "\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }

        // Slide window left by hopSize and append new hopSize samples (50% overlap for 86 Hz smooth updates)
        const int keep = fftSize_ - hopSize;
        if (keep > 0) {
            std::copy(pcmWindow.begin() + hopSize, pcmWindow.end(), pcmWindow.begin());
        }
        std::copy(hopBuf.begin(), hopBuf.end(), pcmWindow.begin() + std::max(0, keep));

        computeFFT(pcmWindow);
    }
}

void LinuxAudioLevel::computeFFT(const std::vector<float>& pcm) {
    // 1. Calculate RMS and fast-exit on silence to save CPU on low-end / Celeron systems
    double sum = 0.0;
    for (float v : pcm) sum += static_cast<double>(v) * v;
    double rmsLinear = std::sqrt(sum / std::max<std::size_t>(1, pcm.size()));

    if (rmsLinear < 1.5e-5) {
        std::lock_guard<std::mutex> lock(dataMutex_);
        targetRmsValue_ = 0.0;
        std::fill(targetBandValues_.begin(), targetBandValues_.end(), 0.0);
        return;
    }

    // Convert to dB
    double rmsDb = 20.0 * std::log10(rmsLinear + 1e-9);

    // Dynamic Range Headroom for musical spectrum visualization
    const double floorDb = -54.0;
    const double ceilingDb = -6.0;

    double currentRms = (rmsDb - floorDb) / (ceilingDb - floorDb);
    currentRms = std::clamp(currentRms, 0.0, 1.0);
    currentRms = std::pow(currentRms, 1.5) * (sensitivity_ / 35.0);
    currentRms = std::clamp(currentRms, 0.0, 1.0);

    // 2. Perform in-place FFT using pre-allocated buffer & pre-computed Hanning window
    for (int i = 0; i < fftSize_; ++i) {
        fftBuffer_[i] = std::complex<float>(pcm[i] * hanningWindow_[i], 0.0f);
    }

    fftInPlace(fftBuffer_);

    // 3. Process into bands using pre-computed logarithmic frequency bin boundaries
    const double invHalfFft = 2.0 / static_cast<double>(fftSize_);
    const double invDbSpan = 1.0 / (ceilingDb - floorDb);
    const double sensScale = sensitivity_ / 35.0;
    std::vector<double> rawBands(bands_, 0.0);

    for (int b = 0; b < bands_; ++b) {
        double bandSum = 0.0;
        double bandPeak = 0.0;
        const int startBin = bandBoundaries_[b];
        const int endBin = bandBoundaries_[b + 1];
        const int count = endBin - startBin;

        for (int i = startBin; i < endBin; ++i) {
            const double mag = std::abs(fftBuffer_[i]);
            bandSum += mag;
            if (mag > bandPeak) bandPeak = mag;
        }

        // Blend average and peak energy per bin for responsive yet stable musical bars
        double magnitude = (count > 0) ? ((0.65 * (bandSum / count) + 0.35 * bandPeak) * invHalfFft) : 0.0;
        double db = 20.0 * std::log10(magnitude + 1e-9);
        double normalized = std::clamp((db - floorDb) * invDbSpan, 0.0, 1.0);
        normalized = std::pow(normalized, 1.55);

        double freqWeight = 0.85 + (static_cast<double>(b) / std::max(1, bands_)) * 0.55;
        normalized *= freqWeight * sensScale;
        rawBands[b] = std::clamp(normalized, 0.0, 1.0);
    }

    // 4. Spatial 3-tap smoothing across adjacent bands + temporal target pre-filter
    std::lock_guard<std::mutex> lock(dataMutex_);
    targetRmsValue_ = targetRmsValue_ * 0.25 + currentRms * 0.75;
    for (int b = 0; b < bands_; ++b) {
        const double prev = (b > 0) ? rawBands[b - 1] : rawBands[b];
        const double curr = rawBands[b];
        const double next = (b + 1 < bands_) ? rawBands[b + 1] : rawBands[b];
        const double spatial = 0.16 * prev + 0.68 * curr + 0.16 * next;
        if (spatial >= targetBandValues_[b]) {
            targetBandValues_[b] = targetBandValues_[b] * 0.20 + spatial * 0.80;
        } else {
            targetBandValues_[b] = targetBandValues_[b] * 0.45 + spatial * 0.55;
        }
    }
}

void LinuxAudioLevel::update(double dtMs) {
    if (isParent_) {
        std::lock_guard<std::mutex> lock(dataMutex_);

        // Frame-rate-independent exponential smoothing (never overshoots or snaps on 16-80ms frames)
        const double clampedDt = std::clamp(dtMs, 1.0, 80.0);
        const double attackTau = std::max(22.0, attack_ * 1.05);
        const double decayTau  = std::max(75.0, decay_ * 0.90);
        const double attackAlpha = 1.0 - std::exp(-clampedDt / attackTau);
        const double decayAlpha  = 1.0 - std::exp(-clampedDt / decayTau);

        if (targetRmsValue_ > rmsValue_) {
            rmsValue_ += (targetRmsValue_ - rmsValue_) * attackAlpha;
        } else {
            rmsValue_ += (targetRmsValue_ - rmsValue_) * decayAlpha;
        }
        if (rmsValue_ < 0.0005 && targetRmsValue_ == 0.0) {
            rmsValue_ = 0.0;
        }
        rmsValue_ = std::clamp(rmsValue_, 0.0, 1.0);

        for (int b = 0; b < bands_; b++) {
            if (targetBandValues_[b] > bandValues_[b]) {
                bandValues_[b] += (targetBandValues_[b] - bandValues_[b]) * attackAlpha;
            } else {
                bandValues_[b] += (targetBandValues_[b] - bandValues_[b]) * decayAlpha;
            }
            if (bandValues_[b] < 0.0005 && targetBandValues_[b] == 0.0) {
                bandValues_[b] = 0.0;
            }
            bandValues_[b] = std::clamp(bandValues_[b], 0.0, 1.0);
        }
        
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
