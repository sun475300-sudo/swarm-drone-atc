# DevOps Pipeline — SDACS Phase 636
module SDACS
  class Pipeline
    attr_reader :stages, :status
    
    def initialize
      @stages = []
      @status = :pending
    end
    
    def add_stage(name, &block)
      @stages << {name: name, block: block}
    end
    
    def run
      @stages.each do |stage|
        stage[:block].call if stage[:block]
      end
      @status = :completed
    end
  end
end
