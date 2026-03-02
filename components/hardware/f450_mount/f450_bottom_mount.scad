// ============================================================
// F450 Bottom Mount — Olimex iCE40-HX8K-EVB + DEMO-BGT60TR13C radar
// Mounts below F450 bottom plate on standoffs
// ============================================================
// ** VERIFY ALL BOARD DIMENSIONS BEFORE PRINTING **

// ---- Parameters ----

// Base plate
plate_thickness = 3.0;
plate_w = 130;          // X dimension (both boards side by side)
plate_h = 66;           // Y dimension (54 + margin)
corner_r = 4;

// F450 center mounting holes (M3)
f450_hole_spacing_x = 45;
f450_hole_spacing_y = 45;
f450_hole_d = 3.2;

// Standoff parameters (plate hangs below F450 bottom plate)
standoff_h = 12;
standoff_od = 7;
standoff_id = 3.2;

// ---- Board dimensions (MEASURE AND ADJUST) ----

// Olimex iCE40-HX8K-EVB
ice40_w = 75;
ice40_h = 54;
ice40_holes = [
    [3.0, 3.0],
    [3.0, 51.0],
    [72.0, 3.0],
    [72.0, 51.0]
];
ice40_hole_d = 3.2;
ice40_standoff_h = 6;
ice40_standoff_od = 6;

// Infineon DEMO-BGT60TR13C radar baseboard
radar_w = 40.64;
radar_h = 25.4;
// Mounting holes — MEASURE YOUR BOARD
radar_holes = [
    [2.0, 2.0],
    [2.0, 23.4],
    [38.64, 2.0],
    [38.64, 23.4]
];
radar_hole_d = 2.5;
radar_standoff_h = 6;
radar_standoff_od = 5;

// ---- Board placement (side by side, both centered in Y) ----
board_gap = 5;
total_w = ice40_w + board_gap + radar_w;

ice40_pos = [-total_w/2, -ice40_h/2];
radar_pos = [-total_w/2 + ice40_w + board_gap, -radar_h/2];

// ============================================================
// Modules
// ============================================================

module rounded_rect(w, h, r, t) {
    linear_extrude(t)
    offset(r) offset(-r)
        square([w, h], center=true);
}

module board_standoff(h, od, id) {
    difference() {
        cylinder(h=h, d=od, $fn=24);
        translate([0, 0, -0.1])
            cylinder(h=h+0.2, d=id, $fn=24);
    }
}

module board_mount(pos, board_w, board_h, holes, hole_d, so_h, so_od) {
    for (h = holes) {
        translate([pos[0] + h[0], pos[1] + h[1], plate_thickness])
            board_standoff(so_h, so_od, hole_d);
    }
    %translate([pos[0], pos[1], plate_thickness + so_h])
        color("green", 0.3)
        cube([board_w, board_h, 1.6]);
}

module board_through_holes(pos, holes, hole_d) {
    for (h = holes) {
        translate([pos[0] + h[0], pos[1] + h[1], -1])
            cylinder(h=plate_thickness + 2, d=hole_d, $fn=24);
    }
}

module f450_mounting_holes() {
    for (x = [-1, 1], y = [-1, 1]) {
        translate([x * f450_hole_spacing_x/2,
                   y * f450_hole_spacing_y/2, -1])
            cylinder(h=plate_thickness + 2, d=f450_hole_d, $fn=24);
    }
}

module f450_standoffs() {
    for (x = [-1, 1], y = [-1, 1]) {
        translate([x * f450_hole_spacing_x/2,
                   y * f450_hole_spacing_y/2, -standoff_h])
            board_standoff(standoff_h, standoff_od, standoff_id);
    }
}


// ============================================================
// Assembly
// ============================================================

module plate_assembly() {
    difference() {
        union() {
            rounded_rect(plate_w, plate_h, corner_r, plate_thickness);
            board_mount(ice40_pos, ice40_w, ice40_h,
                        ice40_holes, ice40_hole_d,
                        ice40_standoff_h, ice40_standoff_od);
            board_mount(radar_pos, radar_w, radar_h,
                        radar_holes, radar_hole_d,
                        radar_standoff_h, radar_standoff_od);
        }
        f450_mounting_holes();
        board_through_holes(ice40_pos, ice40_holes, ice40_hole_d);
        board_through_holes(radar_pos, radar_holes, radar_hole_d);
    }
    f450_standoffs();
}

plate_assembly();

// ---- Visualization: F450 center plate outline ----
%translate([0, 0, -(standoff_h + 2)])
    color("gray", 0.2)
    rounded_rect(155, 155, 5, 2);
