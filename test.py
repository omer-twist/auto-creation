import argparse
import numpy as np
import cv2
from PIL import Image

def remove_bg_if_needed(img_rgba: Image.Image, use_rembg: bool) -> Image.Image:
    if not use_rembg:
        return img_rgba
    from rembg import remove
    return remove(img_rgba)

def good_union_bbox_from_rgba(
    img_rgba: Image.Image,
    alpha_threshold: int = 10,
    close_px: int = 15,
    open_px: int = 3,
    min_component_area_ratio: float = 0.001,
):
    """
    Returns:
      box: (x0, y0, x1, y1) in PIL crop coords (right/bottom exclusive)
      keep_mask: uint8 mask 0/255
    """
    if img_rgba.mode != "RGBA":
        img_rgba = img_rgba.convert("RGBA")

    arr = np.array(img_rgba)
    alpha = arr[:, :, 3]

    # Initial foreground mask from alpha
    mask = (alpha > alpha_threshold).astype(np.uint8) * 255

    h, w = mask.shape
    img_area = h * w

    # Morphology: close (connect + fill small gaps), then open (remove specks)
    if close_px and close_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_px, close_px))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

    if open_px and open_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_px, open_px))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)

    # Keep only sufficiently large components (ignore tiny noise)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    min_area = int(img_area * min_component_area_ratio)
    keep = np.zeros_like(mask)

    for i in range(1, num_labels):  # 0 is background
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            keep[labels == i] = 255

    # Fallback: if filtering removed everything, use raw cleaned mask
    if keep.max() == 0:
        keep = mask

    ys, xs = np.where(keep > 0)
    if len(xs) == 0:
        return None, keep

    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())

    # Convert to PIL crop coords (right/bottom exclusive)
    return (x0, y0, x1 + 1, y1 + 1), keep

def square_crop_box(box, img_w, img_h, padding=0):
    x0, y0, x1, y1 = box

    x0 -= padding; y0 -= padding
    x1 += padding; y1 += padding

    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(img_w, x1); y1 = min(img_h, y1)

    bw = x1 - x0
    bh = y1 - y0
    side = max(bw, bh)

    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2

    sx0 = int(round(cx - side / 2))
    sy0 = int(round(cy - side / 2))
    sx1 = sx0 + side
    sy1 = sy0 + side

    # Shift square into bounds (don't shrink)
    if sx0 < 0:
        sx1 -= sx0
        sx0 = 0
    if sy0 < 0:
        sy1 -= sy0
        sy0 = 0
    if sx1 > img_w:
        shift = sx1 - img_w
        sx0 -= shift
        sx1 = img_w
    if sy1 > img_h:
        shift = sy1 - img_h
        sy0 -= shift
        sy1 = img_h

    sx0 = max(0, sx0); sy0 = max(0, sy0)
    sx1 = min(img_w, sx1); sy1 = min(img_h, sy1)

    return (sx0, sy0, sx1, sy1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", default="out.png")
    ap.add_argument("--use-rembg", action="store_true")
    ap.add_argument("--alpha-threshold", type=int, default=10)
    ap.add_argument("--close-px", type=int, default=15)
    ap.add_argument("--open-px", type=int, default=3)
    ap.add_argument("--min-area-ratio", type=float, default=0.001)
    ap.add_argument("--padding", type=int, default=20)
    ap.add_argument("--out-size", type=int, default=0, help="0 = no resize; else e.g. 1024")
    args = ap.parse_args()

    img = Image.open(args.in_path).convert("RGBA")
    img = remove_bg_if_needed(img, args.use_rembg)

    box, _mask = good_union_bbox_from_rgba(
        img,
        alpha_threshold=args.alpha_threshold,
        close_px=args.close_px,
        open_px=args.open_px,
        min_component_area_ratio=args.min_area_ratio,
    )

    if box is None:
        # If nothing detected, just save (or raise)
        result = img
    else:
        w, h = img.size
        sq = square_crop_box(box, w, h, padding=args.padding)
        result = img.crop(sq)

    if args.out_size and args.out_size > 0:
        result = result.resize((args.out_size, args.out_size), Image.LANCZOS)

    result.save(args.out_path, "PNG")
    print("Saved:", args.out_path)

if __name__ == "__main__":
    main()
