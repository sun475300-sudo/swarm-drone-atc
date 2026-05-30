# Phase 597: config_manager — Tcl 기반 설정 관리자
# SDACS Configuration Manager for Drone Fleet Parameters

package require Tcl 8.6

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 설정 레지스트리 (namespace 기반)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

namespace eval config {
    variable registry [dict create]
    variable defaults [dict create]
    variable validators [dict create]
    variable change_log [list]

    # 기본값 초기화
    proc init_defaults {} {
        variable defaults
        set defaults [dict create \
            simulation.duration         60 \
            simulation.timestep         0.1 \
            drones.default_count        10 \
            drones.max_altitude         120.0 \
            drones.min_separation       10.0 \
            drones.battery_rtl_threshold 20.0 \
            control.frequency_hz        10 \
            control.apf_attractive      1.0 \
            control.apf_repulsive       100.0 \
            wind.enabled                1 \
            wind.max_speed              15.0 \
            wind.direction_deg          270.0 \
            logging.level               "INFO" \
            logging.file                "sdacs.log" \
            network.port                8050 \
            network.host                "localhost" \
        ]
    }

    # 유효성 검사기 등록
    proc register_validator {key proc_name} {
        variable validators
        dict set validators $key $proc_name
    }

    # 설정값 로드 (기본값으로 초기화)
    proc load {} {
        variable registry defaults
        init_defaults
        set registry [dict merge $defaults $registry]
    }

    # 설정값 읽기
    proc get {key {default ""}} {
        variable registry defaults
        if {[dict exists $registry $key]} {
            return [dict get $registry $key]
        } elseif {[dict exists $defaults $key]} {
            return [dict get $defaults $key]
        }
        return $default
    }

    # 설정값 쓰기 (유효성 검사 포함)
    proc set_value {key value} {
        variable registry validators change_log
        # 유효성 검사
        if {[dict exists $validators $key]} {
            set validator [dict get $validators $key]
            if {![{*}$validator $value]} {
                error "설정 유효성 오류: $key = $value"
            }
        }
        set old_value [get $key]
        dict set registry $key $value
        lappend change_log [dict create \
            key $key old $old_value new $value \
            timestamp [clock milliseconds]]
        return $value
    }

    # 설정 섹션별 조회
    proc get_section {prefix} {
        variable registry defaults
        set result [dict create]
        set all [dict merge $defaults $registry]
        dict for {k v} $all {
            if {[string match "${prefix}.*" $k]} {
                set sub_key [string range $k [string length "${prefix}."] end]
                dict set result $sub_key $v
            }
        }
        return $result
    }

    # 설정을 YAML 형식으로 출력
    proc to_yaml {} {
        variable registry defaults
        set all [dict merge $defaults $registry]
        set sections [dict create]
        dict for {k v} $all {
            set parts [split $k "."]
            set section [lindex $parts 0]
            set sub_key [join [lrange $parts 1 end] "."]
            dict set sections $section $sub_key $v
        }
        set yaml ""
        dict for {section keys} $sections {
            append yaml "${section}:\n"
            dict for {k v} $keys {
                append yaml "  ${k}: ${v}\n"
            }
        }
        return $yaml
    }

    # 변경 이력 조회
    proc get_change_log {} {
        variable change_log
        return $change_log
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 유효성 검사 함수들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

proc validate_positive {value} {
    return [expr {[string is double $value] && $value > 0}]
}

proc validate_altitude {value} {
    return [expr {[string is double $value] && $value >= 0 && $value <= 500}]
}

proc validate_battery_threshold {value} {
    return [expr {[string is double $value] && $value >= 5 && $value <= 50}]
}

proc validate_log_level {value} {
    return [expr {$value in {"DEBUG" "INFO" "WARNING" "ERROR" "CRITICAL"}}]
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

puts "SDACS Config Manager — Phase 597\n"

# 유효성 검사기 등록
config::register_validator "drones.max_altitude"         "validate_altitude"
config::register_validator "drones.battery_rtl_threshold" "validate_battery_threshold"
config::register_validator "simulation.timestep"          "validate_positive"
config::register_validator "logging.level"                "validate_log_level"

# 설정 로드
config::load

puts "기본 설정 로드 완료:"
puts "  드론 수:        [config::get drones.default_count]"
puts "  최대 고도:      [config::get drones.max_altitude]m"
puts "  배터리 RTL:     [config::get drones.battery_rtl_threshold]%"
puts "  시뮬 타임스텝:  [config::get simulation.timestep]s"

# 설정 변경
config::set_value "drones.default_count" 15
config::set_value "drones.max_altitude"  100.0
config::set_value "logging.level"        "DEBUG"

puts "\n변경 후:"
puts "  드론 수:   [config::get drones.default_count]"
puts "  최대 고도: [config::get drones.max_altitude]m"
puts "  로그 레벨: [config::get logging.level]"

# 섹션 조회
puts "\n드론 설정 섹션:"
dict for {k v} [config::get_section "drones"] {
    puts "  $k = $v"
}

# 변경 이력
set log [config::get_change_log]
puts "\n변경 이력: [llength $log]건"

# YAML 출력
puts "\n설정 YAML (일부):"
set yaml [config::to_yaml]
set lines [split $yaml "\n"]
foreach line [lrange $lines 0 9] {
    puts "  $line"
}

puts "\n설정 관리자 처리 완료."
