# Phase 560: Ruby API Gateway
# REST API 게이트웨이: 라우팅, 인증, 레이트 리밋, 드론 명령 API 시뮬레이션

class PRNG
  def initialize(seed = 42)
    @state = seed ^ 0x6c62272e
  end

  def next_int
    @state ^= (@state << 13) & 0xFFFFFFFF
    @state ^= (@state >> 7)
    @state ^= (@state << 17) & 0xFFFFFFFF
    @state.abs
  end

  def uniform
    (next_int % 10000) / 10000.0
  end
end

class RateLimiter
  def initialize(max_requests, window_seconds)
    @max = max_requests
    @window = window_seconds
    @requests = Hash.new { |h, k| h[k] = [] }
  end

  def allow?(client_id, timestamp)
    reqs = @requests[client_id]
    reqs.reject! { |t| t < timestamp - @window }
    if reqs.length < @max
      reqs << timestamp
      true
    else
      false
    end
  end
end

class AuthManager
  def initialize
    @tokens = {}
    @valid_keys = {}
  end

  def register(client_id, api_key)
    @valid_keys[client_id] = api_key
  end

  def authenticate(client_id, api_key)
    return nil unless @valid_keys[client_id] == api_key
    token = "tok_#{client_id}_#{rand(99999)}"
    @tokens[token] = { client: client_id, expires: Time.now.to_i + 3600 }
    token
  end

  def verify(token)
    data = @tokens[token]
    return false unless data
    true  # simplified - skip expiry check in simulation
  end
end

class APIRoute
  attr_reader :method, :path, :handler_name

  def initialize(method, path, handler_name)
    @method = method
    @path = path
    @handler_name = handler_name
  end

  def match?(req_method, req_path)
    @method == req_method && path_match?(req_path)
  end

  private

  def path_match?(req_path)
    pattern = @path.gsub(/:(\w+)/, '([^/]+)')
    req_path.match?(/^#{pattern}$/)
  end
end

class APIRequest
  attr_accessor :method, :path, :client_id, :token, :body, :timestamp

  def initialize(method, path, client_id, token = nil, body = {}, timestamp = 0)
    @method = method
    @path = path
    @client_id = client_id
    @token = token
    @body = body
    @timestamp = timestamp
  end
end

class APIResponse
  attr_accessor :status, :body

  def initialize(status, body = {})
    @status = status
    @body = body
  end
end

class APIGateway
  attr_reader :requests_handled, :requests_rejected, :rate_limited

  def initialize(rng_seed = 42)
    @rng = PRNG.new(rng_seed)
    @routes = []
    @rate_limiter = RateLimiter.new(100, 60)
    @auth = AuthManager.new
    @requests_handled = 0
    @requests_rejected = 0
    @rate_limited = 0
    @drone_states = {}
    setup_routes
  end

  def setup_routes
    @routes << APIRoute.new("GET", "/api/v1/drones", "list_drones")
    @routes << APIRoute.new("GET", "/api/v1/drones/:id", "get_drone")
    @routes << APIRoute.new("POST", "/api/v1/drones/:id/command", "send_command")
    @routes << APIRoute.new("GET", "/api/v1/telemetry/:id", "get_telemetry")
    @routes << APIRoute.new("POST", "/api/v1/auth/login", "login")
    @routes << APIRoute.new("GET", "/api/v1/status", "system_status")
  end

  def register_client(client_id, api_key)
    @auth.register(client_id, api_key)
  end

  def register_drone(drone_id)
    @drone_states[drone_id] = {
      id: drone_id,
      altitude: 30 + @rng.uniform * 70,
      battery: 50 + @rng.uniform * 50,
      status: "active"
    }
  end

  def handle(request)
    # Rate limiting
    unless @rate_limiter.allow?(request.client_id, request.timestamp)
      @rate_limited += 1
      return APIResponse.new(429, { error: "Rate limited" })
    end

    # Auth check (except login)
    unless request.path.include?("auth")
      unless request.token && @auth.verify(request.token)
        @requests_rejected += 1
        return APIResponse.new(401, { error: "Unauthorized" })
      end
    end

    # Route matching
    route = @routes.find { |r| r.match?(request.method, request.path) }
    unless route
      @requests_rejected += 1
      return APIResponse.new(404, { error: "Not found" })
    end

    @requests_handled += 1
    dispatch(route.handler_name, request)
  end

  def dispatch(handler, request)
    case handler
    when "list_drones"
      APIResponse.new(200, { drones: @drone_states.keys })
    when "get_drone"
      id = request.path.split("/").last
      state = @drone_states[id]
      state ? APIResponse.new(200, state) : APIResponse.new(404, { error: "Drone not found" })
    when "send_command"
      APIResponse.new(202, { status: "Command queued" })
    when "get_telemetry"
      id = request.path.split("/")[-1]  # simplified
      APIResponse.new(200, { telemetry: @drone_states[id] || {} })
    when "login"
      token = @auth.authenticate(request.client_id, request.body[:api_key] || "")
      token ? APIResponse.new(200, { token: token }) : APIResponse.new(401, { error: "Invalid credentials" })
    when "system_status"
      APIResponse.new(200, { drones: @drone_states.length, uptime: 99.9 })
    else
      APIResponse.new(500, { error: "Internal error" })
    end
  end

  def summary
    {
      routes: @routes.length,
      drones: @drone_states.length,
      handled: @requests_handled,
      rejected: @requests_rejected,
      rate_limited: @rate_limited
    }
  end
end

# Main
gw = APIGateway.new(42)
gw.register_client("admin", "secret123")
10.times { |i| gw.register_drone("drone_#{i}") }

# Simulate requests
token = nil
login_resp = gw.handle(APIRequest.new("POST", "/api/v1/auth/login", "admin", nil, { api_key: "secret123" }, 1))
token = login_resp.body[:token] if login_resp.status == 200

30.times do |t|
  gw.handle(APIRequest.new("GET", "/api/v1/drones", "admin", token, {}, t + 2))
  gw.handle(APIRequest.new("GET", "/api/v1/drones/drone_#{t % 10}", "admin", token, {}, t + 2))
  gw.handle(APIRequest.new("POST", "/api/v1/drones/drone_#{t % 10}/command", "admin", token, { action: "hover" }, t + 2))
end

s = gw.summary
s.each { |k, v| puts "  #{k}: #{v}" }
