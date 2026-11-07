"""Build transparent light/dark Ladya marks from the two source artworks."""

from pathlib import Path

from PIL import Image

DARK_SRC = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets"
    r"\c__Users_Tony_Fedos_AppData_Roaming_Cursor_User_workspaceStorage_"
    r"5869e162cf5cd77ad277dfac9b5471a4_images_"
    r"9dd8bee8-3176-4a51-a462-749c599ff7c6-a6282deb-7592-47e7-b82c-9a9edf51accf.png"
)
LIGHT_SRC = Path(
    r"C:\Users\Tony Fedos\.cursor\projects\d-PycharmProjects-fast-plan\assets"
    r"\c__Users_Tony_Fedos_AppData_Roaming_Cursor_User_workspaceStorage_"
    r"5869e162cf5cd77ad277dfac9b5471a4_images_"
    r"1e2c6c6e-7939-4684-a2f9-d087b17e1a8d-962090cb-d67e-49d5-98fc-66cb9ed49cfb.png"
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
            elif r < 48 and g < 48 and b < 48:
                alpha = max(0, min(255, int((max(r, g, b) - 18) * 9)))
                pixels[x, y] = (r, g, b, alpha)
    return img


def to_square(img: Image.Image, pad: int = 20) -> Image.Image:
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


def export_set(img: Image.Image, stem: str) -> None:
    import shutil

    mark = to_square(knock_black(img))
    OUT.mkdir(parents=True, exist_ok=True)
    SRC_ASSETS.mkdir(parents=True, exist_ok=True)
    for size, suffix in ((512, ""), (128, "-128"), (64, "-64"), (32, "-32")):
        name = f"{stem}{suffix}.png"
        path = OUT / name
        mark.resize((size, size), Image.Resampling.LANCZOS).save(path, optimize=True)
        try:
            shutil.copy2(path, SRC_ASSETS / name)
        except OSError:
            # File may be locked by a viewer; public/ is the runtime source of truth.
            pass


def main() -> None:
    export_set(Image.open(DARK_SRC), "logo-dark-mark")
    export_set(Image.open(LIGHT_SRC), "logo-mark")
    # Keep full plates with original bg for reference/splash
    Image.open(DARK_SRC).convert("RGB").save(OUT / "logo-dark.jpg", quality=92, optimize=True)
    Image.open(DARK_SRC).convert("RGB").save(
        SRC_ASSETS / "logo-dark.jpg", quality=92, optimize=True
    )
    Image.open(LIGHT_SRC).convert("RGB").save(
        OUT / "logo-light-plate.jpg", quality=92, optimize=True
    )
    Image.open(LIGHT_SRC).convert("RGB").save(
        SRC_ASSETS / "logo-light-plate.jpg", quality=92, optimize=True
    )
    print("dark corner alpha", Image.open(OUT / "logo-dark-mark.png").getpixel((0, 0)))
    print("light corner alpha", Image.open(OUT / "logo-mark.png").getpixel((0, 0)))
    print("ok")


if __name__ == "__main__":
    main()
