import io

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1200, 630
PAD = 90
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _hex_to_rgb(h: str):
    h = (h or "#0055FF").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (0, 85, 255)


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _darken(c, f):
    return tuple(int(x * f) for x in c)


def _fit_name(draw, text, max_w, max_lines=3):
    text = text or "Your Website"
    for size in range(96, 42, -6):
        font = ImageFont.truetype(FONT_BOLD, size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines:
            return font, lines, size
    font = ImageFont.truetype(FONT_BOLD, 42)
    return font, lines[:max_lines], 42


def render_og_png(business_name: str, industry: str, brand_color: str) -> bytes:
    brand = _hex_to_rgb(brand_color)
    top = _mix(_darken(brand, 0.38), (14, 14, 17), 0.3)
    bottom = (9, 9, 11)

    img = Image.new("RGB", (W, H), bottom)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        draw.line([(0, y), (W, y)], fill=_mix(top, bottom, y / H))

    # Soft brand glow (top-right)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 540, -280, W + 140, 380], fill=brand + (95,))
    glow = glow.filter(ImageFilter.GaussianBlur(130))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    max_w = W - 2 * PAD

    # Accent bar + industry label
    draw.rectangle([PAD, 98, PAD + 64, 106], fill=brand)
    label = (industry or "Website").upper()[:44]
    draw.text((PAD, 128), label, font=ImageFont.truetype(FONT_REG, 30),
              fill=_mix(brand, (255, 255, 255), 0.6))

    # Business name (auto-fit, wrapped)
    font, lines, size = _fit_name(draw, business_name, max_w)
    y = 200
    lh = int(size * 1.12)
    for ln in lines:
        draw.text((PAD, y), ln, font=font, fill=(255, 255, 255))
        y += lh

    # Bottom wordmark: brand square with lightning bolt + "SiteGenie"
    my = H - 100
    draw.rounded_rectangle([PAD, my, PAD + 42, my + 42], radius=9, fill=brand)
    bolt = [(PAD + 24, my + 8), (PAD + 12, my + 24), (PAD + 20, my + 24),
            (PAD + 17, my + 35), (PAD + 31, my + 17), (PAD + 22, my + 17)]
    draw.polygon(bolt, fill=(255, 255, 255))
    draw.text((PAD + 58, my + 4), "SiteGenie", font=ImageFont.truetype(FONT_BOLD, 32),
              fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
