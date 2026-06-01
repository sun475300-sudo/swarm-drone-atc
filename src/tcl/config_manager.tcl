#!/usr/bin/tclsh
# Phase 597: Config Manager — 드론 시스템 설정 관리자 (Tcl)
# Hierarchical configuration manager for SDACS drone fleet parameters.

package require Tcl 8.5

namespace eval ::sdacs::config {
    variable PHASE 597
    variable store [dict create]
    variable schema [dict create]
    variable history [list]
}

# ── Schema definition ──────────────────────────────────────────────

proc ::sdacs::config::define_schema {} {
    variable schema
    set schema [dict create \
        "drone.default_count"     {type int   min 1   max 1000 default 10} \
        "drone.max_altitude"      {type float min 0   max 500  default 120.0} \
        "drone.max_velocity"      {type float min 0   max 50   default 15.0} \
        "mission.timeout_sec"     {type int   min 10  max 3600 default 300} \
        "comms.heartbeat_hz"      {type float min 0.1 max 100  default 1.0} \
        "safety.min_battery_pct"  {type float min 0   max 50   default 15.0} \
        "logging.level"           {type enum  values {DEBUG INFO WARN ERROR} default INFO} \
    ]
}

# ── Set / Get ──────────────────────────────────────────────────────

proc ::sdacs::config::set_config {key value} {
    variable store
    variable schema
    variable history

    if {[dict exists $schema $key]} {
        set spec [dict get $schema $key]
        set type [dict get $spec type]
        switch $type {
            int   { if {![string is integer $value]} { error "Expected int for $key" } }
            float { if {![string is double  $value]} { error "Expected float for $key" } }
            enum  {
                set vals [dict get $spec values]
                if {$value ni $vals} { error "Invalid enum value '$value' for $key" }
            }
        }
    }
    lappend history [list set $key [dict get $store $key [list]] $value [clock seconds]]
    dict set store $key $value
}

proc ::sdacs::config::get_config {key {default {}}} {
    variable store
    variable schema
    if {[dict exists $store $key]} {
        return [dict get $store $key]
    }
    if {[dict exists $schema $key]} {
        return [dict get [dict get $schema $key] default]
    }
    return $default
}

# ── Load from dict ─────────────────────────────────────────────────

proc ::sdacs::config::load_dict {cfg_dict} {
    dict for {k v} $cfg_dict {
        set_config $k $v
    }
}

# ── Dump config ────────────────────────────────────────────────────

proc ::sdacs::config::dump {} {
    variable store
    set lines [list "# SDACS Config Dump"]
    dict for {k v} $store {
        lappend lines "$k = $v"
    }
    return [join $lines "\n"]
}

# ── Summary ────────────────────────────────────────────────────────

proc ::sdacs::config::summary {} {
    variable store
    variable history
    variable PHASE
    return [dict create \
        phase   $PHASE \
        keys    [llength [dict keys $store]] \
        changes [llength $history] \
    ]
}

# ── Reset ──────────────────────────────────────────────────────────

proc ::sdacs::config::reset {} {
    variable store
    variable history
    set store   [dict create]
    set history [list]
}

# ── Entry point ────────────────────────────────────────────────────

::sdacs::config::define_schema

::sdacs::config::load_dict [dict create \
    "drone.default_count"    20 \
    "drone.max_altitude"     150.0 \
    "drone.max_velocity"     18.0 \
    "mission.timeout_sec"    600 \
    "comms.heartbeat_hz"     2.0 \
    "safety.min_battery_pct" 20.0 \
    "logging.level"          INFO \
]

set phase  [::sdacs::config::get_config "dummy" 597]
set count  [::sdacs::config::get_config "drone.default_count"]
set alt    [::sdacs::config::get_config "drone.max_altitude"]
set vel    [::sdacs::config::get_config "drone.max_velocity"]
set s      [::sdacs::config::summary]

puts "Phase 597: Config Manager — 드론 설정 관리자 (Tcl)"
puts "drone.default_count = $count"
puts "drone.max_altitude  = $alt m"
puts "drone.max_velocity  = $vel m/s"
puts "config keys=[dict get $s keys] changes=[dict get $s changes]"
puts [::sdacs::config::dump]
