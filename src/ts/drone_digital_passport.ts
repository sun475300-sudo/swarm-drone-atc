// Phase 530: drone_digital_passport — TypeScript 기반 드론 디지털 여권
// SDACS Drone Digital Passport System with Certificate-based Authentication

// X.509 스타일 인증서 (Certificate)
export interface Certificate {
    serialNumber: string;
    issuer: string;
    subject: string;
    validFrom: Date;
    validUntil: Date;
    publicKey: string;
    signature: string;
    extensions: Record<string, string>;
}

// 드론 식별 정보
export interface DroneIdentity {
    droneId: string;
    model: string;
    manufacturer: string;
    serialNumber: string;
    productionDate: string;
    maxAltitude: number;
    maxSpeed: number;
    weightKg: number;
}

// 운영자 정보
export interface OperatorInfo {
    operatorId: string;
    name: string;
    licenseNumber: string;
    licenseExpiry: Date;
    certificationLevel: 'basic' | 'advanced' | 'expert';
    authorizedZones: string[];
}

// 디지털 여권 (Digital Passport)
export interface DroneDigitalPassport {
    passportId: string;
    version: string;
    issuedAt: Date;
    expiresAt: Date;
    drone: DroneIdentity;
    operator: OperatorInfo;
    certificate: Certificate;
    flightHistory: FlightRecord[];
    maintenanceLog: MaintenanceEntry[];
    isRevoked: boolean;
}

// 비행 기록
export interface FlightRecord {
    flightId: string;
    date: string;
    duration: number;  // minutes
    maxAltitude: number;
    distance: number;  // km
    zone: string;
    incidents: string[];
}

// 정비 기록
export interface MaintenanceEntry {
    date: string;
    type: 'scheduled' | 'repair' | 'inspection';
    description: string;
    technicianId: string;
    nextDue: string;
}

// Passport 유효성 검증기
export class PassportValidator {
    private readonly trustedIssuers: string[];

    constructor(trustedIssuers: string[]) {
        this.trustedIssuers = trustedIssuers;
    }

    validate(passport: DroneDigitalPassport): ValidationResult {
        const errors: string[] = [];
        const now = new Date();

        if (passport.isRevoked) {
            errors.push('여권이 폐기되었습니다');
        }
        if (passport.expiresAt < now) {
            errors.push('여권이 만료되었습니다');
        }
        if (!this.trustedIssuers.includes(passport.certificate.issuer)) {
            errors.push('신뢰할 수 없는 발급기관');
        }
        if (passport.operator.licenseExpiry < now) {
            errors.push('운영자 면허가 만료되었습니다');
        }
        if (!passport.certificate.serialNumber) {
            errors.push('인증서 일련번호 누락');
        }

        return {
            isValid: errors.length === 0,
            errors,
            checkedAt: now,
        };
    }

    verifyCertificate(cert: Certificate): boolean {
        return cert.validFrom <= new Date() &&
               cert.validUntil >= new Date() &&
               cert.signature.length > 0;
    }
}

export interface ValidationResult {
    isValid: boolean;
    errors: string[];
    checkedAt: Date;
}

// Passport 레지스트리
export class PassportRegistry {
    private passports = new Map<string, DroneDigitalPassport>();
    private validator: PassportValidator;

    constructor(trustedIssuers: string[]) {
        this.validator = new PassportValidator(trustedIssuers);
    }

    register(passport: DroneDigitalPassport): boolean {
        const result = this.validator.validate(passport);
        if (result.isValid) {
            this.passports.set(passport.passportId, passport);
            return true;
        }
        console.error(`등록 실패: ${result.errors.join(', ')}`);
        return false;
    }

    lookup(passportId: string): DroneDigitalPassport | undefined {
        return this.passports.get(passportId);
    }

    revoke(passportId: string): void {
        const passport = this.passports.get(passportId);
        if (passport) {
            (passport as any).isRevoked = true;
        }
    }

    getStats() {
        let valid = 0, revoked = 0;
        this.passports.forEach(p => p.isRevoked ? revoked++ : valid++);
        return { total: this.passports.size, valid, revoked };
    }
}

// 메인 실행
const registry = new PassportRegistry(['SDACS-CA', 'KRCA-DRONE']);

const samplePassport: DroneDigitalPassport = {
    passportId: 'PASS-530-001',
    version: '1.0',
    issuedAt: new Date('2026-01-01'),
    expiresAt: new Date('2028-12-31'),
    drone: {
        droneId: 'DRONE-001',
        model: 'SDACS-X1',
        manufacturer: 'SDACS Corp',
        serialNumber: 'SN-2026-00001',
        productionDate: '2026-01-01',
        maxAltitude: 120,
        maxSpeed: 15,
        weightKg: 2.5,
    },
    operator: {
        operatorId: 'OP-001',
        name: '홍길동',
        licenseNumber: 'KR-UA-2026-001',
        licenseExpiry: new Date('2028-06-30'),
        certificationLevel: 'advanced',
        authorizedZones: ['A', 'B', 'C'],
    },
    certificate: {
        serialNumber: 'CERT-530-20260101',
        issuer: 'SDACS-CA',
        subject: 'CN=DRONE-001',
        validFrom: new Date('2026-01-01'),
        validUntil: new Date('2028-12-31'),
        publicKey: 'RSA-4096-PUBLIC-KEY-PLACEHOLDER',
        signature: 'SIGNATURE-PLACEHOLDER-BASE64',
        extensions: { 'droneClass': 'commercial', 'maxPayload': '0.5kg' },
    },
    flightHistory: [],
    maintenanceLog: [],
    isRevoked: false,
};

console.log('SDACS Drone Digital Passport — Phase 530\n');
const registered = registry.register(samplePassport);
console.log(`여권 등록: ${registered ? '성공' : '실패'}`);

const found = registry.lookup('PASS-530-001');
console.log(`여권 조회: ${found ? found.drone.droneId : '없음'}`);
console.log(`레지스트리 통계: ${JSON.stringify(registry.getStats())}`);
console.log('디지털 여권 처리 완료.');
