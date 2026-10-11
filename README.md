# TRACE — Transparent Requirement Analysis & Customer Evidence

> AI requirement intelligence for product managers.

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

## How it works — a sequential AI pipeline with two human gates

The architecture follows the team's pipeline design: [`docs/design/pipeline-flowchart.jpeg`](docs/design/pipeline-flowchart.jpeg) (Research AI → Model analysis / Brand identification / Trend engine → Synthesis ⇄ Evaluation + Change log → Assessment engine + PM input → Decision Studio). The PM can add **creative input** to the synthesis engine; it is treated as a hypothesis, not evidence.

Four screens, one guided flow (a stepper on every page shows where you are and what to do next):

| Screen | Steps | What the PM does |
|---|---|---|
| **Overview** | – | Sees the scope, data gaps, progress, and the one next action |
| **Insight Explorer** | ① Signal engine → ② **Gate 1** | Accepts insights (one click, or bulk-accept the evidence-based ones); rejects with reason chips |
| **Requirement Board** | ③ Synthesis + Evaluation engines → priority engine | Sees a Kanban board ranked by a transparent score; tunes weights or presets; switches to the **3D customer map** — requirements pinned on a generic sedan where customers feel them (colour = decision, size = priority) |
| **Decision Studio** | ④ **Gate 2** | Decides one requirement at a time: evidence vs. assumption meter, AI self-review, adopt AI wording, reason chips |
| **Audit Trail** | – | Traces any requirement to raw verbatims; change log; append-only event log; sources; exports |

| # | Engine | Who | Output |
|---|---|---|---|
| 0 | Source engine — parse BMW files, topic stats, data gaps | System (deterministic) | stats, gaps |
| 1 | Signal engine — customer needs & pain points with machine-verified citations | AI | insights (JSON) |
| 2 | Synthesis engine — customer-facing requirements with evidence, assumptions, conflicts, current offer | AI | drafts (JSON) |
| 3 | **Evaluation engine** — critiques every draft: BMW brand lens (Sheer Driving Pleasure, premium quality, intuitive technology, sustainability), evidence check, wording; suggestions go to the change log, never auto-applied | AI | reviews (JSON) |
| 4 | Priority engine — weighted score; AI-judged vs computed factors; robustness across presets | System, PM weights | ranking |

Engines run in a fixed order with strict JSON schemas (no autonomous agent loops). **AI never approves anything.**

## Honesty by design
- Data gaps are detected and shown up front (e.g. **no China verbatims** in any feedback file; F70 not sold in CN/US; US study only for G60/G70) and passed to the model as constraints.
- Hallucinated citations are caught deterministically and lower the evidence-strength score.
- Low confidence, thin evidence, unverified citations and weight-sensitive ranks are flagged on every requirement card.

## Layout
```
app.py                      router: BMW theme, top navigation, scope sidebar
views/overview.py           hero + engine panel, stepper with next action, metrics, priority recommendations
views/insight_explorer.py   Gate 1 insight cards + evidence room (signal room, charts, study, sales, search)
views/board.py              Kanban requirement board, weights/presets, ranking breakdown & robustness
views/studio.py             Decision Studio: one-at-a-time review, AI self-review, reason chips
views/audit.py              requirement trace, change log, event log, sources, exports
src/ui/actions.py           pipeline runs shown as visible engine steps
src/ui/evidence_panels.py   deterministic evidence tabs
src/ui/car3d.py             3D customer map: requirement → car zone (wording + VFC topics), procedural sedan in three.js
assets/vendor/three.min.js  three.js r128 (MIT), bundled so the 3D map works offline
src/ui/theme.py             TRACE styling, stepper, evidence meter (design: docs/design/)
src/core/pipeline.py        engines: insights, requirements, evaluation, challenge, research
src/core/prompts.py         versioned system prompts per engine
src/core/schemas.py         strict JSON schemas (pydantic) per engine
src/core/scoring.py         factors (incl. brand fit), weighted score, sensitivity
src/core/evidence.py        topic stats, data gaps, quote sampling, citation verification
src/core/llm.py             provider-agnostic LLM layer (OpenAI or Claude)
src/core/store.py           workspace JSON + append-only audit log
```

## AI provider
Set `LLM_PROVIDER` in `.env`:
- `openai` (default): `gpt-5.5` via the Responses API with strict structured outputs (pydantic schemas) and the built-in `web_search` tool. Needs `OPENAI_API_KEY`.
- `anthropic`: `claude-opus-5-5` with structured outputs, prompt caching and server-side refusal fallback. Needs `ANTHROPIC_API_KEY`.

Override the model with `LLM_MODEL` and reasoning depth with `LLM_EFFORT` (low/medium/high). Every AI run records provider, model and prompt version in the audit log.

