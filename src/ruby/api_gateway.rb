# Phase 560: API Gateway for SDACS Fleet Management
# RESTful API Gateway with routing and authentication
# SDACS Web Services Module

require 'json'
require 'time'
require 'digest'

# HTTP method types
module HttpMethod
  GET    = 'GET'
  POST   = 'POST'
  PUT    = 'PUT'
  DELETE = 'DELETE'
  PATCH  = 'PATCH'
end

# Request context
class Request
  attr_reader :method, :path, :headers, :body, :params, :timestamp

  def initialize(method:, path:, headers: {}, body: nil, params: {})
    @method    = method
    @path      = path
    @headers   = headers
    @body      = body
    @params    = params
    @timestamp = Time.now
  end

  def authenticated?
    @headers.key?('Authorization')
  end

  def json_body
    return {} if @body.nil?
    JSON.parse(@body)
  rescue JSON::ParserError
    {}
  end
end

# Response structure
class Response
  attr_accessor :status, :body, :headers

  def initialize(status: 200, body: {}, headers: {})
    @status  = status
    @body    = body
    @headers = { 'Content-Type' => 'application/json' }.merge(headers)
  end

  def to_json
    JSON.generate({ status: @status, data: @body })
  end

  def self.ok(data)
    new(status: 200, body: { success: true, data: data })
  end

  def self.error(message, code: 400)
    new(status: code, body: { success: false, error: message })
  end

  def self.not_found(resource)
    new(status: 404, body: { success: false, error: "#{resource} not found" })
  end
end

# Route definition
Route = Struct.new(:method, :pattern, :handler, :middleware) do
  def matches?(method, path)
    self.method == method && path.match?(pattern)
  end

  def extract_params(path)
    md = path.match(pattern)
    md ? md.named_captures : {}
  end
end

# API Gateway router
class Gateway
  attr_reader :routes, :request_count, :error_count

  def initialize
    @routes        = []
    @middleware    = []
    @request_count = 0
    @error_count   = 0
    @rate_limits   = Hash.new(0)
  end

  # Register a route
  def route(method, path_pattern, &handler)
    regex = path_to_regex(path_pattern)
    @routes << Route.new(method, regex, handler, [])
  end

  # HTTP method helpers
  def get(path, &handler)    route(HttpMethod::GET,    path, &handler) end
  def post(path, &handler)   route(HttpMethod::POST,   path, &handler) end
  def put(path, &handler)    route(HttpMethod::PUT,    path, &handler) end
  def delete(path, &handler) route(HttpMethod::DELETE, path, &handler) end
  def patch(path, &handler)  route(HttpMethod::PATCH,  path, &handler) end

  # Add middleware
  def use(middleware_proc)
    @middleware << middleware_proc
  end

  # Dispatch a request
  def dispatch(request)
    @request_count += 1

    # Run middleware chain
    @middleware.each do |mw|
      result = mw.call(request)
      return result if result.is_a?(Response)
    end

    # Find matching route
    matched_route = @routes.find { |r| r.matches?(request.method, request.path) }
    unless matched_route
      @error_count += 1
      return Response.not_found("Route #{request.method} #{request.path}")
    end

    path_params = matched_route.extract_params(request.path)
    request.params.merge!(path_params)

    begin
      matched_route.handler.call(request)
    rescue => e
      @error_count += 1
      Response.error("Internal error: #{e.message}", code: 500)
    end
  end

  def stats
    {
      routes:        @routes.length,
      request_count: @request_count,
      error_count:   @error_count,
      gateway:       'SDACS-Gateway'
    }
  end

  private

  def path_to_regex(path)
    pattern = path.gsub(/:(\w+)/, '(?<\1>[^/]+)')
    Regexp.new("^#{pattern}$")
  end
end

# Drone fleet API routes
class DroneFleetAPI
  attr_reader :gateway

  def initialize
    @drones  = {}
    @gateway = Gateway.new
    setup_routes
    seed_data
  end

  def setup_routes
    # Authentication middleware
    @gateway.use(->(req) {
      return Response.error('Unauthorized', code: 401) unless req.authenticated? || req.path.start_with?('/health')
      nil
    })

    # Route definitions
    @gateway.get('/health') { Response.ok({ status: 'ok', service: 'SDACS-Gateway' }) }

    @gateway.get('/api/drones') do
      Response.ok({ drones: @drones.values, count: @drones.size })
    end

    @gateway.get('/api/drones/:id') do |req|
      drone = @drones[req.params['id']]
      drone ? Response.ok(drone) : Response.not_found("Drone #{req.params['id']}")
    end

    @gateway.post('/api/drones') do |req|
      data = req.json_body
      id = "drone_#{@drones.size + 1}"
      @drones[id] = data.merge('id' => id, 'created_at' => Time.now.iso8601)
      Response.ok({ created: id })
    end

    @gateway.put('/api/drones/:id') do |req|
      id = req.params['id']
      if @drones.key?(id)
        @drones[id].merge!(req.json_body)
        Response.ok(@drones[id])
      else
        Response.not_found("Drone #{id}")
      end
    end

    @gateway.delete('/api/drones/:id') do |req|
      id = req.params['id']
      if @drones.delete(id)
        Response.ok({ deleted: id })
      else
        Response.not_found("Drone #{id}")
      end
    end

    @gateway.get('/api/fleet/stats') do
      active  = @drones.values.count { |d| d['status'] == 'active' }
      battery = @drones.values.map { |d| d['battery'].to_f }
      avg_bat = battery.empty? ? 0 : battery.sum / battery.size
      Response.ok({
        total:       @drones.size,
        active:      active,
        avg_battery: avg_bat.round(2)
      })
    end
  end

  def seed_data
    5.times do |i|
      id = "drone_#{i + 1}"
      @drones[id] = {
        'id'       => id,
        'status'   => 'active',
        'battery'  => 80 + rand(20),
        'altitude' => 90 + rand(30),
        'model'    => 'SwarmX-v2'
      }
    end
  end

  def handle(method, path, headers: {}, body: nil)
    req = Request.new(method: method, path: path, headers: headers, body: body)
    @gateway.dispatch(req)
  end
end

# Main
puts "SDACS API Gateway v560"
api = DroneFleetAPI.new

# Simulate requests
health_resp = api.handle('GET', '/health')
puts "Health Route: #{health_resp.status}"

fleet_resp = api.handle('GET', '/api/fleet/stats', headers: { 'Authorization' => 'Bearer token' })
puts "Fleet stats route: #{fleet_resp.status}"

drone_resp = api.handle('GET', '/api/drones/drone_1', headers: { 'Authorization' => 'Bearer token' })
puts "Drone API Gateway active: #{drone_resp.status}"

puts "Gateway stats: #{api.gateway.stats}"
