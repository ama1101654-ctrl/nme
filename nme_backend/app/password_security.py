from pwdlib import PasswordHash
from sqlalchemy import text


PASSWORD_DISABLED_VALUE = "!PASSWORD_HASH_ONLY!"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Create a password hash using pwdlib's recommended Argon2 settings."""
    if not password:
        raise ValueError("Password is required")
    return password_hash.hash(password)


def verify_password(password: str, encoded_password: str | None) -> bool:
    """Verify a password without exposing either value to logs or responses."""
    if not password or not encoded_password:
        return False
    try:
        return password_hash.verify(password, encoded_password)
    except Exception:
        return False


def migrate_legacy_passwords(engine) -> int:
    """Add password_hash and convert legacy plaintext values in one transaction."""
    with engine.begin() as connection:
        columns = connection.execute(text("PRAGMA table_info(users)")).fetchall()
        column_names = {row[1] for row in columns}
        if "password_hash" not in column_names:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))

        users = connection.execute(
            text("SELECT id, password, password_hash FROM users ORDER BY id")
        ).mappings().all()
        migrated_count = 0

        for user in users:
            encoded_password = user["password_hash"]
            if not encoded_password:
                legacy_password = user["password"]
                if not legacy_password or legacy_password == PASSWORD_DISABLED_VALUE:
                    raise RuntimeError("Cannot migrate user without valid legacy password material")
                encoded_password = hash_password(legacy_password)
                migrated_count += 1

            connection.execute(
                text(
                    "UPDATE users "
                    "SET password_hash = :password_hash, password = :disabled_password "
                    "WHERE id = :user_id"
                ),
                {
                    "password_hash": encoded_password,
                    "disabled_password": PASSWORD_DISABLED_VALUE,
                    "user_id": user["id"],
                },
            )

        missing_hash_count = connection.execute(
            text("SELECT COUNT(*) FROM users WHERE password_hash IS NULL OR TRIM(password_hash) = ''")
        ).scalar_one()
        if missing_hash_count:
            raise RuntimeError("Password migration left users without password hashes")

        return migrated_count