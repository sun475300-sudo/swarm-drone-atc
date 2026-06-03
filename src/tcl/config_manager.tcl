# Phase 587: Config Manager — Tcl
# SDACS dynamic configuration management for drone fleet

package provide sdacs::config 1.0

namespace eval sdacs::config {
    # Internal config store
    variable store [dict create]
    variable defaults [dict create]
    variable validators [dict create]
    variable watchers [dict create]
    variable change_count 0

    # Initialize default configuration values
    proc init {} {
        variable defaults
        set defaults [dict create \
            simulation.duration       300 \
            simulation.dt             0.1 \
            simulation.seed           42 \
            drones.default_count      10 \
            drones.max_speed          15.0 \
            drones.max_altitude       120.0 \
            drones.min_separation     30.0 \
            battery.critical_pct      10.0 \
            battery.rtl_pct           20.0 \
            battery.capacity_wh       50.0 \
            wind.enabled              true \
            wind.max_speed            20.0 \
            wind.direction_deg        270.0 \
            geofence.enabled          true \
            geofence.radius_m         1000.0 \
            geofence.lat              37.5665 \
            geofence.lon              126.9780 \
            logging.level             info \
            logging.file              sdacs.log \
        ]
        load_defaults
    }

    # Load defaults into store
    proc load_defaults {} {
        variable store defaults
        dict for {key val} $defaults {
            dict set store $key $val
        }
    }

    # Get a config value with optional default
    proc get {key {default ""}} {
        variable store
        if {[dict exists $store $key]} {
            return [dict get $store $key]
        }
        return $default
    }

    # Set a config value with validation and watchers
    proc set_val {key value} {
        variable store validators watchers change_count
        # Validate if validator exists
        if {[dict exists $validators $key]} {
            set validator [dict get $validators $key]
            if {![{*}$validator $value]} {
                error "Invalid value '$value' for config key '$key'"
            }
        }
        set old_val [get $key ""]
        dict set store $key $value
        incr change_count
        # Notify watchers
        if {[dict exists $watchers $key]} {
            foreach watcher [dict get $watchers $key] {
                {*}$watcher $key $old_val $value
            }
        }
    }

    # Register a validator procedure for a key
    proc register_validator {key validator_proc} {
        variable validators
        dict set validators $key $validator_proc
    }

    # Watch for config changes
    proc watch {key callback_proc} {
        variable watchers
        if {![dict exists $watchers $key]} {
            dict set watchers $key [list]
        }
        dict set watchers $key [lappend [dict get $watchers $key] $callback_proc]
    }

    # Load config from a file (key=value format)
    proc load_file {filename} {
        if {![file exists $filename]} {
            return 0
        }
        set fh [open $filename r]
        while {[gets $fh line] >= 0} {
            set line [string trim $line]
            if {$line eq "" || [string index $line 0] eq "#"} continue
            if {[regexp {^(\S+)\s*=\s*(.*)$} $line -> key val]} {
                set_val $key [string trim $val]
            }
        }
        close $fh
        return 1
    }

    # Save config to a file
    proc save_file {filename} {
        variable store
        set fh [open $filename w]
        puts $fh "# SDACS Configuration — auto-generated"
        puts $fh "# [clock format [clock seconds] -format {%Y-%m-%d %H:%M:%S}]"
        puts $fh ""
        dict for {key val} $store {
            puts $fh "$key = $val"
        }
        close $fh
    }

    # Get all config keys matching a prefix
    proc get_namespace {prefix} {
        variable store
        set result [dict create]
        dict for {key val} $store {
            if {[string match "${prefix}*" $key]} {
                dict set result $key $val
            }
        }
        return $result
    }

    # Merge another dict into config
    proc merge {override_dict} {
        dict for {key val} $override_dict {
            set_val $key $val
        }
    }

    # Return config stats
    proc stats {} {
        variable store change_count validators watchers
        return [dict create \
            total_keys    [dict size $store] \
            change_count  $change_count \
            validators    [dict size $validators] \
            watchers      [dict size $watchers] \
        ]
    }

    # Reset to defaults
    proc reset {} {
        variable store change_count
        set store [dict create]
        set change_count 0
        load_defaults
    }

    # Pretty-print current config
    proc dump {} {
        variable store
        dict for {key val} $store {
            puts [format "%-35s = %s" $key $val]
        }
    }
}

# Initialize on package load
sdacs::config::init
