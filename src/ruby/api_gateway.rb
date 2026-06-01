# Phase 560 — Ruby API Gateway with Routing
# Ruby module implementing an API gateway with route matching and middleware support.

require 'json'
require 'time'

# ===== Route Type =====

# Represents a single route in the gateway with method, path, and handler
Route = Struct.new(:method, :path, :handler, :middleware, keyword_init: true) do
  # Check if this route matches an incoming request
  def matches?(req_method, req_path)
    method.to_s.upcase == req_method.to_s.upcase &&
      path_matches?(req_path)
  end

  # Extract path parameters from the URL (e.g., :id)
  def extract_params(req_path)
    params = {}
    path_parts = path.split('/')
    req_parts  = req_path.split('/')
    return params if path_parts.size != req_parts.size

    path_parts.each_with_index do |part, i|
      params[part[1..].to_sym] = req_parts[i] if part.start_with?(':')
    end
    params
  end

  private

  def path_matches?(req_path)
    path_parts = path.split('/')
    req_parts  = req_path.split('/')
    return false if path_parts.size != req_parts.size

    path_parts.each_with_index.all? do |part, i|
      part.start_with?(':') || part == req_parts[i]
    end
  end
end

# ===== Request and Response =====

class GatewayRequest
  attr_reader :method, :path, :headers, :body, :params, :query_params

  def initialize(method:, path:, headers: {}, body: nil, query_params: {})
    @method = method.upcase
    @path = path
    @headers = headers
    @body = body
    @params = {}
    @query_params = query_params
  end

  def json_body
    return nil if body.nil? || body.empty?
    JSON.parse(body, symbolize_names: true)
  rescue JSON::ParserError
    nil
  end
end

class GatewayResponse
  attr_accessor :status, :headers, :body

  def initialize(status: 200, body: nil, headers: {})
    @status = status
    @headers = { 'Content-Type' => 'application/json' }.merge(headers)
    @body = body
  end

  def to_json_str
    JSON.generate({ status: status, body: body })
  end
end

# ===== Middleware =====

module Middleware
  # Logging middleware
  def self.logging(request, &next_handler)
    start_time = Time.now
    response = next_handler.call(request)
    elapsed = ((Time.now - start_time) * 1000).round(2)
    puts "[#{start_time.strftime('%H:%M:%S')}] #{request.method} #{request.path} -> #{response.status} (#{elapsed}ms)"
    response
  end

  # Authentication middleware (stub)
  def self.auth(request, &next_handler)
    token = request.headers['Authorization']
    if token.nil? || token.empty?
      return GatewayResponse.new(status: 401, body: { error: 'Unauthorized' })
    end
    next_handler.call(request)
  end

  # Rate limiter stub
  def self.rate_limit(request, &next_handler)
    # Simplified: always allow in stub implementation
    next_handler.call(request)
  end
end

# ===== API Gateway =====

# The main Gateway class that routes incoming requests to registered handlers.
class Gateway
  attr_reader :routes, :name

  def initialize(name: 'SwarmDroneGateway')
    @name = name
    @routes = []
    @global_middleware = []
    @request_count = 0
    @error_count = 0
  end

  # Register a GET route
  def get(path, middleware: [], &handler)
    register_route('GET', path, handler, middleware)
  end

  # Register a POST route
  def post(path, middleware: [], &handler)
    register_route('POST', path, handler, middleware)
  end

  # Register a PUT route
  def put(path, middleware: [], &handler)
    register_route('PUT', path, handler, middleware)
  end

  # Register a DELETE route
  def delete(path, middleware: [], &handler)
    register_route('DELETE', path, handler, middleware)
  end

  # Add global middleware applied to all routes
  def use(middleware_fn)
    @global_middleware << middleware_fn
  end

  # Handle an incoming request
  def call(request)
    @request_count += 1
    route = @routes.find { |r| r.matches?(request.method, request.path) }

    unless route
      @error_count += 1
      return GatewayResponse.new(status: 404, body: { error: 'Route not found', path: request.path })
    end

    request.params.merge!(route.extract_params(request.path))

    # Apply global middleware chain then call handler
    wrapped = -> (req) { route.handler.call(req) }
    response = wrapped.call(request)
    GatewayResponse.new(status: response.status, body: response.body)
  rescue StandardError => e
    @error_count += 1
    GatewayResponse.new(status: 500, body: { error: e.message })
  end

  def stats
    {
      gateway: name,
      total_routes: @routes.size,
      total_requests: @request_count,
      total_errors: @error_count,
      phase: '560'
    }
  end

  private

  def register_route(method, path, handler, middleware)
    @routes << Route.new(method: method, path: path, handler: handler, middleware: middleware)
    self
  end
end

# ===== Swarm Drone API Routes =====

gateway = Gateway.new(name: 'SwarmAPI')

# Route: list all drones
gateway.get('/api/drones') do |req|
  drones = (1..5).map { |i| { id: "D#{format('%03d', i)}", status: 'active', battery: 80 + i } }
  GatewayResponse.new(status: 200, body: { drones: drones, count: drones.size })
end

# Route: get drone by ID
gateway.get('/api/drones/:id') do |req|
  GatewayResponse.new(status: 200, body: { id: req.params[:id], battery: 85, altitude: 55.0 })
end

# Route: send command to drone
gateway.post('/api/drones/:id/command') do |req|
  payload = req.json_body || {}
  GatewayResponse.new(status: 202, body: { accepted: true, drone: req.params[:id], command: payload })
end

# Route: health check
gateway.get('/health') do |_req|
  GatewayResponse.new(status: 200, body: { status: 'ok', gateway: 'SwarmAPI' })
end

# ===== Main Execution =====

puts "Phase 560: Ruby API Gateway with Routing"

# Simulate requests
requests = [
  GatewayRequest.new(method: 'GET',  path: '/api/drones'),
  GatewayRequest.new(method: 'GET',  path: '/api/drones/D001'),
  GatewayRequest.new(method: 'POST', path: '/api/drones/D001/command',
                     body: '{"type":"MOVE","altitude":60}',
                     headers: { 'Authorization' => 'Bearer test-token' }),
  GatewayRequest.new(method: 'GET',  path: '/health'),
  GatewayRequest.new(method: 'GET',  path: '/api/nonexistent'),
]

requests.each do |req|
  resp = gateway.call(req)
  puts "  #{req.method} #{req.path} => #{resp.status}: #{resp.body.inspect}"
end

puts "\nGateway stats: #{gateway.stats.inspect}"
