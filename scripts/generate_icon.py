"""Generate app icon for Screenshot Courier. Run once, commit the .ico."""

from PIL import Image, ImageDraw

def create_screenshot_icon(path: str):
    """Generate a screenshot/monitor themed .ico with multiple sizes."""
    # Draw at 256x256, then Pillow will downscale for smaller sizes
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Monitor body (rounded rectangle)
    d.rounded_rectangle([28, 40, 228, 178], radius=16, fill="#3B82F6", outline="#1E40AF", width=4)

    # Screen inner (dark)
    d.rounded_rectangle([40, 52, 216, 166], radius=8, fill="#0F172A")

    # Monitor stand
    d.rectangle([108, 178, 148, 204], fill="#3B82F6")
    d.rounded_rectangle([76, 204, 180, 218], radius=6, fill="#3B82F6", outline="#1E40AF", width=2)

    # Screen content: stylized screenshot crosshair
    # Vertical line
    d.line([128, 72, 128, 148], fill="#34D399", width=2)
    # Horizontal line
    d.line([68, 110, 188, 110], fill="#34D399", width=2)

    # Screenshot capture corners (bracket shape)
    corner_len = 20
    corner_w = 3
    cx1, cy1, cx2, cy2 = 72, 68, 184, 150
    # Top-left
    d.line([cx1, cy1, cx1 + corner_len, cy1], fill="#FBBF24", width=corner_w)
    d.line([cx1, cy1, cx1, cy1 + corner_len], fill="#FBBF24", width=corner_w)
    # Top-right
    d.line([cx2, cy1, cx2 - corner_len, cy1], fill="#FBBF24", width=corner_w)
    d.line([cx2, cy1, cx2, cy1 + corner_len], fill="#FBBF24", width=corner_w)
    # Bottom-left
    d.line([cx1, cy2, cx1 + corner_len, cy2], fill="#FBBF24", width=corner_w)
    d.line([cx1, cy2, cx1, cy2 - corner_len], fill="#FBBF24", width=corner_w)
    # Bottom-right
    d.line([cx2, cy2, cx2 - corner_len, cy2], fill="#FBBF24", width=corner_w)
    d.line([cx2, cy2, cx2, cy2 - corner_len], fill="#FBBF24", width=corner_w)

    # Small camera flash dot (top-right of screen)
    d.ellipse([180, 64, 196, 80], fill="#FBBF24")

    # Strip ICC profile that triggers libpng iCCP warnings when Qt loads the icon
    img.info.pop("icc_profile", None)

    # Save as .ico with multiple sizes
    sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
    img.save(path, format="ICO", sizes=sizes)
    print(f"Icon saved to {path}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(__file__).parent.parent / "resources" / "icon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    create_screenshot_icon(str(out))
