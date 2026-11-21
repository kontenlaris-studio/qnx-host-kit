#!/usr/bin/env python3
"""Selftest for qnx-host-kit.

Verifies, using the real CLI in subprocesses:
  1. `scaffold` creates the expected QNX project layout and the
     generated C source uses QNX Neutrino APIs.
  2. `check` passes the scaffolded project with no warnings or failures.
  3. `analyze` on examples/sample.slog2 reproduces the exact known
     figures for that crafted log: 128 total lines, 16 error-severity
     lines, 12.5% error rate, longest error burst of 8, health verdict
     "ATTENTION".
  4. `analyze --json` output is deterministic (two runs identical).

Run:  python3 selftest.py
Exit code 0 means every check passed.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "qnxhostkit.py")
SAMPLE_LOG = os.path.join(HERE, "examples", "sample.slog2")

FAILURES = []


def run_cli(*argv):
    return subprocess.run([sys.executable, TOOL] + list(argv),
                          capture_output=True, text=True)


def expect(condition, label, detail=""):
    status = "ok" if condition else "FAIL"
    print("[%s] %s%s" % (status, label,
                         (" -- " + detail) if (detail and not condition)
                         else ""))
    if not condition:
        FAILURES.append(label)


def test_scaffold_and_check(tmp):
    project = os.path.join(tmp, "demo_app")
    proc = run_cli("scaffold", project)
    expect(proc.returncode == 0, "scaffold exits 0", proc.stderr)

    expected_files = [
        os.path.join("src", "main.c"),
        "Makefile",
        "README.md",
        os.path.join("qemu", "run-qemu.sh"),
        "LICENSE",
        ".gitignore",
    ]
    for rel in expected_files:
        expect(os.path.isfile(os.path.join(project, rel)),
               "scaffold creates %s" % rel.replace(os.sep, "/"))

    with open(os.path.join(project, "src", "main.c"),
              encoding="utf-8") as handle:
        c_source = handle.read()
    for api in ("ChannelCreate", "MsgReceive", "timer_create",
                "clock_gettime"):
        expect(api in c_source, "generated main.c uses %s" % api)

    with open(os.path.join(project, "Makefile"), encoding="utf-8") as fh:
        makefile = fh.read()
    expect("qcc" in makefile and "gcc_ntox86_64" in makefile
           and "gcc_ntoaarch64le" in makefile,
           "generated Makefile drives qcc for x86_64 and aarch64le")

    script = os.path.join(project, "qemu", "run-qemu.sh")
    expect(os.access(script, os.X_OK), "run-qemu.sh is executable")

    proc = run_cli("check", project, "--json")
    expect(proc.returncode == 0, "check exits 0 on scaffolded project",
           proc.stdout + proc.stderr)
    result = json.loads(proc.stdout)
    expect(result["summary"] == {"pass": 9, "warn": 0, "fail": 0},
           "check summary is 9 pass / 0 warn / 0 fail",
           json.dumps(result["summary"]))
    expect(result["ready"] is True, "check reports project READY")


def test_analyze():
    proc = run_cli("analyze", SAMPLE_LOG, "--json")
    expect(proc.returncode == 0, "analyze exits 0", proc.stderr)
    result = json.loads(proc.stdout)

    expect(result["total_lines"] == 128,
           "sample log: exactly 128 total lines",
           "got %s" % result["total_lines"])
    expect(result["parsed_lines"] == 128,
           "sample log: all 128 lines parse",
           "got %s" % result["parsed_lines"])
    expect(result["error_lines"] == 16,
           "sample log: exactly 16 error-severity lines",
           "got %s" % result["error_lines"])
    expect(result["error_rate_percent"] == 12.5,
           "sample log: error rate exactly 12.5%",
           "got %s" % result["error_rate_percent"])
    expect(result["longest_error_burst"] == 8,
           "sample log: longest error burst exactly 8",
           "got %s" % result["longest_error_burst"])
    expect({"start_line": 15, "length": 8} in result["error_bursts"],
           "sample log: burst of 8 starts at line 15",
           json.dumps(result["error_bursts"]))
    expect(result["health_verdict"] == "ATTENTION",
           "sample log: health verdict is ATTENTION",
           "got %s" % result["health_verdict"])
    expect(result["severity_histogram"] == {
        "emergency": 1, "critical": 1, "error": 14, "warning": 11,
        "notice": 18, "info": 65, "debug": 18, "debug2": 0},
        "sample log: exact severity histogram",
        json.dumps(result["severity_histogram"]))
    expect(result["top_messages"][0] ==
           {"message": "Sensor poll complete", "count": 34},
           "sample log: top message is 'Sensor poll complete' x34",
           json.dumps(result["top_messages"][:1]))

    proc2 = run_cli("analyze", SAMPLE_LOG, "--json")
    expect(proc2.stdout == proc.stdout,
           "analyze output is deterministic across runs")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_scaffold_and_check(tmp)
    test_analyze()
    if FAILURES:
        print("\nSELFTEST FAILED: %d check(s) failed" % len(FAILURES))
        return 1
    print("\nSELFTEST PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
