// Build Pipeline — SDACS Phase 578
// CI/CD automation for SDACS deployment

import groovy.transform.CompileStatic

@CompileStatic
class Stage {
    String name
    Closure action
    boolean optional = false

    Stage(String name, Closure action) {
        this.name = name
        this.action = action
    }

    boolean execute() {
        try {
            println "  [stage] Running: ${name}"
            action.call()
            println "  [stage] PASSED: ${name}"
            return true
        } catch (Exception e) {
            println "  [stage] FAILED: ${name} — ${e.message}"
            if (!optional) throw e
            return false
        }
    }
}

class Pipeline {
    String name
    List<Stage> stages = []
    long startTime
    Map<String, Boolean> results = [:]

    Pipeline(String name) {
        this.name = name
    }

    def stage(String name, Closure action) {
        stages << new Stage(name, action)
    }

    def run() {
        startTime = System.currentTimeMillis()
        println "Pipeline [${name}] started"
        stages.each { s ->
            results[s.name] = s.execute()
        }
        long elapsed = System.currentTimeMillis() - startTime
        println "Pipeline [${name}] completed in ${elapsed}ms"
        results
    }
}

def pipeline = new Pipeline("sdacs-ci")
pipeline.stage("test")    { println "running tests..." }
pipeline.stage("lint")    { println "running linter..." }
pipeline.stage("build")   { println "building image..." }
pipeline.run()
