#!/bin/sh
# Load iCE40 bitstream over SPI
# TODO: implement CRESET + SPI flash sequence
BITSTREAM=/opt/drone/top.bin

if [ ! -f "$BITSTREAM" ]; then
    echo "No bitstream at $BITSTREAM"
    exit 1
fi

echo "Loading $BITSTREAM to iCE40..."
