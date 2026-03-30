"""
Phase 449: Data Encryption System for Secure Storage
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import hashlib
import time


@dataclass
class EncryptedData:
    data_id: str
    encrypted_content: bytes
    key_id: str
    timestamp: float


class DataEncryptionSystem:
    def __init__(self):
        self.keys: Dict[str, bytes] = {}
        self.encrypted_data: Dict[str, EncryptedData] = {}

    def generate_key(self, key_id: str) -> bytes:
        key = hashlib.sha256(f"{key_id}{time.time()}".encode()).digest()
        self.keys[key_id] = key
        return key

    def encrypt(self, data_id: str, content: bytes, key_id: str) -> EncryptedData:
        if key_id not in self.keys:
            self.generate_key(key_id)

        key = self.keys[key_id]
        encrypted = bytes(
            a ^ b for a, b in zip(content, key * (len(content) // len(key) + 1))
        )

        enc_data = EncryptedData(data_id, encrypted, key_id, time.time())
        self.encrypted_data[data_id] = enc_data

        return enc_data

    def decrypt(self, data_id: str) -> bytes:
        if data_id not in self.encrypted_data:
            return b""

        enc = self.encrypted_data[data_id]
        key = self.keys[enc.key_id]

        decrypted = bytes(
            a ^ b
            for a, b in zip(
                enc.encrypted_content,
                key * (len(enc.encrypted_content) // len(key) + 1),
            )
        )

        return decrypted

    def rotate_key(self, old_key_id: str, new_key_id: str) -> bool:
        if old_key_id not in self.keys:
            return False

        old_key = self.keys[old_key_id]

        for data_id, enc in self.encrypted_data.items():
            if enc.key_id == old_key_id:
                decrypted = self.decrypt(data_id)
                self.encrypt(data_id, decrypted, new_key_id)

        del self.keys[old_key_id]
        return True
