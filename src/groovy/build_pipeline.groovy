// Build Pipeline — Groovy DSL for SDACS CI/CD automation
// Phase 578

class PipelineConfig {
    String name
    String branch
    int timeout = 30
    List<String> stages = []
    Map<String, Closure> handlers = [:]
}

class Stage {
    String name
    boolean parallel = false
    List<Closure> steps = []

    Stage(String name) {
        this.name = name
    }

    def run() {
        println "  [Stage] ${name}"
        steps.each { step ->
            try {
                step.call()
            } catch (Exception e) {
                println "  [Stage] ${name} FAILED: ${e.message}"
                throw e
            }
        }
    }
}

class Pipeline {
    String name
    List<Stage> stages = []
    Map<String, Object> env = [:]
    def onFailure = null
    def onSuccess = null

    Pipeline(String name) {
        this.name = name
    }

    def stage(String stageName, Closure body) {
        def s = new Stage(stageName)
        def stageDelegate = [
            sh: { String cmd -> println "    \$ ${cmd}" },
            echo: { String msg -> println "    ${msg}" },
            step: { Closure c -> s.steps << c }
        ]
        body.delegate = stageDelegate
        body.resolveStrategy = Closure.DELEGATE_FIRST
        s.steps << body
        stages << s
    }

    def run() {
        println "[Pipeline] ${name} starting"
        stages.each { s ->
            try {
                s.run()
            } catch (Exception e) {
                onFailure?.call(e)
                return
            }
        }
        println "[Pipeline] ${name} completed"
        onSuccess?.call()
    }

    def withEnv(Map<String, Object> vars, Closure body) {
        env.putAll(vars)
        body.call()
    }
}

// SDACS build pipeline definition
def sdacsPipeline = new Pipeline("SDACS-CI")

sdacsPipeline.stage("lint") {
    sh "ruff check src/ simulation/ --select=E9,F63,F7,F82"
    sh "mypy src/ --error-summary"
}

sdacsPipeline.stage("test") {
    sh "pytest tests/ --tb=short -q --cov=src --cov=simulation --cov-fail-under=80"
}

sdacsPipeline.stage("build") {
    sh "pip install build"
    sh "python -m build --wheel"
}

sdacsPipeline.stage("docker") {
    sh "docker build -t sdacs:latest ."
    sh "docker tag sdacs:latest sdacs:${env.GIT_SHA ?: 'dev'}"
}

sdacsPipeline.onSuccess = {
    println "[Pipeline] All stages passed — artifact ready"
}

sdacsPipeline.onFailure = { Exception e ->
    println "[Pipeline] FAILED: ${e.message}"
}

return sdacsPipeline
