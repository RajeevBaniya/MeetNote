import bcrypt


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(raw, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    raw = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(raw, hashed.encode("utf-8"))
