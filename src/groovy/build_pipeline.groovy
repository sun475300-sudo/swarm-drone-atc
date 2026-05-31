// build_pipeline.groovy - CI/CD build pipeline for SDACS
// Groovy DSL pipeline for drone swarm system deployment

class PipelineConfig {
    String projectName = "sdacs-swarm-drone-atc"
    String version     = "1.2.0"
    String dockerRepo  = "ghcr.io/sdacs"
    int    timeout     = 600
}

class BuildResult {
    String stage
    boolean success
    long duration
    String output
    List<String> artifacts = []
}

class Pipeline {
    private PipelineConfig config
    private List<BuildResult> results = []
    private boolean aborted = false

    Pipeline(PipelineConfig cfg) {
        this.config = cfg
    }

    // Execute a pipeline stage
    BuildResult executeStage(String stageName, Closure action) {
        println "=== Stage: ${stageName} ==="
        long start = System.currentTimeMillis()
        boolean success = false
        String output = ""

        try {
            output = action.call()
            success = true
        } catch (Exception e) {
            output = "ERROR: ${e.message}"
            success = false
            if (isCriticalStage(stageName)) {
                aborted = true
            }
        }

        long duration = System.currentTimeMillis() - start
        BuildResult result = new BuildResult(
            stage: stageName,
            success: success,
            duration: duration,
            output: output
        )
        results << result
        println "  ${success ? 'PASS' : 'FAIL'} (${duration}ms)"
        return result
    }

    boolean isCriticalStage(String stage) {
        return stage in ["lint", "test", "security"]
    }

    // Lint stage
    def lint() {
        executeStage("lint") {
            "ruff check src/ simulation/"
        }
    }

    // Test stage
    def test() {
        executeStage("test") {
            "pytest tests/ --cov=src --cov-fail-under=80 -q"
        }
    }

    // Build Docker image stage
    def buildImage() {
        executeStage("build") {
            def tag = "${config.dockerRepo}/${config.projectName}:${config.version}"
            "docker build -t ${tag} ."
        }
    }

    // Security scan stage
    def securityScan() {
        executeStage("security") {
            "bandit -r src/ -f json"
        }
    }

    // Deploy to Kubernetes stage
    def deploy(String environment) {
        executeStage("deploy-${environment}") {
            "helm upgrade --install sdacs deploy/helm/sdacs --set image.tag=${config.version}"
        }
    }

    // Run full pipeline
    def run(String environment = "staging") {
        println "Starting Pipeline: ${config.projectName} v${config.version}"
        lint()
        if (!aborted) test()
        if (!aborted) buildImage()
        if (!aborted) securityScan()
        if (!aborted) deploy(environment)
        printSummary()
    }

    void printSummary() {
        println "\n=== Pipeline Summary ==="
        results.each { r ->
            println "  [${r.success ? 'OK' : 'FAIL'}] ${r.stage} (${r.duration}ms)"
        }
        int passed = results.count { it.success }
        int failed = results.count { !it.success }
        println "\nTotal: ${results.size()} stages, ${passed} passed, ${failed} failed"
    }

    List<BuildResult> getResults() { return results }
    boolean isSuccess() { return results.every { it.success } }
}

// Main execution
def cfg = new PipelineConfig()
def pipeline = new Pipeline(cfg)

if (this.binding.hasVariable("args") && args) {
    String env = args[0]
    pipeline.run(env)
} else {
    println "Pipeline configured for ${cfg.projectName}"
    pipeline.run()
}
