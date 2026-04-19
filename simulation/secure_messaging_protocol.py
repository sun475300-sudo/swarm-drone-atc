"""
Phase 446: Secure Messaging Protocol for Drone Communication
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib
import time


@dataclass
class Message:
    msg_id: str
    sender_id: str
    recipient_id: str
    content: bytes
    timestamp: float
    encrypted: bool = False


class SecureMessagingProtocol:
    def __init__(self):
        self.message_queue: Dict[str, List[Message]] = {}
        self.encryption_keys: Dict[str, bytes] = {}

    def generate_key(self, drone_id: str) -> bytes:
        key = hashlib.sha256(f"{drone_id}{time.time()}".encode()).digest()
        self.encryption_keys[drone_id] = key
        return key

    def send_message(self, sender: str, recipient: str, content: str) -> Message:
        msg = Message(
            msg_id=f"msg_{int(time.time() * 1000)}",
            sender_id=sender,
            recipient_id=recipient,
            content=content.encode(),
            timestamp=time.time(),
            encrypted=False,
        )

        if recipient not in self.message_queue:
            self.message_queue[recipient] = []
        self.message_queue[recipient].append(msg)

        return msg

    def encrypt_message(self, message: Message) -> Message:
        if message.recipient_id in self.encryption_keys:
            key = self.encryption_keys[message.recipient_id]
            encrypted = bytes(
                a ^ b
                for a, b in zip(
                    message.content, key * (len(message.content) // len(key) + 1)
                )
            )
            message.content = encrypted
            message.encrypted = True
        return message

    def get_messages(self, drone_id: str) -> List[Message]:
        return self.message_queue.get(drone_id, [])
