"""Tests for madrac.core.parser — run with pytest or python -m unittest."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import unittest
from madrac.core.parser import parse_video_filename


class TestParseVideoFilename(unittest.TestCase):

    def test_standard_episode(self):
        r = parse_video_filename("The.Mandalorian.S03E05.1080p.WEB-DL.DDP5.1.H.264.mkv")
        self.assertEqual(r["season"], 3)
        self.assertEqual(r["episode"], 5)
        self.assertEqual(r["resolution"], "1080p")
        self.assertEqual(r["source"], "webdl")
        self.assertEqual(r["audio"], "ddp5.1")
        self.assertEqual(r["type"], "episode")
        self.assertEqual(r["confidence"], 0.8)
        self.assertEqual(r["title_clean"], "The Mandalorian")
        self.assertEqual(r["normalization_version"], "parser_v1")

    def test_multi_episode(self):
        r = parse_video_filename("Breaking.Bad.S01E01E02.720p.WEBRip.x264.mkv")
        self.assertEqual(r["season"], 1)
        self.assertEqual(r["episode"], 1)
        self.assertEqual(r["type"], "episode")
        self.assertEqual(r["confidence"], 0.8)

    def test_movie_with_year(self):
        r = parse_video_filename("Interestelar 2014 1080p BluRay x264 DTS.mkv")
        self.assertEqual(r["year"], 2014)
        self.assertEqual(r["resolution"], "1080p")
        self.assertEqual(r["source"], "bluray")
        self.assertEqual(r["codec"], "x264")
        self.assertEqual(r["audio"], "dts")
        self.assertEqual(r["type"], "movie")
        self.assertEqual(r["title_clean"], "Interestelar")

    def test_low_confidence(self):
        r = parse_video_filename("mi_video_casero.mp4")
        self.assertEqual(r["confidence"], 0.0)
        self.assertIsNone(r["season"])
        self.assertIsNone(r["episode"])
        self.assertIsNone(r["resolution"])

    def test_episode_dash_format(self):
        r = parse_video_filename("Kusuriya no Hitorigoto - 21 (1080p) [A1B2C3D4].mkv")
        # Low confidence (< 0.5) → metadata None
        self.assertEqual(r["confidence"], 0.0)
        self.assertIsNone(r["season"])

    def test_release_group_brackets(self):
        r = parse_video_filename("Show.Name.S01E02.1080p.WEB-DL.x264-[SubsPlease].mkv")
        self.assertEqual(r["season"], 1)
        self.assertEqual(r["episode"], 2)
        self.assertEqual(r["release_group"], "SubsPlease")

    def test_anime_format_low_conf(self):
        r = parse_video_filename("[SubsPlease] Shingeki no Kyojin - 10 (1080p).mkv")
        self.assertEqual(r["confidence"], 0.0)

    def test_anime_format_with_source(self):
        r = parse_video_filename("[SubsPlease] Shingeki no Kyojin - 10 (1080p WEB-DL).mkv")
        self.assertEqual(r["release_group"], "SubsPlease")
        self.assertEqual(r["episode"], 10)
        self.assertEqual(r["confidence"], 0.6)

    def test_year_not_mistaken_for_episode(self):
        r = parse_video_filename("Movie.Title.2025.1080p.BluRay.x264.mkv")
        self.assertEqual(r["year"], 2025)
        self.assertEqual(r["type"], "movie")
        self.assertIsNone(r["season"])


if __name__ == "__main__":
    unittest.main()
