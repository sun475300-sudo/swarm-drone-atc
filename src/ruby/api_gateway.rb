# api_gateway.rb - API Gateway for SDACS drone fleet (Phase 560)
# Ruby-based API gateway with routing and rate limiting

require 'json'
require 'time'

# Route definition for gateway
Route = Struct.new(:method, :path, :handler, :auth_required) do
  def matches?(req_method, req_path)
    method == req_method.upcase && path_matches?(req_path)
  end

  private

  def path_matches?(req_path)
    pattern = path.gsub(/:(\w+)/, '(?<\1>[^/]+)')
    req_path =~ /\A#{pattern}\z/
  end
end

# Request context
RequestContext = Struct.new(:method, :path, :headers, :body, :params)

# Response builder
class Response
  attr_reader :status, :headers, :body

  def initialize(status = 200, body = nil, headers = {})
    @status  = status
    @headers = { 'Content-Type' => 'application/json' }.merge(headers)
    @body    = body
  end

  def to_json
    JSON.generate(@body) rescue @body.to_s
  end
end

# Main API Gateway class
class ApiGateway
  attr_reader :routes, :middleware_stack

  def initialize
    @routes           = []
    @middleware_stack = []
    @rate_limit_store = {}
    @request_count    = 0
    @error_count      = 0
    register_default_routes
  end

  # Register a Route
  def register_route(method, path, handler, auth_required: false)
    @routes << Route.new(method.upcase, path, handler, auth_required)
  end

  # Process an incoming request through gateway
  def process(method, path, headers: {}, body: nil)
    @request_count += 1
    ctx = RequestContext.new(method, path, headers, body, {})

    # Apply middleware
    @middleware_stack.each { |mw| mw.call(ctx) }

    # Find matching route
    route = @routes.find { |r| r.matches?(method, path) }
    return Response.new(404, { error: 'Not Found' }) unless route

    # Auth check
    if route.auth_required && !authenticated?(headers)
      return Response.new(401, { error: 'Unauthorized' })
    end

    Response.new(200, route.handler.call(ctx))
  rescue => e
    @error_count += 1
    Response.new(500, { error: e.message })
  end

  # Add middleware to the stack
  def use(middleware)
    @middleware_stack << middleware
  end

  def stats
    { routes: @routes.size, requests: @request_count, errors: @error_count }
  end

  private

  def authenticated?(headers)
    headers['Authorization']&.start_with?('Bearer ')
  end

  def register_default_routes
    register_route('GET', '/health',          ->(ctx) { { status: 'ok' } })
    register_route('GET', '/api/v1/snapshot', ->(ctx) { { drones: [] } })
    register_route('GET', '/api/v1/metrics',  ->(ctx) { { uptime: 0 } }, auth_required: true)
  end
end

# Phase 560 marker
PHASE = 560
gateway = ApiGateway.new
puts "SDACS API Gateway (Phase #{PHASE}) initialized with #{gateway.routes.size} routes"
