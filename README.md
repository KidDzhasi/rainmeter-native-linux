# Rainmeter Native for Linux (Wayland)

A lightning-fast, native C++ desktop widget and custom skin engine built for Linux on Wayland using NanoVG and the `wlr-layer-shell` protocol. It brings the modular aesthetic and power of Rainmeter directly to Linux desktops like Pop!_OS without legacy Windows translation layers.

---

## 🎨 Featured Suite: TradSunset (Modular Grid)
The flagship **TradSunset** suite features a cyberpunk-inspired modular layout with:
- High-contrast sci-fi typography (**Orbitron**, **Rajdhani**, **Share Tech Mono**)
- Real-time hardware performance rings and vertical progress bars for CPU, RAM, and Swap
- Dynamic digital clock and localized weather widgets

### Installation
1. Clone or copy the `suites/TradSunset` folder into your local configuration directory:
   \`\`\`bash
   mkdir -p ~/.config/rainmeter-native/Skins/
   cp -r suites/TradSunset ~/.config/rainmeter-native/Skins/
   \`\`\`
2. Launch the suite via the native engine:
   \`\`\`bash
   rainmeter-native ~/.config/rainmeter-native/Skins/TradSunset/TradSunset.ini
   \`\`\`

---

## 🌍 Community Skins
Want to share your own custom layout? Check out the [community folder](./community) to see user-submitted themes or learn how to contribute your own custom skin suite separate from the core official releases.

## License
Distributed under the MIT License. See `LICENSE` for more information.
