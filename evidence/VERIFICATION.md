# Live Verification — QNX SDP 8.0 (21 Nov 2026, WIB)

Environment: Linux VM (Ubuntu 24.04, no KVM — QEMU TCG emulation), QNX SDP 8.0
installed via QNX Software Center 2.0.4 CLI with a non-commercial
QNX Everywhere license (obtained and deployed in myQNX License Manager).

## Steps verified end-to-end
1. License sync + activation via `qnxsoftwarecenter_clt` — SDP 8.0 license activated.
2. Baseline install: `com.qnx.qnx800` → `~/qnx800` (3.6 GB) after `-mirror`.
3. `qcc -V` lists targets `gcc_ntox86_64` and `gcc_ntoaarch64le` (GCC 12.2.0), license valid.
4. Scaffold compile: `qnxhostkit.py scaffold` project built with its Makefile:
   `qcc -Vgcc_ntox86_64 -Wall -Wextra -O2 -o build/x86_64/demo_app src/main.c`
   → ELF 64-bit x86-64, interpreter `/usr/lib/ldqnx-64.so.2` (genuine QNX binary).
5. QEMU image built with the SDP's own `mkqnximage` (output/ifs.bin + disk-qemu).
6. Boot (QEMU 8.2.2, `-cpu max`, `-kernel output/ifs.bin`, virtio-net + virtio-rng):
   serial log shows `Startup complete` and
   `QNX noname 8.0.0 2026/10/30-09:10:05EDT x86pc x86_64` (see qemu-boot-serial.log).
   Note: booting via BIOS from the disk image stalls at the IFS loader under TCG;
   the official runimage path (`-kernel ifs.bin`, `-cpu max`) boots cleanly.
7. In-guest shell over serial console: `uname -a` →
   `QNX noname 8.0.0 2026/10/30-09:10:05EDT x86pc x86_64`.
8. Scaffold binary transferred into the guest via curl (guest vtnet0, DHCP 10.0.2.15)
   and executed (see demo-app-run.log):
   `demo_app: received 1000 pulses`, `mean jitter 160395 ns, max jitter 11364742 ns`,
   exit code 0. (High max jitter is expected under TCG emulation without KVM.)

Known wart: sshd in the reference image crashed at startup in this environment
("Memory fault (core dumped)" after "Starting sshd"); the serial console was used
instead. Not a defect of qnx-host-kit.
