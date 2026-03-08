SUMMARY = "USB ECM gadget network for drone companion"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit systemd

SRC_URI = " \
    file://usb-gadget.service \
    file://10-usb0.network \
"

S = "${WORKDIR}"

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/usb-gadget.service ${D}${systemd_system_unitdir}/usb-gadget.service

    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${WORKDIR}/10-usb0.network ${D}${sysconfdir}/systemd/network/10-usb0.network
}

SYSTEMD_SERVICE:${PN} = "usb-gadget.service"
SYSTEMD_AUTO_ENABLE = "enable"

# libcomposite and usb_f_ecm are built-in (=y) via kernel config fragments
# modprobe in the service is a no-op for built-ins
