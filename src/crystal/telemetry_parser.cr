# Phase 576 — Crystal telemetry parser struct with CRC validation
# SDACS drone telemetry parsing and CRC integrity checking

# CRC calculation utilities for telemetry validation
module CRCUtil
  CRC32_POLY = 0xEDB88320_u32

  # Compute CRC checksum over a byte slice
  def self.compute_crc32(data : Bytes) : UInt32
    crc = 0xFFFFFFFF_u32
    data.each do |byte|
      crc ^= byte.to_u32
      8.times do
        if (crc & 1_u32) != 0
          crc = (crc >> 1) ^ CRC32_POLY
        else
          crc >>= 1
        end
      end
    end
    crc ^ 0xFFFFFFFF_u32
  end
end

# drone telemetry message struct — Phase 576
struct Telemetry
  property drone_id : UInt32
  property timestamp_ms : UInt64
  property latitude : Float64
  property longitude : Float64
  property altitude_m : Float32
  property velocity_x : Float32
  property velocity_y : Float32
  property velocity_z : Float32
  property battery_pct : UInt8
  property status_flags : UInt16
  property crc_checksum : UInt32

  def initialize(
    @drone_id : UInt32,
    @timestamp_ms : UInt64,
    @latitude : Float64,
    @longitude : Float64,
    @altitude_m : Float32,
    @velocity_x : Float32,
    @velocity_y : Float32,
    @velocity_z : Float32,
    @battery_pct : UInt8,
    @status_flags : UInt16,
    @crc_checksum : UInt32 = 0_u32
  )
  end

  # Serialize fields to bytes for CRC computation (excludes CRC field itself)
  def to_payload_bytes : Bytes
    io = IO::Memory.new
    io.write_bytes(@drone_id, IO::ByteFormat::LittleEndian)
    io.write_bytes(@timestamp_ms, IO::ByteFormat::LittleEndian)
    io.write_bytes(@latitude, IO::ByteFormat::LittleEndian)
    io.write_bytes(@longitude, IO::ByteFormat::LittleEndian)
    io.write_bytes(@altitude_m, IO::ByteFormat::LittleEndian)
    io.write_bytes(@velocity_x, IO::ByteFormat::LittleEndian)
    io.write_bytes(@velocity_y, IO::ByteFormat::LittleEndian)
    io.write_bytes(@velocity_z, IO::ByteFormat::LittleEndian)
    io.write_bytes(@battery_pct, IO::ByteFormat::LittleEndian)
    io.write_bytes(@status_flags, IO::ByteFormat::LittleEndian)
    io.to_slice
  end

  # Compute CRC over payload bytes
  def compute_crc : UInt32
    CRCUtil.compute_crc32(to_payload_bytes)
  end

  # Validate stored CRC against computed CRC
  def crc_valid? : Bool
    @crc_checksum == compute_crc
  end

  # Attach computed CRC to this struct (returns new instance)
  def with_crc : Telemetry
    Telemetry.new(
      @drone_id, @timestamp_ms, @latitude, @longitude,
      @altitude_m, @velocity_x, @velocity_y, @velocity_z,
      @battery_pct, @status_flags, compute_crc
    )
  end
end

# TelemetryParser handles raw byte stream parsing for drone packets
class TelemetryParser
  PACKET_MAGIC = 0xABCD_u16
  MIN_PACKET_BYTES = 47

  def initialize
    @buffer = IO::Memory.new
    @parse_errors = 0_u32
    @packets_parsed = 0_u32
  end

  getter parse_errors
  getter packets_parsed

  # Parse a raw byte slice into a Telemetry struct; returns nil on error
  def parse(raw : Bytes) : Telemetry?
    return nil if raw.size < MIN_PACKET_BYTES

    io = IO::Memory.new(raw)
    magic = io.read_bytes(UInt16, IO::ByteFormat::LittleEndian)
    unless magic == PACKET_MAGIC
      @parse_errors += 1
      return nil
    end

    drone_id   = io.read_bytes(UInt32, IO::ByteFormat::LittleEndian)
    ts         = io.read_bytes(UInt64, IO::ByteFormat::LittleEndian)
    lat        = io.read_bytes(Float64, IO::ByteFormat::LittleEndian)
    lon        = io.read_bytes(Float64, IO::ByteFormat::LittleEndian)
    alt        = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    vx         = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    vy         = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    vz         = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    batt       = io.read_bytes(UInt8,   IO::ByteFormat::LittleEndian)
    flags      = io.read_bytes(UInt16,  IO::ByteFormat::LittleEndian)
    crc_stored = io.read_bytes(UInt32,  IO::ByteFormat::LittleEndian)

    packet = Telemetry.new(drone_id, ts, lat, lon, alt, vx, vy, vz, batt, flags, crc_stored)

    unless packet.crc_valid?
      @parse_errors += 1
      return nil
    end

    @packets_parsed += 1
    packet
  end
end
