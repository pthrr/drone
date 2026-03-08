# Companion Computer — TODO

## Current blocker: boot loop with initramfs

The kernel boots (red LED blinks) but enters a boot loop. The bundled initramfs
is failing somewhere — either `/dev/mmcblk0p68` never appears, `mount` fails,
or `switch_root` fails. Without serial console we can't see the error.

### What works

- Yocto build succeeds (6342 tasks, all pass)
- `do_bundle_initramfs` + `do_transform_bundled_initramfs` succeed
- Kernel Image is valid ARM64 format (52 MB, initramfs cpio embedded at 27.4 MB offset)
- `flash-all` (EDL) writes firmware + ESP correctly
- Kernel starts booting (red LED appears)
- S3 artifact upload with build job ID namespacing works (build 55)

### What fails

- Board enters boot loop after kernel start (initramfs init fails → kernel panic → reboot)
- No USB ECM interface ever appears on host
- No way to debug without serial console

### Likely causes (investigate with serial)

1. **Wrong partition number** — `/dev/mmcblk0p68` is hardcoded in init script.
   Verify with serial that p68 is actually the rootfs partition. The GPT may
   use a different numbering.

2. **Rootfs not present** — `flash-os` flashed it via fastboot, but was it
   actually written to p68? Check with `fdisk -l /dev/mmcblk0`.

3. **busybox too minimal** — The Yocto busybox might not include `mount`,
   `switch_root`, or ext4 support. Check `busybox --list` from initramfs shell.

4. **switch_root fails** — If `/sbin/init` doesn't exist on the rootfs (wrong
   image, corrupt filesystem), switch_root fails and PID 1 exits → kernel panic.

5. **devtmpfs not enabled** — If `CONFIG_DEVTMPFS=y` is not set, the init
   script can't mount devtmpfs and no device nodes appear.

### Next steps

1. **Get serial console working** — Buy/connect a 1.8V USB-to-UART adapter to
   JCTL header (Pin 3=TX, Pin 4=RX, Pin 6=GND). `task companion:serial` opens
   picocom at 115200. This is the #1 priority — everything else is guessing.

2. **Alternative: USB ECM in initramfs** — If serial isn't available, add USB
   gadget ECM setup directly in the init script (before mounting rootfs). This
   gives a network shell even when rootfs mount fails. Requires adding configfs
   setup to the init script and a static IP. Complex but possible.

3. **Make init script more robust** — Add `set -x` for debug output (visible
   on serial), try multiple root devices (`/dev/mmcblk0p68`, `/dev/mmcblk0p*`
   with label scan), add `findfs` if available.

## Kernel config issues (resolved)

### CONFIG_CMDLINE — dead end

Tried extensively to bake `root=/dev/mmcblk0p68 rootwait rw` into the kernel
via CONFIG_CMDLINE. All approaches failed:

- **`inherit kernel` doesn't merge .cfg fragments** — Fixed with
  `do_configure:append` calling `merge_config.sh` + `olddefconfig`.
- **olddefconfig reverts Kconfig choice groups** — Arduino kernel only has
  `CMDLINE_FROM_BOOTLOADER` and `CMDLINE_FORCE`. `olddefconfig` always reverts
  to `FROM_BOOTLOADER`. Tried: explicit disabling in fragments, `scripts/config`,
  sed hacks, two-pass builds. All reverted by `make`'s implicit `syncconfig`.
- **Patched CMDLINE_EXTEND into Kconfig** — Added the missing option to the
  ARM64 Kconfig choice group. Patch applied cleanly. IKCONFIG confirmed
  `CMDLINE_EXTEND=y`. But kernel didn't boot (no red LED).
- **ANY change from FROM_BOOTLOADER prevents boot** — Both `CMDLINE_FORCE`
  and `CMDLINE_EXTEND` cause no red LED. Root cause unknown without serial.

Resolution: abandoned kernel cmdline approach, switched to initramfs.

### PREEMPT_RT — not available

The Arduino kernel fork does not have `CONFIG_PREEMPT_RT` in its Kconfig.
The `rt.cfg` fragment sets `CONFIG_PREEMPT_RT=y` but it's silently ignored.
The kernel uses `CONFIG_PREEMPT=y` (voluntary preemption) from defconfig.

To get real PREEMPT_RT, either:
- Apply the RT patchset to the Arduino kernel fork
- Wait for Arduino to update their kernel to a version with RT merged

### USB gadget module vs built-in

`CONFIG_USB_CONFIGFS=y` forces `USB_LIBCOMPOSITE` and `USB_F_ECM` from `=m`
to `=y` (built-in). The `kernel-module-*` packages then don't exist, breaking
RDEPENDS. Fixed by removing RDEPENDS from `usb-gadget.bb` and setting all
USB configs to `=y` in `uno-q.cfg`.

## Build infrastructure issues (resolved)

### Shell quoting in Buildbot job_script

The job_script lives inside `-d '...'` (single-quoted curl argument) containing
JSON. Three quoting layers: (1) outer shell single quotes, (2) JSON string
escaping, (3) server-side shell execution.

**NO single quotes can appear anywhere in the job_script** — they break the
outer `-d '...'` context. Use `\"` for inner quotes (→ JSON `"` → server `"`).
Use `sed` instead of `python3 -c` with dict access (which needs `['key']`).

Specific bugs fixed:
- `S3="aws --endpoint-url ..."` — spaces in variable broke arg splitting.
  Fix: `AWS=$path/bin/aws` (no spaces), inline args.
- `python3 -c "...['builds']..."` — single quotes broke outer quoting.
  Fix: replaced with `sed -n "s/.*buildrequestid[^0-9]*\([0-9]*\).*/\1/p"`.
- `sed` without `-n` outputs all lines — non-matching lines passed through
  as BUILD_ID. Fix: `sed -n ... /p`.
- `kas-container shell ... -c 'bitbake ...'` — single quotes broke outer
  quoting. Fix: `\"bitbake ...\"`.

### S3 artifact namespacing

Changed from git short hash to Buildbot build job ID. Artifacts stored at
`s3://buildbot-artifacts/<build-number>/` (e.g., `55/`). `latest/` alias
points to most recent build.

### Kernel sstate caching

Old kernel builds (with stale config patches) were reused from sstate.
Fixed by adding `bitbake -c cleansstate linux-arduino` before each build.
This adds ~20s overhead but guarantees config fragment changes are applied.

## Future work

- [ ] Serial console debugging (1.8V UART adapter needed)
- [ ] Fix initramfs boot loop
- [ ] PREEMPT_RT patchset for Arduino kernel
- [ ] STM32U585 MCU communication (LPUART1, MsgPack RPC)
- [ ] SPI data transfer to iCE40 FPGA
- [ ] iCE40 bitstream loading service
- [ ] Remove `cleansstate` from build script once sstate is reliable
- [ ] Consider dropping initramfs if serial debugging reveals a simpler fix
