from pathlib import Path

from PIL import Image

SRC = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets"
    r"\c__Users_Tony_Fedos_AppData_Roaming_Cursor_User_workspaceStorage_"
    r"5869e162cf5cd77ad277dfac9b5471a4_images_image-48ef42b0-6c14-4011-af07-86c771a57175.png"
)
LOGO_JPG = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets\ladya-logo-light.jpg"
)
HERO_JPG = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets\ladya-hero-light.jpg"
)
OUT = Path(r"d:\PycharmProjects\fast_plan\frontend\public\ladya")
SRC_ASSETS = Path(r"d:\PycharmProjects\fast_plan\frontend\src\assets\ladya")


def knock_black(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, _a = pixels[x, y]
            if r < 28 and g < 28 and b < 28:
                pixels[x, y] = (r, g, b, 0)
            elif r < 45 and g < 45 and b < 45:
                alpha = max(0, min(255, int((max(r, g, b) - 20) * 8)))
                pixels[x, y] = (r, g, b, alpha)
    return img


def knock_near_white(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, _a = pixels[x, y]
            if r > 235 and g > 235 and b > 235:
                pixels[x, y] = (r, g, b, 0)
            elif min(r, g, b) > 210 and abs(r - g) < 12 and abs(g - b) < 12:
                alpha = int(255 * (1 - (min(r, g, b) - 210) / 45))
                pixels[x, y] = (r, g, b, max(0, min(255, alpha)))
    return img


def to_square(img: Image.Image, pad: int = 24) -> Image.Image:
    bbox = img.getbbox()
    if bbox:
        l, t, r, b = bbox
        l = max(0, l - pad)
        t = max(0, t - pad)
        r = min(img.size[0], r + pad)
        b = min(img.size[1], b + pad)
        img = img.crop((l, t, r, b))
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(
        img,
        ((side - img.size[0]) // 2, (side - img.size[1]) // 2),
        img,
    )
    return canvas


def save_pair(img: Image.Image, name: str) -> None:
    for folder in (OUT, SRC_ASSETS):
        folder.mkdir(parents=True, exist_ok=True)
        img.save(folder / name, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SRC_ASSETS.mkdir(parents=True, exist_ok=True)

    mark = to_square(knock_black(Image.open(SRC)))
    for size, name in (
        (512, "logo-mark.png"),
        (128, "logo-mark-128.png"),
        (64, "logo-mark-64.png"),
    ):
        save_pair(mark.resize((size, size), Image.Resampling.LANCZOS), name)

    light = to_square(knock_near_white(Image.open(LOGO_JPG)), pad=8)
    save_pair(light.resize((512, 512), Image.Resampling.LANCZOS), "logo-light.png")
    save_pair(light.resize((128, 128), Image.Resampling.LANCZOS), "logo-light-128.png")

    hero = Image.open(HERO_JPG).convert("RGB")
    for folder in (OUT, SRC_ASSETS):
        hero.save(folder / "hero-light.jpg", quality=90, optimize=True)

    dark = Image.open(SRC).convert("RGB")
    for folder in (OUT, SRC_ASSETS):
        dark.save(folder / "logo-dark.jpg", quality=92, optimize=True)

    print("ok", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
