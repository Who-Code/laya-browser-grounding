"""Resource safety for a 16 GB Mac: measure RAM pressure, swap and free disk, and decide when to stop.

Why this exists: MLX keeps freed GPU buffers in a cache whose default limit on a 16 GB Mac is ~15 GB. Together with local LLMs,
Chrome and normal apps this pushed macOS into heavy swapping; swap files live on the system disk, and with only ~26 GB free the
disk filled up and the machine froze. This module makes that situation visible early and lets the demo stop itself first."""
from __future__ import annotations
import re, shutil, subprocess

# Stop the automation before the system does. Tunable via environment variables in server.py.
LIMITS = {"min_disk_free_gb": 15.0, "warn_disk_free_gb": 30.0, "max_swap_gb": 3.0, "warn_swap_gb": 1.5, "min_mem_available_pct": 12.0}


def _sysctl(name: str) -> str:
    try: return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=2).stdout.strip()
    except Exception: return ""


def snapshot() -> dict:
    swap = _sysctl("vm.swapusage"); m = re.search(r"used = ([\d.]+)([MG])", swap)
    swap_gb = (float(m.group(1)) / (1024 if m.group(2) == "M" else 1)) if m else 0.0
    lvl = _sysctl("kern.memorystatus_level")                  # percent of memory still available to apps (macOS)
    disk = shutil.disk_usage("/System/Volumes/Data" if shutil.os.path.exists("/System/Volumes/Data") else "/")
    return {"disk_free_gb": round(disk.free / 2**30, 1), "swap_used_gb": round(swap_gb, 2), "mem_available_pct": float(lvl) if lvl else None}


def assess(s: dict | None = None, limits: dict = LIMITS) -> tuple[str, list[str]]:
    """-> ('ok' | 'warn' | 'stop', reasons)"""
    s = s or snapshot(); stop, warn = [], []
    if s["disk_free_gb"] < limits["min_disk_free_gb"]: stop.append(f"only {s['disk_free_gb']} GB disk free (swap needs room)")
    elif s["disk_free_gb"] < limits["warn_disk_free_gb"]: warn.append(f"disk is nearly full: {s['disk_free_gb']} GB free")
    if s["swap_used_gb"] > limits["max_swap_gb"]: stop.append(f"{s['swap_used_gb']} GB swap in use")
    elif s["swap_used_gb"] > limits["warn_swap_gb"]: warn.append(f"{s['swap_used_gb']} GB swap in use")
    if s["mem_available_pct"] is not None and s["mem_available_pct"] < limits["min_mem_available_pct"]: stop.append(f"memory available {s['mem_available_pct']:.0f}%")
    return ("stop" if stop else "warn" if warn else "ok"), stop + warn


def preflight(force: bool = False) -> bool:
    """Call once before loading models. Prints a summary; returns False if starting would be unsafe."""
    s = snapshot(); level, why = assess(s)
    print(f"[guard] disk free {s['disk_free_gb']} GB | swap used {s['swap_used_gb']} GB | memory available {s['mem_available_pct']}% -> {level.upper()}")
    for w in why: print(f"[guard]   - {w}")
    if level == "stop" and not force:
        print("[guard] refusing to start. Free disk space / quit heavy apps (Ollama models, simulators), or pass --force."); return False
    return True
