"""build_assets.py - one-time preparation of the Abyss template (run again ONLY if you change template_orig.png / bg_orig.png).
Writes: template.png (placeholder texts removed) and layout.npz (shape/gradient data). Coordinates: 'base units' = 2560x1440 canvas."""
import os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
T = np.array(Image.open(os.path.join(HERE, "template_orig.png")).convert("RGB"))
B = np.asarray(Image.open(os.path.join(HERE, "bg_orig.png")).convert("RGB"))
H, W = T.shape[:2]; K = W / 2560.0
D = lambda v: int(round(v * K))

# ---------------- geometry (base units) ----------------
CARD = (747.0, 90.4, 2557.2, 1368.8, 62.0); A_CARD = 0.785           # big glass card: x0,y0,x1,y1,radius, white opacity
ABOUT = (43.0, 381.6, 590.4, 1188.4, 104.0); A_ABOUT = 0.81          # About glass box
PANEL = (1734.0, 785.5, 2502.0, 1073.0, 58.0)                        # tinted genre panel
TOPBAR = (1214, 93, 2254, 160)
PILLS = [(1747.5, 829, 1969.5, 892), (1992, 829, 2213.5, 892), (2236.5, 829, 2458, 892), (1847, 924, 2068.5, 987), (2111.5, 924, 2333, 987)]
RATING = (1813, 619, 2146, 720); JOIN = (1974, 1155, 2285, 1246); ABOUTTAB = (90.5, 349, 317, 414.5); TITLE = (1730, 293, 2542, 540)
ARC = (747, 152, 1110, 1335)

# ---------------- 1. erase the placeholder texts ----------------
def vfill(box, y_above, y_below, x_range=None):
    """Replace a rectangle by a vertical blend of the rows just above and just below it (gradients here run sideways)."""
    x0, y0, x1, y1 = [D(v) for v in box]
    ya, yb = D(y_above), D(y_below)
    top = np.median(T[ya - 2:ya + 3, x0:x1].astype(np.float32), axis=0); bot = np.median(T[yb - 2:yb + 3, x0:x1].astype(np.float32), axis=0)
    t = np.linspace(0, 1, y1 - y0, dtype=np.float32)[:, None, None]
    T[y0:y1, x0:x1] = (top[None] * (1 - t) + bot[None] * t).astype(np.uint8)

def white_bbox(box, thr=225):
    x0, y0, x1, y1 = [D(v) for v in box]; s = T[y0:y1, x0:x1]; m = s.min(2) > thr; ys, xs = np.where(m)
    return None if not len(xs) else ((xs.min() + x0) / K, (ys.min() + y0) / K, (xs.max() + x0) / K, (ys.max() + y0) / K)


# ---- glass model helpers (analytic rounded rectangles, 1 px soft edge) ----
def rrect_cov(x, y, box):
    """Coverage 0..1 of a rounded rectangle at native pixel coords x,y (arrays)."""
    x0, y0, x1, y1, r = [v * K for v in box]; cx = (x0 + x1) / 2; cy = (y0 + y1) / 2; hx = (x1 - x0) / 2 - r; hy = (y1 - y0) / 2 - r
    dx = np.abs(x - cx) - hx; dy = np.abs(y - cy) - hy
    sd = np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) + np.minimum(np.maximum(dx, dy), 0) - r
    return np.clip(0.5 - sd, 0, 1)
def under_old(x, y, bgrgb):
    cc = rrect_cov(x, y, CARD)[..., None]; ca = rrect_cov(x, y, ABOUT)[..., None]
    return bgrgb + (255 - bgrgb) * (A_CARD * cc + A_ABOUT * ca)

# ---- 2. expected gradient colour of every shape: robust plane fit on its clean pixels ----
def plane_fit(box, exclude=None, stride=6):
    x0, y0, x1, y1 = [D(v) for v in box]
    ys, xs = np.mgrid[y0:y1:stride, x0:x1:stride]; ys = ys.ravel(); xs = xs.ravel()
    px = T[ys, xs].astype(np.float32); bg = B[ys, xs].astype(np.float32)
    u = under_old(xs.astype(np.float32), ys.astype(np.float32), bg)
    dark = px.mean(1) < 0.55 * u.mean(1)
    sat = (px.max(1) - px.min(1)) < 140
    ok = dark & sat
    print('   candidate pixels', int(ok.sum()), 'of', len(ok), 'in', box)
    if ok.sum() < 20: return np.zeros((3, 3), np.float32), 0
    xb = xs[ok] / K; yb = ys[ok] / K; v = px[ok]
    A = np.stack([np.ones_like(xb), xb, yb], 1); coef = np.zeros((3, 3), np.float32)
    for ch in range(3):
        keep = np.ones(len(v), bool)
        for _ in range(6):
            c, *_ = np.linalg.lstsq(A[keep], v[keep, ch], rcond=None); r = v[:, ch] - A @ c
            keep = np.abs(r) < max(6, 2.2 * np.std(r[keep]))
            if keep.sum() < 50: keep[:] = True
        coef[ch] = c
    return coef, int(ok.sum())
ELEMENTS = {   # name: (box used for the fit, box where the plane applies)
    "topbar": ((1230, 98, 2240, 156), (1214, 93, 2254, 160)),
    "title": ((1745, 300, 2535, 532), (1700, 285, 2560, 548)),
    "rating": ((1825, 624, 2135, 715), (1813, 619, 2146, 720)),
    "join": ((1985, 1160, 2275, 1241), (1974, 1155, 2285, 1246)),
    "abouttab": ((96, 355, 311, 410), (90.5, 349, 317, 414.5)),
    "arc": ((752, 170, 960, 1322), (747, 152, 1110, 1335)),
}
for i, p_ in enumerate(PILLS): ELEMENTS[f"pill{i}"] = ((p_[0] + 6, p_[1] + 6, p_[2] - 6, p_[3] - 6), (p_[0] - 8, p_[1] - 8, p_[2] + 8, p_[3] + 8))
names = list(ELEMENTS); planes = np.zeros((len(names), 3, 3), np.float32); apply_boxes = np.zeros((len(names), 4), np.float32)
for k, n in enumerate(names):
    fitbox, applybox = ELEMENTS[n]; planes[k], cnt = plane_fit(fitbox); apply_boxes[k] = applybox
    e0 = planes[k, :, 0] + planes[k, :, 1] * (fitbox[0] + 4) + planes[k, :, 2] * ((fitbox[1] + fitbox[3]) / 2)
    e1 = planes[k, :, 0] + planes[k, :, 1] * (fitbox[2] - 4) + planes[k, :, 2] * ((fitbox[1] + fitbox[3]) / 2)
    print(f"{n:8s} pixels={cnt:6d}  colour at left end {np.round(e0).astype(int)}  right end {np.round(e1).astype(int)}")


def paint_plane(k, box):
    """Paint a rectangle with the fitted gradient plane of shape k (used where the shape is a plain sideways gradient)."""
    x0, y0, x1, y1 = [D(v) for v in box]; xb = (np.arange(x0, x1, dtype=np.float32) + 0.5)[None, :] / K; yb = (np.arange(y0, y1, dtype=np.float32) + 0.5)[:, None] / K
    T[y0:y1, x0:x1] = np.clip(np.stack([planes[k, c, 0] + planes[k, c, 1] * xb + planes[k, c, 2] * yb for c in range(3)], -1) + 0.5, 0, 255).astype(np.uint8)

# ---- 1. erase the placeholder texts ----
vfill((1598, 146, 1799, 154), 144, 156)                                         # underline (it moves with the chosen type)
vfill((1790, 318, 1966, 408), 308, 420)                                         # TITLE
vfill((1850, 640, 2110, 702), 628, 712)                                         # Rating text + star
for i_, p_ in enumerate(PILLS): paint_plane(names.index(f"pill{i_}"), (p_[0] + 34, p_[1] + 2.5, p_[2] - 34, p_[3] - 2.5))   # genre names: repaint the pill's own gradient
vfill((120, 470, 520, 520), 462, 528)                                           # synopsis placeholder

Image.fromarray(T).save(os.path.join(HERE, "template.png"))

# ---- 2b. exact outline of every shape (so soft shadows next to a shape are never mistaken for the shape) ----
COVER_BOX = (973.0, 260.5, 1734.5, 1310.0, 62.0)
def _cov_cover(x, y):
    return rrect_cov(x, y, (COVER_BOX[0] - 3, COVER_BOX[1] - 3, COVER_BOX[2] + 3, COVER_BOX[3] + 3, COVER_BOX[4] + 3))
core = np.zeros((H, W), bool)
for y0 in range(0, H, 256):
    y1 = min(H, y0 + 256); ysg, xsg = np.mgrid[y0:y1, 0:W]
    px = T[y0:y1].astype(np.float32); bg = B[y0:y1].astype(np.float32); u_ = under_old(xsg.astype(np.float32) + 0.5, ysg.astype(np.float32) + 0.5, bg)
    core[y0:y1] = (px.mean(2) < 0.62 * u_.mean(2)) & (_cov_cover(xsg.astype(np.float32) + 0.5, ysg.astype(np.float32) + 0.5) < 0.01)
labels = np.zeros((H, W), np.uint8)
for k, n in enumerate(names):
    bx0, by0, bx1, by1 = [D(v) for v in ELEMENTS[n][1]]; sub = core[by0:by1, bx0:bx1]
    sub = ndi.binary_closing(sub, structure=np.ones((5, 5), bool)); sub = ndi.binary_fill_holes(sub); sub = ndi.binary_dilation(sub, structure=np.ones((3, 3), bool), iterations=5)
    reg = labels[by0:by1, bx0:bx1]; reg[sub & (reg == 0)] = k + 1
TAB = (90.5, 349.0, 317.0, 414.5, 32.5)
kt = names.index('abouttab'); ysg, xsg = np.mgrid[D(335):D(430), D(80):D(330)]
cv = rrect_cov(xsg.astype(np.float32) + 0.5, ysg.astype(np.float32) + 0.5, TAB) > 0.02
cv = ndi.binary_dilation(cv, iterations=3); reg = labels[D(335):D(430), D(80):D(330)]; reg[:] = np.where(cv, kt + 1, 0)
print("outline pixels per shape:", {n: int((labels == k + 1).sum()) for k, n in enumerate(names)})

# ---- 3. tinted genre panel: glass * (1-beta) + sideways gradient * beta (fitted: beta 0.377, left (9,9,24) -> right (58,56,205)) ----
PANEL_BETA = 0.377; PANEL_E0 = np.array([9, 9, 24], np.float32); PANEL_E1 = np.array([58, 56, 205], np.float32)
C1O = np.array([27, 28, 36], np.float32); C2O = np.array([72, 72, 202], np.float32)

# ---- 4. cover placeholder, logo, top-bar words ----
Tq = np.asarray(Image.fromarray(T).resize((W // 4, H // 4), Image.BOX)).astype(np.int16)
Lq = Tq.mean(2); cm = (((Tq[..., 2] > Tq[..., 0] + 15) & (Lq > 170)) | ((Tq[..., 1] > Tq[..., 0] + 30) & (Tq[..., 1] > Tq[..., 2] + 50)))
cm[:, : int(940 * K / 4)] = False; cm[:, int(1760 * K / 4):] = False; cm[: int(230 * K / 4)] = False; cm[int(1345 * K / 4):] = False
ys, xs = np.where(cm); COVER = tuple(float(v * 4 / K) for v in (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)); print("cover placeholder (base units):", COVER)
dd = np.abs(T[: int(240 * K), : int(160 * K)].astype(np.int16) - B[: int(240 * K), : int(160 * K)].astype(np.int16)).sum(2) > 40
ys, xs = np.where(dd); LOGO = tuple(float(v / K) for v in (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)); print("logo box:", LOGO)
w1 = white_bbox((1580, 100, 1830, 142)); w2 = white_bbox((1930, 100, 2120, 142)); print("Manhwa word:", w1, " Manhua word:", w2)
names_arr = np.array(names)
np.savez_compressed(os.path.join(HERE, "layout.npz"), tab=np.array(TAB, np.float32), tab_id=np.int32(kt + 1), labels=labels, names=names_arr, planes=planes, apply_boxes=apply_boxes, c1o=C1O, c2o=C2O,
    panel=np.array(PANEL, np.float32), panel_beta=np.float32(PANEL_BETA), panel_e0=PANEL_E0, panel_e1=PANEL_E1, card=np.array(CARD, np.float32),
    about=np.array(ABOUT, np.float32), a_card=np.float32(A_CARD), a_about=np.float32(A_ABOUT), cover=np.array(COVER, np.float32), logo=np.array(LOGO, np.float32),
    word_manhwa=np.array(w1, np.float32), word_manhua=np.array(w2, np.float32), underline=np.array([1600.4, 149.2, 1797.2, 150.8], np.float32), K=np.float32(K))
print("layout.npz written")
