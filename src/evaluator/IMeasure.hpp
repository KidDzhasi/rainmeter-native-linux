#pragma once

#include <string>
#include <memory>
#include <functional>

class IniLexer;
class ScriptEnvironment;
class ActionTimer;

class IMeasure {
public:
    virtual ~IMeasure() = default;
    
    // Initialize the measure from an INI section.
    virtual void loadFrom(const IniLexer& skin, const std::string& section) = 0;
    
    // Poll/update the measure.
    virtual void update(const IniLexer& skin, double dtMs, std::function<void(const std::string&)> executeBangs) = 0;
    
    // Get the formatted string output.
    virtual std::string getString() const = 0;
    
    // Get the numerical value.
    virtual double getNumeric() const = 0;
    
    // Get the percentage (0.0 to 1.0).
    virtual double getPercent() const = 0;

    // Optional extensions for specific measure types.
    virtual std::shared_ptr<ScriptEnvironment> getScript() const { return nullptr; }
    virtual std::shared_ptr<ActionTimer> getActionTimer() const { return nullptr; }
};
