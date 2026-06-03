# frozen_string_literal: true

# Phase 636: DevOps Pipeline — Ruby
# SDACS CI/CD pipeline automation for drone software deployment

module SDACS
  module DevOps
    Stage = Struct.new(:name, :command, :timeout, :retry_count, keyword_init: true)
    StageResult = Struct.new(:stage, :success, :duration, :output, keyword_init: true)

    class Pipeline
      attr_reader :stages, :results, :name

      def initialize(name:)
        @name    = name
        @stages  = []
        @results = []
      end

      def add_stage(name:, command:, timeout: 300, retry_count: 1)
        @stages << Stage.new(name: name, command: command, timeout: timeout, retry_count: retry_count)
        self
      end

      def run
        @results = @stages.map do |stage|
          t0 = Time.now
          success = simulate_stage(stage)
          StageResult.new(stage: stage.name, success: success,
                          duration: Time.now - t0, output: "")
        end
        all_passed?
      end

      def all_passed? = @results.all?(&:success)

      def summary
        { name: @name, stages: @stages.size, passed: @results.count(&:success),
          failed: @results.count { !_1.success } }
      end

      private

      def simulate_stage(stage)
        stage.name != "always_fail"
      end
    end
  end
end

pipeline = SDACS::DevOps::Pipeline.new(name: "SDACS Deploy")
pipeline.add_stage(name: "lint",  command: "ruff check src/")
        .add_stage(name: "test",  command: "pytest tests/ -q")
        .add_stage(name: "build", command: "python -m build")
pipeline.run
puts "Phase 636: #{pipeline.summary}"
