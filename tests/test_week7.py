import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from turtlebot4_week7.segmentation import pixel_to_world, segment, load_map
from turtlebot4_week7.voice_navigation import (
    parse_command, load_regions, build_guided_prompts, has_navigation_intent,
)
import numpy as np


class SegmentationTests(unittest.TestCase):
    def test_connected_free_components(self):
        image = np.zeros((12, 18), dtype=np.uint8)
        image[1:5, 1:6] = 255
        image[7:11, 12:17] = 255
        labels, components = segment(image, min_area=10)
        self.assertEqual(len(components), 2)
        self.assertNotEqual(labels[2, 2], labels[8, 13])

    def test_pixel_to_world_handles_image_y_flip(self):
        self.assertEqual(pixel_to_world(0, 0, 10, 10, 1.0, [0, 0, 0]), [0.5, 9.5])

    def test_supplied_map_and_goals_are_free(self):
        config, image = load_map(ROOT / 'maps/map.yaml')
        regions, _ = load_regions(ROOT / 'config/regions.yaml')
        self.assertEqual(image.shape, (472, 560))
        for region in regions.values():
            x, y = region['pixel']
            self.assertGreaterEqual(int(image[y, x]), 250, region['id'])


class CommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.aliases = load_regions(ROOT / 'config/regions.yaml')

    def test_single_destination(self):
        self.assertEqual(parse_command('Đi đến khu vực A', self.aliases), ['A'])

    def test_from_to_routes_via_named_origin(self):
        self.assertEqual(parse_command('Di chuyển từ khu vực A đến khu vực B', self.aliases), ['A', 'B'])

    def test_multi_stop(self):
        self.assertEqual(parse_command('Đi qua hành lang C rồi đến khu vực B', self.aliases), ['C', 'B'])

    def test_semantic_alias(self):
        self.assertEqual(parse_command('Đi đến phòng thí nghiệm', self.aliases), ['B'])

    def test_vosk_vietnamese_letter_name_for_region_b(self):
        self.assertEqual(parse_command('Đi đến khu vực bê', self.aliases), ['B'])
        self.assertEqual(parse_command('Đi từ khu vực A đến khu vực bê', self.aliases), ['A', 'B'])

    def test_vosk_misrecognitions_for_guided_a_to_b_command(self):
        self.assertEqual(
            parse_command('đi từ khu vực đa điểm khu vực biệt', self.aliases),
            ['A', 'B'],
        )
        self.assertEqual(
            parse_command('đi từ khu vực iv đến khu vực bị', self.aliases),
            ['A', 'B'],
        )

    def test_observed_vosk_variants_for_region_b(self):
        for transcript in (
            'đi biên khu vực biên',
            'đi đến khu vực biên',
            'đi điểm khu vực đi',
            'đi điểm khu vực nề',
            'đi đến khu vực đề',
            'đi đến khu vực mê',
        ):
            with self.subTest(transcript=transcript):
                self.assertEqual(parse_command(transcript, self.aliases), ['B'])

    def test_unknown_region_rejected(self):
        with self.assertRaises(ValueError):
            parse_command('Đi đến khu vực Z', self.aliases)

    def test_unknown_region_with_longer_guided_prompt_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_command(
                'Đi đến khu vực Z để kiểm tra tên vùng không tồn tại',
                self.aliases,
            )

    def test_noise_without_navigation_intent_is_ignored(self):
        self.assertFalse(has_navigation_intent('sau'))
        self.assertTrue(has_navigation_intent('Đi đến khu vực Z'))

    def test_guided_prompts_include_supported_routes_and_unknown_region_check(self):
        regions, _ = load_regions(ROOT / 'config/regions.yaml')
        prompts = build_guided_prompts(regions)
        self.assertEqual(prompts[0], ('Đi đến khu vực A.', ['A']))
        self.assertIn(('Đi từ khu vực A đến phòng thí nghiệm.', ['A', 'B']), prompts)
        self.assertIsNone(prompts[-1][1])
        self.assertIn('khu vực Z', prompts[-1][0])


if __name__ == '__main__':
    unittest.main()
