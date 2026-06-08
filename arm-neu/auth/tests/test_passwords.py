"""Tests for bcrypt password hashing."""

from arm_auth.passwords import hash_password, verify_password


class TestPasswordHashing:
    def test_hash_returns_bcrypt_format(self):
        hashed = hash_password("secret")
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60

    def test_hash_different_each_time(self):
        h1 = hash_password("secret")
        h2 = hash_password("secret")
        assert h1 != h2  # different salts

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_password(self):
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False

    def test_hash_unicode_password(self):
        hashed = hash_password("p\u00e4ssw\u00f6rd")
        assert verify_password("p\u00e4ssw\u00f6rd", hashed) is True

    def test_hash_empty_password(self):
        hashed = hash_password("")
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60
        assert verify_password("", hashed) is True
