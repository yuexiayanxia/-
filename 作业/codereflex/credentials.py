from __future__ import annotations
import getpass
import logging
import os

logger = logging.getLogger(__name__)


class CredentialStore:
    def __init__(self, use_keyring: bool = True):
        self._use_keyring = use_keyring
        self._keyring = None
        if use_keyring:
            try:
                import keyring
                self._keyring = keyring
            except ImportError:
                logger.warning("keyring not available, falling back to env vars (plaintext risk)")

    def get(self, key_name: str) -> str | None:
        if self._keyring:
            val = self._keyring.get_password("codereflex", key_name)
            if val:
                return val
        return os.environ.get(key_name)

    def set(self, key_name: str, value: str) -> None:
        if self._keyring:
            self._keyring.set_password("codereflex", key_name, value)
        else:
            logger.warning("Storing credential in env var (plaintext) — keyring unavailable")

    def delete(self, key_name: str) -> None:
        if self._keyring:
            try:
                self._keyring.delete_password("codereflex", key_name)
            except Exception:
                pass

    def status(self, key_name: str) -> bool:
        return self.get(key_name) is not None

    def setup_interactive(self, key_name: str) -> None:
        print(f"Enter value for {key_name} (input hidden):")
        value = getpass.getpass("> ")
        if value:
            self.set(key_name, value)
            print(f"{key_name} stored.")
        else:
            print("No value entered, skipping.")
