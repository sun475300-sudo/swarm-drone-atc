// Phase 530: TypeScript Drone Digital Passport — Certificate Chain

import * as crypto from 'crypto';

enum CertificateType {
  Airworthiness = 'airworthiness',
  OperatorLicense = 'operator_license',
  TypeCertificate = 'type_certificate',
  Insurance = 'insurance',
  Registration = 'registration',
}

enum PassportStatus {
  Valid = 'valid',
  Suspended = 'suspended',
  Revoked = 'revoked',
  Expired = 'expired',
}

interface Certificate {
  certId: string;
  certType: CertificateType;
  issuer: string;
  subject: string;
  validFrom: number;
  validUntil: number;
  signature: string;
  revoked: boolean;
}

interface FlightEntry {
  flightId: string;
  departure: string;
  destination: string;
  durationS: number;
  distanceKm: number;
  incidents: number;
}

interface DigitalPassport {
  passportId: string;
  droneId: string;
  manufacturer: string;
  model: string;
  serial: string;
  status: PassportStatus;
  certificates: Certificate[];
  flightHistory: FlightEntry[];
  totalFlightHours: number;
  maintenanceDue: boolean;
}

class PRNG {
  private state: number;
  constructor(seed: number) { this.state = seed ^ 0x6c62272e; }
  next(): number {
    this.state ^= this.state << 13;
    this.state ^= this.state >> 7;
    this.state ^= this.state << 17;
    return Math.abs(this.state);
  }
  float(): number { return (this.next() & 0x7FFFFFFF) / 0x7FFFFFFF; }
}

function sha256Short(data: string): string {
  return crypto.createHash('sha256').update(data).digest('hex').slice(0, 24);
}

class CertificateAuthority {
  private caName: string;
  private counter = 0;
  issued: Certificate[] = [];
  private revoked = new Set<string>();

  constructor(caName: string = 'SDACS-CA') { this.caName = caName; }

  issue(certType: CertificateType, subject: string, validityDays: number = 365): Certificate {
    this.counter++;
    const now = this.counter * 86400;
    const sig = sha256Short(`${this.caName}:${subject}:${this.counter}`);
    const cert: Certificate = {
      certId: `CERT-${String(this.counter).padStart(6, '0')}`,
      certType, issuer: this.caName, subject,
      validFrom: now, validUntil: now + validityDays * 86400,
      signature: sig, revoked: false,
    };
    this.issued.push(cert);
    return cert;
  }

  revoke(certId: string): void {
    this.revoked.add(certId);
    const cert = this.issued.find(c => c.certId === certId);
    if (cert) cert.revoked = true;
  }

  verify(cert: Certificate, currentTime?: number): boolean {
    if (this.revoked.has(cert.certId) || cert.revoked) return false;
    const t = currentTime ?? cert.validFrom + 1;
    return cert.validFrom <= t && t <= cert.validUntil;
  }
}

class DronePassportManager {
  private ca = new CertificateAuthority();
  private rng: PRNG;
  passports = new Map<string, DigitalPassport>();
  private flightCounter = 0;

  constructor(nDrones: number = 20, seed: number = 42) {
    this.rng = new PRNG(seed);
    const manufacturers = ['DroneCorp', 'SkyTech', 'AeroSystems', 'SwarmWorks'];
    const models = ['X-100', 'Falcon-V2', 'Scout-Pro', 'Titan-Heavy'];

    for (let i = 0; i < nDrones; i++) {
      const droneId = `drone_${i}`;
      const serial = sha256Short(`sn_${i}`).slice(0, 12);
      const passport: DigitalPassport = {
        passportId: `PP-${String(i).padStart(5, '0')}`,
        droneId, manufacturer: manufacturers[i % 4],
        model: models[i % 4], serial,
        status: PassportStatus.Valid,
        certificates: [],
        flightHistory: [],
        totalFlightHours: Math.round(this.rng.float() * 490 + 10),
        maintenanceDue: false,
      };

      for (const ct of Object.values(CertificateType)) {
        passport.certificates.push(this.ca.issue(ct as CertificateType, droneId, 90 + this.rng.float() * 640));
      }
      passport.maintenanceDue = passport.totalFlightHours > 400;
      this.passports.set(droneId, passport);
    }
  }

  recordFlight(droneId: string, dep = 'A', dest = 'B', durS = 600, distKm = 5): FlightEntry | null {
    const pp = this.passports.get(droneId);
    if (!pp || pp.status !== PassportStatus.Valid) return null;
    this.flightCounter++;
    const entry: FlightEntry = {
      flightId: `FLT-${String(this.flightCounter).padStart(6, '0')}`,
      departure: dep, destination: dest, durationS: durS, distanceKm: distKm, incidents: 0,
    };
    pp.flightHistory.push(entry);
    pp.totalFlightHours += durS / 3600;
    if (pp.totalFlightHours > 400) pp.maintenanceDue = true;
    return entry;
  }

  suspend(droneId: string): void {
    const pp = this.passports.get(droneId);
    if (pp) pp.status = PassportStatus.Suspended;
  }

  validate(droneId: string): { valid: boolean; status: string; certValid: boolean } {
    const pp = this.passports.get(droneId);
    if (!pp) return { valid: false, status: 'not_found', certValid: false };
    const certValid = pp.certificates.every(c => this.ca.verify(c));
    return { valid: pp.status === PassportStatus.Valid && certValid, status: pp.status, certValid };
  }

  audit(): { total: number; valid: number; suspended: number; flights: number; certs: number } {
    let valid = 0, suspended = 0;
    this.passports.forEach(p => {
      if (p.status === PassportStatus.Valid) valid++;
      if (p.status === PassportStatus.Suspended) suspended++;
    });
    return { total: this.passports.size, valid, suspended, flights: this.flightCounter, certs: this.ca.issued.length };
  }
}

// Main
const mgr = new DronePassportManager(20, 42);
mgr.recordFlight('drone_0', 'Base', 'DropZone', 900, 8.5);
mgr.recordFlight('drone_1', 'Base', 'Warehouse', 1200, 12.0);
mgr.suspend('drone_5');

const v0 = mgr.validate('drone_0');
const v5 = mgr.validate('drone_5');
const audit = mgr.audit();

console.log(`Drone 0: valid=${v0.valid} status=${v0.status}`);
console.log(`Drone 5: valid=${v5.valid} status=${v5.status}`);
console.log(`Audit: total=${audit.total} valid=${audit.valid} suspended=${audit.suspended} flights=${audit.flights} certs=${audit.certs}`);
