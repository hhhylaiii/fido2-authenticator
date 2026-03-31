"""Credential storage backed by macOS keychain via keyring."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import keyring

from .config import AuthenticatorSettings
from .models import CredentialRecord, CredentialRecordModel


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore:
    def __init__(self, settings: AuthenticatorSettings):
        self.settings = settings
        self.service = settings.keyring_service
        self.index_path = Path(settings.credential_index_path).expanduser()
        self._lock = threading.Lock()
        self._sequence = 0
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index({})
        self._initialize_sequence()

    # Index helpers -----------------------------------------------------
    def _read_index(self) -> Dict[str, Dict[str, str]]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text())

    def _write_index(self, data: Dict[str, Dict[str, str]]) -> None:
        self.index_path.write_text(json.dumps(data, indent=2))

    def _update_index(self, record: CredentialRecord) -> None:
        with self._lock:
            index = self._read_index()
            index[record.credential_id] = {
                "user_handle": record.user_handle,
                "rp_id": record.rp_id,
                "last_used": self._next_sequence(),
            }
            self._write_index(index)

    def _remove_from_index(self, credential_id: str) -> None:
        with self._lock:
            index = self._read_index()
            if credential_id in index:
                index.pop(credential_id)
                self._write_index(index)

    def _initialize_sequence(self) -> None:
        with self._lock:
            index = self._read_index()
            max_seq = 0
            for metadata in index.values():
                seq = metadata.get("last_used")
                if isinstance(seq, int) and seq > max_seq:
                    max_seq = seq
            self._sequence = max_seq

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    # CRUD --------------------------------------------------------------
    def save(self, record: CredentialRecord) -> CredentialRecord:
        serialized = record.to_model().encode()
        keyring.set_password(self.service, record.credential_id, serialized)
        self._update_index(record)
        return record

    def delete(self, credential_id: str) -> None:
        keyring.delete_password(self.service, credential_id)
        self._remove_from_index(credential_id)

    def load(self, credential_id: str) -> CredentialRecord:
        serialized = keyring.get_password(self.service, credential_id)
        if serialized is None:
            raise CredentialStoreError(f"Credential {credential_id} not found")
        return CredentialRecord.from_model(CredentialRecordModel.decode(serialized))

    def list_all(self) -> List[CredentialRecord]:
        index = self._read_index()
        return [self.load(cred_id) for cred_id in index.keys()]

    def find_by_user(self, user_handle: str) -> List[CredentialRecord]:
        index = self._read_index()
        matches: List[CredentialRecord] = []
        for credential_id, metadata in index.items():
            if metadata.get("user_handle") == user_handle:
                matches.append(self.load(credential_id))
        return matches

    def find_by_rp(self, rp_id: str) -> List[CredentialRecord]:
        index = self._read_index()
        matches: List[CredentialRecord] = []
        for credential_id, metadata in index.items():
            if metadata.get("rp_id") == rp_id:
                matches.append(self.load(credential_id))
        return matches

    def find_first(self, allow_credentials: Iterable[str]) -> Optional[CredentialRecord]:
        for cred_id in allow_credentials:
            try:
                return self.load(cred_id)
            except CredentialStoreError:
                continue
        return None

    def list_metadata(self) -> Dict[str, Dict[str, str]]:
        with self._lock:
            index = self._read_index()
            return {cred_id: dict(metadata) for cred_id, metadata in index.items()}
