// Phase 578: Build Pipeline — Groovy
// SDACS CI/CD pipeline orchestration for drone software builds

package sdacs.pipeline

import groovy.transform.CompileStatic
import groovy.transform.ToString
import java.time.Instant

@CompileStatic
@ToString(includeNames = true)
class PipelineConfig {
    String name
    String version
    List<String> targets = []
    Map<String, Object> env = [:]
    int timeout = 3600
    boolean parallel = true
}

@CompileStatic
@ToString(includeNames = true)
class StageResult {
    String stageName
    boolean success
    long durationMs
    String output
    String error
}

@CompileStatic
class Pipeline {
    private final PipelineConfig config
    private final List<StageResult> results = []
    private boolean aborted = false

    Pipeline(PipelineConfig config) {
        this.config = config
    }

    StageResult runStage(String stageName, Closure<Boolean> action) {
        if (aborted) {
            return new StageResult(
                stageName: stageName,
                success: false,
                durationMs: 0,
                output: '',
                error: 'Pipeline aborted'
            )
        }

        long start = System.currentTimeMillis()
        def result = new StageResult(stageName: stageName)

        try {
            def output = new StringBuilder()
            result.success = action.call()
            result.output = output.toString()
            result.error = ''
        } catch (Exception e) {
            result.success = false
            result.error = e.message ?: e.class.simpleName
            aborted = true
        } finally {
            result.durationMs = System.currentTimeMillis() - start
        }

        results << result
        return result
    }

    List<StageResult> runParallelStages(Map<String, Closure<Boolean>> stages) {
        def parallelResults = stages.collectParallel { name, action ->
            runStage(name, action)
        } as List<StageResult>
        results.addAll(parallelResults)
        return parallelResults
    }

    boolean allPassed() {
        results.every { it.success }
    }

    Map<String, Object> summary() {
        [
            pipeline: config.name,
            version:  config.version,
            total:    results.size(),
            passed:   results.count { it.success },
            failed:   results.count { !it.success },
            duration: results.sum { it.durationMs } ?: 0,
            aborted:  aborted
        ] as Map<String, Object>
    }
}

@CompileStatic
class SDACSBuildPipeline {
    static Pipeline create(String projectVersion) {
        def config = new PipelineConfig(
            name:    'SDACS Drone Build',
            version: projectVersion,
            targets: ['test', 'lint', 'build', 'package'],
            env:     ['PYTHONPATH': 'src', 'PYTEST_WORKERS': '4'],
            timeout: 1800,
            parallel: true
        )
        return new Pipeline(config)
    }

    static void main(String[] args) {
        def pipeline = create(args ? args[0] : '1.0.0-dev')

        // Stage 1: Environment check
        pipeline.runStage('environment') {
            println "Checking environment..."
            System.getenv('PYTHONPATH') != null
        }

        // Stage 2: Lint
        pipeline.runStage('lint') {
            println "Running ruff linter..."
            def proc = 'ruff check src/'.execute()
            proc.waitFor()
            proc.exitValue() == 0
        }

        // Stage 3: Type check
        pipeline.runStage('type-check') {
            println "Running mypy type checker..."
            def proc = 'mypy src/ --ignore-missing-imports'.execute()
            proc.waitFor()
            proc.exitValue() == 0
        }

        // Stage 4: Unit tests
        pipeline.runStage('unit-tests') {
            println "Running pytest..."
            def proc = 'pytest tests/ -v --tb=short -q'.execute()
            proc.waitFor()
            proc.exitValue() == 0
        }

        // Stage 5: Build artifact
        pipeline.runStage('build') {
            println "Building SDACS package..."
            new File('dist').mkdirs()
            true
        }

        def summary = pipeline.summary()
        println "Pipeline complete: ${summary}"
        System.exit(pipeline.allPassed() ? 0 : 1)
    }
}
