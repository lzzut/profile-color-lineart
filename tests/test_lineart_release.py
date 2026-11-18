import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from custom_nodes.profile_lineart_style import original_marks, outlined_marks
from custom_nodes.profile_lineart_style.image_input import edge_lineart, extract_edges


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def practice_rgb():
    with Image.open(EXAMPLES / "profile_lineart_practice.png") as transparent:
        white = Image.new("RGBA", transparent.size, "white")
        return np.asarray(Image.alpha_composite(white, transparent).convert("RGB"))


class ReleaseTests(unittest.TestCase):
    def test_standard_illustration_keeps_the_original_edges(self):
        source = practice_rgb().astype(np.float32) / 255
        expected = edge_lineart(source, 0.5)
        lines, _ = extract_edges(source, detail=0.5, contrast_recovery=True)
        np.testing.assert_array_equal(lines, expected)

    def test_contrast_recovery_finds_boundaries_in_low_contrast_illustration(self):
        rgb = practice_rgb().astype(np.float32)
        source = np.rint(128 + 0.052 * (rgb - 128)) / 255
        with self.assertRaisesRegex(ValueError, "没有检测到线条"):
            extract_edges(source, detail=0.5, contrast_recovery=False)
        lines, _ = extract_edges(source, detail=0.5, contrast_recovery=True)
        self.assertGreater(np.count_nonzero(lines >= 32 / 255), 1000)
        self.assertGreater(np.count_nonzero(lines[300:510, 100:350]), 100)
        self.assertEqual(np.count_nonzero(lines[:100]), 0)

    def test_blank_canvas_gives_a_clear_error_even_with_recovery(self):
        source = np.ones((128, 128, 3), dtype=np.float32)
        with self.assertRaisesRegex(ValueError, "二次元底图"):
            extract_edges(source, detail=0.5, contrast_recovery=True)

    def test_sampling_finds_each_pale_mark_without_selecting_the_other_region(self):
        with Image.open(EXAMPLES / "profile_lineart_pale_marks.png") as sample:
            source = np.asarray(sample, dtype=np.float32) / 255
        for region, color, x0, x1 in (
            ("0.13,0.35,0.42,0.63", 0x989898, 108, 350),
            ("0.59,0.35,0.87,0.63", 0xDACB9C, 490, 724),
        ):
            with self.subTest(color=color):
                settings = {"target_color": color, "region": region}
                _, previous = original_marks(source, mode="region_color", **settings)
                self.assertEqual(previous.sum(), 0)
                outline, mask = outlined_marks(source, mode="region_sample", **settings)
                ys, xs = np.where(mask > 0)
                self.assertGreater(len(xs), 4000)
                self.assertTrue(((xs >= x0) & (xs < x1) & (ys >= 291) & (ys < 525)).all())
                visible = outline.max(axis=-1) >= 32 / 255
                self.assertGreater(np.count_nonzero(visible), 1000)
                self.assertGreater(np.count_nonzero((mask > 0) & ~visible), 1000)
                full_color = (mask > 0) & (outline.max(axis=-1) == source.max(axis=-1))
                self.assertGreater(np.count_nonzero(full_color), 300)
                np.testing.assert_array_equal(outline[full_color], source[full_color])


if __name__ == "__main__":
    unittest.main()
