# P743 Post-Quantum Crypto Overhead 분석

`src/quantum/pqc_telemetry.py` PoC의 대역폭·CPU 영향 분석.

## 알고리즘

| 용도 | 알고리즘 | 키 크기 | 비고 |
|---|---|---|---|
| KEM | **Kyber-768** | 1184 B (pub), 2400 B (sec) | NIST level 3 |
| Signature | **Dilithium-3** | 1952 B (pub), 4000 B (sec) | NIST level 3 |
| Symmetric | AES-256-GCM | 32 B | 표준 |

## 메시지 오버헤드

```
estimate_overhead(message_size_bytes=100)
→ {
    "plaintext_bytes": 100,
    "aes_gcm_tag_bytes": 16,
    "nonce_bytes": 12,
    "dilithium3_signature_bytes": 3293,
    "kem_ciphertext_bytes_per_session": 1088,
    "total_per_message_bytes": 3421,
    "overhead_pct": 3321.0
}
```

**텔레메트리 페이로드 100B → 3,421B 전송 (33× 증가)**

## 대역폭 영향

| 시나리오 | 드론 수 | 메시지율 | RSA 대비 | 양자 후 |
|---|---|---|---|---|
| 소규모 | 10 | 1 Hz | 1 KB/s | 34 KB/s |
| 중규모 | 50 | 5 Hz | 25 KB/s | 855 KB/s |
| 대규모 | 1000 | 10 Hz | 1 MB/s | **34 MB/s** |

→ 대규모는 LoRa·텔레메트리 채널 한계 초과 → **압축 + 차등 서명** 필요.

## 권장 운영 모드

1. **Critical 모드** (모든 메시지 PQC): F744 군용
2. **Hybrid 모드** (heartbeat만 PQC, 텔레메트리는 RSA): 일반 운영
3. **Legacy 모드** (RSA 전용): 양자 PoC 등장 전 임시

## 향후 작업

- [ ] Falcon-512로 서명 크기 690B로 축소 (NIST level 1)
- [ ] BLAKE3 메시지 해시 → Dilithium은 해시만 서명 (차등 서명)
- [ ] X25519 → ML-KEM 마이그레이션 가이드
