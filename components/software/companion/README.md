# Companion Computer — QRB2210 RT Linux

Yocto (Scarthgap) build for the Arduino Uno Q companion computer (Qualcomm QRB2210, quad Cortex-A53 @ 2.0 GHz, 2 GB RAM, 16 GB eMMC).

Produces a minimal PREEMPT_RT Linux image for low-latency SPI communication with the iCE40 FPGA.

## Prerequisites

- Linux host (tested on Fedora 42)
- ~50 GB free disk space
- `kas`, `git`, `python3`

## Build

```bash
# Install kas
task companion:setup

# RT image (PREEMPT_RT kernel)
task companion:build

# Dev image (standard kernel + gdb, ssh, tcpdump)
task companion:build-dev
```

Output image: `build/tmp/deploy/images/qcom-armv8a/`

## Flash (EDL Mode)

1. Hold **FORCE_USB_BOOT** while powering on the board
2. Verify EDL mode: `lsusb | grep 05c6:9008`
3. Flash: `qdl --storage emmc prog_firehose.elf rawprogram.xml patch.xml`

## Verify RT

```bash
uname -r          # should show -rt suffix
chrt -f 99 sleep 1  # should succeed (RT scheduling)
ls /dev/spidev*    # SPI devices visible
```

## Layer Stack

| Layer | Branch | Purpose |
|---|---|---|
| poky | scarthgap | OE core + bitbake |
| meta-qcom | scarthgap | QRB2210 BSP (machine, DTB, firmware) |
| meta-qcom-hwe | scarthgap | Qualcomm HWE kernel recipes |
| meta-qcom-distro | scarthgap | qcom-wayland distro config |
| meta-qcom-realtime | scarthgap | PREEMPT_RT kernel overlay |
| meta-openembedded | scarthgap | OE recipes (spitools, i2c-tools, etc.) |
