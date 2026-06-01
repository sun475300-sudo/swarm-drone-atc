// Phase 530: Drone Digital Passport — 드론 디지털 여권 (TypeScript)
// Digital identity and certificate management for drone fleet operations.

const PHASE = 530;

// ── Certificate types ──────────────────────────────────────────────

interface Certificate {
  serial: string;
  issuer: string;
  subject: string;
  notBefore: Date;
  notAfter: Date;
  publicKey: string;
  signature: string;
  algorithm: string;
}

interface OperationalLicense {
  licenseId: string;
  droneId: string;
  category: 'A1' | 'A2' | 'A3' | 'STS' | 'NTO';
  maxAltitude: number;
  maxRange: number;
  validUntil: Date;
  restrictions: string[];
}

// ── Digital Passport ───────────────────────────────────────────────

interface DronePassport {
  passportId: string;
  droneId: string;
  manufacturer: string;
  model: string;
  serialNumber: string;
  certificate: Certificate;
  license: OperationalLicense;
  registeredAt: Date;
  issuedBy: string;
  countryCode: string;
  firmwareHash: string;
}

// ── Passport registry ──────────────────────────────────────────────

class PassportRegistry {
  private passports = new Map<string, DronePassport>();
  private revoked   = new Set<string>();

  register(passport: DronePassport): void {
    if (this.passports.has(passport.droneId)) {
      throw new Error(`Passport already exists for drone ${passport.droneId}`);
    }
    this.passports.set(passport.droneId, passport);
  }

  revoke(droneId: string): void {
    this.revoked.add(droneId);
  }

  verify(droneId: string): { valid: boolean; reason?: string } {
    const p = this.passports.get(droneId);
    if (!p) return { valid: false, reason: 'Not registered' };
    if (this.revoked.has(droneId)) return { valid: false, reason: 'Revoked' };
    const now = new Date();
    if (now > p.certificate.notAfter) return { valid: false, reason: 'Certificate expired' };
    if (now > p.license.validUntil)   return { valid: false, reason: 'License expired' };
    return { valid: true };
  }

  lookup(droneId: string): DronePassport | undefined {
    return this.passports.get(droneId);
  }

  count(): number {
    return this.passports.size;
  }

  listActive(): string[] {
    return [...this.passports.keys()].filter(id => !this.revoked.has(id));
  }
}

// ── Passport factory ───────────────────────────────────────────────

function createPassport(droneId: string, index: number): DronePassport {
  const now  = new Date();
  const exp  = new Date(now.getTime() + 365 * 24 * 3600 * 1000);
  return {
    passportId:    `PP-${PHASE}-${index.toString().padStart(4, '0')}`,
    droneId,
    manufacturer:  'SDACS Industries',
    model:         'SwarmDrone-X',
    serialNumber:  `SN-${index}-${PHASE}`,
    certificate: {
      serial:    `CERT-${index}`,
      issuer:    'SDACS-CA',
      subject:   droneId,
      notBefore: now,
      notAfter:  exp,
      publicKey: `pub_key_${droneId}_${PHASE}`,
      signature: `sig_${Math.random().toString(36).slice(2)}`,
      algorithm: 'EC-P256',
    },
    license: {
      licenseId:    `LIC-${droneId}`,
      droneId,
      category:     'A2',
      maxAltitude:  120,
      maxRange:     3000,
      validUntil:   exp,
      restrictions: ['no-fly-zone-excl', 'daylight-only'],
    },
    registeredAt: now,
    issuedBy:     'SDACS-Authority',
    countryCode:  'KR',
    firmwareHash: `sha256:${Math.random().toString(16).slice(2).padEnd(64, '0')}`,
  };
}

// ── Entry point ────────────────────────────────────────────────────

const registry = new PassportRegistry();
for (let i = 0; i < 10; i++) {
  registry.register(createPassport(`drone_${i}`, i));
}

const check = registry.verify('drone_3');
console.log(`Phase ${PHASE}: Drone Digital Passport — 드론 디지털 여권`);
console.log(`Registered: ${registry.count()}, Active: ${registry.listActive().length}`);
console.log(`Passport verify drone_3: valid=${check.valid}`);
console.log(`Certificate issued by SDACS-CA, Passport type: DronePassport`);

export { PassportRegistry, DronePassport, Certificate, createPassport };
