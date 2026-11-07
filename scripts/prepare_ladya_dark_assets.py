from pathlib import Path

from PIL import Image

SRC = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets"
    r"\c__Users_Tony_Fedos_AppData_Roaming_Cursor_User_workspaceStorage_"
    r"5869e162cf5cd77ad277dfac9b5471a4_images_image-b0ba7578-9e1c-499f-86b2-388c30712c7e.png"
)
HERO = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets\ladya-hero-dark.jpg"
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
    canvas.paste(img, ((side - img.size[0]) // 2, (side - img.size[1]) // 2), img)
    return canvas


def save_both(img: Image.Image, name: str, *, jpeg: bool = False) -> None:
    for folder in (OUT, SRC_ASSETS):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        if jpeg:
            img.convert("RGB").save(path, quality=92, optimize=True)
        else:
            img.save(path, optimize=True)


def main() -> None:
    mark = to_square(knock_black(Image.open(SRC)))
    for size, name in (
        (512, "logo-dark-mark.png"),
        (128, "logo-dark-mark-128.png"),
        (64, "logo-dark-mark-64.png"),
    ):
        save_both(mark.resize((size, size), Image.Resampling.LANCZOS), name)

    # Full plate with black bg for dark hero overlays / splash
    Image.open(SRC).convert("RGB").save(OUT / "logo-dark.jpg", quality=92, optimize=True)
    Image.open(SRC).convert("RGB").save(
        SRC_ASSETS / "logo-dark.jpg", quality=92, optimize=True
    )

    hero = Image.open(HERO).convert("RGB")
    save_both(hero, "hero-dark.jpg", jpeg=True)
    print("ok", sorted(p.name for p in OUT.iterdir() if "dark" in p.name))


if __name__ == "__main__":
    main()
