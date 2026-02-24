"""
Unit tests for core.utils.bcrypt — password hashing and verification.
"""

import pytest


@pytest.mark.unit
class TestHashPassword:
    def test_returns_string(self):
        from core.utils.bcrypt import hash_password

        result = hash_password("mypassword")
        assert isinstance(result, str)

    def test_hash_is_not_plaintext(self):
        from core.utils.bcrypt import hash_password

        result = hash_password("secret123")
        assert result != "secret123"

    def test_hash_starts_with_bcrypt_prefix(self):
        from core.utils.bcrypt import hash_password

        result = hash_password("test")
        assert result.startswith("$2b$")

    def test_different_passwords_produce_different_hashes(self):
        from core.utils.bcrypt import hash_password

        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_password_produces_different_hashes(self):
        """Each call uses a new salt, so hashes differ."""
        from core.utils.bcrypt import hash_password

        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_empty_password(self):
        from core.utils.bcrypt import hash_password

        result = hash_password("")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unicode_password(self):
        from core.utils.bcrypt import hash_password

        result = hash_password("pässwörd_日本語")
        assert isinstance(result, str)


@pytest.mark.unit
class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        from core.utils.bcrypt import hash_password, verify_password

        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_wrong_password_returns_false(self):
        from core.utils.bcrypt import hash_password, verify_password

        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_matches_empty_hash(self):
        from core.utils.bcrypt import hash_password, verify_password

        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_empty_password_does_not_match_nonempty(self):
        from core.utils.bcrypt import hash_password, verify_password

        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False

    def test_invalid_hash_raises(self):
        from core.utils.bcrypt import verify_password

        with pytest.raises(Exception):
            verify_password("test", "not-a-valid-hash")
