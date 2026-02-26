"""
Financial Academy Quiz Bank
35 curated multiple-choice questions seeded into Pinecone (namespace: quiz-pool).
Each record is upserted as a vector so that future calls to /quiz/pool/random
can retrieve random unseen questions via semantic search.

Metadata fields:
  type        : "quiz"
  topic       : topic slug used for filtering
  question    : the question text
  choices_json: JSON array of 4 answer strings
  answer_index: 0-based index of the correct answer
  text        : same as question (used as embedding source)
"""

import json

QUIZ_BANK: list[dict] = [
    # ── Compound Interest ──────────────────────────────────────────────────────
    {
        "id": "quiz-compound-1",
        "topic": "compound-interest",
        "question": "What does 'compound interest' mean?",
        "choices": [
            "Interest calculated only on the principal amount",
            "Interest calculated on the principal plus accumulated interest",
            "A fixed interest rate that never changes",
            "Interest paid only at the end of the loan term",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-compound-2",
        "topic": "compound-interest",
        "question": "If you invest $1,000 at 10% annual compound interest, approximately how much will you have after 7 years?",
        "choices": ["$1,700", "$1,948", "$2,000", "$1,610"],
        "answer_index": 1,
    },
    {
        "id": "quiz-compound-3",
        "topic": "compound-interest",
        "question": "How does compounding frequency affect investment growth?",
        "choices": [
            "Higher frequency means slower growth",
            "Frequency has no effect on growth",
            "Higher frequency means slightly more growth",
            "Compounding only works annually",
        ],
        "answer_index": 2,
    },
    {
        "id": "quiz-compound-4",
        "topic": "compound-interest",
        "question": "The 'Rule of 72' helps you estimate what?",
        "choices": [
            "Your annual tax liability",
            "How many years to double an investment at a given rate",
            "The minimum return needed to beat inflation",
            "The maximum safe withdrawal rate in retirement",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-compound-5",
        "topic": "compound-interest",
        "question": "Which type of account commonly compounds interest daily?",
        "choices": ["Traditional IRA", "401(k)", "High-yield savings account", "Series I Bond"],
        "answer_index": 2,
    },

    # ── Investing Basics ───────────────────────────────────────────────────────
    {
        "id": "quiz-investing-1",
        "topic": "investing-basics",
        "question": "What is an ETF (Exchange-Traded Fund)?",
        "choices": [
            "A savings account with a fixed interest rate",
            "A basket of securities that trades on a stock exchange like a stock",
            "A government bond with guaranteed returns",
            "A type of life insurance product",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-investing-2",
        "topic": "investing-basics",
        "question": "What is 'diversification' in investing?",
        "choices": [
            "Putting all money in the highest-performing asset",
            "Holding only index funds",
            "Spreading investments across different asset classes to reduce risk",
            "Buying and selling stocks within the same day",
        ],
        "answer_index": 2,
    },
    {
        "id": "quiz-investing-3",
        "topic": "investing-basics",
        "question": "Dollar-cost averaging involves:",
        "choices": [
            "Investing a lump sum at the market bottom",
            "Investing a fixed amount at regular intervals regardless of price",
            "Only buying stocks when prices drop 10%",
            "Matching your portfolio to a dollar index",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-investing-4",
        "topic": "investing-basics",
        "question": "What is the P/E (Price-to-Earnings) ratio used for?",
        "choices": [
            "Measuring a company's debt level",
            "Measuring stock price volatility",
            "Valuing a company relative to its earnings",
            "Calculating dividend yield",
        ],
        "answer_index": 2,
    },
    {
        "id": "quiz-investing-5",
        "topic": "investing-basics",
        "question": "A stock's 'dividend yield' is best described as:",
        "choices": [
            "Annual dividend per share divided by the current stock price",
            "Total earnings per share over the past year",
            "The percentage of revenue paid out in taxes",
            "The difference between 52-week high and low",
        ],
        "answer_index": 0,
    },
    {
        "id": "quiz-investing-6",
        "topic": "investing-basics",
        "question": "What does 'asset allocation' mean?",
        "choices": [
            "Picking the most popular stocks",
            "Distributing investments across asset categories like stocks, bonds, and cash",
            "Calculating the tax owed on investment gains",
            "The process of rebalancing a portfolio monthly",
        ],
        "answer_index": 1,
    },

    # ── Tax Strategies ─────────────────────────────────────────────────────────
    {
        "id": "quiz-tax-1",
        "topic": "tax-strategies",
        "question": "What is 'tax-loss harvesting'?",
        "choices": [
            "Deferring all taxes until retirement",
            "Selling losing investments to offset capital gains taxes",
            "Claiming depreciation on real estate",
            "Moving income to a lower tax bracket",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-tax-2",
        "topic": "tax-strategies",
        "question": "What is the main tax advantage of a Roth IRA?",
        "choices": [
            "Contributions are tax-deductible",
            "Withdrawals in retirement are tax-free",
            "No contribution limits apply",
            "Gains are never taxed if held more than one year",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-tax-3",
        "topic": "tax-strategies",
        "question": "What is a 'long-term capital gain' typically defined as?",
        "choices": [
            "A gain on an asset held for less than 6 months",
            "Any gain from selling bonds",
            "A gain on an asset held for more than one year",
            "Income from dividends only",
        ],
        "answer_index": 2,
    },
    {
        "id": "quiz-tax-4",
        "topic": "tax-strategies",
        "question": "A 401(k) contribution reduces your taxable income because:",
        "choices": [
            "The gains are never taxed",
            "Contributions are made pre-tax, lowering your current year income",
            "The government matches every dollar you put in",
            "Withdrawals before 59½ are tax-free",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-tax-5",
        "topic": "tax-strategies",
        "question": "The 'wash-sale rule' prevents investors from:",
        "choices": [
            "Claiming a loss if they repurchase the same security within 30 days",
            "Selling stocks at a loss more than once per year",
            "Using losses to offset ordinary income",
            "Holding stocks for less than one year",
        ],
        "answer_index": 0,
    },
    {
        "id": "quiz-tax-6",
        "topic": "tax-strategies",
        "question": "Which account offers a triple tax advantage (contributions, growth, and withdrawals)?",
        "choices": ["Roth IRA", "Traditional 401(k)", "Health Savings Account (HSA)", "529 College Plan"],
        "answer_index": 2,
    },

    # ── Market Mechanics ───────────────────────────────────────────────────────
    {
        "id": "quiz-market-1",
        "topic": "market-mechanics",
        "question": "What is a 'limit order' in stock trading?",
        "choices": [
            "An order that executes immediately at the current market price",
            "An order that executes only at a specified price or better",
            "An order to short-sell a stock",
            "A standing order that expires after one trading day",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-market-2",
        "topic": "market-mechanics",
        "question": "What causes a stock price to rise in a free market?",
        "choices": [
            "The company increases its debt",
            "Demand for shares exceeds supply",
            "The government sets a higher price floor",
            "The stock is added to a new index",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-market-3",
        "topic": "market-mechanics",
        "question": "What is the difference between the 'bid' and 'ask' price?",
        "choices": [
            "They are always equal on liquid markets",
            "Bid is what buyers will pay; ask is what sellers want",
            "Bid is the opening price; ask is the closing price",
            "Bid is the institutional price; ask is the retail price",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-market-4",
        "topic": "market-mechanics",
        "question": "Market capitalization is calculated as:",
        "choices": [
            "Annual revenue multiplied by 10",
            "Total debt minus total equity",
            "Share price multiplied by total shares outstanding",
            "Net income divided by share price",
        ],
        "answer_index": 2,
    },
    {
        "id": "quiz-market-5",
        "topic": "market-mechanics",
        "question": "What is a 'bear market'?",
        "choices": [
            "A market where prices are rising 20% or more",
            "A market where prices have fallen 20% or more from recent highs",
            "A market with very high trading volume",
            "A market limited to institutional investors",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-market-6",
        "topic": "market-mechanics",
        "question": "An IPO (Initial Public Offering) refers to:",
        "choices": [
            "A company buying back its own shares",
            "A merger between two public companies",
            "The first time a company sells shares to the general public",
            "Annual dividend announcements by large corporations",
        ],
        "answer_index": 2,
    },

    # ── Crypto Basics ──────────────────────────────────────────────────────────
    {
        "id": "quiz-crypto-1",
        "topic": "crypto-basics",
        "question": "What is a blockchain?",
        "choices": [
            "A centralised database controlled by a single bank",
            "A distributed, immutable ledger of transactions shared across a network",
            "A type of digital wallet issued by governments",
            "A programming language for smart contracts",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-crypto-2",
        "topic": "crypto-basics",
        "question": "What is 'proof of work' in cryptocurrency?",
        "choices": [
            "A legal document proving ownership of crypto",
            "A consensus mechanism where miners solve complex puzzles to validate blocks",
            "The process of converting fiat to crypto",
            "A security protocol used by crypto exchanges",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-crypto-3",
        "topic": "crypto-basics",
        "question": "What is a 'smart contract'?",
        "choices": [
            "A digital investment advisor powered by AI",
            "A legal contract signed with a digital signature",
            "Self-executing code on a blockchain that runs when pre-set conditions are met",
            "A government-issued digital currency contract",
        ],
        "answer_index": 2,
    },
    {
        "id": "quiz-crypto-4",
        "topic": "crypto-basics",
        "question": "Bitcoin's maximum total supply is capped at:",
        "choices": ["100 million BTC", "21 million BTC", "1 billion BTC", "Unlimited"],
        "answer_index": 1,
    },
    {
        "id": "quiz-crypto-5",
        "topic": "crypto-basics",
        "question": "What does 'DeFi' stand for?",
        "choices": [
            "Digital Finance Infrastructure",
            "Decentralised Finance",
            "Derivative Financial Instruments",
            "Direct Fund Investment",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-crypto-6",
        "topic": "crypto-basics",
        "question": "A 'crypto wallet' primarily stores:",
        "choices": [
            "The actual cryptocurrency coins as files",
            "Private and public keys that allow you to access your crypto on the blockchain",
            "A backup copy of the blockchain",
            "Exchange login credentials",
        ],
        "answer_index": 1,
    },

    # ── Retirement Planning ────────────────────────────────────────────────────
    {
        "id": "quiz-retirement-1",
        "topic": "retirement",
        "question": "What is the 4% rule in retirement planning?",
        "choices": [
            "You should invest 4% of your salary each month",
            "You can safely withdraw 4% of your portfolio per year in retirement",
            "Bond allocation should be 4% of your portfolio",
            "Social Security replaces 4% of income in retirement",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-retirement-2",
        "topic": "retirement",
        "question": "At what age can you withdraw from a traditional IRA without an early withdrawal penalty?",
        "choices": ["55", "62", "59½", "65"],
        "answer_index": 2,
    },
    {
        "id": "quiz-retirement-3",
        "topic": "retirement",
        "question": "What is an employer 401(k) match?",
        "choices": [
            "A penalty for withdrawing before retirement",
            "Free money an employer contributes matching your own 401(k) contributions",
            "A government subsidy for small businesses",
            "A fee charged by the plan administrator",
        ],
        "answer_index": 1,
    },

    # ── Risk Management ────────────────────────────────────────────────────────
    {
        "id": "quiz-risk-1",
        "topic": "risk-management",
        "question": "What does 'beta' measure in stock analysis?",
        "choices": [
            "A stock's dividend growth rate",
            "A stock's volatility relative to the overall market",
            "A stock's price-to-book ratio",
            "A company's quarterly earnings growth",
        ],
        "answer_index": 1,
    },
    {
        "id": "quiz-risk-2",
        "topic": "risk-management",
        "question": "An 'emergency fund' is recommended to cover:",
        "choices": [
            "1 week of expenses",
            "3–6 months of living expenses",
            "1 year of income",
            "Only mortgage payments",
        ],
        "answer_index": 1,
    },
]


def build_pinecone_docs() -> list[dict]:
    """Convert the quiz bank into Pinecone-ready document dicts."""
    docs = []
    for q in QUIZ_BANK:
        choices_json = json.dumps(q["choices"])
        docs.append({
            "id": q["id"],
            "text": q["question"],   # embedded text = the question itself
            "metadata": {
                "type":         "quiz",
                "topic":        q["topic"],
                "question":     q["question"],
                "choices_json": choices_json,
                "answer_index": q["answer_index"],
                "source":       "quiz-bank",
                "agent":        "finance_qa",
            },
        })
    return docs
