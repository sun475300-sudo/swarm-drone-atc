# frozen_string_literal: true

# SDACS 설정 검증기 — Ruby
# ==========================
# YAML 시뮬레이션 설정 검증 + 스키마 유효성 + 자동 교정
#
# 기능:
#   - YAML 설정 스키마 검증
#   - 값 범위 검사 + 자동 클램핑
#   - 의존성 검증 (드론 수 ↔ 시뮬레이션 기간)
#   - 설정 마이그레이션 (구버전 → 신버전)
#   - 검증 리포트 생성

require 'yaml'
require 'json'

module SDACS
  # 설정 스키마 정의
  SCHEMA = {
    'simulation' => {
      'duration' => { type: :float, min: 10, max: 3600, default: 300 },
      'tick_rate' => { type: :float, min: 0.01, max: 10, default: 0.1 },
      'seed' => { type: :integer, min: 0, max: 2**32, default: 42 }
    },
    'drones' => {
      'default_count' => { type: :integer, min: 1, max: 10_000, default: 50 },
      'max_speed_ms' => { type: :float, min: 1, max: 50, default: 15 },
      'min_altitude' => { type: :float, min: 0, max: 50, default: 10 },
      'max_altitude' => { type: :float, min: 50, max: 500, default: 120 },
      'battery_capacity_wh' => { type: :float, min: 50, max: 5000, default: 500 }
    },
    'airspace' => {
      'min_horizontal_sep' => { type: :float, min: 10, max: 200, default: 50 },
      'min_vertical_sep' => { type: :float, min: 5, max: 100, default: 15 },
      'cpa_lookahead_sec' => { type: :float, min: 10, max: 300, default: 90 },
      'area_size' => { type: :float, min: 100, max: 100_000, default: 1000 }
    },
    'apf' => {
      'k_attract' => { type: :float, min: 0.01, max: 10, default: 1.0 },
      'k_repulse' => { type: :float, min: 1, max: 1000, default: 100 },
      'repulse_range' => { type: :float, min: 10, max: 200, default: 50 }
    },
    'wind' => {
      'base_speed' => { type: :float, min: 0, max: 30, default: 5 },
      'gust_factor' => { type: :float, min: 1.0, max: 3.0, default: 1.5 },
      'direction_deg' => { type: :float, min: 0, max: 360, default: 0 }
    }
  }.freeze

  # 검증 결과
  class ValidationResult
    attr_reader :errors, :warnings, :fixes, :valid

    def initialize
      @errors = []
      @warnings = []
      @fixes = []
      @valid = true
    end

    def add_error(path, message)
      @errors << { path: path, message: message }
      @valid = false
    end

    def add_warning(path, message)
      @warnings << { path: path, message: message }
    end

    def add_fix(path, old_value, new_value, reason)
      @fixes << { path: path, old: old_value, new: new_value, reason: reason }
    end

    def to_s
      lines = ["=== SDACS 설정 검증 결과 ==="]
      lines << "상태: #{@valid ? 'VALID' : 'INVALID'}"
      lines << "오류: #{@errors.size}, 경고: #{@warnings.size}, 자동 수정: #{@fixes.size}"

      @errors.each { |e| lines << "  ERROR: #{e[:path]} — #{e[:message]}" }
      @warnings.each { |w| lines << "  WARN:  #{w[:path]} — #{w[:message]}" }
      @fixes.each { |f| lines << "  FIX:   #{f[:path]}: #{f[:old]} → #{f[:new]} (#{f[:reason]})" }

      lines.join("\n")
    end

    def to_hash
      { valid: @valid, errors: @errors, warnings: @warnings, fixes: @fixes }
    end
  end

  # 설정 검증기
  class ConfigValidator
    attr_reader :result

    def initialize(config_hash)
      @config = deep_dup(config_hash)
      @result = ValidationResult.new
    end

    # 전체 검증 실행
    def validate(auto_fix: true)
      SCHEMA.each do |section, fields|
        unless @config.key?(section)
          @result.add_warning(section, "섹션 누락 — 기본값 사용")
          @config[section] = {} if auto_fix
        end

        fields.each do |key, spec|
          path = "#{section}.#{key}"
          value = @config.dig(section, key)

          if value.nil?
            if auto_fix
              @config[section] ||= {}
              @config[section][key] = spec[:default]
              @result.add_fix(path, nil, spec[:default], "기본값 적용")
            else
              @result.add_error(path, "필수 값 누락")
            end
            next
          end

          # 타입 검증
          unless valid_type?(value, spec[:type])
            if auto_fix
              fixed = coerce(value, spec[:type])
              if fixed
                @result.add_fix(path, value, fixed, "타입 변환")
                @config[section][key] = fixed
                value = fixed
              else
                @result.add_error(path, "잘못된 타입: #{value.class} (기대: #{spec[:type]})")
                next
              end
            else
              @result.add_error(path, "잘못된 타입: #{value.class} (기대: #{spec[:type]})")
              next
            end
          end

          # 범위 검증
          if spec[:min] && value < spec[:min]
            if auto_fix
              @result.add_fix(path, value, spec[:min], "최소값 클램핑")
              @config[section][key] = spec[:min]
            else
              @result.add_error(path, "#{value} < 최소값 #{spec[:min]}")
            end
          end

          if spec[:max] && value > spec[:max]
            if auto_fix
              @result.add_fix(path, value, spec[:max], "최대값 클램핑")
              @config[section][key] = spec[:max]
            else
              @result.add_error(path, "#{value} > 최대값 #{spec[:max]}")
            end
          end
        end
      end

      # 교차 의존성 검증
      validate_dependencies

      @result
    end

    # 검증된 설정 반환
    def validated_config
      @config
    end

    private

    def validate_dependencies
      drones = @config.dig('drones', 'default_count') || 50
      area = @config.dig('airspace', 'area_size') || 1000

      density = drones.to_f / (area * area) * 1_000_000
      if density > 100
        @result.add_warning('drones.default_count',
          "밀도 #{density.round(1)}/km² — 매우 높음 (성능 저하 가능)")
      end

      min_alt = @config.dig('drones', 'min_altitude') || 10
      max_alt = @config.dig('drones', 'max_altitude') || 120
      if min_alt >= max_alt
        @result.add_error('drones.min_altitude', "최소 고도(#{min_alt}) >= 최대 고도(#{max_alt})")
      end

      sep = @config.dig('airspace', 'min_horizontal_sep') || 50
      repulse = @config.dig('apf', 'repulse_range') || 50
      if repulse < sep
        @result.add_warning('apf.repulse_range',
          "척력 범위(#{repulse}) < 최소 분리(#{sep}) — APF 효과 부족")
      end
    end

    def valid_type?(value, expected)
      case expected
      when :float then value.is_a?(Numeric)
      when :integer then value.is_a?(Integer)
      when :string then value.is_a?(String)
      when :boolean then [true, false].include?(value)
      else true
      end
    end

    def coerce(value, target)
      case target
      when :float then Float(value) rescue nil
      when :integer then Integer(value) rescue nil
      when :string then value.to_s
      else nil
      end
    end

    def deep_dup(hash)
      hash.each_with_object({}) do |(k, v), h|
        h[k] = v.is_a?(Hash) ? deep_dup(v) : v
      end
    end
  end
end
