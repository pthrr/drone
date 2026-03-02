// ============================================================
// F450 Top Mount — Arduino UNO Q
// Mounts above F450 top plate on standoffs
// ============================================================
// ** VERIFY ALL BOARD DIMENSIONS BEFORE PRINTING **

// ---- Parameters ----

// Base plate
plate_thickness = 3.0;
plate_w = 88;           // X dimension
plate_h = 66;           // Y dimension (53.3 + margin)
corner_r = 4;

// F450 center mounting holes (M3)
f450_hole_spacing_x = 45;
f450_hole_spacing_y = 45;
f450_hole_d = 3.2;

// Standoff parameters (plate sits above F450 top plate)
standoff_h = 12;
standoff_od = 7;
standoff_id = 3.2;

// ---- Board dimensions (MEASURE AND ADJUST) ----

uno_w = 68.6;
uno_h = 53.3;
uno_holes = [
    [14.0, 2.54],
    [15.24, 50.8],
    [66.04, 7.62],
    [66.04, 35.56]
];
uno_hole_d = 3.2;
uno_standoff_h = 6;
uno_standoff_od = 6;

// Board offset +5mm in X to clear F450 standoffs + screw heads
uno_pos = [-uno_w/2 + 5, -uno_h/2];

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
            board_mount(uno_pos, uno_w, uno_h,
                        uno_holes, uno_hole_d,
                        uno_standoff_h, uno_standoff_od);
        }
        f450_mounting_holes();
        board_through_holes(uno_pos, uno_holes, uno_hole_d);
    }
    f450_standoffs();
}

plate_assembly();

// ---- Visualization: F450 center plate outline ----
%translate([0, 0, -(standoff_h + 2)])
    color("gray", 0.2)
    rounded_rect(155, 155, 5, 2);
