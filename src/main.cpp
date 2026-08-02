#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "engine/SkinManager.hpp"
#include "evaluator/ThemeParser.hpp"
#include "installer/SkinInstaller.hpp"
#include "utils/PathResolver.hpp"

namespace {

constexpr auto kTickInterval = std::chrono::milliseconds(1000);

bool isRmskinFile(const std::string &path) {
  if (path.size() < 7) {
    return false;
  }
  std::string ext = path.substr(path.size() - 7);
  for (char &c : ext) {
    if (c >= 'A' && c <= 'Z') {
      c = static_cast<char>(c - 'A' + 'a');
    }
  }
  return ext == ".rmskin";
}

} // namespace

int main(int argc, char **argv) {
  std::cout << "rainmeter-native: starting up..." << std::endl;

  // -----------------------------------------------------------------------
  // CLI: collect all positional arguments as skin / theme / rmskin paths.
  // Flags like --install are handled inline and cause an early return.
  // -----------------------------------------------------------------------
  std::vector<std::string> inputPaths;
  int globalMonitorIndex = -1;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--install") {
      if (i + 1 >= argc) {
        std::cerr << "Error: --install requires a path to a .rmskin file.\n";
        return 1;
      }
      const std::string rmskinPath = argv[i + 1];
      SkinInstaller installer;
      if (!installer.install(rmskinPath).has_value()) {
        std::cerr << "Installation failed.\n";
        return 1;
      }
      std::cout << "Skin installed successfully.\n";
      return 0;
    }
    if (arg == "-m" || arg == "--monitor") {
      if (i + 1 >= argc) {
        std::cerr << "Error: " << arg << " requires a monitor index.\n";
        return 1;
      }
      globalMonitorIndex = std::stoi(argv[++i]);
      continue;
    }
    if (!arg.empty() && arg[0] != '-') {
      inputPaths.push_back(Utils::ResolvePath(arg));
    }
  }

  // Fallback when no arguments are provided.
  if (inputPaths.empty()) {
    inputPaths.push_back(Utils::ResolvePath("~/.config/rainmeter-native/Rainmeter.ini"));
  }

  // -----------------------------------------------------------------------
  // Resolve each input path: .rmskin -> install then use the produced INI,
  // theme files -> expand to individual widget INI paths,
  // plain .ini -> pass through.
  // -----------------------------------------------------------------------
  std::vector<std::string> widgetPaths;

  for (const auto &inputPath : inputPaths) {
    std::string resolvedPath = inputPath;

    // Auto-install .rmskin packages.
    if (isRmskinFile(resolvedPath)) {
      std::cout << "Auto-installing skin package: " << resolvedPath << "\n";
      SkinInstaller installer;
      auto installedIni = installer.install(resolvedPath);
      if (!installedIni.has_value()) {
        std::cerr << "Error: auto-install of '" << resolvedPath
                  << "' failed or no .ini found.\n";
        continue;
      }
      std::cout << "Launching installed skin: " << *installedIni << "\n";
      resolvedPath = *installedIni;
    }

    // Expand theme / layout files into their individual widget INIs.
    if (ThemeParser::isThemeFile(resolvedPath)) {
      std::cout << "Loading theme: " << resolvedPath << "\n";
      ThemeParser theme;
      if (!theme.parse(resolvedPath)) {
        std::cerr << "Error: could not open theme '" << resolvedPath << "'\n";
        continue;
      }
      for (const auto &widget : theme.widgets()) {
        std::cout << "  Active widget: " << widget.config << " -> "
                  << widget.iniPath << "\n";
        widgetPaths.push_back(widget.iniPath);
      }
      if (theme.widgets().empty()) {
        std::cerr << "Theme '" << resolvedPath
                  << "' has no active (Active=1) widgets; skipping.\n";
      }
    } else {
      std::cout << "Loading single skin: " << resolvedPath << "\n";
      widgetPaths.push_back(resolvedPath);
    }
  }

  if (widgetPaths.empty()) {
    std::cerr << "Error: no widget paths resolved; nothing to show.\n";
    return 1;
  }

  // -----------------------------------------------------------------------
  // Load all skins via SkinManager.
  // -----------------------------------------------------------------------
  SkinManager manager;
  for (const auto &path : widgetPaths) {
    manager.LoadSkin(path, globalMonitorIndex);
  }
  if (manager.ActiveCount() == 0) {
    std::cerr << "Error: no skins could be started.\n";
    return 1;
  }

  std::cout << "Presenting " << manager.ActiveCount()
            << " skin(s) on the desktop. Updating continuously. "
               "Ctrl+C to exit.\n";

  // -----------------------------------------------------------------------
  // Daemon loop: render thread + main-thread tick / event dispatch.
  // -----------------------------------------------------------------------
  std::atomic<bool> running{true};

  std::thread renderThread([&manager, &running]() {
    auto lastFrameTime = std::chrono::steady_clock::now();
    constexpr auto frameDuration = std::chrono::milliseconds(16);

    while (running) {
      auto now = std::chrono::steady_clock::now();
      double dt =
          std::chrono::duration<double, std::milli>(now - lastFrameTime)
              .count();
      lastFrameTime = now;

      manager.UpdateAll(dt);
      manager.RenderAll(dt);

      std::this_thread::sleep_until(now + frameDuration);
    }
  });

  auto lastLoopTime = std::chrono::steady_clock::now();

  while (manager.ActiveCount() > 0) {
    auto now = std::chrono::steady_clock::now();
    double dtMs = std::chrono::duration<double, std::milli>(now - lastLoopTime).count();
    lastLoopTime = now;

    manager.UpdateAnimations(dtMs);

    if (!manager.HandleGlobalEvents()) {
      break;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(4));
  }

  running = false;
  if (renderThread.joinable()) {
    renderThread.join();
  }

  return 0;
}
