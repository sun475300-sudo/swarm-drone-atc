# frozen_string_literal: true

# SDACS API Gateway — Ruby (Phase 560)
# 드론 군집 API 게이트웨이 (Route 기반 프록시)

require 'json'
require 'time'

module SDACS
  # 라우팅 규칙 (Route)
  Route = Struct.new(:method, :pattern, :backend, :auth_required, keyword_init: true) do
    def matches?(req_method, path)
      method.to_s.upcase == req_method.to_s.upcase &&
        (pattern.is_a?(Regexp) ? pattern.match?(path) : path.start_with?(pattern))
    end
  end

  # 요청 객체
  Request = Struct.new(:method, :path, :headers, :body, :timestamp, keyword_init: true)

  # 응답 객체
  Response = Struct.new(:status, :headers, :body, keyword_init: true) do
    def to_json
      { status:, body: }.to_json
    end
  end

  # API 게이트웨이 (Gateway, Phase 560)
  class ApiGateway
    DEFAULT_TIMEOUT = 5.0

    attr_reader :routes, :request_count, :error_count

    def initialize
      @routes = []
      @request_count = 0
      @error_count = 0
      @rate_limiter = {}
      @rate_limit = 100  # per minute
    end

    # Route 등록
    def register_route(method:, pattern:, backend:, auth_required: false)
      route = Route.new(method:, pattern:, backend:, auth_required:)
      @routes << route
      route
    end

    # 요청 처리 (dispatch)
    def handle(method, path, headers: {}, body: nil)
      @request_count += 1
      req = Request.new(method:, path:, headers:, body:, timestamp: Time.now)

      # 속도 제한 확인
      return rate_limit_response if rate_limited?(req)

      # 라우트 탐색
      route = @routes.find { |r| r.matches?(method, path) }
      return not_found_response(path) unless route

      # 인증 확인
      return unauthorized_response if route.auth_required && !authenticated?(headers)

      # 백엔드 라우팅
      dispatch(route, req)
    rescue StandardError => e
      @error_count += 1
      error_response(e.message)
    end

    def gateway_stats
      {
        total_requests: @request_count,
        errors: @error_count,
        routes: @routes.size,
        error_rate: @request_count > 0 ? @error_count.to_f / @request_count : 0.0,
      }
    end

    private

    def dispatch(route, req)
      # 실제 구현: HTTP 프록시 or 내부 핸들러 호출
      Response.new(
        status: 200,
        headers: { 'Content-Type' => 'application/json' },
        body: { backend: route.backend, path: req.path, proxied: true }.to_json
      )
    end

    def rate_limited?(req)
      key = req.path.split('/').first(3).join('/')
      @rate_limiter[key] = (@rate_limiter[key] || 0) + 1
      @rate_limiter[key] > @rate_limit
    end

    def authenticated?(headers)
      headers.key?('Authorization') || headers.key?('X-API-Key')
    end

    def rate_limit_response
      Response.new(status: 429, headers: {}, body: '{"error":"rate_limit_exceeded"}')
    end

    def not_found_response(path)
      Response.new(status: 404, headers: {}, body: %({"error":"no route for #{path}"}))
    end

    def unauthorized_response
      Response.new(status: 401, headers: {}, body: '{"error":"unauthorized"}')
    end

    def error_response(msg)
      Response.new(status: 500, headers: {}, body: %({"error":"#{msg}"}))
    end
  end
end
