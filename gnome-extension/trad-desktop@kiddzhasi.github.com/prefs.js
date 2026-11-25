import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class TradDesktopPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const page = new Adw.PreferencesPage({
            title: 'Trad Desktop',
            icon_name: 'preferences-desktop-wallpaper-symbolic',
        });
        window.add(page);

        const group = new Adw.PreferencesGroup({
            title: 'Trad Desktop Control Center & Built-in Pinner',
            description: 'Automatically pins Trad Desktop widgets to your desktop background (stick, below all windows) and manages suites, themes, shapes, weather, and audio visualizers.',
        });
        page.add(group);

        const pinnerRow = new Adw.ActionRow({
            title: 'Built-in Desktop Widget Pinner',
            subtitle: 'Active — automatically strips decorations and pins Trad Desktop widgets below all windows on all workspaces.',
        });
        group.add(pinnerRow);

        const launchRow = new Adw.ActionRow({
            title: 'Launch Trad Desktop Control Center',
            subtitle: 'Open the full GTK4 / Libadwaita studio to customize widgets, themes, shapes, and positions.',
        });

        const launchBtn = new Gtk.Button({
            label: 'Open Control Center',
            valign: Gtk.Align.CENTER,
            css_classes: ['suggested-action'],
        });

        launchBtn.connect('clicked', () => {
            const home = GLib.get_home_dir();
            const candidates = [
                '/usr/share/trad-desktop/launcher_gui.py',
                '/opt/trad-desktop/launcher_gui.py',
                GLib.build_filenamev([home, 'Documents', 'GitHub', 'Trad-Desktop', 'launcher_gui.py']),
                GLib.build_filenamev([home, 'Documents', 'GitHub', 'rainmeter-native-linux', 'launcher_gui.py']),
            ];
            for (const scriptPath of candidates) {
                if (GLib.file_test(scriptPath, GLib.FileTest.EXISTS)) {
                    Gio.Subprocess.new(['python3', scriptPath], Gio.SubprocessFlags.NONE);
                    break;
                }
            }
        });

        launchRow.add_suffix(launchBtn);
        group.add(launchRow);
    }
}
