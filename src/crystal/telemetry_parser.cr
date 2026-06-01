# Phase 576: Telemetry Parser — 드론 텔레메트리 파서 (Crystal)
# Binary and text telemetry packet parser with CRC validation.

require "digest"
require "json"

PHASE = 576

# ── Telemetry packet structure ────────────────────────────────────

struct TelemetryPacket
  property drone_id : UInt32
  property timestamp : UInt64
  property x : Float64
  property y : Float64
  property z : Float64
  property vx : Float64
  property vy : Float64
  property vz : Float64
  property battery : Float32
  property heading : Float32
  property crc : UInt32

  def initialize(@drone_id, @timestamp, @x, @y, @z, @vx, @vy, @vz, @battery, @heading, @crc)
  end

  def to_h
    {
      "drone_id"  => @drone_id,
      "timestamp" => @timestamp,
      "x"         => @x,
      "y"         => @y,
      "z"         => @z,
      "battery"   => @battery,
      "heading"   => @heading,
      "crc"       => @crc
    }
  end
end

# ── CRC32 helper ─────────────────────────────────────────────────

module CRC32
  # Compute CRC32 checksum using standard polynomial.
  TABLE = Array.new(256) do |i|
    crc = i.to_u32
    8.times do
      crc = (crc >> 1) ^ (0xEDB88320_u32 & (-(crc & 1).to_i32).to_u32)
    end
    crc
  end

  def self.compute(data : Bytes) : UInt32
    crc = 0xFFFFFFFF_u32
    data.each { |b| crc = (crc >> 8) ^ TABLE[(crc ^ b) & 0xFF] }
    crc ^ 0xFFFFFFFF_u32
  end
end

# ── Telemetry parser ──────────────────────────────────────────────

class TelemetryParser
  property packets_parsed : Int32
  property parse_errors   : Int32
  property crc_failures   : Int32

  def initialize
    @packets_parsed = 0
    @parse_errors   = 0
    @crc_failures   = 0
  end

  # Parse a text-format telemetry line.
  # Format: "TELEM|drone_id|ts|x|y|z|vx|vy|vz|bat|hdg|crc"
  def parse_text(line : String) : TelemetryPacket?
    parts = line.split('|')
    return nil unless parts.size == 12 && parts[0] == "TELEM"

    begin
      pkt = TelemetryPacket.new(
        drone_id:  parts[1].to_u32,
        timestamp: parts[2].to_u64,
        x:         parts[3].to_f64,
        y:         parts[4].to_f64,
        z:         parts[5].to_f64,
        vx:        parts[6].to_f64,
        vy:        parts[7].to_f64,
        vz:        parts[8].to_f64,
        battery:   parts[9].to_f32,
        heading:   parts[10].to_f32,
        crc:       parts[11].to_u32
      )
      @packets_parsed += 1
      pkt
    rescue
      @parse_errors += 1
      nil
    end
  end

  # Validate CRC of a parsed packet.
  def validate_crc(pkt : TelemetryPacket) : Bool
    data = "#{pkt.drone_id}|#{pkt.x}|#{pkt.y}|#{pkt.z}|#{pkt.battery}"
    computed = CRC32.compute(data.to_slice)
    valid = computed == pkt.crc
    @crc_failures += 1 unless valid
    valid
  end

  def summary : Hash(String, Int32)
    {"parsed" => @packets_parsed, "errors" => @parse_errors, "crc_failures" => @crc_failures}
  end
end

# ── Telemetry generator (for testing) ────────────────────────────

def generate_packets(n_drones : Int32, n_steps : Int32) : Array(String)
  packets = [] of String
  n_drones.times do |d|
    n_steps.times do |t|
      x   = d * 50.0 + t * 1.0
      y   = d * 30.0 + t * 0.5
      z   = 50.0
      bat = 100.0 - t * 0.3
      hdg = (t * 10.0) % 360.0
      crc = CRC32.compute("#{d}|#{x}|#{y}|#{z}|#{bat}".to_slice)
      packets << "TELEM|#{d}|#{Time.utc.to_unix_ms}|#{x}|#{y}|#{z}|1.0|0.5|0.0|#{bat}|#{hdg}|#{crc}"
    end
  end
  packets
end

# ── Entry point ────────────────────────────────────────────────────

puts "Phase #{PHASE}: Telemetry Parser — 드론 텔레메트리 패킷 파서"
parser = TelemetryParser.new
lines  = generate_packets(5, 20)
lines.each { |line| parser.parse_text(line) }
puts "Summary: #{parser.summary}"
puts "CRC check on first packet: #{parser.validate_crc(parser.parse_text(lines[0]).not_nil!)}"
