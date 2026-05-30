# Phase 576: telemetry_parser — Crystal 기반 텔레메트리 파서
# SDACS Telemetry Parser with CRC validation

require "digest"

# 텔레메트리 패킷 구조체
struct TelemetryPacket
  property drone_id   : UInt32
  property timestamp  : Float64
  property lat        : Float64
  property lon        : Float64
  property alt        : Float64
  property battery    : Float32
  property speed      : Float32
  property heading    : Float32
  property crc        : UInt32

  def initialize(@drone_id, @timestamp, @lat, @lon, @alt, @battery, @speed, @heading, @crc = 0_u32)
  end

  def to_payload_string : String
    "#{drone_id}|#{timestamp}|#{lat}|#{lon}|#{alt}|#{battery}|#{speed}|#{heading}"
  end
end

# Telemetry 구조체 (별칭)
alias Telemetry = TelemetryPacket

# CRC32 계산기
module CRCCalculator
  # IEEE 802.3 CRC32 다항식
  POLY = 0xEDB88320_u32

  def self.compute(data : String) : UInt32
    crc = 0xFFFFFFFF_u32
    data.each_byte do |byte|
      crc ^= byte.to_u32
      8.times do
        if (crc & 1_u32) != 0
          crc = (crc >> 1) ^ POLY
        else
          crc >>= 1
        end
      end
    end
    ~crc
  end

  # CRC 검증
  def self.verify(data : String, expected_crc : UInt32) : Bool
    compute(data) == expected_crc
  end
end

# 텔레메트리 직렬화/역직렬화
module TelemetrySerializer
  def self.serialize(pkt : TelemetryPacket) : String
    payload = pkt.to_payload_string
    crc = CRCCalculator.compute(payload)
    "#{payload}|#{crc}"
  end

  def self.deserialize(line : String) : TelemetryPacket?
    parts = line.split("|")
    return nil unless parts.size >= 9

    begin
      drone_id  = parts[0].to_u32
      timestamp = parts[1].to_f64
      lat       = parts[2].to_f64
      lon       = parts[3].to_f64
      alt       = parts[4].to_f64
      battery   = parts[5].to_f32
      speed     = parts[6].to_f32
      heading   = parts[7].to_f32
      crc       = parts[8].to_u32
      TelemetryPacket.new(drone_id, timestamp, lat, lon, alt, battery, speed, heading, crc)
    rescue
      nil
    end
  end
end

# 텔레메트리 스트림 파서
class TelemetryStreamParser
  getter parsed_count   : Int32 = 0
  getter invalid_count  : Int32 = 0
  getter crc_fail_count : Int32 = 0

  def initialize
    @buffer = [] of TelemetryPacket
  end

  def parse_line(line : String) : TelemetryPacket?
    line = line.strip
    return nil if line.empty?

    pkt = TelemetrySerializer.deserialize(line)
    if pkt.nil?
      @invalid_count += 1
      return nil
    end

    # CRC 검증
    payload = pkt.to_payload_string
    unless CRCCalculator.verify(payload, pkt.crc)
      @crc_fail_count += 1
      return nil
    end

    @parsed_count += 1
    @buffer << pkt
    pkt
  end

  def parse_batch(lines : Array(String)) : Array(TelemetryPacket)
    lines.compact_map { |l| parse_line(l) }
  end

  def buffer : Array(TelemetryPacket)
    @buffer.dup
  end

  def stats : Hash(String, Int32)
    {
      "parsed"    => @parsed_count,
      "invalid"   => @invalid_count,
      "crc_fail"  => @crc_fail_count,
      "buffered"  => @buffer.size,
    }
  end

  def average_battery : Float32
    return 0.0_f32 if @buffer.empty?
    total = @buffer.sum(&.battery)
    total / @buffer.size
  end
end

# 메인 실행
puts "SDACS Telemetry Parser — Phase 576\n"

parser = TelemetryStreamParser.new

# 테스트 패킷 생성 및 직렬화
test_packets = [
  TelemetryPacket.new(0_u32, 1748563200.0, 37.500, 127.000, 50.0, 95.0_f32, 5.0_f32, 90.0_f32),
  TelemetryPacket.new(1_u32, 1748563200.1, 37.501, 127.001, 52.0, 88.5_f32, 6.0_f32, 180.0_f32),
  TelemetryPacket.new(2_u32, 1748563200.2, 37.502, 127.002, 55.0, 72.0_f32, 4.5_f32, 270.0_f32),
]

serialized_lines = test_packets.map { |pkt| TelemetrySerializer.serialize(pkt) }
puts "직렬화된 패킷 (#{serialized_lines.size}개):"
serialized_lines.each { |l| puts "  #{l[0..60]}..." }

# 파싱 및 CRC 검증
puts "\n패킷 파싱 및 CRC 검증:"
results = parser.parse_batch(serialized_lines)
results.each do |pkt|
  puts "  드론#{pkt.drone_id}: alt=#{pkt.alt}m bat=#{pkt.battery}%"
end

puts "\n통계: #{parser.stats}"
puts "평균 배터리: #{parser.average_battery.round(1)}%"
puts "텔레메트리 파서 완료."
