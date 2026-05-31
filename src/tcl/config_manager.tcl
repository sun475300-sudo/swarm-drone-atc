# Config Manager — SDACS Phase 597
# Tcl configuration management for SDACS

namespace eval sdacs::config {
    variable data [dict create]
    variable defaults [dict create]

    proc init {} {
        variable defaults
        set defaults [dict create             drones.max_count 100             sim.duration 60             apf.k_att 1.0             apf.k_rep 100.0             log.level INFO         ]
    }

    proc load {filename} {
        variable data
        if {![file exists $filename]} {
            error "Config file not found: $filename"
        }
        set fd [open $filename r]
        set content [read $fd]
        close $fd
        foreach line [split $content "
"] {
            set line [string trim $line]
            if {[string length $line] == 0} continue
            if {[string index $line 0] eq "#"} continue
            if {[regexp {^(\S+)\s*=\s*(.+)$} $line -> key val]} {
                dict set data $key $val
            }
        }
    }

    proc get {key {default ""}} {
        variable data
        variable defaults
        if {[dict exists $data $key]} {
            return [dict get $data $key]
        }
        if {[dict exists $defaults $key]} {
            return [dict get $defaults $key]
        }
        return $default
    }

    proc set_value {key value} {
        variable data
        dict set data $key $value
    }
}

sdacs::config::init
# end
# end
