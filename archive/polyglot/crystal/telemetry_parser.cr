# Phase 576: Telemetry Parser — Crystal
# 드론 텔레메트리 바이너리 프로토콜 파서.
# MAVLink 유사 프레임 구조 해석.

# ─── 텔레메트리 프레임 구조 ───
# | STX (1) | LEN (1) | SEQ (1) | SYS (1) | COMP (1) | MSG_ID (1) | PAYLOAD (N) | CRC (2) |

struct TelemetryFrame
  property stx : UInt8
  property length : UInt8
  property sequence : UInt8
  property system_id : UInt8
  property component_id : UInt8
  property message_id : UInt8
  property payload : Bytes
  property crc : UInt16

  def initialize(@stx, @length, @sequence, @system_id, @component_id, @message_id, @payload, @crc)
  end

  def valid?
    @stx == 0xFE_u8 && computed_crc == @crc
  end

  def computed_crc : UInt16
    crc = CRC16.new
    crc.update(@length)
    crc.update(@sequence)
    crc.update(@system_id)
    crc.update(@component_id)
    crc.update(@message_id)
    @payload.each { |b| crc.update(b) }
    crc.value
  end
end

# ─── CRC16 계산기 ───
class CRC16
  @value : UInt16

  def initialize
    @value = 0xFFFF_u16
  end

  def update(byte : UInt8)
    tmp = byte ^ (@value & 0xFF_u16).to_u8
    tmp ^= (tmp << 4) & 0xFF_u8
    @value = (@value >> 8) ^ (tmp.to_u16 << 8) ^ (tmp.to_u16 << 3) ^ (tmp.to_u16 >> 4)
  end

  def value : UInt16
    @value
  end
end

# ─── 메시지 유형 ───
enum MessageType : UInt8
  Heartbeat      = 0
  Position       = 1
  Attitude       = 2
  Battery        = 3
  GPS            = 4
  Wind           = 5
  Conflict       = 6
  Advisory       = 7
  MissionStatus  = 8
end

# ─── 위치 메시지 ───
struct PositionMessage
  property latitude : Float64
  property longitude : Float64
  property altitude : Float32
  property heading : Float32
  property speed : Float32

  def initialize(@latitude, @longitude, @altitude, @heading, @speed)
  end

  def to_s : String
    "Position(lat=#{@latitude}, lon=#{@longitude}, alt=#{@altitude}m, hdg=#{@heading}°, spd=#{@speed}m/s)"
  end
end

# ─── 배터리 메시지 ───
struct BatteryMessage
  property voltage : Float32
  property current : Float32
  property remaining_pct : UInt8
  property temperature : Float32

  def initialize(@voltage, @current, @remaining_pct, @temperature)
  end

  def critical? : Bool
    @remaining_pct < 15 || @voltage < 10.5
  end
end

# ─── 텔레메트리 파서 ───
class TelemetryParser
  @frames_parsed : Int32
  @errors : Int32
  @messages : Array(TelemetryFrame)

  def initialize
    @frames_parsed = 0
    @errors = 0
    @messages = [] of TelemetryFrame
  end

  def parse(data : Bytes) : Array(TelemetryFrame)
    frames = [] of TelemetryFrame
    offset = 0

    while offset < data.size - 6  # 최소 프레임 크기
      # STX 마커 찾기
      unless data[offset] == 0xFE_u8
        offset += 1
        next
      end

      length = data[offset + 1]
      frame_size = 6 + length + 2  # header + payload + crc

      if offset + frame_size > data.size
        break
      end

      payload = data[offset + 6, length]
      crc_lo = data[offset + 6 + length]
      crc_hi = data[offset + 7 + length]
      crc = (crc_hi.to_u16 << 8) | crc_lo.to_u16

      frame = TelemetryFrame.new(
        stx: data[offset],
        length: length,
        sequence: data[offset + 2],
        system_id: data[offset + 3],
        component_id: data[offset + 4],
        message_id: data[offset + 5],
        payload: payload,
        crc: crc
      )

      if frame.valid?
        frames << frame
        @frames_parsed += 1
      else
        @errors += 1
      end

      @messages << frame
      offset += frame_size
    end

    frames
  end

  def stats : Hash(String, Int32)
    {
      "frames_parsed" => @frames_parsed,
      "errors" => @errors,
      "total_messages" => @messages.size
    }
  end
end

# ─── 텔레메트리 생성기 (테스트용) ───
class TelemetryGenerator
  def initialize(@system_id : UInt8 = 1_u8)
    @sequence = 0_u8
  end

  def heartbeat : Bytes
    build_frame(MessageType::Heartbeat.value, Bytes.new(4, 0_u8))
  end

  def position(lat : Float64, lon : Float64, alt : Float32) : Bytes
    payload = IO::Memory.new
    payload.write_bytes(lat, IO::ByteFormat::LittleEndian)
    payload.write_bytes(lon, IO::ByteFormat::LittleEndian)
    payload.write_bytes(alt, IO::ByteFormat::LittleEndian)
    build_frame(MessageType::Position.value, payload.to_slice)
  end

  private def build_frame(msg_id : UInt8, payload : Bytes) : Bytes
    @sequence = @sequence &+ 1
    frame = IO::Memory.new
    frame.write_byte(0xFE_u8)         # STX
    frame.write_byte(payload.size.to_u8) # LEN
    frame.write_byte(@sequence)        # SEQ
    frame.write_byte(@system_id)       # SYS
    frame.write_byte(0_u8)             # COMP
    frame.write_byte(msg_id)           # MSG_ID
    frame.write(payload)               # PAYLOAD

    # CRC
    crc = CRC16.new
    crc.update(payload.size.to_u8)
    crc.update(@sequence)
    crc.update(@system_id)
    crc.update(0_u8)
    crc.update(msg_id)
    payload.each { |b| crc.update(b) }

    frame.write_byte((crc.value & 0xFF).to_u8)
    frame.write_byte((crc.value >> 8).to_u8)

    frame.to_slice
  end
end

# ─── 메인 ───
parser = TelemetryParser.new
gen = TelemetryGenerator.new(1_u8)

puts "=== SDACS Telemetry Parser ==="
puts "Generating test frames..."

# 테스트 프레임 생성 및 파싱
data = IO::Memory.new
10.times do |i|
  data.write(gen.heartbeat)
  data.write(gen.position(37.5 + i * 0.001, 127.0 + i * 0.001, 100.0_f32 + i * 10))
end

frames = parser.parse(data.to_slice)
puts "Parsed #{frames.size} valid frames"
parser.stats.each { |k, v| puts "  #{k}: #{v}" }
