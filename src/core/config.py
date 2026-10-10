"""Central configuration: paths, vehicle/market definitions, model settings."""
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_RAW = ROOT / "data" / "raw"
WORKSPACE = ROOT / "data" / "workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)
AUDIT_LOG = WORKSPACE / "audit_log.jsonl"

# LLM provider: "openai" (default - hackathon credits) or "anthropic".
PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
_DEFAULT_MODELS = {"openai": "gpt-5.5", "anthropic": "claude-opus-5-5"}
MODEL = os.getenv("LLM_MODEL") or _DEFAULT_MODELS.get(PROVIDER, "gpt-5.5")
EFFORT = os.getenv("LLM_EFFORT", "high")  # reasoning effort: low | medium | high
API_KEY_VAR = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(PROVIDER, "OPENAI_API_KEY")

MARKETS = {"EU": "Europe", "CN": "China", "US": "United States"}

# Country code -> sales market. Anything not listed falls into RoW.
COUNTRY_TO_MARKET = {
    **{c: "EU" for c in [
        "GB", "DE", "FR", "IT", "ES", "PT", "NL", "BE", "LU", "AT", "CH", "SE", "NO", "DK",
        "FI", "IS", "IE", "PL", "CZ", "SK", "HU", "SI", "HR", "RO", "BG", "GR", "EE", "LV", "LT",
    ]},
    "CN": "CN",
    "US": "US",
}

# Per vehicle line: which files/columns hold its data. "study_cn_eu" maps a market to the
# column header used in the CN_EU sheet; "study_us" to the header in the US sheet.
VEHICLES = {
    "F70": {
        "name": "BMW 1 Series (F70)",
        "feedback": "F70_feedback_hackathon.xlsx",
        "sales_sheet": "F70",
        "options": "F70_OptionList.PDF",
        "study_cn_eu": {"EU": "BMW 1 Series F70"},
        "study_us": None,
    },
    "G60": {
        "name": "BMW 5 Series (G60 / G68 LWB China)",
        "feedback": "G60_feedback_hackathon.xlsx",
        "sales_sheet": "G60_G68",
        "options": "G60_OptionList.PDF",
        "study_cn_eu": {"CN": "BMW 5 Series G68", "EU": "BMW 5 Series G60"},
        "study_us": "BMW 5 Series G60",
    },
    "G70": {
        "name": "BMW 7 Series (G70)",
        "feedback": "G70_feedback_hackathon.xlsx",
        "sales_sheet": "G70",
        "options": "G70_OptionList.PDF",
        "study_cn_eu": {"CN": "BMW 7 Series G70", "EU": "BMW 7 Series G70"},
        "study_us": "BMW 7 Series G70",
    },
}

STUDY_FILE = "F70_G60_G68_G70_customer_studies.xlsx"
SALES_FILE = "sales_volumes.xlsx"

NEGATIVE_TYPES = {"Defect", "Difficult to Use"}
