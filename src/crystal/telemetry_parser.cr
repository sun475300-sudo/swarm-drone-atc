# Telemetry Parser — Crystal for SDACS low-latency packet processing
# Phase 576

require "io"

# CRC-16/CCITT checksum
module CRC
  TABLE = Array(UInt16).new(256) do |i|
    crc = i.to_u16
    8.times { crc = (crc & 1) != 0 ? (crc >> 1) ^ 0xA001_u16 : crc >> 1 }
    crc
  end

  def self.compute(data : Bytes) : UInt16
    crc = 0xFFFF_u16
    data.each { |b| crc = (crc >> 8) ^ TABLE[(crc ^ b) & 0xFF] }
    crc
  end
end

# Telemetry frame structure
struct Telemetry
  property drone_id  : String
  property timestamp : Int64
  property lat       : Float64
  property lon       : Float64
  property alt_m     : Float32
  property batt_pct  : Float32
  property speed_mps : Float32
  property heading   : Float32
  property status    : UInt8
  property crc       : UInt16

  def initialize(@drone_id, @timestamp, @lat, @lon, @alt_m, @batt_pct, @speed_mps, @heading, @status, @crc = 0_u16)
  end

  def valid? : Bool
    payload = "#{drone_id}#{timestamp}#{lat}#{lon}#{alt_m}#{batt_pct}".to_slice
    computed_crc = CRC.compute(payload)
    computed_crc == crc || crc == 0_u16
  end
end

# Parser for binary telemetry packets
class TelemetryParser
  MAGIC_HEADER = 0xABCD_u16
  VERSION      = 0x01_u8

  @buffer : Array(UInt8)

  def initialize
    @buffer = [] of UInt8
  end

  def parse(raw : Bytes) : Array(Telemetry)
    frames = [] of Telemetry
    raw.each { |b| @buffer << b }

    while @buffer.size >= 48
      if @buffer[0] == 0xAB && @buffer[1] == 0xCD
        frame = extract_frame
        frames << frame if frame
      else
        @buffer.shift
      end
    end
    frames
  end

  private def extract_frame : Telemetry?
    return nil if @buffer.size < 48

    timestamp = 0_i64
    4.times { |i| timestamp = (timestamp << 8) | @buffer[2 + i] }

    telemetry = Telemetry.new(
      drone_id:  "D-#{@buffer[6..9].map(&.chr).join}",
      timestamp: timestamp,
      lat:       0.0,
      lon:       0.0,
      alt_m:     @buffer[20].to_f32,
      batt_pct:  @buffer[21].to_f32,
      speed_mps: @buffer[22].to_f32,
      heading:   @buffer[23].to_f32,
      status:    @buffer[24],
      crc:       (@buffer[46].to_u16 << 8) | @buffer[47]
    )
    48.times { @buffer.shift }
    telemetry
  end
end
