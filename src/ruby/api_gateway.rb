# P560: APIGateway - Ruby API gateway for SDACS fleet management
# Phase 560: RESTful API gateway with route handling and authentication

require 'json'
require 'time'

module SDACS
  class Gateway
    ROUTES = {
      'GET'    => {},
      'POST'   => {},
      'PUT'    => {},
      'DELETE' => {},
    }.freeze

    def initialize
      @routes   = { 'GET' => {}, 'POST' => {}, 'PUT' => {}, 'DELETE' => {} }
      @middleware = []
      @auth_tokens = {}
    end

    def route(method, path, &handler)
      @routes[method.upcase][path] = handler
    end

    def get(path, &handler)    route('GET', path, &handler) end
    def post(path, &handler)   route('POST', path, &handler) end
    def put(path, &handler)    route('PUT', path, &handler) end
    def delete(path, &handler) route('DELETE', path, &handler) end

    def use(&middleware)
      @middleware << middleware
    end

    def issue_token(subject, role)
      token = SecureRandom.hex(32) rescue "token-#{subject}-#{Time.now.to_i}"
      @auth_tokens[token] = { sub: subject, role: role, issued_at: Time.now.iso8601 }
      token
    end

    def call(env)
      method  = env['REQUEST_METHOD'] || 'GET'
      path    = env['PATH_INFO'] || '/'
      body    = env['rack.input']&.read || '{}'
      headers = { 'Content-Type' => 'application/json' }

      @middleware.each { |m| m.call(env) }

      handler = @routes.dig(method.upcase, path)
      unless handler
        return [404, headers, [JSON.generate({ error: 'Not Found', path: path })]]
      end

      begin
        result = handler.call(env, JSON.parse(body) rescue {})
        [200, headers, [JSON.generate(result)]]
      rescue => e
        [500, headers, [JSON.generate({ error: e.message })]]
      end
    end

    def setup_default_routes
      get('/healthz') { |_, _| { status: 'ok', time: Time.now.iso8601 } }

      get('/api/drones') { |_, _|
        { drones: [], total: 0 }
      }

      post('/api/drones/:id/command') { |env, body|
        drone_id = env['PATH_PARAMS']&.dig(:id) || 'unknown'
        { drone_id: drone_id, command: body['command'], queued: true }
      }

      get('/api/scenarios') { |_, _|
        { scenarios: %w[normal high_density emergency], count: 3 }
      }

      post('/api/auth/token') { |_, body|
        sub  = body['sub']  || 'anonymous'
        role = body['role'] || 'viewer'
        token = issue_token(sub, role)
        { token: token, expires_in: 3600 }
      }

      get('/metrics') { |_, _|
        { sdacs_api_requests_total: 0, sdacs_active_drones: 0 }
      }
    end
  end

  def self.build_gateway
    gw = Gateway.new
    gw.setup_default_routes
    gw
  end
end
