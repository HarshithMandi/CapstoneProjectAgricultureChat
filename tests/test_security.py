from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_verification():
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_access_token_round_trip():
    token = create_access_token("user-123", "admin")
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
