SUMMARY = "Minimal initramfs init script for QRB2210"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://init"

S = "${WORKDIR}"

do_install() {
    install -d ${D}
    install -m 0755 ${WORKDIR}/init ${D}/init
}

FILES:${PN} = "/init"
