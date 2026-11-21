# QNX SDP 8.0 — Feasibility & Setup Plan

For: QNX Global Hackathon 2026 (Devpost, submission deadline **15 Dec 2026 14:00 ET**).
Researched 21 Nov 2026 from official QNX sources + live checks on this VM. Nothing was
downloaded, installed, or registered during this research.

**Bottom line:** Feasible. The only hard prerequisite is a free myQNX account with an
email-only signup (no payment, no ID/KYC, no phone verification found anywhere in the
official flow). Two VM risks to manage: no KVM (QEMU runs in pure emulation) and low
free RAM headroom — both are workable, especially on the host-tool route. Disk is fine
as long as everything is installed under `/home` (see §3).

---

## 1) Getting QNX SDP 8.0 free (QNX Everywhere)

QNX Everywhere is BlackBerry QNX's program giving anyone a free QNX SDP 8.0 license
for **non-commercial** use (hobbyists, students, open-source developers). The license
is the *QNX Development License — Non-Commercial (QDL) for SDP 8.0*. Note: the
hackathon is run by BlackBerry QNX itself and its official QSTI-for-QEMU guide tells
participants to get exactly this free license — so this is the sanctioned path, but
the entrant should still read the QDL terms once at acceptance time.

Exact steps (from the official QNX Everywhere introduction and getqnx page):

1. **Create a myQNX account** — REQUIRED. At qnx.com → Sign In → New Member:
   email address + password (docs note: password alphanumeric characters), then
   profile information, then activate via a **confirmation key sent by email**
   (click the activation link or enter the key). That is the whole verification:
   email only.
2. **Request + accept the license** — While signed in, open
   https://www.qnx.com/getqnx and accept the non-commercial license terms; the free
   license is issued to your account.
3. **Deploy the license** — In the myQNX License Manager, **accept and deploy** the
   license to your account. This step is mandatory: the QNX Software Center will
   refuse to install SDP 8.0 until a deployed license exists.
4. **Download QNX Software Center (QSC)** for **Linux hosts** from myQNX downloads
   (~100 MB installer, a `.run` file) and install it (lands in `~/qnx/qnxsoftwarecenter`
   or similar).
5. **Install SDP 8.0 via QSC** — Sign in to QSC with the myQNX credentials →
   Add Installation → QNX SDP 8.0 → install into e.g. `~/qnx800`.
6. **Install the QEMU quickstart package** in QSC:
   `com.qnx.qnx800.quickstart.qemu` (under Available → QNX Software Development
   Platform → Reference Images; current version 0.5.0 for SDP 8.0.5, Sep 2026 —
   deselect "Show Only Latest Version" in QSC if it doesn't appear).

Headless alternative (useful on this VM): QSC ships a CLI,
`qnxsoftwarecenter_clt`, which can sync license keys, activate them, and install the
baseline non-interactively (`-myqnx.user`, `-myqnx.password`, `-syncLicenseKeys`,
`-activateAll`, `-installBaseline com.qnx.qnx800 -destination <dir>`). Caution from
community guides: the password passed on that command line is recorded in cleartext
in QSC logs under `~/.qnx` — never share those logs, and prefer the interactive
sign-in where practical.

**Hard-stop check (payment / KYC / phone): NONE found.** No source — official docs,
the getqnx page, or community walkthroughs of this exact flow — mentions payment,
government ID, or phone/SMS verification. Only an email confirmation key.

## 2) Running QNX 8.0 in QEMU on Linux x86_64

There **is** an official path: the **Quick Start Target Image (QSTI) for QEMU**
(QNX documentation, "QSTI for QEMU Guide"). It officially supports **Ubuntu 22.04 or
24.04 hosts** — this VM is Ubuntu 24.04, so it matches.

Official host packages for Ubuntu 24.04 (per the QSTI guide):

```bash
sudo apt install qemu-system qemu-utils qemu-user qemu-user-binfmt \
  qemu-block-extra libvirt-daemon-system libvirt-clients libguestfs-tools bridge-utils
```

(QNX recommends QEMU 10 and the guide includes build-from-source steps; the distro
package is the pragmatic first try, with the source build as fallback.)

Get and launch the image:

```bash
# in QSC, install com.qnx.qnx800.quickstart.qemu  (files land in ~/qnx800/images/qemu)
cd ~/qnx800/images/qemu
./unpack_qemu_image.sh            # unpacks the split qnx_sdp8.0_qemu_quickstart_*.tar.gz parts
cd ~/qnx800 && source qnxsdp-env.sh
cd images/qemu/qemu
mkqnximage --run                  # defaults: 8 vCPUs, 4 GB RAM, 720p, no Vulkan
```

On this VM the defaults must be scaled down (see §3): fewer vCPUs and ~2 GB RAM.

For custom images, the classic low-level route also works: build an IFS with `mkifs`
and boot it directly, e.g. (from the official QNX blog series):

```bash
mkifs image.build image.ifs
qemu-system-x86_64 -cpu max -smp 1 -display none -kernel image.ifs -serial stdio
```

Cross toolchain (qcc) basics — all of this ships inside SDP 8.0:

```bash
source ~/qnx800/qnxsdp-env.sh     # sets QNX_HOST, QNX_TARGET, PATH
qcc -V                            # list targets (gcc_ntox86_64, gcc_ntoaarch64le, ...)
qcc -Vgcc_ntox86_64 -o hello hello.c        # build for the QEMU x86_64 target
qcc -Vgcc_ntoaarch64le -o hello hello.c     # build for ARM64 targets
```

SDP 8.0's toolchain is GCC 12-based with C++20 (plus Clang drivers such as
`ntox86_64-clang`, Rust and Python support). QNX recursive makefiles and CMake
projects are both supported; a VS Code "QNX Toolkit" extension exists but is
optional — everything needed works from the shell.

## 3) This VM's readiness (measured 21 Nov 2026, read-only checks)

| Check | Result | Verdict |
|---|---|---|
| OS / arch | Ubuntu 24.04, x86_64 (host CPU: AMD EPYC 9D25) | ✅ Matches QSTI host requirement (Ubuntu 22.04/24.04) |
| `qemu-system-x86_64` | **Not installed** (no qemu binaries on PATH) | ⚠️ Install via apt (package ~49 MB + deps) |
| KVM (`/dev/kvm`) | **Absent** | ⚠️ QEMU will run under TCG pure emulation — noticeably slower; fine for small targets/demos, painful for long in-VM builds |
| CPU | 4 vCPUs visible (`nproc`); shared/throttled allocation | ⚠️ QSTI default (8 vCPUs) must be reduced to 1–2 |
| RAM | ~8 GB total; only ~1.8 GB "available" at check time (fluctuates with other load) | ⚠️ Tightest constraint. QSTI default is 4 GB for the VM alone — run QEMU with ~1–2 GB and keep host load low during runs |
| Disk — `/home` volume | **150 GB total, 143 GB free**; `~/workspace` currently 7.2 GB | ✅ Plenty — install SDP + images here |
| Disk — root overlay `/` | 7.5 GB total, 7.1 GB free | ⛔ Do NOT install SDP/QEMU images under `/opt`, `/usr/local`, etc. |
| Host compilers | gcc 13.3.0, Python 3.12.3 | ✅ Fine for a host tool (qcc itself comes with the SDP) |

Net assessment: the full QNX-in-QEMU route is possible but will be slow (no KVM,
tight RAM). A **host tool** (Linux program that builds/tests/analyzes QNX-targeted
software, cross-compiling with qcc and optionally smoke-booting QEMU briefly) keeps
most work on the fast host side and only touches QEMU for verification — the safer
plan on this hardware.

## 4) Ordered setup plan (with sizes & user-action points)

Estimated downloads: QSC installer ~100 MB; SDP 8.0 several GB download,
~3.5–6.4 GB on disk (installer lists ~6.4 GB installed size; one measured install
took 3.5 GB — a custom package selection in QSC can trim this); QSTI-for-QEMU
package size not officially stated, estimate ~1–3 GB. Total worst case ≈ 10 GB —
fits easily in the 143 GB free on `/home`.

1. **👤 USER ACTION (only mandatory personal step):** create the myQNX account at
   qnx.com (Sign In → New Member) with kontenlaris.studio@gmail.com, activate via
   the email confirmation key, then open https://www.qnx.com/getqnx, accept the
   non-commercial license, and deploy it in the myQNX License Manager.
   *(The password must be set by the user on QNX's own page; nobody else can do
   this step. Everything below can be done by the agent afterwards, with the
   credentials supplied through the secure vault.)*
2. Agent: `sudo apt install` the QEMU package set from §2.
3. Agent: download + install QNX Software Center (Linux hosts, ~100 MB) under
   `~/qnx/`.
4. Agent: sign in to QSC, install **QNX SDP 8.0** into `~/qnx800` (on the `/home`
   volume), plus package `com.qnx.qnx800.quickstart.qemu`.
5. Agent: verify toolchain — `source ~/qnx800/qnxsdp-env.sh && qcc -V` and
   cross-compile a hello-world for `gcc_ntox86_64`.
6. Agent: unpack the QSTI and do a scaled-down smoke boot
   (`mkqnximage --run` with reduced vCPU/RAM, or the direct `qemu-system-x86_64
   -kernel … -serial stdio` route), confirm a QNX shell prompt appears despite
   TCG emulation.
7. Build the actual hackathon project against the verified toolchain; use QEMU
   runs sparingly (short smoke tests) given the RAM/KVM limits.
8. Before the deadline (15 Dec 2026 14:00 ET): public repo + build/run
   instructions + <3 min public YouTube demo + Devpost submission.
   **👤 USER ACTION:** the Devpost submission itself is filed from the user's
   Devpost account (agent can prepare everything up to the final submit click,
   per standing practice).

## Sources

- QNX Everywhere introduction (official): https://www.qnx.com/developers/docs/qnxeverywhere/introduction.html
- Free license entry point: https://www.qnx.com/getqnx
- Create your myQNX account (official QSC guide): http://www.qnx.com/developers/docs/qsc/com.qnx.doc.qsc.user_guide/topic/create_myqnx.html
- QSTI for QEMU guide — about: https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/about.html
- QSTI for QEMU guide — getting started (image + `mkqnximage --run`): https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/getting_started.html
- QNX Everywhere release notes (QSTI QEMU package name/version): https://www.qnx.com/developers/docs/qnxeverywhere/rel_notes.html
- QNX Everywhere overview/FAQ: https://qnx.software/en/developers/get-started/qnx-everywhere
- Hackathon walkthrough with measured sizes (dev.to, written for this hackathon): https://dev.to/adedayoke/run-qnx-80-on-windows-with-wsl2-and-capture-your-first-kernel-trace-5ekg
- QNX blog, custom image + direct QEMU boot: https://qnx.software/en/blog/2026/qnxe-ftbu-2
