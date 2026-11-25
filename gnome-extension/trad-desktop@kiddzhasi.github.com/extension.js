import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const TradDesktopIndicator = GObject.registerClass(
class TradDesktopIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Trad Desktop');
        this._extension = extension;

        const icon = new St.Icon({
            icon_name: 'preferences-desktop-wallpaper-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(icon);

        const headerItem = new PopupMenu.PopupMenuItem('Trad Desktop Engine', {
            reactive: false,
            style_class: 'trad-desktop-header',
        });
        this.menu.addMenuItem(headerItem);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const openGuiItem = new PopupMenu.PopupMenuItem('Open Trad Desktop Control Center');
        openGuiItem.connect('activate', () => {
            this._spawnCommand(['python3', this._getRepoFile('launcher_gui.py')]);
        });
        this.menu.addMenuItem(openGuiItem);

        const weatherItem = new PopupMenu.PopupMenuItem('Weather Forecast & Locations');
        weatherItem.connect('activate', () => {
            this._spawnCommand(['python3', this._getRepoFile('launcher_gui.py'), '--weather-popup']);
        });
        this.menu.addMenuItem(weatherItem);

        const reloadItem = new PopupMenu.PopupMenuItem('Reload Active Desktop Widgets');
        reloadItem.connect('activate', () => {
            this._spawnCommand(['python3', this._getRepoFile('launcher_gui.py'), '--reload']);
        });
        this.menu.addMenuItem(reloadItem);

        const stopItem = new PopupMenu.PopupMenuItem('Turn OFF Desktop Widgets');
        stopItem.connect('activate', () => {
            this._spawnCommand(['pkill', '-f', 'rainmeter-native']);
        });
        this.menu.addMenuItem(stopItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const prefsItem = new PopupMenu.PopupMenuItem('Extension Preferences…');
        prefsItem.connect('activate', () => {
            this._extension.openPreferences();
        });
        this.menu.addMenuItem(prefsItem);
    }

    _getRepoDir() {
        const home = GLib.get_home_dir();
        const candidates = [
            '/usr/share/trad-desktop',
            '/opt/trad-desktop',
            GLib.build_filenamev([home, 'Documents', 'GitHub', 'Trad-Desktop']),
            GLib.build_filenamev([home, 'Documents', 'GitHub', 'rainmeter-native-linux']),
            GLib.build_filenamev([home, '.local', 'share', 'trad-desktop']),
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
            console.error(`[Trad Desktop] Failed to spawn command: ${e}`);
        }
    }
});

export default class TradDesktopExtension extends Extension {
    enable() {
        this._indicator = new TradDesktopIndicator(this);
        Main.panel.addToStatusArea(this.uuid, this._indicator);

        this._windowCreatedId = global.display.connect('window-created', (_display, window) => {
            let attempts = 0;
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
                attempts++;
                if (window.get_wm_class && window.get_wm_class() === 'rainmeter-native-widget') {
                    this._pinWidgetToDesktop(window);
                    return GLib.SOURCE_REMOVE;
                }
                return attempts < 20 ? GLib.SOURCE_CONTINUE : GLib.SOURCE_REMOVE;
            });
        });
        global.display.list_all_windows().forEach(window => {
            if (window.get_wm_class && window.get_wm_class() === 'rainmeter-native-widget') {
                this._pinWidgetToDesktop(window);
            }
        });
    }

    disable() {
        if (this._windowCreatedId) {
            global.display.disconnect(this._windowCreatedId);
            this._windowCreatedId = null;
        }
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }

    _pinWidgetToDesktop(window) {
        try {
            if (window.decorated) {
                window.decorated = false;
            }
        } catch (e) {
            console.warn('[Trad Desktop] Failed to strip decoration:', e);
        }

        try {
            window.stick();
            window.make_below();
        } catch (e) {
            console.warn('[Trad Desktop] Failed to pin below:', e);
        }
    }
}
