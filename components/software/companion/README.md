# Companion Computer — QRB2210 RT Linux

Yocto (Scarthgap) build for the Arduino Uno Q companion computer (Qualcomm QRB2210, quad Cortex-A53 @ 2.0 GHz, 2 GB RAM, 16 GB eMMC).

Produces a minimal PREEMPT_RT Linux image for low-latency SPI communication with the iCE40 FPGA.

## Boot Chain

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────┐
│   PBL    │───>│   XBL    │───>│   ABL    │───>│ U-Boot   │───>│ systemd-boot│───>│ Linux+initrd │───>│  rootfs  │
│ (ROM)    │    │ (eMMC)   │    │ (eMMC)   │    │ (boot_a) │    │ (ESP)       │    │ (bundled)    │    │ (p68)    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └─────────────┘    └──────────────┘    └──────────┘
```

- **PBL** (Primary Boot Loader) — Mask ROM. Loads XBL from eMMC. If it can't (JCTL pins shorted), enters **EDL mode** (USB `05c6:9008`).
- **XBL** (`xbl.elf`) — Qualcomm-signed. Initializes DDR, clocks, PMIC. Loads TrustZone, hypervisor, RPM firmware, then ABL.
- **ABL** (`abl.elf`) — Loads Android boot image from `boot_a`. Falls to **fastboot** if `boot_a` is empty/corrupt.
- **U-Boot** (`boot.img`, 564 KB in `boot_a`) — Packaged as Android boot image. Implements UEFI, loads systemd-boot from ESP.
- **systemd-boot** (`BOOTAA64.EFI` on ESP) — Reads BLS entries from `/loader/entries/*.conf`. Loads kernel as UEFI application.
- **Linux** — Kernel (`Image`) with bundled initramfs on ESP. DTB (`qrb2210-rb1.dtb`) on ESP.
- **initramfs** — Minimal busybox init that waits for `/dev/mmcblk0p68`, mounts it, and `switch_root`s to the real rootfs.

The `boot_a` partition is only 4 MB (Qualcomm GPT layout) — too small for the ~52 MB kernel. U-Boot (564 KB) bridges the gap by loading the kernel from the larger ESP (128 MB).

### Kernel Command Line & Root Device

The Arduino-extracted `systemd-boot` has a bug: changing the boot entry `options` line content/length causes a crash. Do NOT modify the options line.

Instead, the kernel uses `CONFIG_CMDLINE_FROM_BOOTLOADER` (the only option that boots on this board — both `CMDLINE_EXTEND` and `CMDLINE_FORCE` prevent boot). Root device discovery is handled by the **bundled initramfs** (`INITRAMFS_IMAGE_BUNDLE=1`):

1. Kernel boots with bundled initramfs (cpio embedded in Image)
2. initramfs init script (`/init`) mounts procfs/sysfs/devtmpfs
3. Waits up to 10s for `/dev/mmcblk0p68` to appear
4. Mounts it as rootfs and `switch_root`s to `/sbin/init` (systemd)

The boot entry `options` line passes a dummy cmdline — it's never actually used by the kernel for root= because the initramfs handles everything.

### Why Not CONFIG_CMDLINE?

The Arduino kernel fork (`linux-qcom`, branch `qcom-v6.16.7-unoq`) only has two ARM64 Kconfig options for cmdline: `CMDLINE_FROM_BOOTLOADER` and `CMDLINE_FORCE` — no `CMDLINE_EXTEND`. We patched `CMDLINE_EXTEND` in, but ANY change from `FROM_BOOTLOADER` (to either `EXTEND` or `FORCE`) prevents the kernel from booting (no LED). Root cause unknown — needs serial console to debug. The initramfs approach bypasses this entirely.

### Why Not kernel-yocto?

`INITRAMFS_IMAGE_BUNDLE` works with bare `inherit kernel`. It does NOT set `CONFIG_INITRAMFS_SOURCE` in `.config` — it passes it on the `make` command line during `do_bundle_initramfs` (a second compilation pass). The `.config` showing `CONFIG_INITRAMFS_SOURCE=""` is expected and correct.

## Build

```bash
# Remote build via Buildbot — uploads artifacts to SeaweedFS S3
nix develop -c task companion:build
nix develop -c task companion:build-status
nix develop -c task companion:build-log

# Download artifacts (latest by default, or a specific build number)
nix develop -c task companion:download
nix develop -c task companion:download BUILD_ID=55

# Local build via kas-container (Docker)
nix develop -c task companion:build-local
```

Artifacts are stored in SeaweedFS S3 (`nwv-srv:8333`) at `s3://buildbot-artifacts/<build-number>/` with a `latest/` alias. The build script cleans kernel sstate before each build to ensure config fragment changes are applied.

Output: `build/tmp/deploy/images/qcom-armv8a/`

## Flashing

All flashing is done from the host over USB. EDL is the most reliable method.

### Full flash via EDL (recommended)

Writes firmware + ESP in one EDL session. Use for initial setup or re-flashing:

```bash
nix develop -c task companion:download     # download images from S3
nix develop -c task companion:make-esp     # create ESP image with kernel + DTB + systemd-boot
# Short JCTL pins 1-2 (furthest from USB-C), plug in USB
nix develop -c task companion:flash-all    # firmware + ESP via EDL
# Remove jumper, replug — board boots
```

### Firmware only (one-time)

Writes GPT partition table + Qualcomm boot chain. Only needed once per board:

```bash
# Short JCTL pins 1-2, plug in USB
nix develop -c task companion:flash-firmware
# Remove jumper, replug
```

### OS only via fastboot

Writes ESP + rootfs. Board must be in fastboot mode (after `flash-firmware` or `reboot bootloader`):

```bash
nix develop -c task companion:flash-os     # flash ESP + rootfs, set slot A active, clear UEFI vars
```

**Important:** `flash-os` does NOT flash boot_a (U-Boot). If you ran `wipe-boot` first, you MUST run `flash-all` before `flash-os` to restore the boot chain.

### Recovery (board stuck in boot loop)

```bash
# Short JCTL pins 1-2, plug in USB
nix develop -c task companion:wipe-boot    # wipes boot_a/b + ESP via EDL
# Remove jumper, replug — board enters fastboot
nix develop -c task companion:flash-all    # restore firmware + ESP via EDL
nix develop -c task companion:flash-os     # flash rootfs via fastboot
```

**Note:** The `qcserial` kernel module on the host may grab EDL devices before `qdl` can. Fix:
```
# NixOS: boot.blacklistedKernelModules = [ "qcserial" "usb_wwan" ];
# Or temporarily: sudo rmmod qcserial usb_wwan
```

## Connecting

After boot, USB gadget ECM creates a network interface (board=192.168.7.2, host=192.168.7.1):

```bash
nix develop -c task companion:host-setup   # configure host interface
nix develop -c task companion:wait         # wait for board to come up
nix develop -c task companion:ssh          # ssh root@192.168.7.2
```

## Iterative Updates (via SSH)

Once the board is running, update without re-flashing:

```bash
nix develop -c task companion:deploy-kernel      # update kernel + DTB on ESP, reboot
nix develop -c task companion:deploy-services     # rsync services to /opt/drone
nix develop -c task companion:deploy-bitstream    # rsync iCE40 bitstream
nix develop -c task companion:deploy              # all of the above
```

## Serial Console

For boot debugging, connect a **1.8V** USB-to-TTL adapter to the JCTL header:

| JCTL Pin | Signal | Connect to |
|---|---|---|
| 3 | TX (board to host) | Adapter RX |
| 4 | RX (host to board) | Adapter TX |
| 6 | GND | Adapter GND |

**Warning:** The JCTL header is 1.8V logic. A 3.3V adapter will damage the SoC.

```bash
nix develop -c task companion:serial    # picocom at 115200 baud
```

## eMMC Partition Layout

| Partition | Size | Content |
|---|---|---|
| `xbl_a/b` | 3.5 MB | XBL bootloader |
| `tz_a/b` | 4 MB | TrustZone |
| `hyp_a/b` | 512 KB | Hypervisor |
| `rpm_a/b` | 512 KB | RPM firmware |
| `boot_a/b` | 4 MB | U-Boot (Android boot image) |
| `abl_a/b` | 1 MB | Android Boot Loader |
| `efi` (ESP) | 128 MB | FAT32 — systemd-boot, kernel, DTB |
| `rootfs` (p68) | ~10 GB | ext4 — Yocto root filesystem |
| `userdata` | remainder | ext4 — user data |

## Firmware Files

`firmware/` — Arduino Uno Q flash bundle (from `arduino-flasher-cli`):

- `prog_firehose_ddr.elf` — Qualcomm-signed firehose programmer for EDL
- `rawprogram0.xml` / `patch0.xml` — eMMC partition layout + fixups
- `rawprogram_esp.xml` — EDL script to write ESP + clear uefivarstore (used by `flash-all`)
- `rawprogram_wipe_esp.xml` / `blank_esp.img` — EDL script to wipe boot partitions (recovery)
- `boot.img` — U-Boot as Android boot image (564 KB)
- `xbl.elf`, `abl.elf`, `tz.mbn`, `hyp.mbn`, `rpm.mbn` — Qualcomm boot chain binaries
- `gpt_main0.bin` / `gpt_backup0.bin` — GPT partition tables

`bootloader/` — EFI boot manager:

- `BOOTAA64.EFI` — systemd-boot for aarch64, extracted from Arduino Debian image

## Layer Stack

| Layer | Branch | Purpose |
|---|---|---|
| poky | scarthgap | OE core + bitbake |
| meta-qcom | scarthgap | QRB2210 BSP (machine, DTB, firmware) |
| meta-openembedded | scarthgap | OE recipes (spitools, i2c-tools, etc.) |
| meta-virtualization | scarthgap | Container/virtualization support |
| meta-companion | local | Custom: linux-arduino kernel, initramfs, usb-gadget service |

## Verify

```bash
uname -r            # should show -rt suffix
chrt -f 99 sleep 1  # RT scheduling works
ls /dev/spidev*     # SPI devices visible
```
