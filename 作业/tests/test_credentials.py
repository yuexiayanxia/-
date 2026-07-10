import os
from unittest.mock import patch
from codereflex.credentials import CredentialStore


def test_env_fallback():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        store = CredentialStore(use_keyring=False)
        assert store.get("OPENAI_API_KEY") == "sk-test"


def test_status_true_when_set():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        store = CredentialStore(use_keyring=False)
        assert store.status("OPENAI_API_KEY") is True


def test_status_false_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        store = CredentialStore(use_keyring=False)
        assert store.status("MY_KEY") is False


def test_get_returns_none_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        store = CredentialStore(use_keyring=False)
        assert store.get("MY_KEY") is None
