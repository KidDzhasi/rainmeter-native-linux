#include "PluginManager.hpp"

#include <iostream>

std::string PluginManager::normalize(const std::string &pluginName) {
  std::string out = pluginName;

  // Drop anything up to the last path separator ("Plugins\\Foo.dll" ->
  // "Foo.dll").
  const std::size_t sep = out.find_last_of("/\\");
  if (sep != std::string::npos) {
    out = out.substr(sep + 1);
  }

  // Lowercase.
  for (char &c : out) {
    if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>(c - 'A' + 'a');
    }
  }

  // Strip a trailing ".dll".
  const std::string ext = ".dll";
  if (out.size() >= ext.size() &&
      out.compare(out.size() - ext.size(), ext.size(), ext) == 0) {
    out.erase(out.size() - ext.size());
  }
  return out;
}

void PluginManager::registerMock(const std::string &pluginName,
                                 MockValue value) {
  mocks_[normalize(pluginName)] = std::move(value);
}

bool PluginManager::isMocked(const std::string & /*pluginName*/) const {
  // Every plugin is mockable: known names use their registered value, unknown
  // ones fall back to the safe zero/empty default.
  return true;
}

PluginManager::MockValue PluginManager::resolve(const std::string &pluginName) {
  const std::string key = normalize(pluginName);

  // Warn once per distinct plugin so the console isn't spammed every tick.
  if (!warned_[key]) {
    std::cerr << "Mocking Windows Plugin: " << pluginName << "\n";
    warned_[key] = true;
  }

  auto it = mocks_.find(key);
  if (it != mocks_.end()) {
    return it->second;
  }
  return MockValue{}; // numeric 0, string ""
}
