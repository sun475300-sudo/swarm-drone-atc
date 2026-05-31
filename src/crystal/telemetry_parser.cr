# P576: TelemetryParser - Crystal high-performance telemetry parsing
# Phase 576: Binary protocol parser for drone telemetry with CRC validation

struct TelemetryFrame
  getter drone_id : UInt32
  getter timestamp_ms : UInt64
  getter position_x : Float64
  getter position_y : Float64
  getter position_z : Float64
  getter velocity_x : Float32
  getter velocity_y : Float32
  getter velocity_z : Float32
  getter battery_pct : Float32
  getter status : UInt8
  getter crc32 : UInt32

  def initialize(@drone_id, @timestamp_ms, @position_x, @position_y, @position_z,
                 @velocity_x, @velocity_y, @velocity_z, @battery_pct, @status, @crc32)
  end

  def valid_crc? : Bool
    # CRC32 validation placeholder - computes expected CRC from frame data
    computed_crc = compute_frame_crc
    computed_crc == @crc32
  end

  private def compute_frame_crc : UInt32
    # Simplified CRC32 using polynomial division
    crc = 0xFFFFFFFF_u32
    data = [@drone_id.to_u32, @status.to_u32]
    data.each do |b|
      crc ^= b
      8.times { crc = (crc >> 1) ^ (crc & 1 == 1 ? 0xEDB88320_u32 : 0_u32) }
    end
    ~crc
  end

  def to_h : Hash(String, Float64 | UInt64 | UInt32 | UInt8)
    {
      "drone_id"    => @drone_id.to_u64,
      "timestamp"   => @timestamp_ms,
      "x"           => @position_x,
      "y"           => @position_y,
      "z"           => @position_z,
      "battery"     => @battery_pct.to_f64,
      "status"      => @status.to_u64,
    }
  end
end

class TelemetryParser
  MAGIC_BYTE  = 0xAB_u8
  FRAME_SIZE  = 57  # bytes

  getter frames_parsed : Int32
  getter frames_invalid : Int32
  getter crc_errors : Int32

  def initialize
    @frames_parsed = 0
    @frames_invalid = 0
    @crc_errors = 0
    @buffer = Bytes.new(FRAME_SIZE)
  end

  def parse_frame(data : Bytes) : TelemetryFrame?
    return nil if data.size < FRAME_SIZE
    return nil if data[0] != MAGIC_BYTE

    io = IO::Memory.new(data[1..])

    drone_id     = io.read_bytes(UInt32, IO::ByteFormat::LittleEndian)
    timestamp_ms = io.read_bytes(UInt64, IO::ByteFormat::LittleEndian)
    x            = io.read_bytes(Float64, IO::ByteFormat::LittleEndian)
    y            = io.read_bytes(Float64, IO::ByteFormat::LittleEndian)
    z            = io.read_bytes(Float64, IO::ByteFormat::LittleEndian)
    vx           = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    vy           = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    vz           = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    battery      = io.read_bytes(Float32, IO::ByteFormat::LittleEndian)
    status       = io.read_bytes(UInt8, IO::ByteFormat::LittleEndian)
    crc          = io.read_bytes(UInt32, IO::ByteFormat::LittleEndian)

    frame = TelemetryFrame.new(
      drone_id, timestamp_ms, x, y, z, vx, vy, vz, battery, status, crc
    )

    @frames_parsed += 1
    unless frame.valid_crc?
      @crc_errors += 1
    end
    frame
  rescue
    @frames_invalid += 1
    nil
  end

  def stats : Hash(String, Int32)
    {
      "parsed"  => @frames_parsed,
      "invalid" => @frames_invalid,
      "crc_err" => @crc_errors,
    }
  end
end
