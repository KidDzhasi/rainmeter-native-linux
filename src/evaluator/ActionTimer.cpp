#include "ActionTimer.hpp"
#include "parser/IniLexer.hpp"

#include <iostream>
#include <sstream>
#include <algorithm>
#include <cctype>

namespace {
// Trim whitespace from both ends of a string.
std::string trim(const std::string& s) {
    std::size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) ++start;
    std::size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) --end;
    return s.substr(start, end - start);
}

// Case-insensitive prefix check.
bool startsWithCI(const std::string& str, const std::string& prefix) {
    if (str.size() < prefix.size()) return false;
    for (std::size_t i = 0; i < prefix.size(); ++i) {
        if (std::tolower(static_cast<unsigned char>(str[i])) !=
            std::tolower(static_cast<unsigned char>(prefix[i]))) {
            return false;
        }
    }
    return true;
}
} // namespace

void ActionTimer::loadFrom(const IniLexer& skin, const std::string& section) {
    skin_ = &skin;
    section_ = section;
    actionLists_.clear();

    for (int i = 1; ; ++i) {
        std::string key = "ActionList" + std::to_string(i);
        std::string value = skin.getOr(section, key, "");
        if (value.empty()) break;

        ActionList al;
        al.steps = parseActionList(value);
        actionLists_.push_back(std::move(al));
    }

    if (actionLists_.empty()) {
        std::cout << "ActionTimer: no ActionListN keys found in [" << section << "]\n";
    } else {
        std::cout << "ActionTimer: loaded " << actionLists_.size()
                  << " action list(s) from [" << section << "]\n";
    }
}

std::vector<ActionTimer::Step> ActionTimer::parseActionList(const std::string& value) {
    std::vector<Step> steps;

    // Split by pipe '|'
    std::vector<std::string> segments;
    std::size_t start = 0;
    while (start < value.size()) {
        std::size_t end = value.find('|', start);
        if (end == std::string::npos) end = value.size();
        std::string seg = trim(value.substr(start, end - start));
        if (!seg.empty()) segments.push_back(seg);
        start = end + 1;
    }

    for (const auto& seg : segments) {
        Step step;

        if (startsWithCI(seg, "Repeat ")) {
            // Format: Repeat BangName, Interval, Count
            step.type = Step::Type::Repeat;
            std::string args = trim(seg.substr(7));

            // Split by comma
            std::vector<std::string> parts;
            std::size_t pstart = 0;
            while (pstart < args.size()) {
                std::size_t pend = args.find(',', pstart);
                if (pend == std::string::npos) pend = args.size();
                parts.push_back(trim(args.substr(pstart, pend - pstart)));
                pstart = pend + 1;
            }

            if (parts.size() >= 1) step.bangString = parts[0];
            if (parts.size() >= 2) {
                try { step.intervalMs = std::stod(parts[1]); } catch (...) {}
            }
            if (parts.size() >= 3) {
                try { step.repeatCount = std::stoi(parts[2]); } catch (...) {}
            }

            steps.push_back(step);

        } else if (startsWithCI(seg, "Wait ")) {
            // Format: Wait Duration
            step.type = Step::Type::Wait;
            std::string durStr = trim(seg.substr(5));
            try { step.intervalMs = std::stod(durStr); } catch (...) {}
            steps.push_back(step);

        } else {
            // It's a bang string (e.g. [!SetVariable ...]) or an action name
            step.type = Step::Type::Bang;
            step.bangString = seg;
            steps.push_back(step);
        }
    }

    return steps;
}

void ActionTimer::handleCommand(const std::string& command) {
    std::string cmd = trim(command);

    if (startsWithCI(cmd, "Execute ")) {
        std::string numStr = trim(cmd.substr(8));
        int index = 0;
        try { index = std::stoi(numStr); } catch (...) { return; }
        index -= 1; // ActionList1 -> index 0

        if (index >= 0 && index < static_cast<int>(actionLists_.size())) {
            ActionList& al = actionLists_[index];
            al.running = true;
            al.currentStep = 0;
            al.repeatIteration = 0;
            al.accumulator = 0.0;
            std::cout << "ActionTimer: executing ActionList" << (index + 1) << "\n";
        } else {
            std::cerr << "ActionTimer: invalid ActionList index " << (index + 1) << "\n";
        }

    } else if (startsWithCI(cmd, "Stop ")) {
        std::string numStr = trim(cmd.substr(5));
        int index = 0;
        try { index = std::stoi(numStr); } catch (...) { return; }
        index -= 1;

        if (index >= 0 && index < static_cast<int>(actionLists_.size())) {
            actionLists_[index].running = false;
            std::cout << "ActionTimer: stopped ActionList" << (index + 1) << "\n";
        }

    } else {
        std::cout << "ActionTimer: unknown command '" << cmd << "'\n";
    }
}

void ActionTimer::tick(double dtMs, std::function<void(const std::string&)> fireBang) {
    for (auto& al : actionLists_) {
        if (!al.running) continue;
        if (al.currentStep >= static_cast<int>(al.steps.size())) {
            al.running = false;
            continue;
        }

        Step& step = al.steps[al.currentStep];

        switch (step.type) {
        case Step::Type::Bang: {
            // Fire immediately, advance to next step
            std::string bangToFire = skin_->getOr(section_, step.bangString, step.bangString);
            if (!bangToFire.empty() && fireBang) {
                fireBang(bangToFire);
            }
            al.currentStep++;
            al.repeatIteration = 0;
            al.accumulator = 0.0;
            break;
        }

        case Step::Type::Wait:
            al.accumulator += dtMs;
            if (al.accumulator >= step.intervalMs) {
                al.currentStep++;
                al.repeatIteration = 0;
                al.accumulator = 0.0;
            }
            break;

        case Step::Type::Repeat: {
            al.accumulator += dtMs;
            if (al.accumulator >= step.intervalMs) {
                al.accumulator -= step.intervalMs;
                std::string bangToFire = skin_->getOr(section_, step.bangString, step.bangString);
                if (!bangToFire.empty() && fireBang) {
                    fireBang(bangToFire);
                }
                al.repeatIteration++;
                if (al.repeatIteration >= step.repeatCount) {
                    al.currentStep++;
                    al.repeatIteration = 0;
                    al.accumulator = 0.0;
                }
            }
            break;
        }
        } // end switch
    } // end for
} // end tick

bool ActionTimer::isActive() const {
    for (const auto& al : actionLists_) {
        if (al.running) return true;
    }
    return false;
}
