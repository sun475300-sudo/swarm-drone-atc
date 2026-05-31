# frozen_string_literal: true

# Phase 560 — API Gateway (Ruby)
# 군집 드론 제어 인터페이스용 API Gateway — Route 기반 요청 라우팅

require "json"
require "uri"

module SDACS
  module Gateway

    # HTTP 요청을 담는 값 객체.
    Request = Struct.new(:method, :path, :headers, :body, keyword_init: true)

    # HTTP 응답을 담는 값 객체.
    Response = Struct.new(:status, :headers, :body, keyword_init: true) do
      def self.json(data, status: 200)
        new(status: status,
            headers: { "Content-Type" => "application/json" },
            body: JSON.generate(data))
      end

      def self.error(message, status: 500)
        json({ error: message }, status: status)
      end
    end

    # Route 핸들러 정의.
    Route = Struct.new(:method, :pattern, :handler, keyword_init: true) do
      def matches?(req)
        method.upcase == req.method.upcase &&
          pattern === req.path
      end
    end

    # API Gateway — 등록된 Route에 따라 요청을 백엔드로 라우팅한다.
    class Gateway
      def initialize
        @routes = []
        register_default_routes
      end

      def register(method:, pattern:, &handler)
        @routes << Route.new(method: method, pattern: pattern, handler: handler)
        self
      end

      def handle(request)
        route = @routes.find { |r| r.matches?(request) }
        return Response.error("Route not found", status: 404) unless route

        route.handler.call(request)
      rescue StandardError => e
        Response.error(e.message)
      end

      def route_count = @routes.size

      private

      def register_default_routes
        register(method: "GET", pattern: "/health") do |_req|
          Response.json({ status: "ok", gateway: "SDACS", version: "1.0" })
        end

        register(method: "GET", pattern: /\A\/api\/drones\z/) do |_req|
          Response.json({ drones: [], count: 0 })
        end

        register(method: "POST", pattern: "/api/missions") do |req|
          body = JSON.parse(req.body || "{}")
          Response.json({ mission_id: SecureRandom.hex(8), body: body }, status: 201)
        end

        register(method: "GET", pattern: /\A\/api\/drones\/([^\/]+)\z/) do |req|
          id = req.path.split("/").last
          Response.json({ drone_id: id, status: "active" })
        end
      end
    end
  end
end
