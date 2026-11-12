from datetime import timedelta
import pytest
from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_decoding():
    user_id = "user-12345-uuid"
    token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=15),
        extra_claims={"org_id": "org-54321", "role": "admin"},
    )
    
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["org_id"] == "org-54321"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_jwt_expired_token():
    user_id = "user-expired"
    # Token expired 1 minute ago
    token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=-1),
    )
    payload = decode_access_token(token)
    assert payload is None

