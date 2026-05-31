# devops_pipeline.rb - DevOps pipeline automation for SDACS
# Ruby implementation of CI/CD pipeline management

require 'json'
require 'time'

class PipelineStage
  attr_reader :name, :status, :duration, :output

  def initialize(name, &block)
    @name = name
    @block = block
    @status = :pending
    @duration = 0
    @output = ''
  end

  def run
    start_time = Time.now
    begin
      @output = @block.call
      @status = :success
    rescue => e
      @output = "ERROR: #{e.message}"
      @status = :failed
    ensure
      @duration = Time.now - start_time
    end
    self
  end
end

class DevOpsPipeline
  attr_reader :stages, :name

  def initialize(name)
    @name = name
    @stages = []
  end

  def stage(name, &block)
    @stages << PipelineStage.new(name, &block)
    self
  end

  def run!
    puts "Pipeline: #{@name}"
    @stages.each do |s|
      s.run
      status_icon = s.status == :success ? '✓' : '✗'
      puts "  #{status_icon} #{s.name} (#{s.duration.round(2)}s)"
      break if s.status == :failed
    end
    self
  end

  def summary
    passed = @stages.count { |s| s.status == :success }
    failed = @stages.count { |s| s.status == :failed }
    { name: @name, passed: passed, failed: failed, total: @stages.size }
  end
end

pipeline = DevOpsPipeline.new("sdacs-ci")
  .stage("lint")    { "ruff check src/" }
  .stage("test")    { "pytest tests/ -q" }
  .stage("build")   { "docker build -t sdacs:latest ." }
  .stage("deploy")  { "helm upgrade --install sdacs deploy/helm/sdacs" }

puts "SDACS DevOps Pipeline configured with #{pipeline.stages.size} stages"
