// Phase 578: build_pipeline — Groovy 기반 빌드 파이프라인
// SDACS Build Pipeline for Automated Drone Software Deployment

// 파이프라인 결과 타입
enum StageResult {
    SUCCESS, FAILURE, SKIPPED, ABORTED
}

// 빌드 아티팩트
class BuildArtifact {
    String name
    String version
    String checksum
    long sizeBytes
    String path

    @Override
    String toString() { "${name}-${version} (${sizeBytes}B)" }
}

// 파이프라인 스테이지 정의
abstract class PipelineStage {
    String name
    boolean failFast = true
    long durationMs = 0

    abstract StageResult execute(Map context)

    String getStatus(StageResult result) {
        switch (result) {
            case StageResult.SUCCESS: return "✓"
            case StageResult.FAILURE: return "✗"
            case StageResult.SKIPPED: return "○"
            default: return "~"
        }
    }
}

// 린트 스테이지
class LintStage extends PipelineStage {
    List<String> linters

    LintStage(List<String> linters) {
        this.name = "Lint"
        this.linters = linters
    }

    @Override
    StageResult execute(Map context) {
        def start = System.currentTimeMillis()
        linters.each { linter ->
            println "    [Lint] 실행: ${linter}"
        }
        durationMs = System.currentTimeMillis() - start
        context.lint_passed = true
        StageResult.SUCCESS
    }
}

// 테스트 스테이지
class TestStage extends PipelineStage {
    String testCommand
    double coverageThreshold

    TestStage(String cmd, double threshold) {
        this.name = "Test"
        this.testCommand = cmd
        this.coverageThreshold = threshold
    }

    @Override
    StageResult execute(Map context) {
        def start = System.currentTimeMillis()
        println "    [Test] 실행: ${testCommand}"
        // 테스트 시뮬레이션
        def coverage = 85.0 + new Random().nextDouble() * 10
        context.coverage = coverage
        durationMs = System.currentTimeMillis() - start
        coverage >= coverageThreshold ? StageResult.SUCCESS : StageResult.FAILURE
    }
}

// 빌드 스테이지
class BuildStage extends PipelineStage {
    String buildCommand
    String outputDir

    BuildStage(String cmd, String outDir) {
        this.name = "Build"
        this.buildCommand = cmd
        this.outputDir = outDir
    }

    @Override
    StageResult execute(Map context) {
        def start = System.currentTimeMillis()
        println "    [Build] 실행: ${buildCommand}"
        def artifact = new BuildArtifact(
            name: "sdacs-drone-software",
            version: context.version ?: "0.0.0",
            checksum: UUID.randomUUID().toString().replace("-", "").substring(0, 16),
            sizeBytes: 4_500_000L,
            path: "${outputDir}/sdacs-${context.version}.tar.gz"
        )
        context.artifact = artifact
        durationMs = System.currentTimeMillis() - start
        StageResult.SUCCESS
    }
}

// 배포 스테이지
class DeployStage extends PipelineStage {
    List<String> targets

    DeployStage(List<String> targets) {
        this.name = "Deploy"
        this.targets = targets
    }

    @Override
    StageResult execute(Map context) {
        if (!context.artifact) return StageResult.SKIPPED
        def start = System.currentTimeMillis()
        targets.each { target ->
            println "    [Deploy] → ${target}: ${context.artifact}"
        }
        durationMs = System.currentTimeMillis() - start
        StageResult.SUCCESS
    }
}

// 메인 Pipeline 클래스
class Pipeline {
    String name
    String version
    List<PipelineStage> stages = []
    Map context = [:]
    List<Map> results = []

    Pipeline(String name, String version) {
        this.name = name
        this.version = version
        this.context.version = version
    }

    Pipeline addStage(PipelineStage stage) {
        stages << stage
        this
    }

    boolean run() {
        println "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        println "Pipeline: ${name} v${version}"
        println "스테이지 수: ${stages.size()}"
        println "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        boolean allPassed = true
        stages.each { stage ->
            print "  [${stage.name}] 실행 중..."
            def result = stage.execute(context)
            println " ${stage.getStatus(result)} (${stage.durationMs}ms)"
            results << [stage: stage.name, result: result, duration: stage.durationMs]
            if (result == StageResult.FAILURE && stage.failFast) {
                println "  !! 파이프라인 중단: ${stage.name} 실패"
                allPassed = false
                return false
            }
        }
        allPassed
    }

    void printSummary() {
        println "\n=== 파이프라인 결과 요약 ==="
        results.each { r ->
            println "  ${r.stage}: ${r.result} (${r.duration}ms)"
        }
        def total = results.sum { it.duration }
        println "  총 소요 시간: ${total}ms"
    }
}

// 메인 실행
println "SDACS Build Pipeline — Phase 578\n"

def pipeline = new Pipeline("sdacs-drone-build", "2.6.0")
    .addStage(new LintStage(["ruff", "bandit", "mypy"]))
    .addStage(new TestStage("pytest tests/ -v --cov", 80.0))
    .addStage(new BuildStage("python -m build", "dist/"))
    .addStage(new DeployStage(["drone-fleet-01", "drone-fleet-02"]))

boolean success = pipeline.run()
pipeline.printSummary()

println "\n빌드 파이프라인 완료: ${success ? '성공' : '실패'}"
