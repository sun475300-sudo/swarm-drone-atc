// drone_digital_passport.ts - Digital passport for SDACS drones (Phase 530)
// TypeScript implementation of drone identity and certificate management

import { createHash, randomBytes } from "crypto";

export interface DroneIdentity {
  droneId:      string;
  manufacturer: string;
  model:        string;
  serialNumber: string;
  registeredAt: Date;
  owner:        string;
}

export interface Certificate {
  certId:      string;
  droneId:     string;
  issuedBy:    string;
  issuedAt:    Date;
  expiresAt:   Date;
  publicKey:   string;
  signature:   string;
  certType:    "airworthiness" | "operator" | "insurance" | "maintenance";
}

export interface Passport {
  passportId:   string;
  identity:     DroneIdentity;
  certificates: Certificate[];
  flightHours:  number;
  missionCount: number;
  status:       "active" | "suspended" | "expired" | "revoked";
  createdAt:    Date;
  updatedAt:    Date;
}

export interface FlightRecord {
  flightId:    string;
  droneId:     string;
  startTime:   Date;
  endTime:     Date;
  distance_m:  number;
  maxAltitude: number;
  pilotId:     string;
}

// Passport registry for managing drone digital passports
export class PassportRegistry {
  private passports: Map<string, Passport> = new Map();
  private flightRecords: Map<string, FlightRecord[]> = new Map();

  // Issue a new drone digital passport
  issuePassport(identity: DroneIdentity): Passport {
    const passportId = `PP-${randomBytes(8).toString("hex").toUpperCase()}`;
    const passport: Passport = {
      passportId,
      identity,
      certificates:  [],
      flightHours:   0,
      missionCount:  0,
      status:        "active",
      createdAt:     new Date(),
      updatedAt:     new Date(),
    };
    this.passports.set(identity.droneId, passport);
    return passport;
  }

  // Add a certificate to a drone's passport
  addCertificate(droneId: string, cert: Certificate): boolean {
    const passport = this.passports.get(droneId);
    if (!passport) return false;
    passport.certificates.push(cert);
    passport.updatedAt = new Date();
    return true;
  }

  // Verify passport validity
  verifyPassport(droneId: string): { valid: boolean; reason?: string } {
    const passport = this.passports.get(droneId);
    if (!passport) return { valid: false, reason: "Passport not found" };
    if (passport.status !== "active") return { valid: false, reason: `Passport ${passport.status}` };
    const now = new Date();
    const expiredCerts = passport.certificates.filter(c => c.expiresAt < now);
    if (expiredCerts.length > 0) return { valid: false, reason: "Certificates expired" };
    return { valid: true };
  }

  // Create a Certificate for a drone
  createCertificate(droneId: string, type: Certificate["certType"],
                    validDays: number): Certificate {
    const now = new Date();
    const expires = new Date(now.getTime() + validDays * 86400000);
    return {
      certId:    `CERT-${randomBytes(6).toString("hex").toUpperCase()}`,
      droneId,
      issuedBy:  "SDACS-CA",
      issuedAt:  now,
      expiresAt: expires,
      publicKey: randomBytes(32).toString("hex"),
      signature: createHash("sha256").update(droneId + type).digest("hex"),
      certType:  type,
    };
  }

  getPassport(droneId: string): Passport | undefined {
    return this.passports.get(droneId);
  }
}
