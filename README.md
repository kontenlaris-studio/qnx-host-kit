# qnx-host-kit

Host-side tooling for **QNX 8.0** development, built for the
**QNX Global Hackathon 2026** (Devpost), category
**Developer Tooling & Host Tools**.

`qnx-host-kit` is a single-file Python 3 tool (standard library only,
no installation, no network) that supports the everyday QNX 8.0
development loop from a Linux host:

| Subcommand | What it does |
|---|---|
| `scaffold` | Generates a ready-to-build QNX 8.0 C project skeleton: a real-time Neutrino app, a `qcc` Makefile, QEMU run script, README and LICENSE. |
| `analyze` | Parses a QNX **slog2**-style text log and reports a severity histogram, top repeated messages, error bursts and a deterministic health verdict (text or JSON). |
| `check` | Validates a QNX project directory against a pass/warn/fail submission-readiness checklist (build files, `qcc` flags, QNX APIs, license, docs, QEMU helper). |

## Quick start (no installation)

Requires only Python 3.8+ on the host:

```sh
python3 qnxhostkit.py --help
python3 qnxhostkit.py scaffold my_qnx_app
python3 qnxhostkit.py analyze examples/sample.slog2
python3 qnxhostkit.py check my_qnx_app
```

## scaffold — a real QNX 8.0 starter project

```sh
python3 qnxhostkit.py scaffold my_qnx_app
```

creates:

```
my_qnx_app/
├── src/main.c          # real-time QNX Neutrino application
├── Makefile            # qcc targets: x86_64 and aarch64le
├── README.md           # build/run instructions (incl. QEMU)
├── qemu/run-qemu.sh    # boots a QNX target image under QEMU
├── LICENSE             # MIT
└── .gitignore
```

The generated application uses genuine QNX Neutrino APIs —
`ChannelCreate`, `ConnectAttach`, `MsgReceive`, a kernel timer
delivering periodic pulses via `SIGEV_PULSE`, and
`clock_gettime(CLOCK_MONOTONIC)` — to measure period jitter of a 10 ms
real-time loop and print a jitter report.

### Building and running the generated project

You need the **QNX Software Development Platform (SDP) 8.0**, free for
non-commercial use via QNX Everywhere:

```sh
source ~/qnx800/qnxsdp-env.sh   # adjust to your SDP install path
cd my_qnx_app
make                # -> build/x86_64/my_qnx_app
make aarch64le      # -> build/aarch64le/my_qnx_app
```

Run it on QNX hardware by copying the binary to the target, or boot a
QNX 8.0 x86_64 image (built from the SDP's QEMU BSP, with the app
included) under QEMU:

```sh
./qemu/run-qemu.sh build/qnx-x86_64.img
```

See the generated project's own README for the full walkthrough.

## analyze — slog2 log health reports

```sh
python3 qnxhostkit.py analyze examples/sample.slog2
python3 qnxhostkit.py analyze device.log --json --top 10
```

The parser accepts slog2-style lines
(`timestamp hostname component[pid]: severity message`, with numeric
slog2 severities 0–7 or severity names, ISO or syslog timestamps).
Severities 0–2 (emergency/critical/error) count as error-severity.

For the bundled sample log the report is exactly:

- **128 total lines**, all parsed
- **16 error-severity lines → 12.5% error rate**
- **longest error burst: 8** consecutive error lines
- **health verdict: ATTENTION**

Health verdicts are deterministic, derived from the error rate
(0% → `HEALTHY`, ≤5% → `MINOR`, ≤20% → `ATTENTION`, above → `CRITICAL`;
an unbroken error burst of 10+ lines escalates to `CRITICAL`).

## check — submission-readiness checklist

```sh
python3 qnxhostkit.py check my_qnx_app          # text checklist
python3 qnxhostkit.py check my_qnx_app --json   # machine-readable
```

Nine checks: build file present, build invokes `qcc`, `gcc_nto*` target
variants present, C/C++ sources present, QNX Neutrino APIs used,
LICENSE present, README present, README documents QNX build/run with
qcc/QEMU, and a `qemu/run-qemu.sh` helper exists. Exit code is 0 when
nothing fails. A freshly scaffolded project passes all nine checks.

## Selftest

```sh
python3 selftest.py
```

The selftest drives the real CLI and asserts, among other things, the
exact sample-log figures above (128 lines, 16 error lines, 12.5%,
longest burst 8, verdict `ATTENTION`), that `scaffold` produces the
full project layout, and that `check` passes the scaffolded project
9/9 with no warnings or failures.

## How this supports QNX 8.0 development

- **Faster starts:** a correct-by-construction QNX C project with a
  working `qcc` Makefile for both x86_64 and aarch64le targets and a
  QEMU boot helper, instead of a blank directory.
- **Faster debugging:** slog2 logs from a target become a one-command
  health report — severity mix, repeated offenders, error bursts —
  suitable for CI gating (`--json`) as well as eyeballing.
- **Fewer submission mistakes:** the checklist catches the missing
  license, missing QEMU instructions, or non-QNX build setup before
  judges (or teammates) do.

## License

MIT — see `LICENSE`. © 2026 Kontenlaris Studio.

## Demo video

Watch the 2:31 demo (public): https://www.youtube.com/watch?v=jzcTUNwrRXk — scaffold → qcc build → QNX 8.0 QEMU boot → in-guest run → analyze → check, all real output. Live verification logs: see `evidence/`.
