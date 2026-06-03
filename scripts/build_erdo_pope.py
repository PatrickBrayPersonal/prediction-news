import ast
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prediction_news.feed import _build_card

DATA_DIR = Path(__file__).parent.parent / "data"


async def main() -> None:
    raw = (DATA_DIR / "erdo_pope.json").read_text()
    market = ast.literal_eval(raw.strip())

    print(f"Building card for ticker={market.get('ticker')}...")
    card, _ = await _build_card(market, "politics")

    if card is None:
        print("No card returned (missing candlesticks or filtered out).")
        return

    out_path = DATA_DIR / "erdo_pope_card.json"
    out_path.write_text(json.dumps(card.model_dump(), indent=2))
    print(f"Card written to {out_path}")
    print(json.dumps(card.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
