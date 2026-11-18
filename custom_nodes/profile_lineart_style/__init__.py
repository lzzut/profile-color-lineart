"""Local, deterministic styling nodes for white-on-black anime line art."""

import math

import cv2
import numpy as np
import torch

from .image_input import AnimeLineartExtract


def rgb_int(value):
    return np.array([(value >> 16) & 255, (value >> 8) & 255, value & 255], np.float32) / 255


def parse_region(value):
    box = tuple(float(part.strip()) for part in value.split(","))
    if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
        raise ValueError("mark_region must be x0,y0,x1,y1 in 0..1, with x0<x1 and y0<y1")
    return box


def tonal_lines(lines, source, shadow_color, highlight_color, shadow_level=0.45,
                highlight_level=1.1, light_angle=-35.0, tone_contrast=1.6,
                source_shading=0.25, line_gamma=0.72, line_gain=1.1, line_width=0,
                line_texture=0.0):
    height, width = lines.shape[:2]
    source = cv2.resize(source, (width, height), interpolation=cv2.INTER_AREA)
    strength = np.clip((lines.max(axis=-1) - 2 / 255) / (253 / 255), 0, 1)
    strength = np.clip(strength ** line_gamma * line_gain, 0, 1)
    if line_width:
        strength = cv2.dilate(strength, np.ones((2 * line_width + 1,) * 2, np.uint8))
    if line_texture:
        rng = np.random.default_rng(0)
        grain = rng.random((height, width), dtype=np.float32)
        coarse = rng.random((height // 16 + 2, width // 16 + 2), dtype=np.float32)
        pressure = cv2.resize(coarse, (width, height), interpolation=cv2.INTER_LINEAR)
        strength = np.clip(strength * (1 + line_texture * (0.9 * grain + 1.1 * pressure - 1)), 0, 1)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    angle = math.radians(light_angle)
    dx, dy = math.cos(angle), math.sin(angle)
    projection = (xx / max(width - 1, 1) - 0.5) * dx + (yy / max(height - 1, 1) - 0.5) * dy
    tone = 0.5 + projection / (abs(dx) + abs(dy))
    tone = np.clip((tone - 0.5) * tone_contrast + 0.5, 0, 1)
    # Sample nearby fill colors rather than the original black contour pixels.
    fill = cv2.dilate(source, np.ones((9, 9), np.uint8))
    luminance = cv2.GaussianBlur(fill @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 7)
    tone *= (1 - source_shading) + source_shading * luminance ** 0.65
    tone = tone[..., None]
    colors = rgb_int(shadow_color) * (1 - tone) + rgb_int(highlight_color) * tone
    levels = shadow_level * (1 - tone) + highlight_level * tone
    field = np.clip(colors * levels, 0, 1)
    return (strength[..., None] * field).astype(np.float32), field.astype(np.float32)


def original_marks(source, mode="off", target_color=0xEF003E, hue_tolerance=20.0,
                   region="0,0,1,1", skin_contact=0.65, mark_strength=1.0, dark_floor=0.22,
                   color_tolerance=12.0):
    height, width = source.shape[:2]
    mask = np.zeros((height, width), np.float32)
    if mode == "off":
        return np.zeros_like(source), mask
    x0, y0, x1, y1 = parse_region(region)
    box = np.s_[int(y0 * height):math.ceil(y1 * height), int(x0 * width):math.ceil(x1 * width)]
    if mode == "region_sample":
        pixels = cv2.cvtColor(source[box].astype(np.float32), cv2.COLOR_RGB2LAB)
        target = cv2.cvtColor(rgb_int(target_color).reshape(1, 1, 3), cv2.COLOR_RGB2LAB)[0, 0]
        mask[box] = np.sum((pixels - target) ** 2, axis=-1) <= color_tolerance ** 2
        return np.clip(source * mark_strength, 0, 1) * mask[..., None], mask

    area = np.zeros((height, width), bool)
    area[box] = True
    hsv = cv2.cvtColor(source.astype(np.float32), cv2.COLOR_RGB2HSV)
    if mode == "region_dark":
        selected = area & (hsv[..., 2] < 0.30)
    elif mode == "region_light":
        selected = area & (hsv[..., 2] > 0.78) & (hsv[..., 1] < 0.25)
    elif mode in ("skin_color", "region_color"):
        target_hsv = cv2.cvtColor(rgb_int(target_color).reshape(1, 1, 3), cv2.COLOR_RGB2HSV)[0, 0]
        distance = np.abs(hsv[..., 0] - target_hsv[0])
        distance = np.minimum(distance, 360 - distance)
        selected = area & (distance <= hue_tolerance) & (hsv[..., 1] >= 0.45) & (hsv[..., 2] >= 0.15)
        if mode == "skin_color":
            red, green, blue = source.transpose(2, 0, 1)
            skin = ((red > 0.45) & (green > 0.22) & (blue > 0.12) &
                    (red > green + 0.025) & (red > blue + 0.05) & (hsv[..., 1] < 0.5))
            count, labels, stats, _ = cv2.connectedComponentsWithStats(selected.astype(np.uint8), 8)
            accepted = np.zeros_like(selected)
            for index in range(1, count):
                x, y, w, h, pixels = stats[index]
                if pixels < max(8, height * width * 0.00006) or pixels > height * width * 0.015 or max(w, h) > max(width, height) * 0.22:
                    continue
                left, top, right, bottom = max(x - 10, 0), max(y - 10, 0), min(x + w + 10, width), min(y + h + 10, height)
                component = (labels[top:bottom, left:right] == index).astype(np.uint8)
                ring = (cv2.dilate(component, np.ones((15, 15), np.uint8)) > 0) & (component == 0)
                if ring.any() and skin[top:bottom, left:right][ring].mean() >= skin_contact:
                    accepted[top:bottom, left:right] |= component.astype(bool)
            selected = accepted
    else:
        raise ValueError(f"Unknown mark mode: {mode}")
    mask = selected.astype(np.float32)
    colors = source.copy()
    if mode == "region_dark":
        value = colors.max(axis=-1, keepdims=True)
        colors = np.where(value > 0.001, colors / np.maximum(value, 0.001), 1) * np.maximum(value, dark_floor)
    overlay = np.clip(colors * mark_strength, 0, 1) * mask[..., None]
    return overlay.astype(np.float32), mask


def outlined_marks(source, outline_width=1.5, ink_color=None, **settings):
    ink, selection = original_marks(source, **settings)
    if not selection.any():
        return ink, selection
    if ink_color is not None:
        color = np.clip(rgb_int(ink_color) * settings.get("mark_strength", 1.0), 0, 1)
        ink = selection[..., None] * color

    binary = selection.astype(np.uint8)
    x, y, width, height = cv2.boundingRect(binary)
    region = np.s_[max(0, y - 3):y + height + 3, max(0, x - 3):x + width + 3]
    local_mask = selection[region]
    height, width = local_mask.shape

    # Smooth the shape before drawing the outline, then average subpixel coverage.
    scale = 4
    fine_size = ((width + 2) * scale, (height + 2) * scale)
    fine = cv2.resize(np.pad(local_mask, 1), fine_size, interpolation=cv2.INTER_CUBIC)
    fine = cv2.GaussianBlur(fine, (0, 0), 0.7 * scale)
    inside = (fine >= 0.5).astype(np.uint8)
    distance = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
    band = np.clip(outline_width * scale + 0.5 - distance, 0, 1) * inside
    coverage = cv2.resize(band, (width + 2, height + 2), interpolation=cv2.INTER_AREA)[1:-1, 1:-1]

    # Keep narrow source strokes that a smoothed contour could erase.
    kernel = np.ones((3, 3), np.uint8)
    wide = cv2.morphologyEx(binary[region], cv2.MORPH_OPEN, kernel)
    thin = (local_mask > 0) & (cv2.dilate(wide, kernel) == 0)
    coverage[thin] = np.maximum(coverage[thin], min(outline_width, 1.0))

    local_ink = ink[region]
    # Use nearby ink color for partial coverage outside the original mask.
    edge = (coverage > 0) & (local_mask == 0)
    weights = cv2.GaussianBlur(local_mask, (5, 5), 0.8)
    nearby_ink = cv2.GaussianBlur(local_ink, (5, 5), 0.8)
    local_ink[edge] = nearby_ink[edge] / np.maximum(weights[edge, None], 1e-6)
    local_ink *= coverage[..., None]
    return ink, selection


def composite_glow(colored_lines, marks, mark_mask, glow_strength=0.45, glow_radius=1.6):
    mask = mark_mask[..., None]
    clearance = cv2.dilate(mark_mask, np.ones((5, 5), np.uint8))
    base = colored_lines * (1 - clearance[..., None])
    base_glow = (cv2.GaussianBlur(base, (0, 0), glow_radius) * 0.75 +
                 cv2.GaussianBlur(base, (0, 0), glow_radius * 3) * 0.25) * glow_strength
    mark_glow = (cv2.GaussianBlur(marks, (0, 0), glow_radius) * 0.75 +
                 cv2.GaussianBlur(marks, (0, 0), glow_radius * 3) * 0.25) * glow_strength
    # The ink itself retains its source RGB; bloom is composited underneath it.
    return np.clip((base + base_glow + mark_glow) * (1 - mask) + marks, 0, 1).astype(np.float32)


class AnimeTonalLineart:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "lines": ("IMAGE",), "source": ("IMAGE",),
            "shadow_color": ("INT", {"default": 0x087B80, "min": 0, "max": 0xFFFFFF}),
            "highlight_color": ("INT", {"default": 0x9CFFF0, "min": 0, "max": 0xFFFFFF}),
            "shadow_level": ("FLOAT", {"default": 0.45, "min": 0.05, "max": 2.0, "step": 0.05}),
            "highlight_level": ("FLOAT", {"default": 1.1, "min": 0.1, "max": 2.0, "step": 0.05}),
            "light_angle": ("FLOAT", {"default": -35.0, "min": -180.0, "max": 180.0, "step": 5.0}),
            "tone_contrast": ("FLOAT", {"default": 1.6, "min": 0.0, "max": 3.0, "step": 0.1}),
            "source_shading": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0, "step": 0.05}),
            "line_gamma": ("FLOAT", {"default": 0.72, "min": 0.3, "max": 2.0, "step": 0.05}),
            "line_gain": ("FLOAT", {"default": 1.1, "min": 0.1, "max": 2.0, "step": 0.05}),
            "line_width": ("INT", {"default": 0, "min": 0, "max": 2}),
        }, "optional": {
            "line_texture": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05}),
        }}

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("colored_lines", "tone_field")
    FUNCTION = "render"
    CATEGORY = "Profile Lineart v4"

    def render(self, lines, source, **settings):
        source = source.cpu()
        result = [tonal_lines(line.numpy(), source[min(i, len(source) - 1)].numpy(), **settings)
                  for i, line in enumerate(lines.cpu())]
        return tuple(torch.from_numpy(np.stack(items)) for items in zip(*result))


class AnimeOriginalMarks:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "source": ("IMAGE",),
            "mode": (["off", "skin_color", "region_color", "region_dark"], {"default": "off"}),
            "target_color": ("INT", {"default": 0xEF003E, "min": 0, "max": 0xFFFFFF}),
            "hue_tolerance": ("FLOAT", {"default": 20.0, "min": 1.0, "max": 90.0, "step": 1.0}),
            "region": ("STRING", {"default": "0,0,1,1"}),
            "skin_contact": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "mark_strength": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.05}),
            "dark_floor": ("FLOAT", {"default": 0.22, "min": 0.0, "max": 0.8, "step": 0.02}),
        }}

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("original_ink", "mark_mask")
    FUNCTION = "extract"
    CATEGORY = "Profile Lineart v4"

    def extract(self, source, **settings):
        result = [original_marks(frame.numpy(), **settings) for frame in source.cpu()]
        return tuple(torch.from_numpy(np.stack(items)) for items in zip(*result))


class AnimeMarkLineart(AnimeOriginalMarks):
    @classmethod
    def INPUT_TYPES(cls):
        schema = super().INPUT_TYPES()
        schema["required"]["outline_width"] = ("FLOAT", {"default": 1.5, "min": 0.5, "max": 3.0, "step": 0.1})
        return schema

    RETURN_NAMES = ("original_color_lines", "mark_region_mask")

    def extract(self, source, **settings):
        result = [outlined_marks(frame.numpy(), **settings) for frame in source.cpu()]
        return tuple(torch.from_numpy(np.stack(items)) for items in zip(*result))


class AnimeColoredMarkLineart(AnimeMarkLineart):
    @classmethod
    def INPUT_TYPES(cls):
        schema = super().INPUT_TYPES()
        schema["required"]["mode"][0].extend(["region_light", "region_sample"])
        schema["required"]["color_mode"] = (["original", "custom"], {
            "default": "original",
            "tooltip": "original 沿用图上的原色。custom 使用独立的轮廓色。",
        })
        schema["required"]["ink_color"] = ("INT", {"default": 0xFFCB6B, "min": 0, "max": 0xFFFFFF})
        schema["optional"] = {
            "color_tolerance": ("FLOAT", {"default": 12.0, "min": 1.0, "max": 35.0, "step": 1.0,
                                          "tooltip": "仅用于 region_sample。值越大，越容易选中接近取样色的像素。"}),
        }
        return schema

    RETURN_NAMES = ("mark_lines", "mark_region_mask")

    def extract(self, source, color_mode, ink_color, **settings):
        return super().extract(source, ink_color=ink_color if color_mode == "custom" else None, **settings)


class AnimeLineartGlow:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "colored_lines": ("IMAGE",), "marks": ("IMAGE",), "mark_mask": ("MASK",),
            "glow_strength": ("FLOAT", {"default": 0.45, "min": 0.0, "max": 2.0, "step": 0.05}),
            "glow_radius": ("FLOAT", {"default": 1.6, "min": 0.3, "max": 8.0, "step": 0.1}),
        }, "optional": {"second_marks": ("IMAGE",), "second_mark_mask": ("MASK",)}}

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "render"
    CATEGORY = "Profile Lineart v4"

    def render(self, colored_lines, marks, mark_mask, second_marks=None, second_mark_mask=None, **settings):
        result = []
        for i, frame in enumerate(colored_lines.cpu()):
            ink = marks[min(i, len(marks) - 1)].cpu().numpy()
            mask = mark_mask[min(i, len(mark_mask) - 1)].cpu().numpy()
            if second_marks is not None and second_mark_mask is not None:
                other_ink = second_marks[min(i, len(second_marks) - 1)].cpu().numpy()
                other_mask = second_mark_mask[min(i, len(second_mark_mask) - 1)].cpu().numpy()
                ink = np.clip(ink * (1 - other_mask[..., None]) + other_ink, 0, 1)
                mask = np.maximum(mask, other_mask)
            result.append(composite_glow(frame.numpy(), ink, mask, **settings))
        return (torch.from_numpy(np.stack(result)),)


NODE_CLASS_MAPPINGS = {"AnimeTonalLineart": AnimeTonalLineart, "AnimeOriginalMarks": AnimeOriginalMarks,
                       "AnimeMarkLineart": AnimeMarkLineart,
                       "AnimeColoredMarkLineart": AnimeColoredMarkLineart,
                       "AnimeLineartGlow": AnimeLineartGlow,
                       "AnimeLineartExtract": AnimeLineartExtract}
NODE_DISPLAY_NAME_MAPPINGS = {"AnimeTonalLineart": "动漫线稿：明暗与双色",
                             "AnimeOriginalMarks": "动漫记号：保留原色",
                             "AnimeMarkLineart": "动漫记号：以原色绘制轮廓线",
                             "AnimeColoredMarkLineart": "记号轮廓配色",
                             "AnimeLineartGlow": "动漫线稿：合成与发光",
                             "AnimeLineartExtract": "从二次元底图提取线条"}
