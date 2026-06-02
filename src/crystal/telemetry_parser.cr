# Phase 576: Telemetry Parser — Crystal Lang
# SDACS high-performance telemetry frame parsing with CRC validation

require "io"
require "bit_array"

module SDACS
  # CRC-16 CCITT implementation for frame validation
  module CRC
    CRC16_TABLE = begin
      table = Array(UInt16).new(256, 0u16)
      256.times do |i|
        crc = i.to_u16
        8.times do
          if (crc & 0x0001u16) != 0
            crc = (crc >> 1) ^ 0x8408u16
          else
            crc >>= 1
          end
        end
        table[i] = crc
      end
      table
    end

    def self.compute(data : Bytes) : UInt16
      crc = 0xFFFFu16
      data.each do |byte|
        crc = (crc >> 8) ^ CRC16_TABLE[(crc ^ byte) & 0xFF]
      end
      crc ^ 0xFFFFu16
    end

    def self.valid?(data : Bytes, expected : UInt16) : Bool
      compute(data) == expected
    end
  end

  # Telemetry frame structure
  struct Telemetry
    MAGIC        = 0xABCDu16
    HEADER_SIZE  = 12

    getter drone_id   : UInt16
    getter timestamp  : UInt64
    getter latitude   : Float32
    getter longitude  : Float32
    getter altitude   : Float32
    getter speed      : Float32
    getter heading    : Float32
    getter battery    : Float32
    getter sequence   : UInt32
    getter crc        : UInt16

    def initialize(
      @drone_id : UInt16,
      @timestamp : UInt64,
      @latitude : Float32,
      @longitude : Float32,
      @altitude : Float32,
      @speed : Float32,
      @heading : Float32,
      @battery : Float32,
      @sequence : UInt32,
      @crc : UInt16 = 0u16
    )
    end

    def to_bytes : Bytes
      io = IO::Memory.new
      io.write_bytes(MAGIC, IO::ByteFormat::LittleEndian)
      io.write_bytes(@drone_id, IO::ByteFormat::LittleEndian)
      io.write_bytes(@timestamp, IO::ByteFormat::LittleEndian)
      io.write_bytes(@latitude, IO::ByteFormat::LittleEndian)
      io.write_bytes(@longitude, IO::ByteFormat::LittleEndian)
      io.write_bytes(@altitude, IO::ByteFormat::LittleEndian)
      io.write_bytes(@speed, IO::ByteFormat::LittleEndian)
      io.write_bytes(@heading, IO::ByteFormat::LittleEndian)
      io.write_bytes(@battery, IO::ByteFormat::LittleEndian)
      io.write_bytes(@sequence, IO::ByteFormat::LittleEndian)
      payload = io.to_slice
      crc_val = CRC.compute(payload)
      io.write_bytes(crc_val, IO::ByteFormat::LittleEndian)
      io.to_slice
    end

    def self.parse(data : Bytes) : Telemetry?
      return nil if data.size < 44

      io = IO::Memory.new(data)
      magic = io.read_bytes(UInt16, IO::ByteFormat::LittleEndian)
      return nil unless magic == MAGIC

      payload = data[0...-2]
      expected_crc = IO::Memory.new(data[-2..]).read_bytes(UInt16, IO::ByteFormat::LittleEndian)
      return nil unless CRC.valid?(payload, expected_crc)

      new(
        drone_id:  io.read_bytes(UInt16, IO::ByteFormat::LittleEndian),
        timestamp: io.read_bytes(UInt64, IO::ByteFormat::LittleEndian),
        latitude:  io.read_bytes(Float32, IO::ByteFormat::LittleEndian),
        longitude: io.read_bytes(Float32, IO::ByteFormat::LittleEndian),
        altitude:  io.read_bytes(Float32, IO::ByteFormat::LittleEndian),
        speed:     io.read_bytes(Float32, IO::ByteFormat::LittleEndian),
        heading:   io.read_bytes(Float32, IO::ByteFormat::LittleEndian),
        battery:   io.read_bytes(Float32, IO::ByteFormat::LittleEndian),
        sequence:  io.read_bytes(UInt32, IO::ByteFormat::LittleEndian),
        crc:       expected_crc
      )
    end

    def valid? : Bool
      battery >= 0.0_f32 && battery <= 100.0_f32 &&
      altitude >= 0.0_f32 &&
      speed >= 0.0_f32
    end

    def to_s : String
      "Telemetry(drone=#{drone_id} lat=#{latitude} lon=#{longitude} " \
      "alt=#{altitude}m spd=#{speed}m/s bat=#{battery}% seq=#{sequence})"
    end
  end

  # Streaming telemetry parser
  class TelemetryParser
    def initialize
      @buffer = Bytes.new(0)
      @parsed_count = 0u64
      @error_count = 0u64
    end

    def feed(data : Bytes) : Array(Telemetry)
      @buffer = @buffer + data
      frames = [] of Telemetry
      loop do
        frame = extract_frame
        break unless frame
        frames << frame
        @parsed_count += 1
      end
      frames
    end

    def stats : NamedTuple(parsed: UInt64, errors: UInt64)
      {parsed: @parsed_count, errors: @error_count}
    end

    private def extract_frame : Telemetry?
      magic_bytes = Bytes[0xCD, 0xAB]
      idx = find_magic(@buffer, magic_bytes)
      return nil unless idx

      @buffer = @buffer[idx..]
      return nil if @buffer.size < 44

      if frame = Telemetry.parse(@buffer[0...44])
        @buffer = @buffer[44..]
        frame
      else
        @error_count += 1
        @buffer = @buffer[2..]
        nil
      end
    end

    private def find_magic(data : Bytes, magic : Bytes) : Int32?
      (0..data.size - magic.size).each do |i|
        return i if data[i...i + magic.size] == magic
      end
      nil
    end
  end
end
