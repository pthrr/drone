# AT86RF215 RF Shield

Dual-band RF transceiver shield for the Lattice iCE40-HX8K breakout board (ICE40HX8K-B-EVN). Hosts a Microchip AT86RF215-ZU providing simultaneous sub-GHz and 2.4 GHz radio with LVDS I/Q streaming to the FPGA.

## Frequency bands

| Band    | Frequency | Connector |
|---------|-----------|-----------|
| Sub-GHz | 432 MHz   | SMA J1    |
| 2.4 GHz | 2.4 GHz   | SMA J2    |

## Interfaces

- **SPI** — configuration and register access (active-low CSn, active-low RSTn, active-low IRQ), routed via iCE40 J2 (Bank 0)
- **LVDS I/Q** — high-speed baseband streaming (5 differential pairs: RX data × 2 bands, RX clock, TX data, TX clock), routed via iCE40 J4 (Bank 3) with 100 Ω termination resistors

## Files

| File | Description |
|------|-------------|
| `at86rf215_shield.kicad_pro` | KiCad 8 project |
| `at86rf215_shield.kicad_sch` | Schematic |
| `at86rf215_shield.pcf`       | FPGA pin constraints (for `nextpnr-ice40`) |
| `BOM.csv`                    | Bill of materials |
| `PIN_MAPPING.txt`            | Full pin mapping and design notes |

## Opening in KiCad

Open `at86rf215_shield.kicad_pro` in KiCad 8+. The schematic is self-contained in `at86rf215_shield.kicad_sch`.
