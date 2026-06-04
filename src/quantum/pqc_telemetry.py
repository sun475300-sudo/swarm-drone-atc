"""P743: 포스트양자 KEM (Kyber/Dilithium) 텔레메트리 채널 PoC.

NIST PQC 표준 Kyber-768 (KEM) + Dilithium-3 (서명) 기반 텔레메트리 암호화.

목적: 양자 컴퓨터 등장 후에도 안전한 드론↔지상국 통신.

의존성: pqcrypto (Python wrapper for liboqs)
    pip install pqcrypto

보안 가정:
- 사전 공유: 지상국 Dilithium 공개키
- 매 세션: Kyber로 AES-256 세션키 교환
- 매 메시지: AES-256-GCM 암호화 + Dilithium 서명
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PQCKeys:
    """포스트양자 키 쌍."""

    kyber_public: bytes      # 1184 bytes for Kyber-768
    kyber_secret: bytes      # 2400 bytes
    dilithium_public: bytes  # 1952 bytes for Dilithium-3
    dilithium_secret: bytes  # 4000 bytes


@dataclass(frozen=True)
class EncryptedFrame:
    """암호화된 텔레메트리 프레임."""

    kem_ciphertext: bytes    # Kyber encapsulation (1088 B)
    nonce: bytes             # AES-GCM nonce (12 B)
    ciphertext: bytes        # AES-256-GCM(plaintext)
    signature: bytes         # Dilithium-3 sig (3293 B)
    sender_id: str
    sequence_num: int


def generate_keys() -> PQCKeys:
    """Kyber-768 + Dilithium-3 키 쌍 생성."""
    try:
        from pqcrypto.kem import kyber768  # type: ignore[import-not-found]
        from pqcrypto.sign import dilithium3  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("pqcrypto 필요: pip install pqcrypto") from e

    kyber_pk, kyber_sk = kyber768.generate_keypair()
    dilith_pk, dilith_sk = dilithium3.generate_keypair()
    return PQCKeys(
        kyber_public=kyber_pk, kyber_secret=kyber_sk,
        dilithium_public=dilith_pk, dilithium_secret=dilith_sk,
    )


def derive_session_key(kyber_public: bytes) -> tuple[bytes, bytes]:
    """Kyber KEM으로 세션키 도출.

    Returns:
        (kem_ciphertext, session_key) — 32 bytes shared secret
    """
    try:
        from pqcrypto.kem import kyber768  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("pqcrypto 필요") from e
    ciphertext, shared_secret = kyber768.encrypt(kyber_public)
    return ciphertext, shared_secret


def decrypt_session_key(kyber_secret: bytes, kem_ciphertext: bytes) -> bytes:
    """Kyber 비밀키로 세션키 복호화."""
    try:
        from pqcrypto.kem import kyber768  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("pqcrypto 필요") from e
    return kyber768.decrypt(kyber_secret, kem_ciphertext)


def encrypt_telemetry(
    plaintext: bytes,
    session_key: bytes,
    dilithium_secret: bytes,
    sender_id: str,
    sequence_num: int,
) -> EncryptedFrame:
    """AES-256-GCM 암호화 + Dilithium-3 서명."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]
        from pqcrypto.sign import dilithium3  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("cryptography + pqcrypto 필요") from e

    aes = AESGCM(session_key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext, associated_data=sender_id.encode())
    signature = dilithium3.sign(dilithium_secret, ct + nonce)

    return EncryptedFrame(
        kem_ciphertext=b"",  # 세션마다 한 번만 보냄 (별도 frame)
        nonce=nonce,
        ciphertext=ct,
        signature=signature,
        sender_id=sender_id,
        sequence_num=sequence_num,
    )


def verify_and_decrypt(
    frame: EncryptedFrame,
    session_key: bytes,
    dilithium_public: bytes,
) -> bytes:
    """서명 검증 + 복호화. 실패 시 raise."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-not-found]
        from pqcrypto.sign import dilithium3  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("cryptography + pqcrypto 필요") from e

    # Dilithium 서명 검증
    try:
        dilithium3.verify(dilithium_public, frame.ciphertext + frame.nonce, frame.signature)
    except Exception as exc:
        raise ValueError(f"Dilithium 서명 검증 실패: {exc}") from exc

    # AES-256-GCM 복호화
    aes = AESGCM(session_key)
    return aes.decrypt(frame.nonce, frame.ciphertext, associated_data=frame.sender_id.encode())


def estimate_overhead(message_size_bytes: int = 100) -> dict[str, int]:
    """프레임 오버헤드 분석 — 텔레메트리 대역폭 영향 평가."""
    return {
        "plaintext_bytes": message_size_bytes,
        "aes_gcm_tag_bytes": 16,
        "nonce_bytes": 12,
        "dilithium3_signature_bytes": 3293,
        "kem_ciphertext_bytes_per_session": 1088,  # session-level
        "total_per_message_bytes": message_size_bytes + 16 + 12 + 3293,
        "overhead_pct": round((16 + 12 + 3293) / message_size_bytes * 100, 1),
    }
