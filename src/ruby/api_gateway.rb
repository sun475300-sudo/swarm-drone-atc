# Phase 560: API Gateway — 드론 관제 API 게이트웨이 (Ruby)
# HTTP API gateway for swarm drone control station.

require 'json'
require 'time'

PHASE = 560

# ── Route definition ───────────────────────────────────────────────

class Route
  attr_reader :method, :path_pattern, :handler

  def initialize(method, path_pattern, &handler)
    @method = method.upcase
    @path_pattern = path_pattern
    @handler = handler
  end

  def match?(method, path)
    @method == method.upcase && path =~ @path_pattern
  end

  def call(request)
    @handler.call(request)
  end
end

# ── Request / Response ─────────────────────────────────────────────

class Request
  attr_accessor :method, :path, :headers, :body, :params

  def initialize(method:, path:, headers: {}, body: nil, params: {})
    @method  = method
    @path    = path
    @headers = headers
    @body    = body
    @params  = params
  end
end

class Response
  attr_accessor :status, :body, :headers

  def initialize(status: 200, body: {}, headers: {})
    @status  = status
    @body    = body
    @headers = headers.merge('Content-Type' => 'application/json')
  end

  def to_json_str
    JSON.generate(@body)
  end
end

# ── API Gateway ────────────────────────────────────────────────────

class Gateway
  attr_reader :routes, :middleware, :request_log

  def initialize
    @routes      = []
    @middleware  = []
    @request_log = []
    register_default_routes
  end

  def get(path, &block)
    @routes << Route.new('GET', Regexp.new("^#{path}$"), &block)
  end

  def post(path, &block)
    @routes << Route.new('POST', Regexp.new("^#{path}$"), &block)
  end

  def use(&block)
    @middleware << block
  end

  def dispatch(request)
    # Run middleware chain
    @middleware.each { |m| m.call(request) }
    @request_log << {method: request.method, path: request.path, ts: Time.now.iso8601}

    route = @routes.find { |r| r.match?(request.method, request.path) }
    if route
      route.call(request)
    else
      Response.new(status: 404, body: {error: 'Not Found', path: request.path})
    end
  end

  private

  def register_default_routes
    get('/health') do |_req|
      Response.new(body: {status: 'ok', phase: PHASE, version: 'v2'})
    end

    get('/drones') do |_req|
      drones = (1..5).map { |i| {id: i, status: 'active', battery: 80 + i} }
      Response.new(body: {drones: drones, count: drones.size})
    end

    get('/drones/\d+') do |req|
      id = req.path.split('/').last.to_i
      Response.new(body: {id: id, status: 'active', pos: {x: id*10.0, y: id*5.0, z: 50.0}})
    end

    post('/drones/command') do |req|
      cmd = req.body || {}
      Response.new(status: 201, body: {accepted: true, command: cmd, ts: Time.now.iso8601})
    end

    get('/metrics') do |_req|
      Response.new(body: {
        requests_total: 0,
        phase: PHASE,
        uptime_s: 0
      })
    end
  end
end

# ── Entry point ────────────────────────────────────────────────────

if __FILE__ == $PROGRAM_NAME
  puts "Phase #{PHASE}: API Gateway — 드론 관제 API 게이트웨이"

  gw = Gateway.new
  gw.use { |req| puts "  [MW] #{req.method} #{req.path}" }

  requests = [
    Request.new(method: 'GET',  path: '/health'),
    Request.new(method: 'GET',  path: '/drones'),
    Request.new(method: 'GET',  path: '/drones/3'),
    Request.new(method: 'POST', path: '/drones/command', body: {drone_id: 1, cmd: 'hover'}),
    Request.new(method: 'GET',  path: '/unknown'),
  ]

  requests.each do |req|
    resp = gw.dispatch(req)
    puts "  #{req.method} #{req.path} -> #{resp.status}: #{resp.to_json_str[0..60]}"
  end

  puts "Routes registered: #{gw.routes.size}"
  puts "Requests logged:   #{gw.request_log.size}"
end
