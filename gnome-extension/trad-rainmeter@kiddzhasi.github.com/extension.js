import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const TradRainmeterIndicator = GObject.registerClass(
class TradRainmeterIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Trad Rainmeter');
        this._extension = extension;

        const icon = new St.Icon({
            icon_name: 'preferences-desktop-wallpaper-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(icon);

        // Header item
        const headerItem = new PopupMenu.PopupMenuItem('Trad Rainmeter Desktop Engine', {
            reactive: false,
            style_class: 'trad-rainmeter-header',
        });
        this.menu.addMenuItem(headerItem);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Open Control Center
        const openGuiItem = new PopupMenu.PopupMenuItem('Open Trad Rainmeter Control Center');
        openGuiItem.connect('activate', () => {
            this._spawnCommand(['python3', this._getRepoFile('launcher_gui.py')]);
        });
        this.menu.addMenuItem(openGuiItem);

        // Open Weather Forecast & Villages
        const weatherItem = new PopupMenu.PopupMenuItem('Weather Forecast & Locations');
        weatherItem.connect('activate', () => {
            this._spawnCommand(['python3', this._getRepoFile('launcher_gui.py'), '--weather-popup']);
        });
        this.menu.addMenuItem(weatherItem);

        // Reload Active Widgets
        const reloadItem = new PopupMenu.PopupMenuItem('Reload Active Desktop Widgets');
        reloadItem.connect('activate', () => {
            this._spawnCommand(['python3', this._getRepoFile('launcher_gui.py'), '--reload']);
        });
        this.menu.addMenuItem(reloadItem);

        // Stop Engine
        const stopItem = new PopupMenu.PopupMenuItem('Turn OFF Desktop Widgets');
        stopItem.connect('activate', () => {
            this._spawnCommand(['pkill', '-f', 'rainmeter-native']);
        });
        this.menu.addMenuItem(stopItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Preferences
        const prefsItem = new PopupMenu.PopupMenuItem('Extension Preferences…');
        prefsItem.connect('activate', () => {
            this._extension.openPreferences();
        });
        this.menu.addMenuItem(prefsItem);
    }

    _getRepoDir() {
        const home = GLib.get_home_dir();
        const candidates = [
            '/usr/share/trad-rainmeter',
            '/opt/trad-rainmeter',
            GLib.build_filenamev([home, 'Documents', 'GitHub', 'Trad-rainmeter']),
            GLib.build_filenamev([home, 'Documents', 'GitHub', 'rainmeter-native-linux']),
            GLib.build_filenamev([home, '.local', 'share', 'trad-rainmeter']),
        ];
        for (const dir of candidates) {
            if (GLib.file_test(GLib.build_filenamev([dir, 'launcher_gui.py']), GLib.FileTest.EXISTS))
                return dir;
        }
        return candidates[2];
    }

    _getRepoFile(relPath) {
        return GLib.build_filenamev([this._getRepoDir(), relPath]);
    }

    _spawnCommand(argv) {
        try {
            Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
        } catch (e) {
            console.error(`[Trad Rainmeter] Failed to spawn command: ${e}`);
        }
    }
});

export default class TradRainmeterExtension extends Extension {
    enable() {
        this._indicator = new TradRainmeterIndicator(this);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
