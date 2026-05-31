# telemetry_parser.cr - Crystal telemetry parser for SDACS
# High-performance binary telemetry parsing with CRC validation

require "io"
require "json"

# Telemetry frame structure for drone data
struct TelemetryFrame
  property drone_id : String
  property timestamp : Float64
  property latitude : Float64
  property longitude : Float64
  property altitude : Float32
  property velocity_x : Float32
  property velocity_y : Float32
  property velocity_z : Float32
  property battery : UInt8
  property status : UInt8
  property crc : UInt32

  def initialize(@drone_id, @timestamp, @latitude, @longitude,
                 @altitude, @velocity_x, @velocity_y, @velocity_z,
                 @battery, @status, @crc)
  end

  def to_json_object
    {
      drone_id:   @drone_id,
      timestamp:  @timestamp,
      position:   {lat: @latitude, lon: @longitude, alt: @altitude},
      velocity:   {vx: @velocity_x, vy: @velocity_y, vz: @velocity_z},
      battery:    @battery,
      status:     @status,
      crc_valid:  crc_valid?
    }
  end

  def crc_valid? : Bool
    computed = TelemetryParser.compute_crc(self)
    computed == @crc
  end
end

# CRC32 lookup table for telemetry validation
CRC_TABLE = Array(UInt32).new(256) do |i|
  c = i.to_u32
  8.times { c = (c & 1) != 0 ? 0xEDB88320_u32 ^ (c >> 1) : c >> 1 }
  c
end

# Main telemetry parser class
class TelemetryParser
  FRAME_MAGIC = 0xDEADBEEF_u32
  FRAME_SIZE  = 64

  getter frames_parsed : Int32 = 0
  getter crc_errors : Int32 = 0
  getter parse_errors : Int32 = 0

  def initialize
    @buffer = IO::Memory.new
    @frames = [] of TelemetryFrame
  end

  # Parse raw binary telemetry data
  def parse(data : Bytes) : Array(TelemetryFrame)
    results = [] of TelemetryFrame
    offset = 0

    while offset + FRAME_SIZE <= data.size
      frame = parse_frame(data, offset)
      if frame
        results << frame
        @frames_parsed += 1
      end
      offset += FRAME_SIZE
    end

    @frames.concat(results)
    results
  end

  # Parse individual telemetry frame
  def parse_frame(data : Bytes, offset : Int32) : TelemetryFrame?
    magic = IO::ByteFormat::LittleEndian.decode(UInt32, data[offset, 4])
    return nil unless magic == FRAME_MAGIC

    drone_id  = String.new(data[offset + 4, 8]).strip('\0')
    timestamp = IO::ByteFormat::LittleEndian.decode(Float64, data[offset + 12, 8])
    lat       = IO::ByteFormat::LittleEndian.decode(Float64, data[offset + 20, 8])
    lon       = IO::ByteFormat::LittleEndian.decode(Float64, data[offset + 28, 8])
    alt       = IO::ByteFormat::LittleEndian.decode(Float32, data[offset + 36, 4])
    vx        = IO::ByteFormat::LittleEndian.decode(Float32, data[offset + 40, 4])
    vy        = IO::ByteFormat::LittleEndian.decode(Float32, data[offset + 44, 4])
    vz        = IO::ByteFormat::LittleEndian.decode(Float32, data[offset + 48, 4])
    battery   = data[offset + 52]
    status    = data[offset + 53]
    crc_val   = IO::ByteFormat::LittleEndian.decode(UInt32, data[offset + 60, 4])

    TelemetryFrame.new(drone_id, timestamp, lat, lon, alt, vx, vy, vz, battery, status, crc_val)
  rescue
    @parse_errors += 1
    nil
  end

  # Compute CRC32 of telemetry frame
  def self.compute_crc(frame : TelemetryFrame) : UInt32
    data = frame.drone_id.bytes
    crc = 0xFFFFFFFF_u32
    data.each do |byte|
      crc = CRC_TABLE[((crc ^ byte) & 0xFF).to_i] ^ (crc >> 8)
    end
    ~crc
  end

  # Get parser statistics
  def stats : Hash(String, Int32)
    {
      "frames_parsed" => @frames_parsed,
      "crc_errors"    => @crc_errors,
      "parse_errors"  => @parse_errors,
      "total_frames"  => @frames.size
    }
  end
end
