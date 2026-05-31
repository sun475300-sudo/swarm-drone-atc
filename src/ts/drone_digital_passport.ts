// P530: DroneDigitalPassport - TypeScript digital identity for drone operations
// Phase 530: Certificate-based digital passport for regulatory compliance

export enum DroneClass {
  Class0 = 'C0',
  Class1 = 'C1',
  Class2 = 'C2',
  Class3 = 'C3',
  Class4 = 'C4',
}

export enum CertificateType {
  Airworthiness = 'AIRWORTHINESS',
  Registration = 'REGISTRATION',
  Operator = 'OPERATOR',
  RemotePilot = 'REMOTE_PILOT',
  Insurance = 'INSURANCE',
}

export interface Certificate {
  id: string;
  type: CertificateType;
  issuedBy: string;
  issuedAt: Date;
  expiresAt: Date;
  subject: string;
  serialNumber: string;
  signature: string;
  isRevoked: boolean;
}

export interface PassportHolder {
  operatorId: string;
  operatorName: string;
  registrationNumber: string;
  country: string;
}

export interface DronePassport {
  passportId: string;
  droneSerialNumber: string;
  droneClass: DroneClass;
  manufacturer: string;
  model: string;
  maxTakeoffWeight_g: number;
  holder: PassportHolder;
  certificates: Certificate[];
  issuedAt: Date;
  validUntil: Date;
}

export class PassportRegistry {
  private passports: Map<string, DronePassport> = new Map();
  private revokedCerts: Set<string> = new Set();

  register(passport: DronePassport): void {
    this.passports.set(passport.droneSerialNumber, passport);
  }

  getPassport(serialNumber: string): DronePassport | undefined {
    return this.passports.get(serialNumber);
  }

  validatePassport(serialNumber: string, checkDate: Date = new Date()): {
    valid: boolean;
    errors: string[];
  } {
    const passport = this.passports.get(serialNumber);
    const errors: string[] = [];

    if (!passport) {
      return { valid: false, errors: ['Passport not found'] };
    }

    if (checkDate > passport.validUntil) {
      errors.push(`Passport expired on ${passport.validUntil.toISOString()}`);
    }

    for (const cert of passport.certificates) {
      if (this.revokedCerts.has(cert.id)) {
        errors.push(`Certificate ${cert.id} has been revoked`);
      }
      if (checkDate > cert.expiresAt) {
        errors.push(`Certificate ${cert.type} expired on ${cert.expiresAt.toISOString()}`);
      }
    }

    return { valid: errors.length === 0, errors };
  }

  revokeCertificate(certId: string): void {
    this.revokedCerts.add(certId);
  }

  issueCertificate(params: {
    type: CertificateType;
    issuedBy: string;
    subject: string;
    validDays: number;
  }): Certificate {
    const now = new Date();
    const expires = new Date(now.getTime() + params.validDays * 86400000);
    return {
      id: `cert-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      type: params.type,
      issuedBy: params.issuedBy,
      issuedAt: now,
      expiresAt: expires,
      subject: params.subject,
      serialNumber: `SN-${Date.now()}`,
      signature: `sig-${Math.random().toString(36).slice(2)}`,
      isRevoked: false,
    };
  }
}
