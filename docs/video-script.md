# Demo Video Script — qnx-host-kit (target runtime: 2:45, hard limit 3:00)

**Format:** screen recording of a Linux terminal (1920×1080, large font), English voiceover.
**Before recording:** source the QNX SDP environment, pre-build nothing, have `~/qnx-apps` empty, and keep the bundled `examples/sample.slog2` ready as the analysis input (deterministic output; a live QEMU boot is shown briefly in Segment 3 using a pre-booted snapshot to stay within the time limit).

---

## Segment 1 — Hook & problem (0:00–0:20)

**On screen:** Title card: "qnx-host-kit — host tooling for QNX 8.0". Cut to a terminal showing a long, raw slog2 log scrolling.

**Narration:**
> "Building for QNX 8.0 is powerful — but getting started means hand-writing boilerplate, and debugging means reading walls of log text like this. qnx-host-kit fixes both. It's one Python file, zero dependencies, with three commands: scaffold, analyze, and check."

## Segment 2 — Scaffold & build (0:20–0:55)

**On screen (terminal, in order):**

```bash
git clone [REPO URL] qnx-host-kit
cd qnx-host-kit
python3 qnxhostkit.py scaffold ~/qnx-apps/hello-qnx --name hello-qnx
ls -R ~/qnx-apps/hello-qnx
cd ~/qnx-apps/hello-qnx && make
```

Show the generated tree, then the `qcc` build line completing.

**Narration:**
> "No install — just clone and run. Scaffold generates a complete QNX 8.0 C project: source that logs through slog2, a qcc Makefile, and QEMU run instructions. One make later, it builds with the real QNX compiler from SDP 8.0."

## Segment 3 — Run in QEMU (0:55–1:20)

**On screen:** Run the QEMU helper (pre-booted snapshot for time), show QNX boot messages and the app starting, then the captured log file appearing:

```bash
./qemu/run-qemu.sh
ls -l logs/
```

**Narration:**
> "The included helper boots the app under QEMU with a QNX 8.0 image and captures the slog2 output to a file. Now — what did that run actually do? Let's ask the log."

## Segment 4 — Analyze the log (1:20–2:05)

**On screen (terminal):**

```bash
cd ~/qnx-host-kit
python3 qnxhostkit.py analyze examples/sample.slog2
```

Scroll slowly through the four output sections: severity histogram → top repeated messages → error bursts → health summary. Highlight the burst line and the verdict with the mouse.

**Narration:**
> "Analyze turns the raw log into answers. A severity histogram shows the shape of the run. Top repeated messages expose a retry loop — eighteen identical timeouts, counted once. Error bursts pinpoint the two seconds where everything went wrong together. And the health summary gives a verdict: in this run, 'attention' — twelve and a half percent errors, with one clear burst to investigate. Same input, same output, every time."

## Segment 5 — Readiness check (2:05–2:35)

**On screen (terminal):**

```bash
python3 qnxhostkit.py check ~/qnx-apps/hello-qnx
```

Show the PASS/WARN list and the final "READY" verdict.

**Narration:**
> "Finally, check reviews a project the way a judge would: build instructions, a qcc Makefile, sources, license, QEMU instructions, no stray build artifacts. It flags what's missing before you submit — here, just a warning that this README still needs its demo video link. Which, after this recording, it will have."

## Segment 6 — Close & codelab pointer (2:35–2:50)

**On screen:** End card with the repo URL and the codelab path: `[REPO URL]` → `docs/codelab.md`. Show the three command names one last time: `scaffold · analyze · check`.

**Narration:**
> "qnx-host-kit: scaffold, analyze, check — host-side tooling that supports real QNX 8.0 development. Want to do everything you just saw, hands-on? The repo includes a full step-by-step codelab that takes you from a bare Linux machine to a running, analyzed QNX application. Link in the description. Thanks for watching."

**[END — total ≈ 2:50]**

---

### Recording notes

- Keep every command typed or pasted exactly as shown; outputs must be the tool's real outputs (the QEMU segment's boot text may vary by SDP image — that is expected and noted in the codelab).
- If the QEMU segment runs long, cut boot footage, not the analyze segment — the log analysis is the centerpiece.
- Upload as a **public** YouTube video, under 3 minutes, and paste its URL into the Devpost submission and the project README.
