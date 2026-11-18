"""Extract line art from the supplied illustration on a shared canvas."""

import cv2
import numpy as np
import torch
from torch.nn import functional as F


def fit_lineart_canvas(image):
    _, height, width, _ = image.shape
    scale = min(832 / min(height, width), 1216 / max(height, width))
    target_h, target_w = max(1, round(height * scale)), max(1, round(width * scale))
    pixels = image.movedim(-1, 1)
    if (height, width) != (target_h, target_w):
        pixels = F.interpolate(pixels, size=(target_h, target_w), mode="bilinear",
                               align_corners=False, antialias=True)
    # The line art and mark coordinates use the same canvas.
    pad_x, pad_y = -target_w % 64, -target_h % 64
    if pad_x or pad_y:
        pixels = F.pad(pixels, (pad_x // 2, pad_x - pad_x // 2, pad_y // 2, pad_y - pad_y // 2),
                       mode="replicate")
    return pixels.movedim(1, -1).contiguous()


def first_frame(image, transparency):
    image = image[:1, :, :, :3]
    if transparency is not None and transparency.shape[-2:] == image.shape[1:3]:
        alpha = transparency[:1, :, :, None].to(image)
        image = image * (1 - alpha) + alpha
    return image


def edge_lineart(source, detail):
    rgb = np.rint(source.clip(0, 1) * 255).astype(np.uint8)
    smooth = cv2.bilateralFilter(rgb, 7, 26, 4)
    light, chroma_a, chroma_b = cv2.split(cv2.cvtColor(smooth, cv2.COLOR_RGB2LAB))
    threshold = 128 - 72 * detail
    light_edges = cv2.Canny(light, threshold * 0.42, threshold, L2gradient=True)
    color_edges = cv2.Canny(chroma_a, threshold * 0.42, threshold, L2gradient=True)
    color_edges |= cv2.Canny(chroma_b, threshold * 0.42, threshold, L2gradient=True)

    # Retain drawn dark strokes and suppress the two Canny edges around them.
    stroke_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    dark_ridges = cv2.morphologyEx(light, cv2.MORPH_BLACKHAT, stroke_kernel).astype(np.float32)
    strokes = np.clip((dark_ridges - (35 - 20 * detail)) / 65, 0, 1)
    strokes *= np.clip((155 - light.astype(np.float32)) / 85, 0, 1)
    stroke_neighborhood = cv2.dilate(strokes, np.ones((5, 5), np.uint8))
    edges = np.maximum(light_edges / 255, color_edges * (0.78 / 255))
    edges = np.maximum(strokes, edges * (1 - stroke_neighborhood)).astype(np.float32)
    return 0.65 * edges + 0.35 * cv2.GaussianBlur(edges, (3, 3), 0.65)


def visible_line_pixels(lines):
    return np.count_nonzero(lines >= 32 / 255)


def extract_edges(source, detail, contrast_recovery):
    lines = edge_lineart(source, detail)
    visible = visible_line_pixels(lines)
    sparse_limit = max(8, lines.size // 4000)
    recovered = False
    if contrast_recovery and visible < sparse_limit:
        low, high = np.percentile(source, (1, 99))
        span = high - low
        # Bound amplification and avoid retrying on blank canvases or rounding noise.
        if 4 / 255 <= span < 0.25:
            gain = min(12, 1 / span)
            enhanced = np.clip(0.5 + (source - (low + high) / 2) * gain, 0, 1)
            retry = edge_lineart(enhanced, detail)
            retry_visible = visible_line_pixels(retry)
            if retry_visible > visible:
                lines, visible = retry, retry_visible
                recovered = True
    if visible < 8:
        raise ValueError("几乎没有检测到线条。请提高 detail，或换一张轮廓清楚、反差更大的二次元底图。")
    if visible < sparse_limit:
        return lines, "线条很少。请检查白线预览，必要时提高 detail 或换一张底图。"
    if recovered:
        return lines, "已自动增强反差并重新提线。"
    return lines, "已从彩色底图提线。"


class AnimeLineartExtract:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "method": (["edges", "anime_model"], {
                    "default": "edges",
                    "tooltip": "edges 使用本地图像算法。anime_model 使用可选的 Anime Lineart 模型。",
                }),
                "detail": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05,
                                     "tooltip": "仅用于 edges。值越大越容易保留弱边缘。"}),
            },
            "optional": {
                "transparency": ("MASK",),
                "contrast_recovery": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "仅用于 edges。白线几乎为空时自动尝试一次增强反差。",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("白线", "彩色底图", "提线状态")
    FUNCTION = "extract"
    CATEGORY = "Profile Lineart v4"

    def extract(self, image, method, detail, transparency=None, contrast_recovery=False):
        canvas = fit_lineart_canvas(first_frame(image, transparency))
        if method == "edges":
            lines, status = extract_edges(canvas[0].cpu().numpy(), detail, contrast_recovery)
            lines = torch.from_numpy(lines)[None, ..., None].repeat(1, 1, 1, 3)
            return lines, canvas, status

        import nodes
        from comfy_execution.graph_utils import GraphBuilder

        if "AnimeLineArtPreprocessor" not in nodes.NODE_CLASS_MAPPINGS:
            raise RuntimeError("anime_model 需要 comfyui_controlnet_aux。可以选择 edges 直接提线。")
        graph = GraphBuilder()
        lines = graph.node("AnimeLineArtPreprocessor", image=canvas, resolution=min(canvas.shape[1:3]))
        return {"result": (lines.out(0), canvas, "使用 Anime Lineart 模型提线。"), "expand": graph.finalize()}
