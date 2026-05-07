from datetime import datetime, timezone
import secrets


def generate_paystack_reference() -> str:
    nonce = secrets.token_hex(4).upper()
    return f"TKF-{datetime.now(timezone.utc):%Y%m%d}-{nonce}"
