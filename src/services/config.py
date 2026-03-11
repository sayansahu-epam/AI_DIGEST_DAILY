"""
Configuration loader.
Reads settings from .env file.
"""

import os
from pathlib import Path

# Load .env file manually (no external dependencies)
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def _load_env():
    """Load .env file into environment variables."""
    if not ENV_PATH.exists():
        return
    
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse KEY=value
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Don't override existing env vars
                if key not in os.environ:
                    os.environ[key] = value


# Load on import
_load_env()


# ---------------------------------------------------------------------------
# Configuration Values
# ---------------------------------------------------------------------------


# Persona Toggles
PERSONA_GENAI_NEWS_ENABLED = os.getenv("PERSONA_GENAI_NEWS_ENABLED", "true").lower() == "true"
PERSONA_PRODUCT_IDEAS_ENABLED = os.getenv("PERSONA_PRODUCT_IDEAS_ENABLED", "true").lower() == "true"

# LLM Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# Evaluation Thresholds
GENAI_NEWS_MIN_RELEVANCE = float(os.getenv("GENAI_NEWS_MIN_RELEVANCE", "0.6"))
PRODUCT_IDEAS_MIN_RELEVANCE = float(os.getenv("PRODUCT_IDEAS_MIN_RELEVANCE", "0.5"))
MAX_ITEMS_TO_EVALUATE = int(os.getenv("MAX_ITEMS_TO_EVALUATE", "20"))
MAX_ITEMS_IN_DIGEST = int(os.getenv("MAX_ITEMS_IN_DIGEST", "10"))

# Delivery
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Quick Test
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=" * 60)
    print("  Configuration")
    print("=" * 60)
    
    print(f"\n📁 .env path: {ENV_PATH}")
    print(f"   Exists: {ENV_PATH.exists()}")
    
    print(f"\n🎭 Personas:")
    print(f"   GENAI_NEWS enabled:    {PERSONA_GENAI_NEWS_ENABLED}")
    print(f"   PRODUCT_IDEAS enabled: {PERSONA_PRODUCT_IDEAS_ENABLED}")
    
    print(f"\n🤖 LLM:")
    print(f"   Ollama URL: {OLLAMA_BASE_URL}")
    print(f"   Model:      {OLLAMA_MODEL}")
    
    print(f"\n📊 Thresholds:")
    print(f"   GENAI_NEWS min score:    {GENAI_NEWS_MIN_RELEVANCE}")
    print(f"   PRODUCT_IDEAS min score: {PRODUCT_IDEAS_MIN_RELEVANCE}")
    print(f"   Max items to evaluate:   {MAX_ITEMS_TO_EVALUATE}")
    print(f"   Max items in digest:     {MAX_ITEMS_IN_DIGEST}")
    
    print(f"\n📬 Delivery:")
    print(f"   Email enabled:    {EMAIL_ENABLED}")
    print(f"   Telegram enabled: {TELEGRAM_ENABLED}")
    
    print("\n" + "=" * 60)
    print("  ✅ Config loaded successfully!")
    print("=" * 60)