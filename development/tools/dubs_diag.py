#!/usr/bin/env python3
"""Diagnóstico: lanza DUBS, chequea health, envía un job, monitorea."""
import subprocess, sys, time, os, threading, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

python_path = r"D:\madrac-dubs\venv\Scripts\python.exe"
src_path = str(Path(python_path).resolve().parent.parent.parent / "src")
env = os.environ.copy()
env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

cmd = [python_path, "-m", "madrac_dubbing", "api", "--port", "5000"]
print("Launching: " + " ".join(cmd))
print("PYTHONPATH: " + src_path)

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

def read_pipe(pipe, label):
    for line in iter(pipe.readline, b""):
        decoded = line.decode("utf-8", errors="replace").rstrip()
        if decoded:
            print("[%s] %s" % (label, decoded))
    pipe.close()

threading.Thread(target=read_pipe, args=(proc.stdout, "OUT"), daemon=True).start()
threading.Thread(target=read_pipe, args=(proc.stderr, "ERR"), daemon=True).start()

import requests

deadline = time.time() + 45
ok = False
while time.time() < deadline:
    if proc.poll() is not None:
        print("DUBS exited early with code %d" % proc.returncode)
        break
    try:
        r = requests.get("http://127.0.0.1:5000/health", timeout=3)
        if r.status_code == 200 and r.json().get("status") == "ok":
            print("=" * 50)
            print("HEALTH CHECK PASSED")
            print("=" * 50)
            ok = True
            break
    except Exception as e:
        pass
    time.sleep(1)

if ok:
    # Submit a job
    payload = {
        "video_path": r"D:\De Noorderlingen (1992) de brief in de bus bezorgen (Alex van Warmerdam).mp4",
        "srt_path": r"D:\De Noorderlingen (1992) de brief in de bus bezorgen (Alex van Warmerdam).srt",
        "output_path": r"D:\_dub_test_output.mkv",
        "config": {"language": "es"},
    }
    print("Submitting job...")
    try:
        r = requests.post("http://127.0.0.1:5000/dubbing", json=payload, timeout=10)
        print("Submit status: %d" % r.status_code)
        print("Submit response: " + r.text)
        data = r.json()
        job_id = data.get("job_id")
        print("Job ID: " + str(job_id))

        if job_id:
            # Poll for a while
            for _ in range(30):
                time.sleep(2)
                if proc.poll() is not None:
                    print("DUBS died during poll (code %d)" % proc.returncode)
                    break
                try:
                    r = requests.get("http://127.0.0.1:5000/dubbing/" + job_id, timeout=5)
                    j = r.json()
                    print("Poll: status=%s pct=%s msg=%s" % (
                        j.get("status"), j.get("progress_pct"), j.get("message", "")[:60]
                    ))
                    if j.get("status") in ("completed", "failed"):
                        print("Job final: %s" % j.get("status"))
                        if j.get("error"):
                            print("Error: " + j.get("error"))
                        break
                except Exception as e:
                    print("Poll error: %s" % e)
                    break
    except Exception as e:
        print("Submit failed: %s" % type(e).__name__)
        import traceback
        traceback.print_exc()

    proc.terminate()
    proc.wait(timeout=5)

# Get remaining stderr
try:
    remaining = proc.stderr.read().decode("utf-8", errors="replace")
    if remaining.strip():
        print("=== REMAINING STDERR ===")
        print(remaining)
except:
    pass

print("Exit: %d" % proc.returncode)
