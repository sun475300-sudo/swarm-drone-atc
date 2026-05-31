# P597: ConfigManager - Tcl configuration management for SDACS
# Phase 597: Dynamic configuration loading and validation

package provide sdacs::config 1.0

namespace eval sdacs::config {
    variable defaults {
        simulation.duration         300
        simulation.time_step        0.1
        simulation.max_drones       100
        airspace.width              5000
        airspace.height             5000
        airspace.altitude_min       30
        airspace.altitude_max       150
        apf.k_att                   1.0
        apf.k_rep                   500.0
        apf.rho_0                   50.0
        logging.level               INFO
        logging.file                sdacs.log
        api.host                    0.0.0.0
        api.port                    8000
        api.jwt_ttl_min             60
        metrics.enabled             true
        metrics.port                9090
    }

    variable config_data {}
    variable config_file ""

    # Load config from dict (key=path, val=value)
    proc load {data} {
        variable config_data
        set config_data $data
    }

    # Load config from file (key=value format)
    proc load_file {path} {
        variable config_file
        variable config_data
        set config_file $path
        if {![file exists $path]} {
            return [defaults]
        }
        set config_data {}
        set fh [open $path r]
        while {[gets $fh line] >= 0} {
            set line [string trim $line]
            if {[string match "#*" $line] || $line eq ""} continue
            if {[regexp {^(\S+)\s*=\s*(.+)$} $line -> key val]} {
                dict set config_data $key [string trim $val]
            }
        }
        close $fh
        return $config_data
    }

    # Get a config value with fallback to default
    proc get {key {fallback ""}} {
        variable config_data
        variable defaults
        if {[dict exists $config_data $key]} {
            return [dict get $config_data $key]
        }
        if {[dict exists $defaults $key]} {
            return [dict get $defaults $key]
        }
        return $fallback
    }

    # Set a config value
    proc set_value {key value} {
        variable config_data
        dict set config_data $key $value
    }

    # Return defaults dict
    proc defaults {} {
        variable defaults
        return $defaults
    }

    # Validate required config keys
    proc validate {required_keys} {
        set errors {}
        foreach key $required_keys {
            if {[get $key ""] eq ""} {
                lappend errors "Missing required config: $key"
            }
        }
        return $errors
    }

    # Merge override dict into current config
    proc merge {override_dict} {
        variable config_data
        dict for {k v} $override_dict {
            dict set config_data $k $v
        }
    }

    # Dump current config
    proc dump {} {
        variable config_data
        variable defaults
        set merged [dict merge $defaults $config_data]
        return $merged
    }

    # Export namespace commands
    namespace export load load_file get set_value defaults validate merge dump
}
