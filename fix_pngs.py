from PIL import Image

def make_png(path, color):
    img = Image.new('RGBA', (120, 120), color)
    img.save(path)

assets_dir = "/home/remember/.config/rainmeter-native/Skins/PopNative/MediaWidget/assets/"
make_png(assets_dir + "play.png", (0, 255, 0, 255))
make_png(assets_dir + "pause.png", (255, 0, 0, 255))
make_png(assets_dir + "next.png", (0, 0, 255, 255))
make_png(assets_dir + "prev.png", (255, 255, 0, 255))
make_png("/tmp/rainmeter_cover.png", (255, 0, 255, 255))
print("Created valid PNGs!")
