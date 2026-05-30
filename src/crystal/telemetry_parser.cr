# SDACS Telemetry Parser — Crystal
# Parses drone telemetry packets with CRC verification.

require "digest/crc32"

# Telemetry packet structure
struct Telemetry
  getter drone_id : UInt16
  getter timestamp : UInt64
  getter latitude : Float64
  getter longitude : Float64
  getter altitude : Float32
  getter velocity_x : Float32
  getter velocity_y : Float32
  getter velocity_z : Float32
  getter battery_pct : UInt8
  getter motor_rpm : StaticArray(UInt16, 4)
  getter crc : UInt32

  def initialize(
    @drone_id : UInt16,
    @timestamp : UInt64,
    @latitude : Float64,
    @longitude : Float64,
    @altitude : Float32,
    @velocity_x : Float32,
    @velocity_y : Float32,
    @velocity_z : Float32,
    @battery_pct : UInt8,
    @motor_rpm : StaticArray(UInt16, 4),
    @crc : UInt32
  )
  end
end

# CRC32 verification helper
module CRC
  CRC32_POLY = 0xEDB88320_u32

  def self.compute(data : Bytes) : UInt32
    crc = 0xFFFFFFFF_u32
    data.each do |byte|
      crc ^= byte.to_u32
      8.times do
        if crc & 1 == 1
          crc = (crc >> 1) ^ CRC32_POLY
        else
          crc >>= 1
        end
      end
    end
    ~crc
  end

  def self.verify(data : Bytes, expected : UInt32) : Bool
    compute(data) == expected
  end
end

# Telemetry packet parser
class TelemetryParser
  PACKET_MAGIC = 0xA5C3_u16
  MIN_PACKET_SIZE = 48

  def initialize
    @parse_errors = 0_u64
    @packets_parsed = 0_u64
  end

  def parse(buffer : Bytes) : Telemetry?
    return nil if buffer.size < MIN_PACKET_SIZE

    magic = IO::ByteFormat::LittleEndian.decode(UInt16, buffer[0, 2])
    return nil unless magic == PACKET_MAGIC

    drone_id  = IO::ByteFormat::LittleEndian.decode(UInt16, buffer[2, 2])
    timestamp = IO::ByteFormat::LittleEndian.decode(UInt64, buffer[4, 8])
    lat       = IO::ByteFormat::LittleEndian.decode(Float64, buffer[12, 8])
    lon       = IO::ByteFormat::LittleEndian.decode(Float64, buffer[20, 8])
    alt       = IO::ByteFormat::LittleEndian.decode(Float32, buffer[28, 4])
    vx        = IO::ByteFormat::LittleEndian.decode(Float32, buffer[32, 4])
    vy        = IO::ByteFormat::LittleEndian.decode(Float32, buffer[36, 4])
    vz        = IO::ByteFormat::LittleEndian.decode(Float32, buffer[40, 4])
    batt      = buffer[44]
    stored_crc = IO::ByteFormat::LittleEndian.decode(UInt32, buffer[buffer.size - 4, 4])

    payload = buffer[0, buffer.size - 4]
    unless CRC.verify(payload, stored_crc)
      @parse_errors += 1
      return nil
    end

    rpms = StaticArray(UInt16, 4).new(0_u16)

    @packets_parsed += 1
    Telemetry.new(drone_id, timestamp, lat, lon, alt, vx, vy, vz, batt, rpms, stored_crc)
  end

  def stats
    {parsed: @packets_parsed, errors: @parse_errors}
  end
end
