// Phase 530: Drone Digital Passport — TypeScript
// SDACS blockchain-backed digital identity and certification for drones

// Phase 530 marker — digital passport with Certificate and Passport management

import { createHash, randomUUID } from "crypto";

// ============================================================
// Types

export interface DroneIdentity {
  droneId:       string;
  model:         string;
  serialNumber:  string;
  manufacturer:  string;
  productionDate: string;
  maxAltitude:   number;
  maxSpeed:      number;
  weightKg:      number;
}

export interface Certificate {
  certId:        string;
  type:          CertificateType;
  issuedBy:      string;
  issuedAt:      string;
  expiresAt:     string;
  droneId:       string;
  fingerprint:   string;
  revoked:       boolean;
  metadata:      Record<string, string>;
}

export type CertificateType =
  | "airworthiness"
  | "registration"
  | "operator_license"
  | "rfid_transponder"
  | "remote_id"
  | "insurance";

export interface FlightPermission {
  permissionId:  string;
  droneId:       string;
  zone:          string;
  validFrom:     string;
  validUntil:    string;
  maxAltitude:   number;
  maxSpeed:      number;
  grantedBy:     string;
}

export interface Passport {
  passportId:    string;
  version:       number;
  identity:      DroneIdentity;
  certificates:  Certificate[];
  permissions:   FlightPermission[];
  createdAt:     string;
  updatedAt:     string;
  checksum:      string;
}

// ============================================================
// Certificate factory

export class CertificateFactory {
  static create(
    type:      CertificateType,
    droneId:   string,
    issuedBy:  string,
    validDays: number = 365,
    metadata:  Record<string, string> = {}
  ): Certificate {
    const now      = new Date();
    const expires  = new Date(now.getTime() + validDays * 86400_000);
    const certId   = randomUUID();
    const payload  = `${certId}:${type}:${droneId}:${issuedBy}:${now.toISOString()}`;
    const fingerprint = createHash("sha256").update(payload).digest("hex");

    return {
      certId,
      type,
      issuedBy,
      issuedAt:  now.toISOString(),
      expiresAt: expires.toISOString(),
      droneId,
      fingerprint,
      revoked:   false,
      metadata,
    };
  }

  static isValid(cert: Certificate): boolean {
    if (cert.revoked) return false;
    return new Date(cert.expiresAt) > new Date();
  }

  static revoke(cert: Certificate): Certificate {
    return { ...cert, revoked: true };
  }
}

// ============================================================
// Passport manager

export class PassportManager {
  private passports: Map<string, Passport> = new Map();
  private revokedCerts: Set<string> = new Set();

  createPassport(identity: DroneIdentity): Passport {
    const passportId = randomUUID();
    const now = new Date().toISOString();
    const passport: Passport = {
      passportId,
      version:      1,
      identity,
      certificates: [],
      permissions:  [],
      createdAt:    now,
      updatedAt:    now,
      checksum:     "",
    };
    passport.checksum = this.computeChecksum(passport);
    this.passports.set(passport.passportId, passport);
    return passport;
  }

  addCertificate(passportId: string, cert: Certificate): Passport | null {
    const passport = this.passports.get(passportId);
    if (!passport) return null;

    const updated: Passport = {
      ...passport,
      certificates: [...passport.certificates, cert],
      version:      passport.version + 1,
      updatedAt:    new Date().toISOString(),
      checksum:     "",
    };
    updated.checksum = this.computeChecksum(updated);
    this.passports.set(passportId, updated);
    return updated;
  }

  addPermission(passportId: string, permission: FlightPermission): Passport | null {
    const passport = this.passports.get(passportId);
    if (!passport) return null;

    const updated: Passport = {
      ...passport,
      permissions: [...passport.permissions, permission],
      version:     passport.version + 1,
      updatedAt:   new Date().toISOString(),
      checksum:    "",
    };
    updated.checksum = this.computeChecksum(updated);
    this.passports.set(passportId, updated);
    return updated;
  }

  validatePassport(passportId: string): { valid: boolean; issues: string[] } {
    const passport = this.passports.get(passportId);
    if (!passport) return { valid: false, issues: ["Passport not found"] };

    const issues: string[] = [];

    // Verify checksum
    const expectedChecksum = this.computeChecksum({ ...passport, checksum: "" });
    if (expectedChecksum !== passport.checksum) {
      issues.push("Checksum mismatch — passport may be tampered");
    }

    // Check certificates
    for (const cert of passport.certificates) {
      if (this.revokedCerts.has(cert.certId)) {
        issues.push(`Certificate ${cert.certId} has been revoked`);
      } else if (!CertificateFactory.isValid(cert)) {
        issues.push(`Certificate ${cert.type} (${cert.certId}) is expired`);
      }
    }

    // Check required certs
    const requiredTypes: CertificateType[] = ["airworthiness", "registration", "remote_id"];
    for (const required of requiredTypes) {
      const hasCert = passport.certificates.some(c => c.type === required && CertificateFactory.isValid(c));
      if (!hasCert) {
        issues.push(`Missing required certificate: ${required}`);
      }
    }

    return { valid: issues.length === 0, issues };
  }

  revokeCertificate(certId: string): void {
    this.revokedCerts.add(certId);
  }

  getPassport(passportId: string): Passport | undefined {
    return this.passports.get(passportId);
  }

  getAllPassports(): Passport[] {
    return Array.from(this.passports.values());
  }

  private computeChecksum(passport: Omit<Passport, "checksum"> & { checksum?: string }): string {
    const payload = JSON.stringify({
      passportId:   passport.passportId,
      version:      passport.version,
      identity:     passport.identity,
      certificates: passport.certificates,
      permissions:  passport.permissions,
      createdAt:    passport.createdAt,
    });
    return createHash("sha256").update(payload).digest("hex");
  }
}

// ============================================================
// Demo

const manager = new PassportManager();
const identity: DroneIdentity = {
  droneId:        "D-530-DEMO",
  model:          "SDACS-X3",
  serialNumber:   "SN-2026-530",
  manufacturer:   "SDACS Labs",
  productionDate: "2026-01-01",
  maxAltitude:    120,
  maxSpeed:       15,
  weightKg:       2.5,
};

const passport = manager.createPassport(identity);
const airCert  = CertificateFactory.create("airworthiness", identity.droneId, "KCAB", 730);
const regCert  = CertificateFactory.create("registration",  identity.droneId, "MOLIT", 365);
const remId    = CertificateFactory.create("remote_id",     identity.droneId, "KCAB", 365);

manager.addCertificate(passport.passportId, airCert);
manager.addCertificate(passport.passportId, regCert);
manager.addCertificate(passport.passportId, remId);

const result = manager.validatePassport(passport.passportId);
console.log(`Phase 530: Passport valid=${result.valid} issues=${result.issues.length}`);
console.log(`Passport ID: ${passport.passportId}`);
