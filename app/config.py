import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # No API key needed — uses claude CLI (Claude Code auth)

    DIGEST_HOUR: int = int(os.getenv("DIGEST_HOUR", "7"))
    DIGEST_MINUTE: int = int(os.getenv("DIGEST_MINUTE", "30"))
    DIGEST_TIMEZONE: str = os.getenv("DIGEST_TIMEZONE", "America/New_York")

    ENABLED_SOURCES: list[str] = [
        s.strip()
        for s in os.getenv(
            "ENABLED_SOURCES",
            "globenewswire,coindesk,cointelegraph,decrypt,theblock,wsj,bitcoinmagazine",
        ).split(",")
        if s.strip()
    ]

    GNW_KEYWORDS: list[str] = [
        k.strip().lower()
        for k in os.getenv(
            "GNW_KEYWORDS",
            "bitcoin,crypto,blockchain,ethereum,defi,stablecoin,digital asset,web3,nft,coinbase,binance,ripple,solana,polygon",
        ).split(",")
        if k.strip()
    ]

    MAX_ARTICLES_PER_CATEGORY: int = int(os.getenv("MAX_ARTICLES_PER_CATEGORY", "5"))
    LOOKBACK_HOURS: int = int(os.getenv("LOOKBACK_HOURS", "24"))

    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "8080"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crypto-digest.db')}",
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "crypto-digest-dev-key-change-in-prod")


config = Config()
