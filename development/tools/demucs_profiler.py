#!/usr/bin/env python3
"""Demucs Performance Profiling - DT-001 Investigation"""

import sys
import time
import argparse
from pathlib import Path
import cProfile
import pstats
import io

sys.path.insert(0, str(Path(r"D:\madrac-dubs\src")))

def profile_demucs_separation(audio_path, duration_sec=60):
	"""Profile Demucs separation with detailed timing."""
	from madrac_dubbing.audio.separation import separate_stems, has_demucs

	audio_path = Path(audio_path)
	if not audio_path.exists():
		print(f"ERROR: Audio file not found: {audio_path}")
		return False

	print(f"[PROFILE] Audio file: {audio_path} ({audio_path.stat().st_size / 1e6:.1f} MB)")

	print("[PROFILE] Checking Demucs availability...")
	t0 = time.perf_counter()
	demucs_available = has_demucs()
	t_check = time.perf_counter() - t0
	print(f"  has_demucs() = {demucs_available} (took {t_check:.3f}s)")

	if not demucs_available:
		print("ERROR: Demucs not available")
		return False

	print("\n[PROFILE] Starting separation profiling...")

	pr = cProfile.Profile()
	video_hash = "test-hash-001"
	t_start = time.perf_counter()

	try:
		pr.enable()
		stems = separate_stems(audio_path, video_hash=video_hash)
		pr.disable()

		t_total = time.perf_counter() - t_start

		print(f"\n[PROFILE] Separation complete!")
		print(f"  Total time: {t_total:.2f}s ({t_total/60:.1f}m)")
		print(f"  Background audio: {stems.background}")
		print(f"  Vocals audio: {stems.vocals}")
		print(f"  Cache hit: {stems.metadata.get('cache_hit', False)}")
		print(f"  Model: {stems.metadata.get('model', 'unknown')}")

		print("\n" + "="*70)
		print("[PROFILE] Top 15 functions (cumulative time):")
		print("="*70)

		s = io.StringIO()
		ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
		ps.print_stats(15)
		print(s.getvalue())

		print("\n" + "="*70)
		print("[PROFILE] Top 10 functions (direct time):")
		print("="*70)

		s = io.StringIO()
		ps = pstats.Stats(pr, stream=s).sort_stats('time')
		ps.print_stats(10)
		print(s.getvalue())

		return True

	except Exception as e:
		print(f"ERROR: {type(e).__name__}: {e}")
		import traceback
		traceback.print_exc()
		return False

def create_synthetic_audio(output_path, duration_sec=10.0, sample_rate=16000):
	"""Create synthetic WAV file for testing."""
	try:
		import numpy as np
		import soundfile as sf

		output_path = Path(output_path)
		output_path.parent.mkdir(parents=True, exist_ok=True)

		t = np.linspace(0, duration_sec, int(duration_sec * sample_rate), endpoint=False)

		speech_envelope = (np.sin(2 * np.pi * 2 * t) + 1) / 2
		speech = 0.3 * speech_envelope * np.sin(2 * np.pi * 300 * t)

		background = 0.2 * (np.sin(2 * np.pi * 100 * t) + np.sin(2 * np.pi * 150 * t))

		audio = speech + background
		audio = audio / np.max(np.abs(audio))

		sf.write(str(output_path), audio, sample_rate)
		print(f"[SYNTHETIC] Created {output_path} ({duration_sec}s)")
		return str(output_path)
	except Exception as e:
		print(f"ERROR: {e}")
		return None

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--audio", type=str)
	parser.add_argument("--duration-sec", type=int, default=60)
	parser.add_argument("--create-synthetic", action="store_true")

	args = parser.parse_args()

	audio_path = args.audio

	if not audio_path:
		if args.create_synthetic:
			print("[PROFILE] Creating synthetic audio...")
			audio_path = create_synthetic_audio("D:\\temp\\synthetic_10s.wav", 10.0)
			if not audio_path:
				sys.exit(1)
		else:
			print("ERROR: Use --audio <path> or --create-synthetic")
			sys.exit(1)

	success = profile_demucs_separation(audio_path, args.duration_sec)
	sys.exit(0 if success else 1)
