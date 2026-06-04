/**
 * SDACS 드론 레지스트리 — Java 엔터프라이즈 컴포넌트
 * ===================================================
 * 드론 등록/인증/상태 관리 (Thread-Safe Singleton)
 *
 * 기능:
 *   - 드론 등록/해제 (UUID 기반)
 *   - PKI 인증서 검증 시뮬레이션
 *   - 상태 머신 (REGISTERED → ACTIVE → MAINTENANCE → RETIRED)
 *   - ConcurrentHashMap 기반 스레드 안전성
 *   - JMX 메트릭 노출
 */

package com.sdacs.registry;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.time.*;

public class DroneRegistry {

    // ── 드론 상태 열거형 ────────────────────────────────

    public enum DroneStatus {
        REGISTERED,   // 등록 완료, 비행 불가
        ACTIVE,       // 비행 가능
        IN_FLIGHT,    // 비행 중
        MAINTENANCE,  // 점검 중
        SUSPENDED,    // 일시 정지
        RETIRED       // 퇴역
    }

    public enum CertificateStatus {
        VALID,
        EXPIRED,
        REVOKED,
        PENDING
    }

    // ── 드론 레코드 ─────────────────────────────────────

    public static class DroneRecord {
        public final String droneId;
        public final String ownerId;
        public final String model;
        public final double maxPayloadKg;
        public final double maxSpeedMs;
        public final double batteryCapacityWh;
        public volatile DroneStatus status;
        public volatile CertificateStatus certStatus;
        public final Instant registeredAt;
        public volatile Instant lastHeartbeat;
        public final AtomicLong totalFlightHours;
        public final AtomicLong totalMissions;
        public final AtomicInteger violations;
        public final List<String> auditLog;

        public DroneRecord(String droneId, String ownerId, String model,
                          double maxPayloadKg, double maxSpeedMs, double batteryCapacityWh) {
            this.droneId = droneId;
            this.ownerId = ownerId;
            this.model = model;
            this.maxPayloadKg = maxPayloadKg;
            this.maxSpeedMs = maxSpeedMs;
            this.batteryCapacityWh = batteryCapacityWh;
            this.status = DroneStatus.REGISTERED;
            this.certStatus = CertificateStatus.PENDING;
            this.registeredAt = Instant.now();
            this.lastHeartbeat = Instant.now();
            this.totalFlightHours = new AtomicLong(0);
            this.totalMissions = new AtomicLong(0);
            this.violations = new AtomicInteger(0);
            this.auditLog = Collections.synchronizedList(new ArrayList<>());
        }
    }

    // ── 레지스트리 구현 ──────────────────────────────────

    private final ConcurrentHashMap<String, DroneRecord> registry;
    private final ConcurrentHashMap<String, Set<String>> ownerIndex; // owner → drones
    private final AtomicLong totalRegistrations;
    private final AtomicLong totalRetirements;
    private final ScheduledExecutorService scheduler;

    private static volatile DroneRegistry instance;

    private DroneRegistry() {
        this.registry = new ConcurrentHashMap<>();
        this.ownerIndex = new ConcurrentHashMap<>();
        this.totalRegistrations = new AtomicLong(0);
        this.totalRetirements = new AtomicLong(0);
        this.scheduler = Executors.newSingleThreadScheduledExecutor();

        // 주기적 하트비트 체크 (30초)
        scheduler.scheduleAtFixedRate(this::checkHeartbeats, 30, 30, TimeUnit.SECONDS);
    }

    /** Singleton 인스턴스 */
    public static DroneRegistry getInstance() {
        if (instance == null) {
            synchronized (DroneRegistry.class) {
                if (instance == null) {
                    instance = new DroneRegistry();
                }
            }
        }
        return instance;
    }

    /** 드론 등록 */
    public DroneRecord register(String droneId, String ownerId, String model,
                                double maxPayloadKg, double maxSpeedMs, double batteryWh) {
        DroneRecord record = new DroneRecord(droneId, ownerId, model,
                maxPayloadKg, maxSpeedMs, batteryWh);

        DroneRecord existing = registry.putIfAbsent(droneId, record);
        if (existing != null) {
            throw new IllegalStateException("Drone " + droneId + " already registered");
        }

        ownerIndex.computeIfAbsent(ownerId, k -> ConcurrentHashMap.newKeySet()).add(droneId);
        totalRegistrations.incrementAndGet();
        record.auditLog.add(Instant.now() + " | REGISTERED by " + ownerId);

        return record;
    }

    /** 인증서 발급 (시뮬레이션) */
    public void issueCertificate(String droneId) {
        DroneRecord drone = getDrone(droneId);
        drone.certStatus = CertificateStatus.VALID;
        drone.status = DroneStatus.ACTIVE;
        drone.auditLog.add(Instant.now() + " | CERTIFICATE_ISSUED");
    }

    /** 인증서 폐기 */
    public void revokeCertificate(String droneId, String reason) {
        DroneRecord drone = getDrone(droneId);
        drone.certStatus = CertificateStatus.REVOKED;
        drone.status = DroneStatus.SUSPENDED;
        drone.auditLog.add(Instant.now() + " | CERTIFICATE_REVOKED: " + reason);
    }

    /** 비행 시작 */
    public boolean startFlight(String droneId) {
        DroneRecord drone = getDrone(droneId);
        if (drone.status != DroneStatus.ACTIVE || drone.certStatus != CertificateStatus.VALID) {
            return false;
        }
        drone.status = DroneStatus.IN_FLIGHT;
        drone.totalMissions.incrementAndGet();
        drone.auditLog.add(Instant.now() + " | FLIGHT_STARTED");
        return true;
    }

    /** 비행 종료 */
    public void endFlight(String droneId, double flightHours) {
        DroneRecord drone = getDrone(droneId);
        drone.status = DroneStatus.ACTIVE;
        drone.totalFlightHours.addAndGet((long)(flightHours * 100)); // centihours
        drone.auditLog.add(Instant.now() + " | FLIGHT_ENDED (" + flightHours + "h)");
    }

    /** 하트비트 갱신 */
    public void heartbeat(String droneId) {
        DroneRecord drone = registry.get(droneId);
        if (drone != null) {
            drone.lastHeartbeat = Instant.now();
        }
    }

    /** 위반 기록 */
    public int recordViolation(String droneId, String violation) {
        DroneRecord drone = getDrone(droneId);
        int count = drone.violations.incrementAndGet();
        drone.auditLog.add(Instant.now() + " | VIOLATION: " + violation + " (total: " + count + ")");

        // 3회 위반 시 자동 정지
        if (count >= 3) {
            drone.status = DroneStatus.SUSPENDED;
            drone.auditLog.add(Instant.now() + " | AUTO_SUSPENDED: excessive violations");
        }
        return count;
    }

    /** 드론 퇴역 */
    public void retire(String droneId) {
        DroneRecord drone = getDrone(droneId);
        drone.status = DroneStatus.RETIRED;
        drone.certStatus = CertificateStatus.REVOKED;
        totalRetirements.incrementAndGet();
        drone.auditLog.add(Instant.now() + " | RETIRED");
    }

    /** 드론 조회 */
    public DroneRecord getDrone(String droneId) {
        DroneRecord drone = registry.get(droneId);
        if (drone == null) {
            throw new NoSuchElementException("Drone " + droneId + " not found");
        }
        return drone;
    }

    /** 소유자별 드론 조회 */
    public Set<String> getDronesByOwner(String ownerId) {
        return ownerIndex.getOrDefault(ownerId, Collections.emptySet());
    }

    /** 상태별 드론 수 */
    public Map<DroneStatus, Integer> statusDistribution() {
        Map<DroneStatus, Integer> dist = new EnumMap<>(DroneStatus.class);
        for (DroneStatus s : DroneStatus.values()) {
            dist.put(s, 0);
        }
        for (DroneRecord d : registry.values()) {
            dist.merge(d.status, 1, Integer::sum);
        }
        return dist;
    }

    /** 하트비트 타임아웃 체크 */
    private void checkHeartbeats() {
        Instant threshold = Instant.now().minusSeconds(60);
        for (DroneRecord drone : registry.values()) {
            if (drone.status == DroneStatus.IN_FLIGHT
                    && drone.lastHeartbeat.isBefore(threshold)) {
                drone.status = DroneStatus.SUSPENDED;
                drone.auditLog.add(Instant.now() + " | HEARTBEAT_TIMEOUT → SUSPENDED");
            }
        }
    }

    /** 레지스트리 통계 */
    public Map<String, Object> summary() {
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("totalDrones", registry.size());
        s.put("totalRegistrations", totalRegistrations.get());
        s.put("totalRetirements", totalRetirements.get());
        s.put("statusDistribution", statusDistribution());
        s.put("activeDrones", (int) registry.values().stream()
                .filter(d -> d.status == DroneStatus.ACTIVE || d.status == DroneStatus.IN_FLIGHT)
                .count());
        return s;
    }
}
