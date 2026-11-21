# Devpost Submission Draft — QNX Global Hackathon 2026

> Fill in the two placeholders before submitting: **[REPO URL]** and **[VIDEO URL]**.

---

## Project name

**qnx-host-kit**

## Tagline

**Scaffold, analyze, and readiness-check QNX 8.0 projects** (55 characters)

## Category

**Developer Tooling & Host Tools**

## Built with

- Python 3 (standard library only — no third-party dependencies)
- QNX SDP 8.0 (`qcc`, `slog2`)
- QEMU
- Make

## Description

### The problem

Getting started with QNX 8.0 development has three friction points that have nothing to do with writing your actual application:

1. **Boilerplate.** Every new project needs the same skeleton — a `qcc` Makefile, a source layout, QEMU run instructions — assembled by hand from documentation.
2. **Opaque logs.** QNX's `slog2` logging is powerful, but a captured log is a wall of text. Finding the retry loop, the error burst, or the one component that is actually failing means scrolling and guessing.
3. **Forgotten basics.** Projects get shared or submitted missing a license file, with build artifacts committed, or without run instructions — small omissions that cost reviewers' time and entrants' credibility.

### The solution

**qnx-host-kit** is a single-file, install-free Python 3 host tool (standard library only, runs on any Linux development machine) with three commands:

- **`scaffold`** — generates a complete QNX 8.0 C project skeleton: a `src/main.c` demo application that logs through `slog2`, a `qcc` Makefile, a README with build instructions, and a QEMU launch helper that captures serial and log output to files.
- **`analyze`** — parses QNX slog2-style log files and reports a severity histogram (CRITICAL → DEBUG), the top repeated messages (deduplicated, so retry loops stand out), error bursts (time windows where ERROR/CRITICAL lines cluster), and a plain-language health summary with an OK / ATTENTION / CRITICAL verdict.
- **`check`** — runs a submission-readiness checklist against a project directory: README and build instructions present, Makefile invokes `qcc`, sources and license in place, QEMU run instructions included, no build artifacts committed, demo link present. Every item reports PASS / WARN / FAIL with a final READY or NOT READY verdict.

### How it uses and supports QNX 8.0

qnx-host-kit is a **host tool that supports software targeting QNX 8.0**, in the Developer Tooling & Host Tools category:

- Its generated projects are native QNX 8.0 applications: C code built with the SDP's `qcc`, using the `slog2` logging API, and run under QEMU with a QNX 8.0 image (or on QNX-supported hardware).
- Its log analyzer speaks the slog2 text format, so it works on logs captured from QEMU sessions, from `slog2info` exports, and from real target boards.
- Its readiness checklist encodes the conventions of a well-formed QNX project (qcc build, run instructions, licensing), lowering the barrier for developers publishing QNX 8.0 open-source work.

The tool itself never needs to run on the target: it lives on the developer's Linux host, where the SDP cross-development workflow already happens.

### What was built during the hackathon period

Everything in this project was created new during the QNX Global Hackathon 2026 submission period (from 2 November 2026):

- The `qnxhostkit.py` tool with all three commands (scaffold / analyze / check), written from scratch in dependency-free Python 3.
- The QNX 8.0 project templates embedded in `scaffold` (C source using `slog2`, `qcc` Makefile, QEMU helper script).
- The slog2 log parser and the burst-detection and health-verdict logic in `analyze`.
- The readiness rule set in `check`.
- A step-by-step codelab (`docs/codelab.md`) that takes a reader from a bare Linux host to a built, QEMU-running, log-analyzed, readiness-checked QNX 8.0 application — our entry for the Best Codelab/Tutorial bonus.
- Sample slog2 logs and documentation.

### Try it

```bash
git clone [REPO URL]
cd qnx-host-kit
python3 qnxhostkit.py scaffold ~/hello-qnx --name hello-qnx
python3 qnxhostkit.py analyze examples/sample.slog2
python3 qnxhostkit.py check ~/hello-qnx
```

No installation, no dependencies, no network access required.

## Links

- **Code repository:** [REPO URL]
- **Demo video (< 3 min):** [VIDEO URL]
- **Codelab:** see `docs/codelab.md` in the repository

## License

Open source — see the `LICENSE` file in the repository.
