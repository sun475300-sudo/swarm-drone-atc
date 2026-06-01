// Phase 530 — Drone Digital Passport with Certificate and Passport Types
// TypeScript module for drone identity management, certification, and digital credentials.

// ===== Enumerations =====

enum PassportStatus {
    ACTIVE = "ACTIVE",
    SUSPENDED = "SUSPENDED",
    REVOKED = "REVOKED",
    EXPIRED = "EXPIRED",
}

enum CertificateType {
    AIRWORTHINESS = "AIRWORTHINESS",
    OPERATOR_LICENSE = "OPERATOR_LICENSE",
    REGISTRATION = "REGISTRATION",
    INSURANCE = "INSURANCE",
    MAINTENANCE = "MAINTENANCE",
}

enum AuthorityLevel {
    NATIONAL = "NATIONAL",
    REGIONAL = "REGIONAL",
    LOCAL = "LOCAL",
}

// ===== Certificate Type =====

/**
 * Certificate represents a regulatory or operational credential issued to a drone.
 * Phase 530: Core identity document in the drone digital passport system.
 */
interface Certificate {
    certificateId: string;
    type: CertificateType;
    issuedBy: string;
    issuedDate: string;       // ISO 8601
    expiryDate: string;       // ISO 8601
    authorityLevel: AuthorityLevel;
    digitalSignature: string; // hex-encoded SHA-256 stub
    revoked: boolean;
}

// ===== Passport Type =====

/**
 * Passport is the comprehensive digital identity document for a drone.
 * Contains all certificates, ownership, and operational history.
 */
interface Passport {
    passportId: string;
    droneSerialNumber: string;
    manufacturer: string;
    model: string;
    registrationCountry: string;
    ownerName: string;
    ownerContactEmail: string;
    status: PassportStatus;
    certificates: Certificate[];
    flightHours: number;
    lastMaintenanceDate: string;
    createdAt: string;
    updatedAt: string;
}

// ===== Certificate Factory =====

function createCertificate(
    type: CertificateType,
    issuedBy: string,
    validityDays: number,
    authorityLevel: AuthorityLevel = AuthorityLevel.NATIONAL
): Certificate {
    const now = new Date();
    const expiry = new Date(now.getTime() + validityDays * 24 * 60 * 60 * 1000);
    const certId = `CERT-${type.slice(0, 3)}-${Date.now().toString(36).toUpperCase()}`;
    return {
        certificateId: certId,
        type,
        issuedBy,
        issuedDate: now.toISOString(),
        expiryDate: expiry.toISOString(),
        authorityLevel,
        digitalSignature: Buffer.from(certId + issuedBy).toString("hex"),
        revoked: false,
    };
}

// ===== Passport Factory and Registry =====

function createPassport(
    droneSerial: string,
    manufacturer: string,
    model: string,
    country: string,
    ownerName: string,
    ownerEmail: string
): Passport {
    const now = new Date().toISOString();
    return {
        passportId: `PP-${droneSerial}-${country}`,
        droneSerialNumber: droneSerial,
        manufacturer,
        model,
        registrationCountry: country,
        ownerName,
        ownerContactEmail: ownerEmail,
        status: PassportStatus.ACTIVE,
        certificates: [],
        flightHours: 0,
        lastMaintenanceDate: now,
        createdAt: now,
        updatedAt: now,
    };
}

// ===== Passport Registry =====

class PassportRegistry {
    private passports: Map<string, Passport> = new Map();

    register(passport: Passport): void {
        this.passports.set(passport.passportId, passport);
    }

    find(passportId: string): Passport | undefined {
        return this.passports.get(passportId);
    }

    addCertificate(passportId: string, cert: Certificate): boolean {
        const pp = this.passports.get(passportId);
        if (!pp) return false;
        pp.certificates.push(cert);
        pp.updatedAt = new Date().toISOString();
        return true;
    }

    revokeCertificate(passportId: string, certId: string): boolean {
        const pp = this.passports.get(passportId);
        if (!pp) return false;
        const cert = pp.certificates.find(c => c.certificateId === certId);
        if (!cert) return false;
        cert.revoked = true;
        return true;
    }

    suspend(passportId: string): boolean {
        const pp = this.passports.get(passportId);
        if (!pp) return false;
        pp.status = PassportStatus.SUSPENDED;
        return true;
    }

    isOperational(passportId: string): boolean {
        const pp = this.passports.get(passportId);
        if (!pp || pp.status !== PassportStatus.ACTIVE) return false;
        const now = new Date();
        const hasValidAirworthiness = pp.certificates.some(c =>
            c.type === CertificateType.AIRWORTHINESS &&
            !c.revoked &&
            new Date(c.expiryDate) > now
        );
        return hasValidAirworthiness;
    }

    summary(): Record<string, number> {
        const active = [...this.passports.values()].filter(p => p.status === PassportStatus.ACTIVE).length;
        return {
            total: this.passports.size,
            active,
            suspended: [...this.passports.values()].filter(p => p.status === PassportStatus.SUSPENDED).length,
        };
    }
}

// ===== Usage Example =====

const registry = new PassportRegistry();

const dronePassport = createPassport(
    "DRN-2025-00042",
    "SwarmTech",
    "Falcon-X",
    "KR",
    "Sunwoo Park",
    "sunwoo@swarmtech.kr"
);

const airworthinessCert = createCertificate(
    CertificateType.AIRWORTHINESS,
    "KCAB-Korea",
    365,
    AuthorityLevel.NATIONAL
);

registry.register(dronePassport);
registry.addCertificate(dronePassport.passportId, airworthinessCert);

console.log(`Phase 530: Drone Digital Passport System`);
console.log(`Passport ID: ${dronePassport.passportId}`);
console.log(`Operational: ${registry.isOperational(dronePassport.passportId)}`);
console.log(`Registry summary:`, registry.summary());

export { Certificate, Passport, PassportRegistry, PassportStatus, CertificateType, createPassport, createCertificate };
