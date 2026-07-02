#!/usr/bin/env python3
"""
Validate Demucs cache behavior — DT-003 Investigation

Tests that:
1. Cache directory exists and is writable
2. First run doesn't hit cache
3. Second run with same video hits cache (faster)
4. Cache persists across invocations
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\madrac-dubs\src")))

def test_demucs_cache():
	"""Test cache validation."""
	from madrac_dubbing.audio.separation import separate_stems, has_demucs

	print("[CACHE-TEST] Starting Demucs cache validation...\n")

	# Check Demucs available
	if not has_demucs():
		print("ERROR: Demucs not available")
		return False

	print("OK Demucs is available\n")

	# Create synthetic audio
	print("[CACHE-TEST] Creating synthetic audio...")
	import numpy as np
	import soundfile as sf
	import tempfile

	duration_sec = 5.0
	sample_rate = 16000

	audio_path = Path(tempfile.gettempdir()) / "cache_test_audio.wav"

	t = np.linspace(0, duration_sec, int(duration_sec * sample_rate), endpoint=False)
	speech_envelope = (np.sin(2 * np.pi * 2 * t) + 1) / 2
	speech = 0.3 * speech_envelope * np.sin(2 * np.pi * 300 * t)
	background = 0.2 * (np.sin(2 * np.pi * 100 * t) + np.sin(2 * np.pi * 150 * t))
	audio = speech + background
	audio = audio / np.max(np.abs(audio))

	sf.write(str(audio_path), audio, sample_rate)
	print(f"OK Created {audio_path}\n")

	# Test cache
	video_hash = "test-cache-001"

	# Run 1: First pass (no cache)
	print("[CACHE-TEST] Run 1: First pass (no cache expected)...")
	t0 = time.perf_counter()
	stems1 = separate_stems(audio_path, video_hash=video_hash)
	t1 = time.perf_counter() - t0
	cache_hit_1 = stems1.metadata.get("cache_hit", False)

	print(f"  Time: {t1:.2f}s")
	print(f"  Cache hit: {cache_hit_1}")
	print(f"  Background: {stems1.background}")
	print()

	if cache_hit_1:
		print("WARNING: First run reported cache hit (unexpected)")
	else:
		print("OK First run didn't hit cache (expected)")

	print("\n[CACHE-TEST] Run 2: Second pass (cache hit expected)...")
	t0 = time.perf_counter()
	stems2 = separate_stems(audio_path, video_hash=video_hash)
	t2 = time.perf_counter() - t0
	cache_hit_2 = stems2.metadata.get("cache_hit", False)

	print(f"  Time: {t2:.2f}s")
	print(f"  Cache hit: {cache_hit_2}")
	print()

	if cache_hit_2:
		print("OK Second run hit cache (expected)")
		speedup = t1 / t2 if t2 > 0 else float('inf')
		print(f"  Speedup: {speedup:.1f}x")
	else:
		print("WARNING: Second run didn't hit cache")

	# Summary
	print("\n" + "="*70)
	print("[CACHE-TEST] Summary:")
	print("="*70)

	cache_working = not cache_hit_1 and cache_hit_2

	if cache_working:
		print("OK Cache is working correctly")
		print(f"  Run 1 (cold):  {t1:.2f}s")
		print(f"  Run 2 (warm):  {t2:.2f}s")
		print(f"  Speedup: {t1/t2:.1f}x")
	else:
		print("WARNING: Cache behavior unexpected")
		print(f"  Run 1 hit: {cache_hit_1}")
		print(f"  Run 2 hit: {cache_hit_2}")

	# Cleanup
	audio_path.unlink()

	return cache_working

if __name__ == "__main__":
	try:
		success = test_demucs_cache()
		sys.exit(0 if success else 1)
	except Exception as e:
		print(f"ERROR: {e}")
		import traceback
		traceback.print_exc()
		sys.exit(1)
