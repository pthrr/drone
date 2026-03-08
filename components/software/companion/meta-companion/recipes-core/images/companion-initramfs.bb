SUMMARY = "Minimal initramfs for QRB2210 root device discovery"
LICENSE = "MIT"

PACKAGE_INSTALL = "initramfs-boot busybox"

IMAGE_FSTYPES = "cpio.gz"
IMAGE_NAME_SUFFIX = ""

# Minimal — no package manager, no kernel modules
IMAGE_FEATURES = ""
IMAGE_LINGUAS = ""

inherit core-image
