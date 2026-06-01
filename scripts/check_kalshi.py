"""
Smoke-test script: list open Kalshi markets and inspect series tickers.
Run from the repo root: poetry run python scripts/check_kalshi.py
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from prediction_news.kalshi import list_markets


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()


async def main() -> None:
    from prediction_news.config import settings
    from prediction_news.kalshi import _REPO_ROOT

    key_path = _REPO_ROOT / settings.kalshi_private_key_path

    if key_path.exists():
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import hashlib

        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        pub_key_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        fingerprint = hashlib.sha256(pub_key_bytes).hexdigest()
        key_type = type(private_key).__name__

        print(f"  Key type       : {key_type}")
        if isinstance(private_key, rsa.RSAPrivateKey):
            print(f"  Key size       : {private_key.key_size} bits")
        print("  Public key SHA-256 fingerprint:")
        print(f"    {fingerprint}")
        print()
        print(
            "  Compare the fingerprint above with the key shown on your Kalshi dashboard."
        )
        print(
            "  If they differ, the private key file doesn't match the registered public key."
        )
    print()

    print("Fetching open markets (no series filter, limit 200)...")
    try:
        markets = await list_markets()
    except Exception as exc:
        print(f"\nERROR calling list_markets(): {type(exc).__name__}: {exc}")
        print(
            "\nIf 401: the UUID or private key doesn't match what's registered on the Kalshi dashboard."
        )
        print("If 403: wrong environment (demo key vs live API, or vice versa).")
        return

    if not markets:
        print(
            "API returned 0 markets. Either no open markets or series filter returned nothing."
        )
        return

    print(f"\nFound {len(markets)} open markets.\n")

    series_seen: dict[str, list[str]] = {}
    for m in markets:
        series = m.get("series_ticker", "(none)")
        ticker = m.get("ticker", "?")
        series_seen.setdefault(series, []).append(ticker)

    print("Series tickers and sample markets:")
    for series, tickers in sorted(series_seen.items()):
        print(f"  {series:30s}  ({len(tickers)} markets)  e.g. {tickers[0]}")

    print("\nFirst 3 markets (full detail):")
    for m in markets[:3]:
        print(
            f"  ticker={m.get('ticker')}  title={m.get('title', '')[:60]}  series={m.get('series_ticker')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
