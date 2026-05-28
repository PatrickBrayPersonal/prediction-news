from models import StoryCard, SparklinePoint, Source

MOCK_CARDS: list[StoryCard] = [
    # ── POLITICS ─────────────────────────────────────────────────────────────
    StoryCard(
        id="trump-approval-50",
        domain="politics",
        headline="Trump approval crosses 50% for first time since January",
        platform="Kalshi",
        market_name="Trump approval above 50% before July 2026",
        current_probability=0.61,
        probability_move=0.18,
        volume_usd=1_820_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.43),
            SparklinePoint(date="2026-05-22", probability=0.44),
            SparklinePoint(date="2026-05-23", probability=0.45),
            SparklinePoint(date="2026-05-24", probability=0.47),
            SparklinePoint(date="2026-05-25", probability=0.52),
            SparklinePoint(date="2026-05-26", probability=0.57),
            SparklinePoint(date="2026-05-27", probability=0.59),
            SparklinePoint(date="2026-05-28", probability=0.61),
        ],
        summary=(
            "A Reuters/Ipsos poll released Monday showed Trump's approval rating at 51%, "
            "the first reading above 50% since his second inauguration. The move was driven "
            "primarily by softening disapproval among independent voters in the Midwest, "
            "coinciding with the administration's announcement of a domestic manufacturing tax credit."
        ),
        calibration_note=(
            "A single poll crossing 50% is within the margin of error of several others still "
            "showing sub-50% approval. The market may be pricing in trend momentum rather than "
            "a durable shift."
        ),
        sources=[
            Source(
                title="Reuters/Ipsos: Trump approval hits 51% in new poll",
                url="https://www.reuters.com",
                type="rss",
            ),
            Source(
                title="@PollTracker: First 50+ reading since Jan 20",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    StoryCard(
        id="house-reconciliation-vote",
        domain="politics",
        headline="House budget reconciliation clears Ways and Means committee",
        platform="Polymarket",
        market_name="Reconciliation bill passes House before August 2026",
        current_probability=0.54,
        probability_move=0.12,
        volume_usd=980_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.42),
            SparklinePoint(date="2026-05-22", probability=0.41),
            SparklinePoint(date="2026-05-23", probability=0.43),
            SparklinePoint(date="2026-05-24", probability=0.44),
            SparklinePoint(date="2026-05-25", probability=0.46),
            SparklinePoint(date="2026-05-26", probability=0.50),
            SparklinePoint(date="2026-05-27", probability=0.52),
            SparklinePoint(date="2026-05-28", probability=0.54),
        ],
        summary=(
            "The House Ways and Means Committee advanced the reconciliation package Wednesday "
            "on a party-line vote after last-minute changes to the SALT deduction cap satisfied "
            "three holdout members from high-tax states. The bill now moves to the Rules Committee "
            "before a floor vote expected next week."
        ),
        calibration_note=(
            "Committee passage is a necessary but not sufficient step. The bill still faces "
            "opposition from at least four fiscal hawks who have not signaled support for the "
            "current spending levels. Floor passage remains genuinely uncertain."
        ),
        sources=[
            Source(
                title="Ways and Means advances reconciliation 23-18",
                url="https://www.axios.com",
                type="rss",
            ),
            Source(
                title="@HouseFloorWatch: Rules Committee scheduled for Thursday",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    StoryCard(
        id="fed-rate-hold",
        domain="politics",
        headline="Fed holds rates, removes language forecasting two 2026 cuts",
        platform="Kalshi",
        market_name="Fed cuts rates at least twice in 2026",
        current_probability=0.29,
        probability_move=-0.21,
        volume_usd=3_100_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.50),
            SparklinePoint(date="2026-05-22", probability=0.49),
            SparklinePoint(date="2026-05-23", probability=0.48),
            SparklinePoint(date="2026-05-24", probability=0.45),
            SparklinePoint(date="2026-05-25", probability=0.40),
            SparklinePoint(date="2026-05-26", probability=0.35),
            SparklinePoint(date="2026-05-27", probability=0.31),
            SparklinePoint(date="2026-05-28", probability=0.29),
        ],
        summary=(
            "The FOMC held rates at 4.25–4.50% and, in a significant shift, removed the "
            "phrase 'the Committee anticipates that adjustments may be appropriate' from its "
            "statement. Powell said in the press conference that the committee sees 'no urgency' "
            "to cut given sticky services inflation running at 4.1% annualized."
        ),
        calibration_note=(
            "Language changes in Fed statements are high-signal. Removing forward guidance "
            "language is a deliberate communication choice, not an accident. The market repricing "
            "here is likely well-founded."
        ),
        sources=[
            Source(
                title="Fed holds, drops rate-cut guidance from statement",
                url="https://www.axios.com",
                type="rss",
            ),
            Source(
                title="@NickTimiraos: Powell explicitly pushed back on near-term cuts",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    # ── WORLD ─────────────────────────────────────────────────────────────────
    StoryCard(
        id="eu-ai-act-delay",
        domain="world",
        headline="EU AI Act enforcement delayed past Q3 2026",
        platform="Polymarket",
        market_name="EU AI Act GPAI compliance deadline before Q3 2026",
        current_probability=0.48,
        probability_move=0.14,
        volume_usd=610_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.34),
            SparklinePoint(date="2026-05-22", probability=0.34),
            SparklinePoint(date="2026-05-23", probability=0.35),
            SparklinePoint(date="2026-05-24", probability=0.36),
            SparklinePoint(date="2026-05-25", probability=0.40),
            SparklinePoint(date="2026-05-26", probability=0.44),
            SparklinePoint(date="2026-05-27", probability=0.46),
            SparklinePoint(date="2026-05-28", probability=0.48),
        ],
        summary=(
            "Three EU member states circulated a draft amendment yesterday proposing an 18-month "
            "grace period for GPAI model compliance, citing concerns from national AI competitiveness "
            "bodies. The proposal has not yet been formally tabled, and two major member states have "
            "not signaled support."
        ),
        calibration_note=(
            "The odds movement likely reflects the proposal's existence rather than its likely "
            "passage. EU legislative amendments of this type typically require broad coalition "
            "support before advancing."
        ),
        sources=[
            Source(
                title="Three EU states push for AI Act grace period extension",
                url="https://www.euractiv.com",
                type="rss",
            ),
            Source(
                title="@MLStreet: Draft amendment text leaked, 18-month delay proposed",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    StoryCard(
        id="ukraine-ceasefire-talks",
        domain="world",
        headline="Ukraine and Russia resume direct talks in Istanbul for first time since 2022",
        platform="Kalshi",
        market_name="Ukraine ceasefire agreement before end of 2026",
        current_probability=0.38,
        probability_move=0.16,
        volume_usd=2_450_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.22),
            SparklinePoint(date="2026-05-22", probability=0.23),
            SparklinePoint(date="2026-05-23", probability=0.25),
            SparklinePoint(date="2026-05-24", probability=0.28),
            SparklinePoint(date="2026-05-25", probability=0.31),
            SparklinePoint(date="2026-05-26", probability=0.35),
            SparklinePoint(date="2026-05-27", probability=0.37),
            SparklinePoint(date="2026-05-28", probability=0.38),
        ],
        summary=(
            "Ukrainian and Russian delegations met in Istanbul Tuesday in the first direct "
            "government-to-government talks since March 2022. Turkish and US mediators were present. "
            "No joint statement was issued, but both sides confirmed a second meeting is planned "
            "within two weeks. The talks focused on prisoner exchanges and humanitarian corridors "
            "rather than territorial questions."
        ),
        calibration_note=(
            "Talks resuming is a meaningful signal, but the agenda — prisoner exchanges rather than "
            "borders — suggests this is early-stage confidence-building, not ceasefire negotiation. "
            "Historical base rates for these talks converting to agreements remain low."
        ),
        sources=[
            Source(
                title="Ukraine, Russia hold direct talks in Istanbul",
                url="https://www.bbc.com",
                type="rss",
            ),
            Source(
                title="@KyivIndependent: Second session confirmed, no territorial agenda yet",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    StoryCard(
        id="china-rare-earths",
        domain="world",
        headline="China partially lifts rare earth export restrictions on five elements",
        platform="Polymarket",
        market_name="US-China trade war de-escalation before Q4 2026",
        current_probability=0.44,
        probability_move=0.11,
        volume_usd=870_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.33),
            SparklinePoint(date="2026-05-22", probability=0.33),
            SparklinePoint(date="2026-05-23", probability=0.34),
            SparklinePoint(date="2026-05-24", probability=0.36),
            SparklinePoint(date="2026-05-25", probability=0.39),
            SparklinePoint(date="2026-05-26", probability=0.41),
            SparklinePoint(date="2026-05-27", probability=0.43),
            SparklinePoint(date="2026-05-28", probability=0.44),
        ],
        summary=(
            "China's Ministry of Commerce announced Tuesday that export licensing requirements "
            "for dysprosium, terbium, europium, gadolinium, and lutetium would be suspended for "
            "90 days for exports to non-sanctioned countries. The announcement came one day after "
            "a bilateral call between Treasury Secretary and Vice Premier He Lifeng."
        ),
        calibration_note=(
            "The 90-day suspension is a targeted, reversible gesture rather than a structural "
            "change. It covers five of the seventeen restricted elements. The market move reflects "
            "the call and gesture together — watch for whether the next bilateral meeting produces "
            "anything binding."
        ),
        sources=[
            Source(
                title="China suspends rare earth export curbs for 90 days",
                url="https://www.ft.com",
                type="rss",
            ),
            Source(
                title="@TradeDesk: Covers dysprosium + 4 others, not heavy REEs",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    # ── SPORTS ────────────────────────────────────────────────────────────────
    StoryCard(
        id="celtics-nba-finals",
        domain="sports",
        headline="Celtics advance to NBA Finals after Game 6 blowout over Knicks",
        platform="Kalshi",
        market_name="Boston Celtics win 2026 NBA Championship",
        current_probability=0.52,
        probability_move=0.24,
        volume_usd=1_340_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.28),
            SparklinePoint(date="2026-05-22", probability=0.29),
            SparklinePoint(date="2026-05-23", probability=0.31),
            SparklinePoint(date="2026-05-24", probability=0.33),
            SparklinePoint(date="2026-05-25", probability=0.38),
            SparklinePoint(date="2026-05-26", probability=0.44),
            SparklinePoint(date="2026-05-27", probability=0.49),
            SparklinePoint(date="2026-05-28", probability=0.52),
        ],
        summary=(
            "Boston closed out the Eastern Conference Finals in six games with a 118-94 win "
            "at Madison Square Garden. Jayson Tatum scored 38 points and Jaylen Brown added 27. "
            "The Celtics will face the Oklahoma City Thunder, who finished off the Nuggets on "
            "Sunday, in a Finals that begins Friday in Boston."
        ),
        calibration_note=(
            "Home-court advantage and defensive depth favor Boston, but OKC held the league's "
            "best regular-season record. This market is reflecting a genuine coin-flip series "
            "— the move is almost entirely explained by conference finals outcome, not new information "
            "about the matchup."
        ),
        sources=[
            Source(
                title="Celtics rout Knicks in Game 6, advance to Finals",
                url="https://www.espn.com",
                type="rss",
            ),
            Source(
                title="@ShamsCharania: Tatum confirmed healthy, no load management planned",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    StoryCard(
        id="dodgers-ace-injury",
        domain="sports",
        headline="Dodgers' ace tears UCL, out for season; World Series odds lengthen sharply",
        platform="Polymarket",
        market_name="Los Angeles Dodgers win 2026 World Series",
        current_probability=0.14,
        probability_move=-0.13,
        volume_usd=920_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.27),
            SparklinePoint(date="2026-05-22", probability=0.27),
            SparklinePoint(date="2026-05-23", probability=0.26),
            SparklinePoint(date="2026-05-24", probability=0.25),
            SparklinePoint(date="2026-05-25", probability=0.22),
            SparklinePoint(date="2026-05-26", probability=0.18),
            SparklinePoint(date="2026-05-27", probability=0.15),
            SparklinePoint(date="2026-05-28", probability=0.14),
        ],
        summary=(
            "The Dodgers announced Wednesday that Tyler Glasnow has a complete UCL tear and will "
            "undergo Tommy John surgery, ending his season. Glasnow led the rotation with a 2.71 ERA "
            "through eleven starts. The team has called up prospect Emmet Sheehan from Triple-A "
            "Oklahoma City to fill the rotation spot."
        ),
        calibration_note=(
            "Losing a frontline starter is the highest-impact roster event for World Series odds. "
            "The market repricing here is well-grounded — Glasnow accounted for a disproportionate "
            "share of the Dodgers' playoff rotation value. Sheehan is promising but unproven at "
            "this level."
        ),
        sources=[
            Source(
                title="Glasnow to undergo Tommy John, out for 2026 season",
                url="https://www.mlb.com",
                type="rss",
            ),
            Source(
                title="@JeffPassan: Surgery confirmed, 12-14 month recovery timeline",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
    StoryCard(
        id="verstappen-monaco",
        domain="sports",
        headline="Verstappen wins Monaco GP, extends F1 championship lead to 47 points",
        platform="Kalshi",
        market_name="Max Verstappen wins 2026 F1 World Championship",
        current_probability=0.67,
        probability_move=0.09,
        volume_usd=540_000,
        sparkline=[
            SparklinePoint(date="2026-05-21", probability=0.58),
            SparklinePoint(date="2026-05-22", probability=0.58),
            SparklinePoint(date="2026-05-23", probability=0.59),
            SparklinePoint(date="2026-05-24", probability=0.60),
            SparklinePoint(date="2026-05-25", probability=0.62),
            SparklinePoint(date="2026-05-26", probability=0.64),
            SparklinePoint(date="2026-05-27", probability=0.65),
            SparklinePoint(date="2026-05-28", probability=0.67),
        ],
        summary=(
            "Verstappen converted pole to victory in Monaco for the second consecutive year, "
            "with Norris finishing second and Hamilton third. The result extends Verstappen's "
            "championship lead over Norris to 47 points with 14 races remaining. Red Bull's "
            "pace advantage in high-downforce circuits was evident throughout the weekend."
        ),
        calibration_note=(
            "A 47-point lead with 14 races is historically very hard to overturn — only two "
            "drivers have overcome larger deficits at this stage in the modern points era. "
            "The market move is proportionate; Verstappen is now a strong favorite barring "
            "mechanical failures or incidents."
        ),
        sources=[
            Source(
                title="Verstappen wins Monaco, leads Norris by 47 points",
                url="https://www.formula1.com",
                type="rss",
            ),
            Source(
                title="@WillBuxton: Red Bull looked untouchable in race trim",
                url="https://x.com",
                type="x",
            ),
        ],
    ),
]
