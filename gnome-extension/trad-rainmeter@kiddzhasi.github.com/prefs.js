import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class TradRainmeterPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const page = new Adw.PreferencesPage({
            title: 'Trad Rainmeter',
            icon_name: 'preferences-desktop-wallpaper-symbolic',
        });
        window.add(page);

        const group = new Adw.PreferencesGroup({
            title: 'Trad Rainmeter Control Center',
            description: 'Manage desktop suites, Basic Widgets shapes & themes, Music Players, and Audio Visualizers.',
        });
        page.add(group);

        const launchRow = new Adw.ActionRow({
            title: 'Launch Trad Rainmeter Control Center',
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
                '/usr/share/trad-rainmeter/launcher_gui.py',
                '/opt/trad-rainmeter/launcher_gui.py',
                GLib.build_filenamev([home, 'Documents', 'GitHub', 'Trad-rainmeter', 'launcher_gui.py']),
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
