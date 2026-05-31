/**
 * Phase 530 — Drone digital Passport with Certificate chain and Passport identity management.
 * Each drone carries a digitally signed Passport that is verified on airspace entry.
 * Certificate chains anchor trust to a root CA operated by the swarm ATC authority.
 */

// ---- Phase marker ----
export const PHASE_MARKER = 530;

// ---- Certificate types ----

/** X.509-style certificate record for a drone or CA entity. */
export interface Certificate {
  serialNumber: string;
  subject: string;           // e.g. "drone-1001.swarm.atc"
  issuer: string;            // e.g. "intermediate-ca.swarm.atc"
  validFrom: Date;
  validUntil: Date;
  publicKey: string;         // PEM-encoded public key (stub: base64 placeholder)
  signature: string;         // Issuer's signature over the cert body (stub: hex string)
  keyUsage: CertificateKeyUsage[];
}

export type CertificateKeyUsage =
  | "digitalSignature"
  | "keyEncipherment"
  | "dataEncipherment"
  | "keyAgreement"
  | "keyCertSign"
  | "cRLSign";

// ---- Certificate chain ----

/**
 * CertificateChain holds root CA → intermediate CA → end-entity (drone) certificates.
 * Validates the chain in order: each cert must be signed by the next.
 */
export class CertificateChain {
  private certs: Certificate[];

  constructor(certs: Certificate[]) {
    if (certs.length < 2) {
      throw new Error("CertificateChain requires at least root + end-entity certs");
    }
    this.certs = certs;
  }

  /** Leaf certificate (drone end-entity cert). */
  get leaf(): Certificate {
    return this.certs[this.certs.length - 1];
  }

  /** Root CA certificate (trust anchor). */
  get root(): Certificate {
    return this.certs[0];
  }

  /** Returns chain depth (number of certificates). */
  get depth(): number {
    return this.certs.length;
  }

  /**
   * Validate the chain structure:
   * - each non-root cert's issuer matches the subject of the cert above it
   * - no cert is expired at `atTime`
   * Returns a ValidationResult with per-cert status.
   */
  validate(atTime: Date = new Date()): ValidationResult {
    const errors: string[] = [];
    for (let i = 0; i < this.certs.length; i++) {
      const cert = this.certs[i];
      // Expiry check
      if (atTime < cert.validFrom || atTime > cert.validUntil) {
        errors.push(`Certificate[${i}] "${cert.subject}" is expired or not yet valid`);
      }
      // Chain linkage check
      if (i > 0) {
        const parent = this.certs[i - 1];
        if (cert.issuer !== parent.subject) {
          errors.push(
            `Certificate[${i}] issuer "${cert.issuer}" ≠ parent subject "${parent.subject}"`
          );
        }
        // In a real implementation: verify cert.signature using parent.publicKey
      }
    }
    return {
      valid: errors.length === 0,
      errors,
      chainDepth: this.depth,
      leafSubject: this.leaf.subject,
    };
  }

  toJSON(): Certificate[] {
    return [...this.certs];
  }
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  chainDepth: number;
  leafSubject: string;
}

// ---- Drone Passport ----

/** Operational capabilities declared in the Passport. */
export interface DroneCapabilities {
  maxSpeedMs: number;
  maxAltitudeM: number;
  payloadKg: number;
  enduranceMinutes: number;
  hasCollisionAvoidance: boolean;
  hasBeyondVisualLineOfSight: boolean;
}

/** Airspace authority registration record. */
export interface AirspaceRegistration {
  registrationId: string;
  authorityName: string;
  country: string;
  registeredAt: Date;
  classes: string[];  // e.g. ["A", "B", "G"]
}

/**
 * DronePassport is the root identity document for a swarm drone.
 * It bundles the Certificate chain, capabilities, and registration data.
 * Passport instances are immutable after issuance.
 */
export class DronePassport {
  readonly passportId: string;
  readonly droneId: string;
  readonly manufacturer: string;
  readonly modelDesignation: string;
  readonly serialNumber: string;
  readonly certChain: CertificateChain;
  readonly capabilities: DroneCapabilities;
  readonly registrations: AirspaceRegistration[];
  readonly issuedAt: Date;
  readonly version: number;

  constructor(params: {
    droneId: string;
    manufacturer: string;
    modelDesignation: string;
    serialNumber: string;
    certChain: CertificateChain;
    capabilities: DroneCapabilities;
    registrations: AirspaceRegistration[];
  }) {
    this.passportId = `PASS-${params.droneId}-${Date.now()}`;
    this.droneId = params.droneId;
    this.manufacturer = params.manufacturer;
    this.modelDesignation = params.modelDesignation;
    this.serialNumber = params.serialNumber;
    this.certChain = params.certChain;
    this.capabilities = { ...params.capabilities };
    this.registrations = [...params.registrations];
    this.issuedAt = new Date();
    this.version = PHASE_MARKER;
  }

  /** Validate the Passport's Certificate chain and return overall status. */
  verify(atTime?: Date): ValidationResult {
    return this.certChain.validate(atTime);
  }

  /** Check if drone is authorised to operate in a given airspace class. */
  isAuthorisedForClass(airspaceClass: string): boolean {
    return this.registrations.some(r => r.classes.includes(airspaceClass));
  }

  /** Serialise to a JSON-compatible object for ATC data exchange. */
  toRecord(): Record<string, unknown> {
    return {
      passportId:       this.passportId,
      droneId:          this.droneId,
      manufacturer:     this.manufacturer,
      modelDesignation: this.modelDesignation,
      serialNumber:     this.serialNumber,
      certChain:        this.certChain.toJSON(),
      capabilities:     this.capabilities,
      registrations:    this.registrations,
      issuedAt:         this.issuedAt.toISOString(),
      version:          this.version,
    };
  }
}

// ---- Passport registry (in-memory stub for ATC lookup) ----

export class PassportRegistry {
  private store = new Map<string, DronePassport>();

  register(passport: DronePassport): void {
    this.store.set(passport.droneId, passport);
  }

  lookup(droneId: string): DronePassport | undefined {
    return this.store.get(droneId);
  }

  /** Verify and return the Passport, or throw if invalid / unknown. */
  verifyEntry(droneId: string, atTime?: Date): DronePassport {
    const passport = this.store.get(droneId);
    if (!passport) throw new Error(`PassportRegistry: unknown drone "${droneId}"`);
    const result = passport.verify(atTime);
    if (!result.valid) {
      throw new Error(`Passport verification failed for "${droneId}": ${result.errors.join("; ")}`);
    }
    return passport;
  }

  get size(): number {
    return this.store.size;
  }
}

// ---- Factory helpers for stub certificates ----

export function makeStubCert(subject: string, issuer: string, daysValid = 365): Certificate {
  const now = new Date();
  const expiry = new Date(now.getTime() + daysValid * 86400_000);
  return {
    serialNumber: `SN-${Math.random().toString(36).slice(2, 10).toUpperCase()}`,
    subject,
    issuer,
    validFrom: now,
    validUntil: expiry,
    publicKey: Buffer.from(`pub:${subject}`).toString("base64"),
    signature: Buffer.from(`sig:${issuer}→${subject}`).toString("hex"),
    keyUsage: ["digitalSignature", "keyEncipherment"],
  };
}

export function makeStubPassport(droneId: string): DronePassport {
  const rootCert = makeStubCert("root-ca.swarm.atc", "root-ca.swarm.atc");
  const intCert  = makeStubCert("intermediate-ca.swarm.atc", "root-ca.swarm.atc");
  const droneCert = makeStubCert(`${droneId}.swarm.atc`, "intermediate-ca.swarm.atc");
  const chain = new CertificateChain([rootCert, intCert, droneCert]);

  return new DronePassport({
    droneId,
    manufacturer: "SDACS Robotics",
    modelDesignation: "SR-4B",
    serialNumber: `SR4B-${droneId.toUpperCase()}`,
    certChain: chain,
    capabilities: {
      maxSpeedMs: 20,
      maxAltitudeM: 150,
      payloadKg: 1.5,
      enduranceMinutes: 30,
      hasCollisionAvoidance: true,
      hasBeyondVisualLineOfSight: false,
    },
    registrations: [{
      registrationId: `REG-${droneId}`,
      authorityName: "SDACS ATC Authority",
      country: "KR",
      registeredAt: new Date(),
      classes: ["G", "D"],
    }],
  });
}
