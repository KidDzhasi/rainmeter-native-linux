#pragma once

#include <string>
#include <unordered_map>

// PluginManager bridges Rainmeter's Measure=Plugin measures, which normally
// load a Windows .dll, to safe no-op mocks on Linux.
//
// Many popular skins reference Windows-only plugins (Backlight.dll,
// PerfMon.dll, etc.). Loading those is impossible here and letting the
// measure fall through unhandled can crash a naive engine. Instead we
// intercept the measure, log that we are mocking it, and hand back a benign
// default (numeric 0, string "") so the rest of the skin keeps rendering.
//
// A small registry lets us register better-behaved mocks per plugin name in
// the future without touching the call sites.
class PluginManager {
public:
  // The value a mocked plugin measure reports each tick.
  struct MockValue {
    double numeric = 0.0;
    std::string string;
  };

  PluginManager() = default;

  // Registers (or overrides) the mock value returned for `pluginName`.
  // `pluginName` is matched case-insensitively and with any ".dll" suffix
  // stripped (so "Backlight", "backlight", and "Backlight.dll" are the same).
  void registerMock(const std::string &pluginName, MockValue value);

  // Returns true if this manager knows how to mock `pluginName` (either an
  // explicitly registered mock or the catch-all default).
  bool isMocked(const std::string &pluginName) const;

  // Resolves a plugin measure to its mock value. The first time a given
  // plugin name is seen, prints a one-line warning to the console so the user
  // knows a Windows plugin was stubbed out. Unknown plugins fall back to the
  // safe zero/empty default.
  MockValue resolve(const std::string &pluginName);

private:
  // Normalizes a plugin name for lookup: lowercased, ".dll" stripped, and
  // any path separators removed (skins sometimes write "Plugins\Foo.dll").
  static std::string normalize(const std::string &pluginName);

  std::unordered_map<std::string, MockValue> mocks_;
  std::unordered_map<std::string, bool> warned_; // names already logged
};
