# frozen_string_literal: true

# Phase 636 — DevOps Pipeline (Ruby)
# SDACS CI/CD 파이프라인 자동화 스크립트

require "json"
require "open3"
require "time"

module SDACS
  module DevOps
    # 파이프라인 단계 결과를 담는 값 객체.
    PipelineResult = Struct.new(:stage, :success, :duration_s, :output, keyword_init: true)

    class Pipeline
      STAGES = %w[lint typecheck test build docker_build helm_lint].freeze

      def initialize(project_root: Dir.pwd)
        @root = project_root
        @results = []
      end

      attr_reader :results

      def run(stages: STAGES)
        stages.each { |stage| @results << run_stage(stage) }
        self
      end

      def success?
        @results.all?(&:success)
      end

      def report
        lines = ["SDACS DevOps Pipeline Report", "=" * 40]
        @results.each do |r|
          icon = r.success ? "✓" : "✗"
          lines << format("  %s %-20s %.2fs", icon, r.stage, r.duration_s)
        end
        lines << "=" * 40
        lines << (success? ? "PASSED" : "FAILED")
        lines.join("\n")
      end

      private

      STAGE_COMMANDS = {
        "lint"         => "ruff check src/",
        "typecheck"    => "mypy src/ --ignore-missing-imports",
        "test"         => "pytest tests/ -x -q --timeout=120",
        "build"        => "python -m build --wheel --no-isolation",
        "docker_build" => "docker build -t sdacs:latest . --no-cache",
        "helm_lint"    => "helm lint deployment/helm/sdacs",
      }.freeze

      def run_stage(stage)
        cmd = STAGE_COMMANDS.fetch(stage, "echo 'unknown stage: #{stage}'")
        t0 = Time.now
        output, status = Open3.capture2e(cmd, chdir: @root)
        duration = Time.now - t0
        PipelineResult.new(
          stage:, success: status.success?, duration_s: duration, output:
        )
      end
    end
  end
end
