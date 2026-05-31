# Phase 636 — DevOps Pipeline Automation in Ruby
require 'json'
require 'open3'

module SDACS
  class DevOpsPipeline
    STAGES = %w[lint test build deploy].freeze

    def initialize(config = {})
      @config = config
      @results = {}
    end

    def run
      STAGES.each do |stage|
        @results[stage] = run_stage(stage)
        break unless @results[stage][:success]
      end
      @results
    end

    private

    def run_stage(stage)
      cmd = @config.fetch(stage, "echo #{stage} skipped")
      stdout, stderr, status = Open3.capture3(cmd)
      { success: status.success?, stdout: stdout, stderr: stderr }
    end
  end
end
