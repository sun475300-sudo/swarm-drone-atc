# frozen_string_literal: true

# Phase 560: API Gateway — Ruby
# SDACS API gateway with route management, auth, and rate limiting

# Phase 560 marker — Gateway, Route management for drone API

require 'json'
require 'time'
require 'digest'
require 'base64'

module SDACS
  module Gateway
    # HTTP method constants
    METHODS = %w[GET POST PUT PATCH DELETE].freeze

    # ============================================================
    # Route definition

    Route = Struct.new(:method, :path, :pattern, :handler, :middleware) do
      def initialize(method:, path:, handler:, middleware: [])
        pattern = path_to_regex(path)
        super(method.upcase, path, pattern, handler, middleware)
      end

      def matches?(method, request_path)
        method.upcase == self.method && pattern.match?(request_path)
      end

      def extract_params(request_path)
        match = pattern.match(request_path)
        return {} unless match
        match.named_captures.transform_keys(&:to_sym)
      end

      private

      def path_to_regex(path)
        regex_str = path.gsub(%r{:([a-zA-Z_][a-zA-Z0-9_]*)}) { "(?<#{Regexp.last_match(1)}>[^/]+)" }
        Regexp.new("^#{regex_str}$")
      end
    end

    # ============================================================
    # Request/Response

    Request = Struct.new(:method, :path, :headers, :body, :params, :user) do
      def initialize(method:, path:, headers: {}, body: nil)
        super(method.upcase, path, headers, body, {}, nil)
      end

      def json_body
        return nil unless body.is_a?(String) && !body.empty?
        JSON.parse(body, symbolize_names: true)
      rescue JSON::ParserError
        nil
      end

      def bearer_token
        auth = headers['Authorization'] || headers['authorization'] || ''
        auth.sub(/\ABearer\s+/i, '')
      end
    end

    Response = Struct.new(:status, :headers, :body) do
      def initialize(status: 200, headers: {}, body: nil)
        super(status, { 'Content-Type' => 'application/json' }.merge(headers), body)
      end

      def json(data, status: self.status)
        self.status = status
        self.body   = JSON.generate(data)
        self
      end

      def error(message, status: 400)
        json({ error: message, status: status }, status: status)
      end
    end

    # ============================================================
    # Rate limiter (token bucket per IP)

    class RateLimiter
      def initialize(max_requests: 100, window_seconds: 60)
        @max_requests   = max_requests
        @window_seconds = window_seconds
        @buckets        = {}
      end

      def allow?(client_id)
        now = Time.now.to_f
        bucket = @buckets[client_id] ||= { count: 0, window_start: now }

        if now - bucket[:window_start] >= @window_seconds
          bucket[:count]        = 0
          bucket[:window_start] = now
        end

        if bucket[:count] < @max_requests
          bucket[:count] += 1
          true
        else
          false
        end
      end

      def stats
        { buckets: @buckets.size, max_requests: @max_requests, window_s: @window_seconds }
      end
    end

    # ============================================================
    # API Gateway

    class APIGateway
      attr_reader :routes, :rate_limiter

      def initialize(name: 'SDACS-GW', rate_limit: 100)
        @name         = name
        @routes       = []
        @middleware   = []
        @rate_limiter = RateLimiter.new(max_requests: rate_limit)
        @request_log  = []
        @error_count  = 0
      end

      # Register a route
      def route(method, path, middleware: [], &handler)
        r = Route.new(method: method, path: path, handler: handler, middleware: middleware)
        @routes << r
        r
      end

      # Convenience methods
      def get(path, **opts, &block)    = route('GET',    path, **opts, &block)
      def post(path, **opts, &block)   = route('POST',   path, **opts, &block)
      def put(path, **opts, &block)    = route('PUT',    path, **opts, &block)
      def delete(path, **opts, &block) = route('DELETE', path, **opts, &block)

      # Use global middleware
      def use(middleware_fn)
        @middleware << middleware_fn
      end

      # Dispatch a request
      def dispatch(request)
        client_id = request.headers['X-Client-IP'] || 'unknown'

        # Rate limiting check
        unless @rate_limiter.allow?(client_id)
          resp = Response.new
          return resp.error('Rate limit exceeded', status: 429)
        end

        # Find matching route
        matched_route = @routes.find { |r| r.matches?(request.method, request.path) }

        unless matched_route
          resp = Response.new
          log_request(request, 404)
          return resp.error('Route not found', status: 404)
        end

        # Extract path params
        request.params.merge!(matched_route.extract_params(request.path))

        # Run middleware chain
        response = Response.new
        begin
          run_middleware(@middleware + matched_route.middleware, request, response) do
            matched_route.handler.call(request, response)
          end
        rescue StandardError => e
          @error_count += 1
          response.error("Internal error: #{e.message}", status: 500)
        end

        log_request(request, response.status)
        response
      end

      def stats
        {
          name:         @name,
          routes:       @routes.size,
          requests:     @request_log.size,
          errors:       @error_count,
          rate_limiter: @rate_limiter.stats,
        }
      end

      private

      def run_middleware(stack, request, response, &final)
        if stack.empty?
          final.call
        else
          head, *rest = stack
          head.call(request, response) { run_middleware(rest, request, response, &final) }
        end
      end

      def log_request(request, status)
        @request_log << { method: request.method, path: request.path,
                          status: status, time: Time.now.iso8601 }
        @request_log.shift if @request_log.size > 10_000
      end
    end
  end
end

# Demo
gw = SDACS::Gateway::APIGateway.new(name: 'SDACS-GW-1')

gw.get('/api/v1/drones') do |req, res|
  res.json({ drones: ['D001', 'D002', 'D003'], total: 3 })
end

gw.get('/api/v1/drones/:drone_id') do |req, res|
  res.json({ drone_id: req.params[:drone_id], status: 'active', battery: 85.0 })
end

gw.post('/api/v1/drones/:drone_id/command') do |req, res|
  body = req.json_body
  res.json({ success: true, drone_id: req.params[:drone_id], command: body&.dig(:command) }, status: 201)
end

req1 = SDACS::Gateway::Request.new(method: 'GET', path: '/api/v1/drones')
resp1 = gw.dispatch(req1)
puts "Phase 560: API Gateway"
puts "GET /api/v1/drones → #{resp1.status}: #{resp1.body}"

req2 = SDACS::Gateway::Request.new(method: 'GET', path: '/api/v1/drones/D001')
resp2 = gw.dispatch(req2)
puts "GET /api/v1/drones/D001 → #{resp2.status}: #{resp2.body}"
puts "Gateway stats: #{gw.stats}"
