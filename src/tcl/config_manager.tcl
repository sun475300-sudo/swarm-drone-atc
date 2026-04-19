#!/usr/bin/env tclsh
# Phase 597: Configuration Manager — Tcl
# 드론 설정 관리: 계층적 설정, 검증, 핫 리로드, diff.

namespace eval ::sdacs::config {

    # ─── 기본 설정 ───
    variable defaults
    array set defaults {
        drone.max_altitude       400.0
        drone.max_speed          25.0
        drone.min_battery        15.0
        drone.geofence_radius    5000.0
        control.update_rate      10
        control.pid_kp           0.8
        control.pid_ki           0.1
        control.pid_kd           0.05
        comms.frequency          2400
        comms.tx_power           20
        comms.protocol           "mavlink"
        comms.encryption         "aes256"
        safety.min_separation    50.0
        safety.emergency_land    true
        safety.return_home       true
        safety.tmr_voting        true
        mission.max_duration     3600
        mission.max_waypoints    100
        mission.auto_rtl         true
    }

    # ─── 현재 설정 ───
    variable current
    array set current {}

    # ─── 변경 이력 ───
    variable history {}
    variable version 0

    # ─── 초기화 ───
    proc init {} {
        variable defaults
        variable current
        variable version

        array set current [array get defaults]
        set version 1
        log "Configuration initialized (v$version)"
    }

    # ─── 값 조회 ───
    proc get {key} {
        variable current
        if {[info exists current($key)]} {
            return $current($key)
        }
        return ""
    }

    # ─── 값 설정 ───
    proc set_value {key value} {
        variable current
        variable history
        variable version

        # 이전 값 기록
        set old_value ""
        if {[info exists current($key)]} {
            set old_value $current($key)
        }

        # 검증
        if {![validate $key $value]} {
            log "REJECTED: $key = $value (validation failed)"
            return 0
        }

        set current($key) $value
        incr version

        # 이력 추가
        lappend history [list $version $key $old_value $value [clock seconds]]
        log "SET: $key = $value (was: $old_value) [v$version]"
        return 1
    }

    # ─── 검증 규칙 ───
    proc validate {key value} {
        switch -glob $key {
            "drone.max_altitude" {
                return [expr {[string is double $value] && $value > 0 && $value <= 10000}]
            }
            "drone.max_speed" {
                return [expr {[string is double $value] && $value > 0 && $value <= 100}]
            }
            "drone.min_battery" {
                return [expr {[string is double $value] && $value >= 0 && $value <= 100}]
            }
            "control.update_rate" {
                return [expr {[string is integer $value] && $value >= 1 && $value <= 100}]
            }
            "control.pid_*" {
                return [expr {[string is double $value] && $value >= 0}]
            }
            "safety.min_separation" {
                return [expr {[string is double $value] && $value >= 10}]
            }
            "safety.*" {
                return [expr {$value in {true false 1 0}}]
            }
            default {
                return 1
            }
        }
    }

    # ─── Diff (변경 사항) ───
    proc diff {} {
        variable defaults
        variable current
        set changes {}

        foreach key [array names current] {
            if {[info exists defaults($key)]} {
                if {$current($key) ne $defaults($key)} {
                    lappend changes [list $key $defaults($key) $current($key)]
                }
            } else {
                lappend changes [list $key "(new)" $current($key)]
            }
        }
        return $changes
    }

    # ─── 설정 내보내기 ───
    proc export_config {{format "yaml"}} {
        variable current
        variable version

        set output "# SDACS Configuration v$version\n"
        set prev_section ""

        foreach key [lsort [array names current]] {
            set parts [split $key "."]
            set section [lindex $parts 0]

            if {$section ne $prev_section} {
                append output "\n${section}:\n"
                set prev_section $section
            }

            set param [lindex $parts 1]
            append output "  ${param}: $current($key)\n"
        }
        return $output
    }

    # ─── 설정 가져오기 ───
    proc import_config {data} {
        variable current
        set count 0

        foreach line [split $data "\n"] {
            set line [string trim $line]
            if {$line eq "" || [string index $line 0] eq "#"} continue

            if {[regexp {^(\S+)\s*[:=]\s*(.+)$} $line -> key value]} {
                set value [string trim $value]
                if {[set_value $key $value]} {
                    incr count
                }
            }
        }
        return $count
    }

    # ─── 리셋 ───
    proc reset {} {
        variable defaults
        variable current
        variable version
        array set current [array get defaults]
        incr version
        log "Configuration RESET to defaults (v$version)"
    }

    # ─── 로깅 ───
    proc log {msg} {
        puts "  \[CONFIG\] $msg"
    }

    # ─── 통계 ───
    proc stats {} {
        variable current
        variable history
        variable version
        return [list \
            keys [array size current] \
            version $version \
            changes [llength $history] \
        ]
    }
}

# ─── 메인 실행 ───
puts "=== SDACS Configuration Manager ==="
puts ""

# 초기화
::sdacs::config::init

# 설정 변경
::sdacs::config::set_value "drone.max_altitude" 300.0
::sdacs::config::set_value "drone.max_speed" 20.0
::sdacs::config::set_value "safety.min_separation" 75.0
::sdacs::config::set_value "control.pid_kp" 1.2

# 잘못된 값 (거부됨)
::sdacs::config::set_value "drone.max_altitude" -100
::sdacs::config::set_value "safety.min_separation" 5

# 변경 사항 확인
puts "\n--- Changes from defaults ---"
foreach change [::sdacs::config::diff] {
    lassign $change key old new
    puts "  $key: $old -> $new"
}

# YAML 내보내기
puts "\n--- Exported Config ---"
puts [::sdacs::config::export_config]

# 통계
puts "--- Stats ---"
foreach {key value} [::sdacs::config::stats] {
    puts "  $key: $value"
}
