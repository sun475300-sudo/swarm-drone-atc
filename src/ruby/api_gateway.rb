# Phase 560: api_gateway — Ruby 기반 API Gateway
# SDACS API Gateway — Route 기반 요청 라우팅

require 'json'
require 'time'

# API Gateway 모듈
module SDACS
  # Route 구조체
  Route = Struct.new(:method, :path, :handler, :middleware) do
    def match?(req_method, req_path)
      method.to_s.upcase == req_method.upcase && path_match?(req_path)
    end

    private

    def path_match?(req_path)
      return path == req_path unless path.include?(':')
      pattern = path.gsub(/:(\w+)/, '(?<\1>[^/]+)')
      req_path.match?(/^#{pattern}$/)
    end

    def extract_params(req_path)
      return {} unless path.include?(':')
      pattern = path.gsub(/:(\w+)/, '(?<\1>[^/]+)')
      match   = req_path.match(/^#{pattern}$/)
      match ? match.named_captures : {}
    end
  end

  # Request/Response 구조체
  Request = Struct.new(:method, :path, :headers, :body, :params) do
    def json_body
      JSON.parse(body) rescue {}
    end
  end

  Response = Struct.new(:status, :headers, :body) do
    def self.ok(data)
      new(200, {'Content-Type' => 'application/json'}, JSON.generate({success: true, data: data}))
    end

    def self.error(code, message)
      new(code, {'Content-Type' => 'application/json'}, JSON.generate({success: false, error: message}))
    end

    def self.not_found
      error(404, 'Route not found')
    end
  end

  # API Gateway 클래스
  class Gateway
    attr_reader :routes

    def initialize
      @routes     = []
      @middleware = []
      @rate_limit = {}
    end

    # Route 등록 메서드
    def get(path, &handler)
      register_route('GET', path, handler)
    end

    def post(path, &handler)
      register_route('POST', path, handler)
    end

    def put(path, &handler)
      register_route('PUT', path, handler)
    end

    def delete(path, &handler)
      register_route('DELETE', path, handler)
    end

    # 미들웨어 등록
    def use(&middleware)
      @middleware << middleware
    end

    # 요청 처리
    def handle(request)
      # 미들웨어 체인 실행
      @middleware.each do |mw|
        result = mw.call(request)
        return result if result.is_a?(Response) && result.status != 200
      end

      route = find_route(request.method, request.path)
      return Response.not_found unless route

      begin
        route.handler.call(request)
      rescue => e
        Response.error(500, "Internal error: #{e.message}")
      end
    end

    private

    def register_route(method, path, handler)
      @routes << Route.new(method, path, handler, [])
      self
    end

    def find_route(method, path)
      @routes.find { |r| r.match?(method, path) }
    end
  end

  # SDACS API 라우터 설정
  class ApiRouter
    def self.build
      gateway = Gateway.new

      # 헬스체크 route
      gateway.get('/healthz') do |_req|
        Response.ok({ status: 'ok', ts: Time.now.iso8601 })
      end

      # 텔레메트리 스냅샷 route
      gateway.get('/api/airspace/snapshot') do |_req|
        Response.ok({
          drones: [],
          conflicts: 0,
          timestamp: Time.now.to_f,
        })
      end

      # 드론 상태 조회 route
      gateway.get('/api/drones/:drone_id') do |req|
        Response.ok({
          drone_id: req.params['drone_id'].to_i,
          status: 'active',
          battery: 85.0,
          altitude: 50.0,
        })
      end

      # 명령 전송 route
      gateway.post('/api/drones/:drone_id/command') do |req|
        body = req.json_body
        cmd  = body['command'] || 'UNKNOWN'
        Response.ok({
          drone_id: req.params['drone_id'].to_i,
          command: cmd,
          queued: true,
          ts: Time.now.to_f,
        })
      end

      # 시나리오 실행 route
      gateway.post('/api/scenarios/:scenario_id/run') do |req|
        Response.ok({
          run_id: "run_#{Time.now.to_i}",
          scenario_id: req.params['scenario_id'],
          status: 'started',
        })
      end

      gateway
    end
  end
end

# 메인 실행
puts "SDACS API Gateway — Phase 560"
router = SDACS::ApiRouter.build
puts "Registered #{router.routes.length} routes:"
router.routes.each do |route|
  puts "  #{route.method} #{route.path}"
end

# 테스트 요청 처리
test_req = SDACS::Request.new('GET', '/healthz', {}, '', {})
response = router.handle(test_req)
puts "\nGET /healthz → #{response.status}: #{response.body}"

drone_req = SDACS::Request.new('GET', '/api/drones/1', {}, '', { 'drone_id' => '1' })
response2 = router.handle(drone_req)
puts "GET /api/drones/1 → #{response2.status}: #{response2.body}"
