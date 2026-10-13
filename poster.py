"""poster.py - Manhwa Abyss poster (6400x3600 template): recolourable background + gradient shapes. Pillow + numpy."""
import colorsys, os, shutil, subprocess, tempfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageColor, ImageOps
from palettes import BG_COLORS, GRADIENTS

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
FONTS = {"BebasNeue-Regular.ttf": "bebasneue/BebasNeue-Regular.ttf", "Poppins-Light.ttf": "poppins/Poppins-Light.ttf", "Poppins-SemiBold.ttf": "poppins/Poppins-SemiBold.ttf"}
def ensure_fonts():
    os.makedirs(FONT_DIR, exist_ok=True)
    for name, path in FONTS.items():
        dst = os.path.join(FONT_DIR, name)
        if not os.path.exists(dst): urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/" + path, dst)
def find_font(words, fallback):
    """Your own font file wins: any .ttf/.otf in fonts/ whose name contains all the words."""
    if os.path.isdir(FONT_DIR):
        for f in sorted(os.listdir(FONT_DIR)):
            n = f.lower().replace("-", "").replace("_", "").replace(" ", "")
            if f.lower().endswith((".ttf", ".otf")) and all(w in n for w in words): return f
    return fallback
def genre_font_name(): return find_font(["apricot"], "Poppins-Light.ttf")                 # Apricots (free "white apricot" file in fonts/)
def body_font_name(): return find_font(["glacial", "regular"], "Poppins-Light.ttf")        # Glacial Indifference
def font(name, size): return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

# ---------------- assets (loaded once) ----------------
_A = {}
def assets():
    if not _A:
        L = np.load(os.path.join(HERE, "layout.npz"))
        _A["L"] = {k: L[k] for k in L.files}
        _A["T"] = np.asarray(Image.open(os.path.join(HERE, "template.png")).convert("RGB"))
        _A["Bold"] = np.asarray(Image.open(os.path.join(HERE, "bg_orig.png")).convert("RGB"))
        half = Image.open(os.path.join(HERE, "bg_orig.png")).convert("RGB").resize((_A["Bold"].shape[1] // 2, _A["Bold"].shape[0] // 2), Image.BOX)
        _A["Bhalf"] = np.asarray(half).astype(np.float32) / 255.0
        h, s, v = _rgb2hsv(_A["Bhalf"]); w = s * v
        _A["H0"] = float(np.angle((w * np.exp(2j * np.pi * h)).sum()) / (2 * np.pi)) % 1.0       # average hue of the original rays
    return _A

def _rgb2hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; mx = a.max(-1); mn = a.min(-1); d = mx - mn; dd = np.where(d < 1e-6, 1, d)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) / 6.0
    return np.where(d < 1e-6, 0, h), np.where(mx > 0, d / np.maximum(mx, 1e-6), 0), mx
def _hsv2rgb(h, s, v):
    i = np.floor(h * 6).astype(np.int32) % 6; f = h * 6 - np.floor(h * 6); p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q]); return np.stack([r, g, b], -1)

def bg_recolor_half(hexcolor, arr=None):
    """The glowing rays take the chosen colour; the dark parts stay dark. hexcolor None = the original blue."""
    A = assets(); src = A["Bhalf"] if arr is None else arr
    if not hexcolor: return src
    tr, tg, tb = [v / 255.0 for v in ImageColor.getrgb(hexcolor)]; ht, st, vt = colorsys.rgb_to_hsv(tr, tg, tb)
    h, s, v = _rgb2hsv(src)
    h2 = (h - A["H0"] + ht) % 1.0; s2 = np.clip(s * min(1.0, st / 0.80), 0, 1); v2 = v * (0.30 + 0.70 * vt)
    return _hsv2rgb(h2, s2, v2)

def bg_preview(hexcolor, size=(800, 450)):
    """Small preview of the recoloured background."""
    A = assets(); small = np.asarray(Image.fromarray((A["Bhalf"] * 255).astype(np.uint8)).resize(size, Image.LANCZOS)).astype(np.float32) / 255.0
    return Image.fromarray((np.clip(bg_recolor_half(hexcolor, small), 0, 1) * 255).astype(np.uint8))

# ---------------- layout (base units = 2560x1440) ----------------
TITLE_C = (2100, 410); TITLE_W = 700
RATING_C = (1979.5, 669.5)
PILL_C = [(1858.5, 860.5), (2102.7, 860.5), (2347.2, 860.5), (1957.7, 955.5), (2222.2, 955.5)]; PILL_W = 190
SYN_BOX = (70, 478, 563, 1150)
COVER = (973.0, 260.5, 1734.5, 1310.0); COVER_R = 62.0
LOGO_CIRCLE = (93.8, 126.2, 64.0)
SIZES = {"small": 28, "medium": 34, "large": 40}
WHITE_ORANGE = None

def _rrect_cov(x, y, box, K):
    x0, y0, x1, y1, r = [v * K for v in box]; cx = (x0 + x1) / 2; cy = (y0 + y1) / 2; hx = (x1 - x0) / 2 - r; hy = (y1 - y0) / 2 - r
    dx = np.abs(x - cx) - hx; dy = np.abs(y - cy) - hy
    sd = np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) + np.minimum(np.maximum(dx, dy), 0) - r
    return np.clip(0.5 - sd, 0, 1)

def _proj(E, c1o, d, dd):
    return np.clip(((E - c1o) * d).sum(-1) / dd, 0, 1)

def render_base(c1, c2, bg_hex):
    """Background + glass + gradient shapes, all recoloured. Returns a native-size RGB image."""
    A = assets(); L = A["L"]; T = A["T"]; Bold = A["Bold"]; H, W = T.shape[:2]; K = float(L["K"])
    bn_half = bg_recolor_half(bg_hex)
    Bnew = np.asarray(Image.fromarray((np.clip(bn_half, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((W, H), Image.BICUBIC))
    c1 = np.array(c1, np.float32); c2 = np.array(c2, np.float32); c1o = L["c1o"]; c2o = L["c2o"]; d = c2o - c1o; dd = float((d * d).sum())
    CARD, ABOUT, PANEL = L["card"], L["about"], L["panel"]; ac, aa = float(L["a_card"]), float(L["a_about"]); beta = float(L["panel_beta"])
    pe0, pe1 = L["panel_e0"], L["panel_e1"]; planes = L["planes"]; boxes = L["apply_boxes"]; labels = L["labels"]
    out = np.empty_like(T)

    def work(y0, y1):
        p = T[y0:y1].astype(np.float32); bo = Bold[y0:y1].astype(np.float32); bn = Bnew[y0:y1].astype(np.float32)
        xs = (np.arange(W, dtype=np.float32) + 0.5)[None, :]; ys = (np.arange(y0, y1, dtype=np.float32) + 0.5)[:, None]
        gl = (ac * _rrect_cov(xs, ys, CARD, K) + aa * _rrect_cov(xs, ys, ABOUT, K))[..., None]
        Uo = bo + (255 - bo) * gl; Un = bn + (255 - bn) * gl
        # tinted genre panel = glass*(1-beta) + a sideways gradient*beta
        cp = _rrect_cov(xs, ys, PANEL, K) * beta
        t = np.clip((xs / K - PANEL[0]) / (PANEL[2] - PANEL[0]), 0, 1)[..., None]
        ep = pe0 + (pe1 - pe0) * t; sp = _proj(ep, c1o, d, dd)[..., None]; cpn = c1 + (c2 - c1) * sp
        Uo = Uo * (1 - cp[..., None]) + ep * cp[..., None]; Un = Un * (1 - cp[..., None]) + cpn * cp[..., None]
        # shapes: expected original colour E and gradient position S
        E = Uo.copy(); S = np.zeros(Uo.shape[:2], np.float32); lab = labels[y0:y1]; has = lab > 0
        for k in range(len(planes)):
            bx0, by0, bx1, by1 = boxes[k] * K; ra0 = max(int(by0), y0); ra1 = min(int(by1) + 1, y1); ca0 = max(int(bx0), 0); ca1 = min(int(bx1) + 1, W)
            if ra1 <= ra0 or ca1 <= ca0: continue
            msk = (lab[ra0 - y0:ra1 - y0, ca0:ca1] == k + 1)
            if not msk.any(): continue
            xb = (np.arange(ca0, ca1, dtype=np.float32) + 0.5)[None, :] / K; yb = (np.arange(ra0, ra1, dtype=np.float32) + 0.5)[:, None] / K
            blk = np.stack([planes[k, c, 0] + planes[k, c, 1] * xb + planes[k, c, 2] * yb for c in range(3)], -1)
            sub_e = E[ra0 - y0:ra1 - y0, ca0:ca1]; sub_s = S[ra0 - y0:ra1 - y0, ca0:ca1]
            sub_e[msk] = blk[msk]; sub_s[msk] = _proj(blk, c1o, d, dd)[msk]
        dv = E - Uo; ddv = (dv * dv).sum(-1) + 1e-3
        ae = np.clip(((p - Uo) * dv).sum(-1) / ddv, 0, 1) * has
        tab = (lab == int(L['tab_id']))
        if tab.any(): ae = np.where(tab, np.maximum(_rrect_cov(xs, ys, L['tab'], K), 0), ae)      # the tab sits on the dark background: use its exact shape
        ae3 = ae[..., None]
        base_old = Uo + ae3 * dv; Cn = c1 + (c2 - c1) * S[..., None]; base_new = Un + ae3 * (Cn - Un)
        resid = p - base_old; rm = resid.mean(-1)
        wt = np.clip((resid / (255 - base_old + 1e-3)).mean(-1), 0, 1)[..., None]
        sh = np.clip(p.mean(-1) / (base_old.mean(-1) + 1e-3), 0, 1.2)[..., None]
        res = np.where((rm > 0)[..., None], base_new + (255 - base_new) * wt, base_new * sh)
        out[y0:y1] = np.clip(res + 0.5, 0, 255).astype(np.uint8)

    strips = [(y, min(H, y + 64)) for y in range(0, H, 64)]
    with ThreadPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as ex: list(ex.map(lambda t_: work(*t_), strips))
    return Image.fromarray(out)

# ---------- upscale ----------
def upscale(img, target_w, target_h):
    """Auto-HD: Real-ESRGAN if installed, else Lanczos 2x + sharpen, then fit to the cover shape."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    exe = shutil.which("realesrgan-ncnn-vulkan")
    if exe and min(img.size) < target_h:
        try:
            with tempfile.TemporaryDirectory() as t:
                a_, b_ = os.path.join(t, "a.png"), os.path.join(t, "b.png"); img.save(a_)
                subprocess.run([exe, "-i", a_, "-o", b_, "-s", "4"], check=True, capture_output=True, timeout=180)
                img = Image.open(b_).convert("RGB")
        except Exception: pass
    if img.width < target_w or img.height < target_h:
        k = max(target_w / img.width, target_h / img.height)
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=max(2, target_w / 500), percent=110, threshold=2))
    return ImageOps.fit(img, (target_w, target_h), Image.LANCZOS, centering=(.5, .5))

# ---------- text helpers ----------
def _wrap_fit(d, text, fname, w, h, max_size, min_size, spacing, step):
    for size in range(max_size, min_size - 1, -step):
        f = font(fname, size); lines, cur = [], ""
        for word in text.split():
            t = (cur + " " + word).strip()
            if d.textlength(t, font=f) <= w: cur = t
            else:
                if cur: lines.append(cur)
                cur = word
        if cur: lines.append(cur)
        lh = int(size * spacing)
        if len(lines) * lh <= h and all(d.textlength(l, font=f) <= w for l in lines): return f, lines, lh
    return f, lines, lh

def _clip(d, lines, f, w, maxlines):
    """Safety net: if it still does not fit at the smallest size, cut with ... so text never leaves its box."""
    maxlines = max(maxlines, 1)
    if len(lines) <= maxlines: return lines
    lines = lines[:maxlines]; last = lines[-1]
    while last and d.textlength(last + "…", font=f) > w: last = last[:-1]
    lines[-1] = last.rstrip() + "…"; return lines

def _one_line(d, text, fname, max_size, min_size, w):
    for size in range(max_size, min_size - 1, -2):
        f = font(fname, size)
        if d.textlength(text, font=f) <= w: return f, text
    while len(text) > 2 and d.textlength(text + "…", font=f) > w: text = text[:-1]
    return f, text.rstrip() + "…"


# ---------------- texts ----------------
def _ink(f, text):
    """Real ink box (left, top, right, bottom) of a text relative to its left-baseline origin."""
    pad = 60; w = int(f.getlength(text)) + 2 * pad; h = int(f.size * 2) + 2 * pad
    im = Image.new("L", (w, h), 0); oy = pad + int(f.size * 1.3)
    ImageDraw.Draw(im).text((pad, oy), text, font=f, fill=255, anchor="ls")
    b = im.getbbox()
    return (b[0] - pad, b[1] - oy, b[2] - pad, b[3] - oy) if b else (0, 0, 0, 0)

def _star(d, cx, cy, r, width=3, color="white"):
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5; rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.line(pts + [pts[0]], fill=color, width=width, joint="curve")

def _justify(d, f, words, width, x, y, last):
    """Draw one line, spreading the spaces so both edges are straight (the last line of a paragraph stays left)."""
    if last or len(words) == 1:
        d.text((x, y), " ".join(words), font=f, fill=(18, 18, 18), anchor="la"); return
    total = sum(d.textlength(w, font=f) for w in words); gap = (width - total) / (len(words) - 1); cx = x
    for w in words:
        d.text((cx, y), w, font=f, fill=(18, 18, 18), anchor="la"); cx += d.textlength(w, font=f) + gap

def _layout_paragraphs(d, text, f, width):
    lines = []                                                    # (words, is_last_of_paragraph)
    for para in [p_ for p_ in text.replace("\r", "").split("\n") if p_.strip()]:
        cur = []
        for w in para.split():
            if cur and d.textlength(" ".join(cur + [w]), font=f) > width: lines.append((cur, False)); cur = [w]
            else: cur.append(w)
        if cur: lines.append((cur, True))
    return lines

def render(title, synopsis, genres, rating, cover_img, fill, text_size="medium", media_type="Manhwa", out_path=None, scale=None):
    """fill = {"bg": "#hex" or None, "c1": "#hex", "c2": "#hex"}"""
    ensure_fonts(); A = assets(); L = A["L"]; K = float(L["K"]); P = lambda v: int(round(v * K))
    genres = [g.strip() for g in genres if g.strip()][:5]
    c1, c2 = ImageColor.getrgb(fill["c1"]), ImageColor.getrgb(fill["c2"])
    im = render_base(c1, c2, fill.get("bg"))

    # header logo: restored exactly as in the template
    cx, cy, r = LOGO_CIRCLE; box = (P(cx - r - 3), P(cy - r - 3), P(cx + r + 3), P(cy + r + 3)); crop = Image.fromarray(A["T"][box[1]:box[3], box[0]:box[2]])
    m = Image.new("L", (crop.width * 2, crop.height * 2), 0); ImageDraw.Draw(m).ellipse((P(3) * 2, P(3) * 2, (crop.width - P(3)) * 2, (crop.height - P(3)) * 2), fill=255)
    im.paste(crop, box[:2], m.resize(crop.size, Image.LANCZOS))
    d = ImageDraw.Draw(im)

    # top bar: the underline sits under the chosen type
    word = L["word_manhua"] if media_type.lower() == "manhua" else L["word_manhwa"]; ul = L["underline"]
    wc = (word[0] + word[2]) / 2; half = (word[2] - word[0]) / 2 + 22.4
    # wipe the old underline (it was removed from the template), draw the new one
    d.rectangle((P(wc - half), P(ul[1]), P(wc + half), P(ul[3])), fill=(255, 255, 255))

    # cover
    cw, ch = P(COVER[2] - COVER[0]), P(COVER[3] - COVER[1]); cov = upscale(cover_img, cw, ch)
    mk = Image.new("L", (cw, ch), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, cw - 1, ch - 1), P(COVER_R), fill=255)
    im.paste(cov, (P(COVER[0]), P(COVER[1])), mk)

    # title: Bebas Neue Regular, centred in the title shape, shrinks (or wraps to 2 lines) to fit
    f, lines, lh = _wrap_fit(d, title.upper(), "BebasNeue-Regular.ttf", P(TITLE_W), P(225), P(116 / 0.7 * 0.7), P(48), 1.05, P(2))
    lines = _clip(d, lines, f, P(TITLE_W), int(P(225) // lh))
    cap = -_ink(f, "H")[1]; top = P(TITLE_C[1]) - ((len(lines) - 1) * lh + cap) / 2
    for i, l in enumerate(lines):
        il, _, ir, _ = _ink(f, l); d.text((P(TITLE_C[0]) - (il + ir) / 2, top + cap + i * lh), l, font=f, fill="white", anchor="ls")

    # rating (percent) with the star
    bname = body_font_name(); rf = font(bname, P(46)); txt = f"Rating : {rating}"; tw = d.textlength(txt, font=rf); star = P(40); gap = P(12)
    total = tw + gap + star; x = P(RATING_C[0]) - total / 2; capr = -_ink(rf, "R")[1]; yb = P(RATING_C[1]) + capr / 2
    d.text((x, yb), txt, font=rf, fill="white", anchor="ls"); _star(d, x + tw + gap + star / 2, yb - capr / 2, P(19), max(2, P(3)))

    # genres (up to 5), Apricots font, each centred in its pill
    gname = genre_font_name()
    for g_, (pcx, pcy) in zip(genres, PILL_C):
        g_ = " ".join(w[:1].upper() + w[1:] for w in g_.split()); size = P(60)
        while True:
            gf = font(gname, size); il, it, ir, ib = _ink(gf, g_)
            if (ir - il) <= P(PILL_W) and (ib - it) <= P(46) or size <= P(22): break
            size -= P(1)
        d.text((P(pcx) - (il + ir) / 2, P(pcy) - (it + ib) / 2), g_, font=gf, fill="white", anchor="ls")

    # synopsis in the About box: Glacial Indifference, justified, auto-shrinks, never leaves the box
    sx0, sy0, sx1, sy1 = SYN_BOX; width = P(sx1 - sx0); maxh = P(sy1 - sy0); size = P(SIZES.get(text_size, 34)); chosen = None
    while size >= P(13):
        sf = font(bname, size); lhh = int(size * 1.18); lines_ = _layout_paragraphs(d, synopsis, sf, width)
        if len(lines_) * lhh <= maxh: chosen = (sf, lines_, lhh); break
        size -= P(1)
    if chosen is None:
        sf = font(bname, P(13)); lhh = int(P(13) * 1.18); lines_ = _layout_paragraphs(d, synopsis, sf, width)[: max(1, maxh // lhh)]
        w_, last_ = lines_[-1]; lines_[-1] = (w_[:-1] + [w_[-1] + "…"], True); chosen = (sf, lines_, lhh)
    sf, lines_, lhh = chosen; y = P(sy0)
    for words, last in lines_: _justify(d, sf, words, width, P(sx0), y, last); y += lhh

    S = SCALE if scale is None else scale
    if S != 1: im = im.resize((int(im.width * S), int(im.height * S)), Image.LANCZOS)
    if out_path: im.save(out_path)
    return im

SCALE = float(os.environ.get("POSTER_SCALE", "1"))            # 1 = full 6400x3600. 0.5 = half size (faster, smaller file)

def save_png_capped(im, max_mb=25):
    """Best-quality PNG under max_mb (Telegram allows up to 50). Shrinks only if it has to."""
    import io
    cur = im; limit = max_mb * 1024 * 1024
    for _ in range(4):
        buf = io.BytesIO(); cur.save(buf, "PNG", compress_level=4)
        if buf.tell() <= limit: buf.seek(0); return buf, cur.size
        k = max(0.5, min(0.95, (limit / buf.tell()) ** 0.5 * 0.97)); cur = cur.resize((int(cur.width * k), int(cur.height * k)), Image.LANCZOS)
    buf.seek(0); return buf, cur.size

def swatch(hex_, name, size=(520, 300)):
    return gradient_preview(name, hex_, hex_, only_solid=True, size=size)

def gradient_preview(name, c1, c2, only_solid=False, size=(900, 340)):
    """Small preview card: the two bars the template uses (left to right, top to bottom)."""
    ensure_fonts(); im = Image.new("RGB", size, (245, 245, 245)); d = ImageDraw.Draw(im)
    def grad(w, h, vertical):
        a = np.array(ImageColor.getrgb(c1), np.float32); b = np.array(ImageColor.getrgb(c2), np.float32)
        s = (np.linspace(0, 1, h, dtype=np.float32)[:, None] + 0 * np.linspace(0, 1, w)[None, :]) if vertical else (np.linspace(0, 1, w, dtype=np.float32)[None, :] + 0 * np.linspace(0, 1, h)[:, None])
        g = Image.fromarray((a + (b - a) * s[..., None]).astype(np.uint8)); mk = Image.new("L", (w, h), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=255); return g, mk
    title_f = font("Poppins-SemiBold.ttf", 30); small = font("Poppins-Light.ttf", 22)
    if only_solid:
        g, mk = grad(size[0] - 28, size[1] - 28, False); im.paste(g, (14, 14), mk)
        r, gg, b = ImageColor.getrgb(c1); fg = (0, 0, 0) if (r * .299 + gg * .587 + b * .114) > 160 else (255, 255, 255)
        d.text((size[0] // 2, size[1] // 2 - 16), name, font=font("Poppins-SemiBold.ttf", 34), fill=fg, anchor="mm")
        d.text((size[0] // 2, size[1] // 2 + 30), c1.upper(), font=font("Poppins-Light.ttf", 28), fill=fg, anchor="mm"); return im
    d.text((size[0] // 2, 34), f"{name}   {c1.upper()}  +  {c2.upper()}", font=title_f, fill=(40, 40, 40), anchor="mm")
    g, mk = grad(520, 90, False); im.paste(g, (40, 80), mk); d.text((300, 192), "Left to right (title, bars, pills)", font=small, fill=(60, 60, 60), anchor="mm")
    g, mk = grad(220, 230, True); im.paste(g, (640, 80), mk); d.text((750, 330), "Top to bottom (left side)", font=small, fill=(60, 60, 60), anchor="mm")
    return im
