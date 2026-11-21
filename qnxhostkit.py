#!/usr/bin/env python3
"""qnx-host-kit - host-side tooling for QNX 8.0 development.

A single-file, standard-library-only Linux host tool with three subcommands:

  scaffold  Generate a ready-to-build QNX 8.0 C project skeleton
            (Neutrino IPC + timer-pulse real-time app, qcc Makefile,
            QEMU run script, README, LICENSE).
  analyze   Parse a QNX slog2-style text log and report a severity
            histogram, top repeated messages, error bursts and a
            deterministic health verdict (text or JSON).
  check     Validate a QNX project directory against a pass/warn/fail
            submission-readiness checklist.

No network access, no third-party dependencies, deterministic output.

Usage:
  python3 qnxhostkit.py scaffold <dir> [--name NAME] [--force]
  python3 qnxhostkit.py analyze <logfile> [--json] [--top N]
  python3 qnxhostkit.py check <dir> [--json]
"""

import argparse
import json
import os
import re
import stat
import sys
from collections import Counter

# --------------------------------------------------------------------------
# Severity model (QNX slog2 numbering)
# --------------------------------------------------------------------------
# slog2 severities: 0 emergency, 1 critical, 2 error, 3 warning,
# 4 notice, 5 info, 6 debug_1, 7 debug_2. Lines at severity <= 2 are
# counted as "error-severity" lines.
SEVERITY_NAMES = ["emergency", "critical", "error", "warning",
                  "notice", "info", "debug", "debug2"]
SEVERITY_ALIASES = {
    "emergency": 0, "emerg": 0,
    "critical": 1, "crit": 1, "alert": 1,
    "error": 2, "err": 2,
    "warning": 3, "warn": 3,
    "notice": 4,
    "info": 5, "informational": 5,
    "debug": 6, "debug1": 6,
    "debug2": 7,
}
ERROR_MAX_SEVERITY = 2

# Health verdict bands, based on the error-severity rate. A very long
# unbroken error burst escalates the verdict to CRITICAL on its own.
HEALTH_MINOR_MAX = 5.0        # percent
HEALTH_ATTENTION_MAX = 20.0   # percent
HEALTH_BURST_CRITICAL = 10    # consecutive error lines

# --------------------------------------------------------------------------
# analyze
# --------------------------------------------------------------------------
_ISO_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(.*)$")
_SYSLOG_RE = re.compile(
    r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(.*)$")
# Optional hostname, then component[pid]: severity message
_COMP_RE = re.compile(
    r"^(?:\S+\s+)?(\S+?)(?:\[(\d+)\])?:\s+(\S+)\s+(.*)$")


def _severity_index(token):
    """Map a severity token (slog2 number or name) to 0..7, or None."""
    if token.isdigit():
        value = int(token)
        return value if 0 <= value <= 7 else None
    return SEVERITY_ALIASES.get(token.lower())


def parse_log_line(line):
    """Parse one slog2-style line. Returns a dict or None if unparsed."""
    rest = None
    match = _ISO_RE.match(line) or _SYSLOG_RE.match(line)
    if match:
        rest = match.group(match.lastindex)
    else:
        rest = line
    comp = _COMP_RE.match(rest)
    if not comp:
        return None
    component, _pid, sev_token, message = comp.groups()
    severity = _severity_index(sev_token)
    if severity is None or not message.strip():
        return None
    return {"component": component, "severity": severity,
            "message": message.strip()}


def health_verdict(error_rate_percent, longest_burst):
    """Deterministic health verdict from error rate and longest burst."""
    if longest_burst >= HEALTH_BURST_CRITICAL:
        return "CRITICAL"
    if error_rate_percent <= 0.0:
        return "HEALTHY"
    if error_rate_percent <= HEALTH_MINOR_MAX:
        return "MINOR"
    if error_rate_percent <= HEALTH_ATTENTION_MAX:
        return "ATTENTION"
    return "CRITICAL"


def analyze_log(path, top_n=5):
    """Analyze a slog2-style log file and return a result dict."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()

    total_lines = len(lines)
    parsed = []          # (line_number, entry)
    unparsed = 0
    for number, raw in enumerate(lines, 1):
        entry = parse_log_line(raw)
        if entry is None:
            unparsed += 1
        else:
            parsed.append((number, entry))

    histogram = {name: 0 for name in SEVERITY_NAMES}
    messages = Counter()
    components = Counter()
    for _number, entry in parsed:
        histogram[SEVERITY_NAMES[entry["severity"]]] += 1
        messages[entry["message"]] += 1
        components[entry["component"]] += 1

    error_lines = sum(
        1 for _n, e in parsed if e["severity"] <= ERROR_MAX_SEVERITY)
    error_rate = (round(100.0 * error_lines / total_lines, 2)
                  if total_lines else 0.0)

    # Error bursts: maximal runs of error-severity lines on adjacent
    # line numbers.
    bursts = []
    run_start = None
    run_length = 0
    previous_line = None
    for number, entry in parsed:
        is_error = entry["severity"] <= ERROR_MAX_SEVERITY
        if is_error and run_start is not None and number == previous_line + 1:
            run_length += 1
        elif is_error:
            if run_length >= 2:
                bursts.append({"start_line": run_start, "length": run_length})
            run_start, run_length = number, 1
        else:
            if run_length >= 2:
                bursts.append({"start_line": run_start, "length": run_length})
            run_start, run_length = None, 0
        previous_line = number
    if run_length >= 2:
        bursts.append({"start_line": run_start, "length": run_length})
    longest_burst = max([b["length"] for b in bursts] +
                        [1 if error_lines else 0])

    verdict = health_verdict(error_rate, longest_burst)
    top_messages = [
        {"message": message, "count": count}
        for message, count in sorted(
            messages.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    ]
    if top_messages:
        top_issue = "'%s' x%d" % (top_messages[0]["message"],
                                  top_messages[0]["count"])
    else:
        top_issue = "none"
    summary = ("%s: %d/%d error-severity lines (%.2f%%), longest error "
               "burst %d, top issue: %s"
               % (verdict, error_lines, total_lines, error_rate,
                  longest_burst, top_issue))

    return {
        "file": os.path.basename(path),
        "total_lines": total_lines,
        "parsed_lines": len(parsed),
        "unparsed_lines": unparsed,
        "severity_histogram": histogram,
        "components": dict(sorted(components.items())),
        "error_lines": error_lines,
        "error_rate_percent": error_rate,
        "error_bursts": bursts,
        "longest_error_burst": longest_burst,
        "top_messages": top_messages,
        "health_verdict": verdict,
        "health_summary": summary,
    }


def format_analysis(result):
    out = []
    out.append("Log analysis: %s" % result["file"])
    out.append("  lines: %d total, %d parsed, %d unparsed"
               % (result["total_lines"], result["parsed_lines"],
                  result["unparsed_lines"]))
    out.append("  severity histogram:")
    for name in SEVERITY_NAMES:
        out.append("    %-10s %d" % (name, result["severity_histogram"][name]))
    out.append("  error-severity lines: %d (%.2f%%)"
               % (result["error_lines"], result["error_rate_percent"]))
    out.append("  error bursts (runs of >= 2):")
    if result["error_bursts"]:
        for burst in result["error_bursts"]:
            out.append("    line %d: %d consecutive error lines"
                       % (burst["start_line"], burst["length"]))
    else:
        out.append("    none")
    out.append("  longest error burst: %d" % result["longest_error_burst"])
    out.append("  top repeated messages:")
    for item in result["top_messages"]:
        out.append("    %4d  %s" % (item["count"], item["message"]))
    out.append("  health: %s" % result["health_summary"])
    return "\n".join(out)


# --------------------------------------------------------------------------
# scaffold: generated QNX 8.0 project templates (__NAME__ is substituted)
# --------------------------------------------------------------------------
MAIN_C = r"""/*
 * __NAME__ - a minimal real-time application for QNX Neutrino (QNX 8.0).
 *
 * Demonstrates core QNX IPC and timing primitives:
 *   - ChannelCreate / ConnectAttach / MsgReceive for message passing
 *   - a kernel timer delivering periodic pulses (SIGEV_PULSE)
 *   - clock_gettime(CLOCK_MONOTONIC) based period/jitter measurement
 *
 * The process receives TIMER_PULSE pulses, measures the actual period
 * against the expected period, and prints jitter statistics before
 * exiting cleanly.
 *
 * Build:  make            (x86_64)
 *         make aarch64le  (ARM64)
 */

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/neutrino.h>
#include <sys/siginfo.h>
#include <time.h>

#define TIMER_PULSE_CODE (_PULSE_CODE_MINAVAIL + 1)
#define DEFAULT_PERIOD_NS 10000000LL /* 10 ms */
#define DEFAULT_PULSES 1000

static long long timespec_diff_ns(const struct timespec *a,
                                  const struct timespec *b)
{
    /* returns a - b in nanoseconds */
    return (a->tv_sec - b->tv_sec) * 1000000000LL +
           (a->tv_nsec - b->tv_nsec);
}

int main(int argc, char *argv[])
{
    int chid, coid, timer_id, rcvid;
    long pulses_wanted = DEFAULT_PULSES;
    long long period_ns = DEFAULT_PERIOD_NS;
    long long count = 0, jitter_sum_ns = 0, jitter_max_ns = 0;
    struct sigevent event;
    struct itimerspec itime;
    struct _pulse pulse;
    struct timespec prev, now;

    if (argc > 1) {
        pulses_wanted = strtol(argv[1], NULL, 10);
        if (pulses_wanted <= 0) {
            pulses_wanted = DEFAULT_PULSES;
        }
    }

    chid = ChannelCreate(0);
    if (chid == -1) {
        perror("ChannelCreate");
        return EXIT_FAILURE;
    }

    coid = ConnectAttach(0, 0, chid, _NTO_SIDE_CHANNEL, 0);
    if (coid == -1) {
        perror("ConnectAttach");
        ChannelDestroy(chid);
        return EXIT_FAILURE;
    }

    SIGEV_PULSE_INIT(&event, coid, SIGEV_PULSE_PRIO_INHERIT,
                     TIMER_PULSE_CODE, 0);
    if (timer_create(CLOCK_MONOTONIC, &event, &timer_id) == -1) {
        perror("timer_create");
        ConnectDetach(coid);
        ChannelDestroy(chid);
        return EXIT_FAILURE;
    }

    memset(&itime, 0, sizeof(itime));
    itime.it_value.tv_sec = period_ns / 1000000000LL;
    itime.it_value.tv_nsec = period_ns % 1000000000LL;
    itime.it_interval = itime.it_value;
    if (timer_settime(timer_id, 0, &itime, NULL) == -1) {
        perror("timer_settime");
        timer_delete(timer_id);
        ConnectDetach(coid);
        ChannelDestroy(chid);
        return EXIT_FAILURE;
    }

    printf("__NAME__: waiting for %ld pulses at %lld ns period\n",
           pulses_wanted, period_ns);
    fflush(stdout);

    clock_gettime(CLOCK_MONOTONIC, &prev);
    while (count < pulses_wanted) {
        rcvid = MsgReceive(chid, &pulse, sizeof(pulse), NULL);
        if (rcvid == -1) {
            perror("MsgReceive");
            break;
        }
        if (rcvid == 0 && pulse.code == TIMER_PULSE_CODE) {
            long long actual_ns, jitter_ns;
            clock_gettime(CLOCK_MONOTONIC, &now);
            actual_ns = timespec_diff_ns(&now, &prev);
            prev = now;
            if (count > 0) { /* first period includes setup time */
                jitter_ns = llabs(actual_ns - period_ns);
                jitter_sum_ns += jitter_ns;
                if (jitter_ns > jitter_max_ns) {
                    jitter_max_ns = jitter_ns;
                }
            }
            count++;
        }
    }

    printf("__NAME__: received %lld pulses\n", count);
    if (count > 1) {
        printf("__NAME__: mean jitter %lld ns, max jitter %lld ns\n",
               jitter_sum_ns / (count - 1), jitter_max_ns);
    }

    timer_delete(timer_id);
    ConnectDetach(coid);
    ChannelDestroy(chid);
    return EXIT_SUCCESS;
}
"""

MAKEFILE_LINES = [
    "# __NAME__ - QNX 8.0 build (requires the QNX Software Development",
    "# Platform 8.0; source qnxsdp-env.sh so that qcc is on PATH).",
    "",
    "QCC     ?= qcc",
    "CFLAGS  ?= -Wall -Wextra -O2",
    "SRC     := src/main.c",
    "BUILD   := build",
    "NAME    := __NAME__",
    "",
    ".PHONY: all x86_64 aarch64le clean",
    "",
    "all: x86_64",
    "",
    "x86_64:",
    "\t@mkdir -p $(BUILD)/x86_64",
    "\t$(QCC) -Vgcc_ntox86_64 $(CFLAGS) -o $(BUILD)/x86_64/$(NAME) $(SRC)",
    "",
    "aarch64le:",
    "\t@mkdir -p $(BUILD)/aarch64le",
    "\t$(QCC) -Vgcc_ntoaarch64le $(CFLAGS) -o $(BUILD)/aarch64le/$(NAME) $(SRC)",
    "",
    "clean:",
    "\trm -rf $(BUILD)",
    "",
]

PROJECT_README = r"""# __NAME__

A minimal real-time application for **QNX Neutrino (QNX 8.0)** generated
by qnx-host-kit. It demonstrates core QNX IPC and timing primitives:

- `ChannelCreate` / `ConnectAttach` / `MsgReceive` message passing
- a kernel timer delivering periodic pulses (`SIGEV_PULSE`)
- `clock_gettime(CLOCK_MONOTONIC)` period and jitter measurement

The process receives timer pulses, measures the actual period against
the expected 10 ms period, and prints jitter statistics before exiting.

## Prerequisites

- QNX Software Development Platform (SDP) 8.0 - free for non-commercial
  use via QNX Everywhere. Install it, then load the environment:

  ```sh
  source ~/qnx800/qnxsdp-env.sh   # adjust to your SDP install path
  qcc -V                          # lists the available targets
  ```

## Build

```sh
make                # x86_64 binary  -> build/x86_64/__NAME__
make aarch64le      # ARM64 binary   -> build/aarch64le/__NAME__
make clean
```

The Makefile drives `qcc` with the `gcc_ntox86_64` and
`gcc_ntoaarch64le` target variants.

## Run on hardware

Copy the binary to a QNX 8.0 target (for example with `scp`, or via
Momentics/qconn) and run it there:

```sh
./__NAME__          # 1000 pulses at a 10 ms period
./__NAME__ 100      # optional: number of pulses
```

## Run under QEMU

`qemu/run-qemu.sh` boots a QNX 8.0 x86_64 target image under QEMU:

1. Build a bootable QNX image that contains this application, using the
   x86_64 QEMU BSP from the SDP (build the BSP's IFS image with the
   application added to the image buildfile), or create an image with
   `mkqnximage`. Place the image at `build/qnx-x86_64.img` (or pass its
   path as the first argument).
2. Run:

   ```sh
   ./qemu/run-qemu.sh                 # uses build/qnx-x86_64.img
   ./qemu/run-qemu.sh /path/to.img    # explicit image path
   ```

   The script invokes `qemu-system-x86_64` with the serial console on
   stdio, so the application's jitter report appears in your terminal.

## License

MIT - see `LICENSE`.
"""

RUN_QEMU_SH = r"""#!/bin/sh
# run-qemu.sh - boot a QNX 8.0 x86_64 target image under QEMU.
#
# The image must contain the __NAME__ application (see README.md,
# "Run under QEMU"). Usage:
#   ./qemu/run-qemu.sh [path-to-qnx-image]
# Environment:
#   QEMU_MEM   guest RAM (default: 512M)
set -eu

IMAGE="${1:-build/qnx-x86_64.img}"
MEM="${QEMU_MEM:-512M}"

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    echo "error: qemu-system-x86_64 not found on PATH" >&2
    exit 1
fi

if [ ! -f "$IMAGE" ]; then
    echo "error: QNX target image not found: $IMAGE" >&2
    echo "Build one from the QNX 8.0 x86_64 QEMU BSP (or mkqnximage)" >&2
    echo "with __NAME__ included, then re-run this script." >&2
    exit 1
fi

exec qemu-system-x86_64 \
    -m "$MEM" \
    -drive file="$IMAGE",format=raw,if=ide \
    -serial stdio \
    -display none
"""

GITIGNORE = "build/\n*.o\n__pycache__/\n"

MIT_LICENSE = """MIT License

Copyright (c) 2026 Kontenlaris Studio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _fill(template, name):
    return template.replace("__NAME__", name)


def cmd_scaffold(args):
    name = args.name or os.path.basename(os.path.abspath(args.directory))
    name = re.sub(r"[^A-Za-z0-9_]", "_", name) or "qnx_app"
    dest = args.directory
    if os.path.isdir(dest) and os.listdir(dest) and not args.force:
        print("error: %s exists and is not empty (use --force)" % dest,
              file=sys.stderr)
        return 2
    files = {
        os.path.join("src", "main.c"): _fill(MAIN_C, name),
        "Makefile": _fill("\n".join(MAKEFILE_LINES), name),
        "README.md": _fill(PROJECT_README, name),
        os.path.join("qemu", "run-qemu.sh"): _fill(RUN_QEMU_SH, name),
        "LICENSE": MIT_LICENSE,
        ".gitignore": GITIGNORE,
    }
    created = []
    for relpath, content in sorted(files.items()):
        full = os.path.join(dest, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(content)
        created.append(relpath)
    script = os.path.join(dest, "qemu", "run-qemu.sh")
    os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR |
             stat.S_IXGRP | stat.S_IXOTH)
    print("Scaffolded QNX 8.0 project '%s' in %s:" % (name, dest))
    for relpath in created:
        print("  %s" % relpath.replace(os.sep, "/"))
    print("Next: source qnxsdp-env.sh, then run 'make' inside the project.")
    return 0


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------
QNX_APIS = ["ChannelCreate", "ConnectAttach", "MsgReceive", "MsgSend",
            "MsgSendPulse", "TimerCreate", "timer_create", "name_attach",
            "clock_gettime", "pthread_mutex_init", "procmgr_ability"]
BUILD_FILE_NAMES = ["Makefile", "makefile", "GNUmakefile",
                    "CMakeLists.txt", "meson.build"]
LICENSE_NAMES = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _project_files(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in ("build", ".git", "__pycache__"))
        for filename in sorted(filenames):
            found.append(os.path.relpath(
                os.path.join(dirpath, filename), root))
    return sorted(found)


def check_project(root):
    """Run the submission-readiness checklist against a project dir."""
    files = _project_files(root)
    by_name = {}
    for rel in files:
        by_name.setdefault(os.path.basename(rel), []).append(rel)

    build_file = next((n for n in BUILD_FILE_NAMES if n in by_name), None)
    build_text = _read_text(os.path.join(root, build_file)) if build_file \
        else ""

    sources = [f for f in files
               if os.path.splitext(f)[1] in (".c", ".cc", ".cpp", ".h",
                                             ".hpp")]
    source_text = "\n".join(_read_text(os.path.join(root, f))
                            for f in sources)
    license_file = next((n for n in LICENSE_NAMES if n in by_name), None)
    readme_file = next((n for n in by_name
                        if n.upper().startswith("README")), None)
    readme_text = _read_text(os.path.join(root, readme_file)) \
        if readme_file else ""
    qemu_script = next((f for f in files
                        if os.path.basename(f) == "run-qemu.sh"), None)

    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    if build_file:
        add("build-file-present", "pass", "found %s" % build_file)
    else:
        add("build-file-present", "fail",
            "no Makefile, CMakeLists.txt or meson.build found")

    if not build_file:
        add("uses-qcc", "fail", "no build file to inspect for qcc")
    elif "qcc" in build_text:
        add("uses-qcc", "pass", "%s invokes qcc" % build_file)
    else:
        add("uses-qcc", "warn", "%s does not mention qcc" % build_file)

    if build_file and "gcc_nto" in build_text:
        variants = sorted(set(re.findall(r"gcc_nto\w+", build_text)))
        add("qnx-target-variants", "pass",
            "qcc target variants: %s" % ", ".join(variants))
    else:
        add("qnx-target-variants", "warn",
            "no qcc target variant (gcc_nto*) found in the build file")

    if sources:
        add("c-sources-present", "pass",
            "%d C/C++ source/header file(s)" % len(sources))
    else:
        add("c-sources-present", "fail", "no C/C++ sources found")

    apis_found = [api for api in QNX_APIS if api in source_text]
    if apis_found:
        add("qnx-neutrino-apis", "pass",
            "QNX APIs used: %s" % ", ".join(apis_found))
    else:
        add("qnx-neutrino-apis", "warn",
            "no QNX Neutrino APIs detected in the sources")

    if license_file:
        add("license-present", "pass", "found %s" % license_file)
    else:
        add("license-present", "fail", "no LICENSE/COPYING file found")

    if readme_file:
        add("readme-present", "pass", "found %s" % readme_file)
    else:
        add("readme-present", "fail", "no README file found")

    lowered = readme_text.lower()
    if readme_file and "qnx" in lowered and ("qemu" in lowered or
                                             "qcc" in lowered):
        add("readme-documents-qnx", "pass",
            "README documents QNX build/run (qcc/QEMU)")
    elif readme_file:
        add("readme-documents-qnx", "warn",
            "README does not mention QNX with qcc or QEMU instructions")
    else:
        add("readme-documents-qnx", "warn", "no README to inspect")

    if qemu_script:
        add("qemu-run-script", "pass", "found %s" % qemu_script)
    else:
        add("qemu-run-script", "warn",
            "no qemu/run-qemu.sh helper found")

    summary = {"pass": 0, "warn": 0, "fail": 0}
    for item in checks:
        summary[item["status"]] += 1
    return {
        "project": os.path.basename(os.path.abspath(root)),
        "checks": checks,
        "summary": summary,
        "ready": summary["fail"] == 0,
    }


def format_check(result):
    marks = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    out = ["Project check: %s" % result["project"]]
    for item in result["checks"]:
        out.append("  [%s] %-22s %s" % (marks[item["status"]],
                                        item["check"], item["detail"]))
    out.append("  summary: %d pass, %d warn, %d fail -> %s"
               % (result["summary"]["pass"], result["summary"]["warn"],
                  result["summary"]["fail"],
                  "READY" if result["ready"] else "NOT READY"))
    return "\n".join(out)


def cmd_check(args):
    if not os.path.isdir(args.directory):
        print("error: not a directory: %s" % args.directory, file=sys.stderr)
        return 2
    result = check_project(args.directory)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_check(result))
    return 0 if result["ready"] else 1


def cmd_analyze(args):
    if not os.path.isfile(args.logfile):
        print("error: no such file: %s" % args.logfile, file=sys.stderr)
        return 2
    result = analyze_log(args.logfile, top_n=args.top)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_analysis(result))
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="qnxhostkit",
        description="Host-side tooling for QNX 8.0 development: scaffold "
                    "QNX C projects, analyze slog2 logs, and check "
                    "submission readiness.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scaffold = sub.add_parser(
        "scaffold", help="generate a ready-to-build QNX 8.0 C project")
    p_scaffold.add_argument("directory", help="target directory to create")
    p_scaffold.add_argument("--name",
                            help="project name (default: directory name)")
    p_scaffold.add_argument("--force", action="store_true",
                            help="write into a non-empty directory")
    p_scaffold.set_defaults(func=cmd_scaffold)

    p_analyze = sub.add_parser(
        "analyze", help="analyze a QNX slog2-style text log")
    p_analyze.add_argument("logfile", help="path to the log file")
    p_analyze.add_argument("--json", action="store_true",
                           help="emit JSON instead of text")
    p_analyze.add_argument("--top", type=int, default=5,
                           help="number of top repeated messages (default 5)")
    p_analyze.set_defaults(func=cmd_analyze)

    p_check = sub.add_parser(
        "check", help="validate a QNX project directory")
    p_check.add_argument("directory", help="project directory to validate")
    p_check.add_argument("--json", action="store_true",
                         help="emit JSON instead of text")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
