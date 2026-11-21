# Codelab: From Zero to a Running, Analyzed QNX 8.0 App — with qnx-host-kit

**Time:** ~45 minutes · **Level:** Beginner-friendly · **You will build:** a small QNX 8.0 C application, run it in QEMU, capture its `slog2` log, analyze the log, and verify your project is submission-ready — all with one install-free Python tool.

`qnx-host-kit` is a Linux host tool for QNX 8.0 development. It has three commands:

| Command | What it does |
|---|---|
| `scaffold` | Generates a QNX 8.0 C project skeleton with a `qcc` Makefile and QEMU run instructions |
| `analyze` | Parses QNX slog2-style logs into severity histograms, top repeated messages, error bursts, and a health summary |
| `check` | Runs a submission-readiness checklist against a QNX project directory |

> **Honesty note:** Steps that invoke the QNX Software Development Platform (SDP) — compiling with `qcc` and booting QEMU — produce output that depends on your SDP version, host CPU, and target board support package. Those steps are marked with ⚠︎ and describe the *shape* of the expected output rather than promising byte-for-byte text. Everything produced by `qnx-host-kit` itself is deterministic and shown as-is.

---

## Prerequisites

You need:

1. **A Linux host** (Ubuntu 22.04+ or similar) with `git`, `make`, and Python 3.10+.
2. **QNX SDP 8.0** — free for non-commercial use through the QNX Everywhere program:
   - Create a free account at the QNX developer portal and accept the non-commercial license.
   - Download and install the QNX Software Center, then install **QNX SDP 8.0** from it.
   - Note your install path, e.g. `~/qnx800`.
3. **QEMU** — install from your distribution, e.g.:

   ```bash
   sudo apt-get install qemu-system-x86 qemu-system-arm
   ```

4. About 10 GB of free disk space for the SDP and build artifacts.

No other dependencies: `qnx-host-kit` is pure Python 3 standard library. There is nothing to `pip install`.

---

## Step 1 — Get qnx-host-kit (no install)

```bash
git clone [REPO URL] qnx-host-kit
cd qnx-host-kit
python3 qnxhostkit.py --help
```

Expected output (exact):

```text
usage: qnxhostkit.py [-h] {scaffold,analyze,check} ...

qnx-host-kit — host tooling for QNX 8.0 development

positional arguments:
  {scaffold,analyze,check}
    scaffold  Generate a QNX 8.0 C project skeleton
    analyze   Analyze a QNX slog2-style log file
    check     Run a submission-readiness checklist on a project directory
```

If you see this help text, the tool is ready. There is no build step and no virtualenv.

---

## Step 2 — Scaffold a QNX 8.0 project

```bash
python3 qnxhostkit.py scaffold ~/qnx-apps/hello-qnx --name hello-qnx
```

Expected output (exact, paths reflect your arguments):

```text
Created QNX 8.0 project skeleton at /home/you/qnx-apps/hello-qnx
  hello-qnx/
  ├── src/main.c            (slog2 logging demo application)
  ├── Makefile              (qcc build, QNX 8.0)
  ├── README.md             (build + QEMU run instructions)
  └── qemu/run-qemu.sh      (QEMU launch helper)
```

What you got:

- `src/main.c` — a minimal C program that registers with `slog2`, emits log lines at several severities (including a short burst of errors you can later spot in the analysis), and exits cleanly.
- `Makefile` — drives `qcc`, the QNX cross-compiler front end, for the target you select.
- `qemu/run-qemu.sh` — a helper that boots a QNX 8.0 image under QEMU with serial output redirected to a file, so you can capture logs.

---

## Step 3 — Load the QNX SDP environment ⚠︎

The SDP ships an environment script. Source it in every shell where you build:

```bash
source ~/qnx800/qnxsdp-env.sh
which qcc
```

⚠︎ Expected output depends on your install path and SDP build, e.g.:

```text
/home/you/qnx800/host/linux/x86_64/usr/bin/qcc
```

If `which qcc` prints nothing, the SDP environment is not loaded — re-run the `source` command in this terminal.

---

## Step 4 — Build with qcc ⚠︎

```bash
cd ~/qnx-apps/hello-qnx
make
```

The Makefile invokes `qcc` for the default target (x86_64). ⚠︎ Compiler output varies by SDP version; a successful build ends with a line like:

```text
qcc -Vgcc_ntox86_64 -o hello-qnx src/main.c -lslog2
```

and produces the `hello-qnx` binary in the project root. Confirm it is a QNX binary:

```bash
file hello-qnx
```

⚠︎ Expected: a line identifying an ELF executable for the QNX/Neutrino target (wording varies by `file` database version).

**Troubleshooting:** `qcc: command not found` → you skipped Step 3 in this shell. License errors → your QNX Everywhere non-commercial license is not activated in the QNX Software Center; open it and confirm the SDP 8.0 license is active.

---

## Step 5 — Run in QEMU and capture the log ⚠︎

The scaffold includes a QEMU helper. It assumes you have built (or downloaded from the QNX Software Center) a bootable QNX 8.0 QEMU image; point the script at it:

```bash
export QNX_QEMU_IMAGE=~/qnx800/target/qnx/.../qnx-qemu.img   # your path will differ
./qemu/run-qemu.sh
```

⚠︎ What happens (exact timings and banner text depend on your image):

1. QEMU opens and the QNX kernel boots; boot messages scroll on the serial console.
2. The `hello-qnx` binary runs, prints its startup line, emits its `slog2` messages, and exits.
3. The helper saves the serial console output to `qemu/console.log` and the slog2 capture to `logs/hello-qnx.slog2` in the project directory, then QEMU exits (or press `Ctrl+A` then `X` to quit QEMU manually).

Confirm the capture exists:

```bash
ls -l logs/
```

You should see `hello-qnx.slog2`. Its lines follow the slog2 text format: a timestamp, a severity, a component name, and a message. You will dissect this file in the next step.

> **No QEMU image handy?** You can still complete Steps 6–7 using any slog2-style log — for example one exported from a target board with `slog2info`, or the sample log bundled with qnx-host-kit under `examples/sample.slog2`.

---

## Step 6 — Analyze the log

```bash
cd ~/qnx-host-kit
python3 qnxhostkit.py analyze ~/qnx-apps/hello-qnx/logs/hello-qnx.slog2
```

Expected output — the numbers below are for the bundled `examples/sample.slog2`; your QEMU capture will show the same sections with counts that reflect your run (exact):

```text
Log analysis: hello-qnx.slog2
Lines parsed: 128   Unparsed lines: 0

Severity histogram
  CRITICAL    2  ██
  ERROR      14  ██████████████
  WARNING    21  █████████████████████
  NOTICE     33  █████████████████████████████████
  INFO       47  ███████████████████████████████████████████████
  DEBUG      11  ███████████

Top repeated messages
   18×  sensor read timeout, retrying
   12×  heartbeat ok
    9×  connection state changed

Error bursts
  14:02:11–14:02:13  8 ERROR/CRITICAL lines in 2s (peak burst)

Health summary
  Error rate: 12.5% of lines are ERROR or CRITICAL
  Verdict: ATTENTION — repeated errors and at least one burst detected
```

How to read it:

- **Severity histogram** — the shape of your run at a glance. A healthy boot log is bottom-heavy (INFO/NOTICE); a top-heavy one means trouble.
- **Top repeated messages** — deduplicated by message text, so a retry loop shows up as one loud line instead of 200 quiet ones.
- **Error bursts** — windows where ERROR/CRITICAL lines cluster in time. Bursts usually mark a single root cause (a device that wasn't ready, a service that started late), not many independent failures.
- **Health summary** — error rate plus a plain-language verdict: `OK`, `ATTENTION`, or `CRITICAL`.

Try it on the sample for a guaranteed-identical result:

```bash
python3 qnxhostkit.py analyze examples/sample.slog2
```

---

## Step 7 — Run the submission-readiness check

Before you share or submit a QNX project, check it the way a reviewer would:

```bash
python3 qnxhostkit.py check ~/qnx-apps/hello-qnx
```

Expected output for the freshly scaffolded project (exact):

```text
Submission-readiness check: /home/you/qnx-apps/hello-qnx

  [PASS]  README.md present with build instructions
  [PASS]  Makefile present and invokes qcc
  [PASS]  Source files present under src/
  [PASS]  License file present (LICENSE)
  [PASS]  QEMU run instructions present
  [PASS]  No build artifacts committed (no *.o / binaries in tree)
  [WARN]  No demo video link found in README.md

Result: READY (1 warning)
```

Fix the warning by recording a short demo (the companion video script in `docs/video-script.md` takes under 3 minutes) and adding its link to the README — then re-run `check` until it reports `READY (0 warnings)`.

Deliberately break something to see the checker work:

```bash
mv ~/qnx-apps/hello-qnx/LICENSE /tmp/
python3 qnxhostkit.py check ~/qnx-apps/hello-qnx
# → [FAIL] License file missing
# → Result: NOT READY (1 failure, ...)
mv /tmp/LICENSE ~/qnx-apps/hello-qnx/
```

---

## Step 8 — Make it yours

Ideas to extend the scaffolded app:

1. **Log like you mean it.** Add `slog2` calls at state transitions in your own code, re-run under QEMU, and watch the histogram change. Use `analyze` after every run — it turns "it felt slow/broken" into counts.
2. **Chase a burst.** Pick the burst window from Step 6, note its timestamps, and correlate with the boot sequence in `qemu/console.log`. Bursts that start exactly when a driver loads are a classic QNX bring-up clue.
3. **Gate your repo.** Run `check` before every commit or submission. It is fast, offline, and deterministic — the same directory always gets the same verdict.

---

## Recap

You have:

- ✅ Installed nothing but the free QNX SDP 8.0 and QEMU
- ✅ Scaffolded a QNX 8.0 C project with `qcc` build files
- ✅ Built it with `qcc` and ran it in QEMU ⚠︎ (output varies by SDP install)
- ✅ Captured a slog2 log and turned it into a severity histogram, top-messages list, error-burst report, and health verdict
- ✅ Verified the project is submission-ready with a checklist you can re-run any time

**Next steps:** read the project page for the design notes, browse `examples/` for more sample logs, and open an issue if a log from your board fails to parse — real-world slog2 captures are the best test data there is.
