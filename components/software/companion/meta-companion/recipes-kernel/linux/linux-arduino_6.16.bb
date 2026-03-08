SUMMARY = "Linux kernel for Arduino Uno Q (QRB2210)"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=6bc538ed5bd9a7fc9398086aedcd7e46"

inherit kernel

SRC_URI = "git://github.com/arduino/linux-qcom.git;protocol=https;branch=qcom-v6.16.7-unoq"
SRCREV = "${AUTOREV}"
PV = "6.16.7+git"

S = "${WORKDIR}/git"

COMPATIBLE_MACHINE = "qcom-armv8a"

# Use standard arm64 defconfig (same as Arduino)
KBUILD_DEFCONFIG = "defconfig"

# Config fragments: board support (no CMDLINE changes — initramfs handles root)
SRC_URI += "file://rt.cfg \
            file://uno-q.cfg"

# inherit kernel does NOT auto-merge .cfg fragments — do it manually
do_configure:append() {
    ${S}/scripts/kconfig/merge_config.sh -m ${B}/.config ${WORKDIR}/rt.cfg ${WORKDIR}/uno-q.cfg
    oe_runmake -C ${S} O=${B} olddefconfig
}
