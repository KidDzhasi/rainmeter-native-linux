# Community Skins & Contributions

Welcome to the `rainmeter-native` community folder! This space is reserved for user-submitted custom widget suites and themes. 

## Contribution Guidelines
* **Keep it Separate:** All community skins must be placed inside their own unique folder within the `community/` directory (e.g., `community/YourSkinName/`). Do not modify the official suites in `suites/`.
* **Structure:** Each custom skin folder should contain your `.ini` configuration files and any required resource packs (`@Resources/Fonts/`).

## How to Create & Package Custom Skins (.rmskin equivalent)
While traditional Rainmeter uses `.rmskin` zip archives, `rainmeter-native` reads standard folder structures directly on Linux. To package your custom skin for others:
1. Create your skin folder under `~/.config/rainmeter-native/Skins/YourCustomSuite/`.
2. Use absolute layout configurations (`AnchorX=`, `AnchorY=`, or explicit pixel coordinates).
3. Export your folder and submit a Pull Request to add it to the `community/` directory in this repository!
