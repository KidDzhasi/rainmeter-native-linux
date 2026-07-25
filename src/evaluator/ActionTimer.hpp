#pragma once

#include <string>
#include <vector>
#include <functional>

class IniLexer;

// ActionTimer is a native C++ replacement for Rainmeter's ActionTimer.dll plugin.
// It parses ActionListN keys and executes sequences of bangs at timed intervals,
// driven by the render thread's delta time (dt).
//
// Usage in a skin:
//   [MeasureTimer]
//   Measure=Plugin
//   Plugin=ActionTimer
//   ActionList1=Repeat FadeIn, 16, 15 | Wait 500 | Repeat FadeOut, 16, 15
//
// The ActionTimer receives commands via !CommandMeasure:
//   [!CommandMeasure MeasureTimer "Execute 1"]  -> runs ActionList1
//   [!CommandMeasure MeasureTimer "Stop 1"]     -> stops ActionList1
class ActionTimer {
public:
    ActionTimer() = default;

    // Called once during measure loading. Parses ActionListN keys from the skin.
    void loadFrom(const IniLexer& skin, const std::string& section);

    // Called from the render thread with the frame delta time in milliseconds.
    // Fires any due bangs through the provided callback.
    void tick(double dtMs, std::function<void(const std::string&)> fireBang);

    // Processes a command string from !CommandMeasure (e.g. "Execute 1", "Stop 1").
    void handleCommand(const std::string& command);

    // Returns true if any action list is currently executing.
    bool isActive() const;

private:
    // A single step in an action list.
    struct Step {
        enum class Type { Bang, Wait, Repeat };
        Type type = Type::Bang;
        std::string bangString;      // For Bang type: the bang to fire
        double intervalMs = 0;       // For Wait: duration; For Repeat: interval
        int repeatCount = 0;         // For Repeat: total iterations
    };

    // An action list parsed from an ActionListN key.
    struct ActionList {
        std::vector<Step> steps;
        bool running = false;
        int currentStep = 0;
        int repeatIteration = 0;     // Current iteration of a Repeat step
        double accumulator = 0.0;    // Time accumulator for Wait/Repeat intervals
    };

    std::vector<ActionList> actionLists_;

    // Parses a single ActionList value string into steps.
    static std::vector<Step> parseActionList(const std::string& value);

    const IniLexer* skin_ = nullptr;
    std::string section_;
};
