// SDACS Drone Digital Passport — TypeScript (Phase 530)
// 드론 디지털 여권 및 인증서 관리

export interface Certificate {
  serialNumber: string;
  droneId: string;
  issuer: string;
  validFrom: Date;
  validUntil: Date;
  publicKey: string;
  signature: string;
  capabilities: string[];
}

export interface Passport {
  passportId: string;
  droneId: string;
  manufacturer: string;
  model: string;
  serialNumber: string;
  certificate: Certificate;
  flightLog: FlightRecord[];
  issuedAt: Date;
  status: 'active' | 'suspended' | 'revoked';
}

export interface FlightRecord {
  flightId: string;
  timestamp: Date;
  departure: string;
  destination: string;
  duration: number;  // seconds
  maxAltitude: number;
  incidents: number;
}

// Phase 530 — 여권 서비스
export class DronePassportService {
  private passports = new Map<string, Passport>();
  private revokedCerts = new Set<string>();

  issueCertificate(droneId: string, publicKey: string): Certificate {
    return {
      serialNumber: `CERT-${droneId}-${Date.now()}`,
      droneId,
      issuer: 'SDACS-CA',
      validFrom: new Date(),
      validUntil: new Date(Date.now() + 365 * 24 * 3600 * 1000),
      publicKey,
      signature: this.sign(droneId + publicKey),
      capabilities: ['visual_los', 'bvlos', 'night_ops'],
    };
  }

  issuePassport(droneId: string, manufacturer: string, model: string, cert: Certificate): Passport {
    const passport: Passport = {
      passportId: `PASS-${droneId}`,
      droneId,
      manufacturer,
      model,
      serialNumber: `SN-${Math.random().toString(36).slice(2).toUpperCase()}`,
      certificate: cert,
      flightLog: [],
      issuedAt: new Date(),
      status: 'active',
    };
    this.passports.set(droneId, passport);
    return passport;
  }

  validatePassport(droneId: string): boolean {
    const passport = this.passports.get(droneId);
    if (!passport || passport.status !== 'active') return false;
    const cert = passport.certificate;
    if (this.revokedCerts.has(cert.serialNumber)) return false;
    const now = new Date();
    return cert.validFrom <= now && now <= cert.validUntil;
  }

  revokePassport(droneId: string, reason: string): void {
    const passport = this.passports.get(droneId);
    if (passport) {
      passport.status = 'revoked';
      this.revokedCerts.add(passport.certificate.serialNumber);
    }
  }

  addFlightRecord(droneId: string, record: FlightRecord): void {
    const passport = this.passports.get(droneId);
    if (passport) passport.flightLog.push(record);
  }

  getPassport(droneId: string): Passport | undefined {
    return this.passports.get(droneId);
  }

  private sign(data: string): string {
    // Production: RSA/ECDSA signature
    return Buffer.from(data).toString('base64').slice(0, 32);
  }

  listActive(): string[] {
    return [...this.passports.entries()]
      .filter(([_, p]) => p.status === 'active')
      .map(([id]) => id);
  }
}
