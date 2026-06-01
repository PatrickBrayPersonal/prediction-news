import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prediction_news.feed import build_feed

DATA_DIR = Path(__file__).parent.parent / "data" / "feeds"
# DOMAINS = ["politics", "world", "sports"]
DOMAINS = ["politics"]


async def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for domain in DOMAINS:
        print(f"Building {domain}...", flush=True)
        cards = await build_feed(domain)
        path = DATA_DIR / f"{domain}.json"
        path.write_text(json.dumps([c.model_dump() for c in cards], indent=2))
        print(f"  {len(cards)} cards → {path}")
    (DATA_DIR / "last_updated.json").write_text(
        json.dumps({"last_updated": datetime.now(timezone.utc).isoformat()})
    )
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
