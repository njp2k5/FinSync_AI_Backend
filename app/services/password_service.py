from passlib.hash import bcrypt

def hash_password(p: str) -> str:
    return bcrypt.hash(p)

def verify_password(p: str, hash: str) -> bool:
    return bcrypt.verify(p, hash)
