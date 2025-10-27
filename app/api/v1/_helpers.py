# app/api/v1/_helpers.py
import secrets, string

def gen_code(n: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))
