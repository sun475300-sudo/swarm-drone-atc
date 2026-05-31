# Telemetry Parser — SDACS Phase 576
# Parses drone telemetry packets with CRC validation

require "json"

struct Telemetry
  include JSON::Serializable
  property drone_id : String
  property lat : Float64
  property lon : Float64
  property alt : Float64
  property battery : Int32
  property timestamp : Int64

  def initialize(@drone_id, @lat, @lon, @alt, @battery)
    @timestamp = Time.utc.to_unix_ms
  end
end

module CRC
  POLY = 0xEDB88320_u32

  def self.compute(data : Bytes) : UInt32
    crc = 0xFFFFFFFF_u32
    data.each do |byte|
      crc ^= byte.to_u32
      8.times do
        crc = if (crc & 1) != 0
          (crc >> 1) ^ POLY
        else
          crc >> 1
        end
      end
    end
    crc ^ 0xFFFFFFFF_u32
  end
end

class TelemetryParser
  def initialize
    @buffer = IO::Memory.new
  end

  def parse(data : Bytes) : Telemetry?
    return nil if data.size < 4
    checksum = CRC.compute(data[0..-5])
    stored = data[-4..].reinterpret_as(UInt32)[0]
    return nil unless checksum == stored
    Telemetry.from_json(String.new(data[0..-5]))
  end
end
