"""Wrap macOS networkQuality CLI tool for speed tests."""
import json
import subprocess


def start_test():
    """Start a networkQuality test, return Popen handle (caller can .terminate())."""
    return subprocess.Popen(
        ["networkQuality", "-c"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def parse_output(stdout_text):
    """Parse networkQuality JSON output, return result dict or None."""
    if not stdout_text:
        return None
    try:
        data = json.loads(stdout_text)
    except json.JSONDecodeError:
        return None
    return {
        "dl_bps": _num(data.get("dl_throughput")),
        "ul_bps": _num(data.get("ul_throughput")),
        "base_rtt_ms": _num(data.get("base_rtt")),
        "responsiveness_rpm": _num(data.get("responsiveness")),
        "raw": data,
    }


def run_test(timeout=90):
    """Blocking wrapper — start, wait, parse. Returns dict or None."""
    proc = start_test()
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return None
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return parse_output(out)


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
