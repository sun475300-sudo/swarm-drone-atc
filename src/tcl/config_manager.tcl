# SDACS Config Manager — Tcl
# 군집드론 설정 관리 시스템

package require Tcl 8.6

# 전역 설정 딕셔너리
set config [dict create]

# 기본 설정 초기화
proc config::init {} {
    global config
    set config [dict create \
        simulation.duration 3600 \
        simulation.timestep 0.1 \
        drones.default_count 10 \
        drones.max_altitude 400 \
        drones.min_separation 5.0 \
        wind.enabled true \
        wind.max_speed 15.0 \
        safety.geofence_radius 1000 \
        safety.collision_threshold 3.0 \
        logging.level INFO \
        logging.file sdacs.log \
    ]
    puts "Config initialized with [dict size $config] entries"
}

# 설정 값 가져오기
proc config::get {key {default ""}} {
    global config
    if {[dict exists $config $key]} {
        return [dict get $config $key]
    }
    return $default
}

# 설정 값 설정
proc config::set_value {key value} {
    global config
    dict set config $key $value
    puts "Config set: $key = $value"
}

# 설정 값 삭제
proc config::unset_key {key} {
    global config
    if {[dict exists $config $key]} {
        dict unset config $key
        puts "Config unset: $key"
        return 1
    }
    return 0
}

# YAML 파일에서 설정 로드 (시뮬레이션)
proc config::load_file {filename} {
    global config
    if {![file exists $filename]} {
        puts "Warning: Config file not found: $filename"
        return 0
    }
    set fh [open $filename r]
    while {[gets $fh line] >= 0} {
        set line [string trim $line]
        if {[string match "#*" $line] || $line eq ""} continue
        if {[regexp {^(\S+):\s+(.+)$} $line -> key val]} {
            dict set config $key [string trim $val]
        }
    }
    close $fh
    puts "Config loaded from: $filename"
    return 1
}

# 설정 전체 출력
proc config::dump {} {
    global config
    puts "=== SDACS Configuration ==="
    dict for {key val} $config {
        puts "  $key: $val"
    }
    puts "==========================="
}

# 설정 섹션별 필터
proc config::get_section {prefix} {
    global config
    set result [dict create]
    dict for {key val} $config {
        if {[string match "${prefix}.*" $key]} {
            dict set result $key $val
        }
    }
    return $result
}

# 메인 실행
config::init
config::set_value "drones.default_count" 20
config::set_value "simulation.duration" 7200
set drone_config [config::get_section "drones"]
puts "Drone config entries: [dict size $drone_config]"
config::dump
