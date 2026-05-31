// Phase 530: Drone Digital Passport and Certificate System
// PKI-based identity management for swarm drones
// SDACS Digital Identity Module

import * as crypto from 'crypto';

// Certificate types for drone identity
export enum CertificateType {
  IDENTITY = 'identity',
  OPERATIONAL = 'operational',
  AIRSPACE = 'airspace',
  MAINTENANCE = 'maintenance',
}

// X.509-style Certificate for drone
export interface Certificate {
  serialNumber: string;
  issuer: string;
  subject: string;
  validFrom: Date;
  validUntil: Date;
  publicKey: string;
  signature: string;
  certType: CertificateType;
  droneId: string;
}

// Digital Passport for a drone
export interface Passport {
  passportId: string;
  droneId: string;
  manufacturer: string;
  model: string;
  serialNumber: string;
  registrationDate: Date;
  country: string;
  certificates: Certificate[];
  flightHours: number;
  lastInspection: Date;
  operationalStatus: 'active' | 'suspended' | 'maintenance';
}

// Certificate Authority for issuing drone certificates
export class CertificateAuthority {
  private readonly issuerName: string;
  private readonly keyPair: crypto.KeyPairKeyObjectResult;
  private issuedCerts: Map<string, Certificate> = new Map();

  constructor(issuerName: string) {
    this.issuerName = issuerName;
    // Generate RSA key pair for CA
    this.keyPair = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
  }

  issueCertificate(
    droneId: string,
    publicKey: string,
    certType: CertificateType,
    validDays: number = 365
  ): Certificate {
    const now = new Date();
    const validUntil = new Date(now.getTime() + validDays * 24 * 3600 * 1000);
    const serialNumber = crypto.randomBytes(16).toString('hex');

    const certData = JSON.stringify({
      serialNumber,
      droneId,
      publicKey,
      issuer: this.issuerName,
      validFrom: now.toISOString(),
      validUntil: validUntil.toISOString(),
    });

    const sign = crypto.createSign('SHA256');
    sign.update(certData);
    const signature = sign.sign(this.keyPair.privateKey, 'hex');

    const cert: Certificate = {
      serialNumber,
      issuer: this.issuerName,
      subject: droneId,
      validFrom: now,
      validUntil,
      publicKey,
      signature,
      certType,
      droneId,
    };

    this.issuedCerts.set(serialNumber, cert);
    return cert;
  }

  verifyCertificate(cert: Certificate): boolean {
    if (new Date() > cert.validUntil) return false;
    return this.issuedCerts.has(cert.serialNumber);
  }

  revokeCertificate(serialNumber: string): boolean {
    return this.issuedCerts.delete(serialNumber);
  }
}

// Passport registry for the swarm fleet
export class PassportRegistry {
  private passports: Map<string, Passport> = new Map();
  private ca: CertificateAuthority;

  constructor(caName: string = 'SDACS-CA') {
    this.ca = new CertificateAuthority(caName);
  }

  registerDrone(
    droneId: string,
    manufacturer: string,
    model: string,
    country: string = 'KR'
  ): Passport {
    const { publicKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
    const pubKeyStr = publicKey.export({ type: 'pkcs1', format: 'pem' }).toString();

    const identityCert = this.ca.issueCertificate(
      droneId, pubKeyStr, CertificateType.IDENTITY, 730
    );
    const operationalCert = this.ca.issueCertificate(
      droneId, pubKeyStr, CertificateType.OPERATIONAL, 365
    );

    const passport: Passport = {
      passportId: crypto.randomBytes(8).toString('hex'),
      droneId,
      manufacturer,
      model,
      serialNumber: `${manufacturer.toUpperCase()}-${Date.now()}`,
      registrationDate: new Date(),
      country,
      certificates: [identityCert, operationalCert],
      flightHours: 0,
      lastInspection: new Date(),
      operationalStatus: 'active',
    };

    this.passports.set(droneId, passport);
    return passport;
  }

  getPassport(droneId: string): Passport | undefined {
    return this.passports.get(droneId);
  }

  validatePassport(droneId: string): boolean {
    const passport = this.passports.get(droneId);
    if (!passport) return false;
    if (passport.operationalStatus !== 'active') return false;
    return passport.certificates.every(cert => this.ca.verifyCertificate(cert));
  }

  updateFlightHours(droneId: string, hours: number): void {
    const passport = this.passports.get(droneId);
    if (passport) {
      passport.flightHours += hours;
    }
  }

  getFleetStats(): Record<string, number> {
    const drones = Array.from(this.passports.values());
    return {
      total: drones.length,
      active: drones.filter(d => d.operationalStatus === 'active').length,
      suspended: drones.filter(d => d.operationalStatus === 'suspended').length,
      totalFlightHours: drones.reduce((sum, d) => sum + d.flightHours, 0),
    };
  }
}

// Main
const registry = new PassportRegistry('SDACS-CA');
const passport = registry.registerDrone('drone_001', 'SDACS', 'SwarmX-v2');
console.log(`SDACS Drone Digital Passport v530`);
console.log(`Passport issued: ${passport.passportId}`);
console.log(`Certificate count: ${passport.certificates.length}`);
console.log(`Validation: ${registry.validatePassport('drone_001')}`);
