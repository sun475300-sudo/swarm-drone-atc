# Phase 597 — Tcl config manager script
# SDACS configuration management for drone simulation parameters

package require Tcl 8.5

# ---- Namespace for config manager ----
namespace eval ::sdacs::config {
    variable config_store [dict create]
    variable config_file  ""
    variable loaded       0
    variable modified     0

    # Default configuration values
    variable defaults [dict create \
        simulation.duration_s      60     \
        simulation.timestep_ms    100     \
        drones.default_count       10     \
        drones.max_speed_mps       30.0   \
        drones.min_altitude_m       5.0   \
        drones.max_altitude_m     400.0   \
        drones.battery_warn_pct    20.0   \
        wind.enabled                1     \
        wind.speed_mps              5.0   \
        wind.direction_deg        270.0   \
        conflict.separation_m      10.0   \
        conflict.alert_radius_m    20.0   \
        logging.level            "INFO"   \
        logging.file             "sdacs.log" \
    ]
}

# ---- Initialise config with defaults ----
proc ::sdacs::config::init {} {
    variable config_store
    variable defaults
    variable loaded

    set config_store [dict merge $defaults $config_store]
    set loaded 1
    puts "config: initialised with [dict size $config_store] keys"
}

# ---- Get a config value (with optional fallback) ----
proc ::sdacs::config::get {key {fallback ""}} {
    variable config_store
    if {[dict exists $config_store $key]} {
        return [dict get $config_store $key]
    }
    return $fallback
}

# ---- Set a config value ----
proc ::sdacs::config::set {key value} {
    variable config_store
    variable modified
    dict set config_store $key $value
    set modified 1
    puts "config: set $key = $value"
}

# ---- Load config from a simple key=value file ----
proc ::sdacs::config::load_file {filepath} {
    variable config_store
    variable config_file
    variable modified

    if {![file exists $filepath]} {
        puts "config: file not found: $filepath"
        return 0
    }
    set config_file $filepath
    set fh [open $filepath r]
    while {[gets $fh line] >= 0} {
        # Strip comments and blank lines
        set line [string trim $line]
        if {$line eq "" || [string index $line 0] eq "#"} { continue }
        if {[regexp {^([^=]+)=(.*)$} $line -> k v]} {
            dict set config_store [string trim $k] [string trim $v]
        }
    }
    close $fh
    set modified 0
    puts "config: loaded from $filepath"
    return 1
}

# ---- Save current config to a key=value file ----
proc ::sdacs::config::save_file {{filepath ""}} {
    variable config_store
    variable config_file
    variable modified

    if {$filepath eq ""} { set filepath $config_file }
    if {$filepath eq ""} {
        puts "config: no filepath specified for save"
        return 0
    }
    set fh [open $filepath w]
    puts $fh "# SDACS configuration — auto-generated"
    dict for {k v} $config_store {
        puts $fh "$k = $v"
    }
    close $fh
    set modified 0
    puts "config: saved to $filepath"
    return 1
}

# ---- Print all config entries ----
proc ::sdacs::config::print_all {} {
    variable config_store
    puts "=== SDACS Config ==="
    dict for {k v} $config_store {
        puts [format "  %-35s %s" $k $v]
    }
    puts "Total keys: [dict size $config_store]"
}

# ---- Validate required keys exist ----
proc ::sdacs::config::validate {required_keys} {
    variable config_store
    set missing [list]
    foreach k $required_keys {
        if {![dict exists $config_store $k]} {
            lappend missing $k
        }
    }
    if {[llength $missing] > 0} {
        puts "config ERROR: missing required keys: [join $missing {, }]"
        return 0
    }
    puts "config: validation passed"
    return 1
}

# ---- Main script ----
::sdacs::config::init
::sdacs::config::set "drones.default_count" 20
::sdacs::config::set "wind.speed_mps" 8.5
::sdacs::config::print_all
::sdacs::config::validate {simulation.duration_s drones.default_count wind.enabled}
