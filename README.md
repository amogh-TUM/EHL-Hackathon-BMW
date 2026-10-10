# BMW Requirement Copilot

AI-assisted derivation, justification and prioritisation of customer requirements for the next BMW vehicle generation — built for the BMW "AI for Product Decision Making" hackathon challenge. **The AI proposes, the product manager decides.**

## Quick start

```bash
git clone -b uzzi https://github.com/amogh-TUM/EHL-Hackathon-BMW.git
cd EHL-Hackathon-BMW
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip
cp .env.example .env                              # then put your OPENAI_API_KEY in .env
.venv/Scripts/streamlit run app.py                # macOS/Linux: .venv/bin/streamlit
```

The BMW data files are in `data/raw/`; a first AI run for the 5 Series (EU+US+CN) is in `data/workspace/`.
Tests (no API key needed): `.venv/Scripts/python tests/test_core.py`

## Workflow (maps to the evaluation criteria)

| Step | Who | What |
|---|---|---|
| 1 Data | System | Loads feedback (de-duplicated per comment), CN/EU + US customer studies (normalised 0-100), sales 2024/25/30, option lists; computes topic stats and **data gaps** |
| 2 Insights | AI proposes → **Gate 1: PM** | Claude synthesises needs/pain points with cited evidence; every citation is **machine-verified** against the dataset (✅ / 🟡 / ❌) |
| 3 Requirements | AI proposes | Customer-facing statements with evidence, **assumptions vs. evidence**, uncertainties, conflicts, what the current option list already offers |
| 4 Prioritisation | System computes, PM sets weights | Transparent weighted score; factors labelled *AI-judged* or *Computed*; **sensitivity** across weighting presets flags rank-unstable items |
| 5 Review | **Gate 2: PM** | Challenge (AI devil's advocate), web research (cited, labelled external), edit; approve / modify / postpone / reject with mandatory rationale |
| 6 Trace | System | Append-only audit log (`data/workspace/audit_log.jsonl`); requirement → insight → evidence → raw verbatim; JSON/Markdown export |

## Honesty by design
- Data gaps are detected and shown up front (e.g. **no China verbatims** in any feedback file; F70 not sold in CN/US; US study only for G60/G70) and passed to the model as constraints.
- Hallucinated citations are caught deterministically and lower the evidence-strength score.
- Low confidence, thin evidence, unverified citations and weight-sensitive ranks are flagged on every requirement card.

## Layout
```
app.py                  router: BMW theme, top navigation, scope sidebar
views/overview.py       hero + agent orchestration panel, metrics, priority recommendations, data in scope
views/evidence.py       signal room (clusters + verbatims with IDs), topic charts, customer study, sales, search
views/insights.py       Gate 1 - review AI insights
views/requirements.py   weights, ranking, sensitivity, Gate 2 review (challenge, research, decide)
views/decisions.py      PM decision queue across both gates
views/sources.py        source register incl. market boundaries and collected web sources
views/audit.py          trace a requirement, event log, exports
src/ui/theme.py         BMW Product Intelligence styling (from docs/design/bmw-requirement-intelligence.html)
src/core/config.py      vehicles, markets, file mapping, model settings
src/core/data_loader.py deterministic parsing of the BMW files
src/core/evidence.py    topic stats, data-gap report, quote sampling, citation verification
src/core/scoring.py     factor normalisation, weighted score, sensitivity
src/core/llm.py         provider-agnostic LLM layer (OpenAI or Claude): structured outputs + web search
src/core/prompts.py     versioned system prompts
src/core/pipeline.py    AI stages; all outputs enter as "proposed" and are logged
src/core/store.py       workspace JSON + append-only audit log
```

## AI provider
Set `LLM_PROVIDER` in `.env`:
- `openai` (default): `gpt-5.5` via the Responses API with strict structured outputs (pydantic schemas) and the built-in `web_search` tool. Needs `OPENAI_API_KEY`.
- `anthropic`: `claude-opus-5-5` with structured outputs, prompt caching and server-side refusal fallback. Needs `ANTHROPIC_API_KEY`.

Override the model with `LLM_MODEL` and reasoning depth with `LLM_EFFORT` (low/medium/high). Every AI run records provider, model and prompt version in the audit log.
