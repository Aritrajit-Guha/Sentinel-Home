# SentinelHome

A personalized disaster early-warning and evacuation coordination agent.
Detect -> Assess -> Advise -> Alert -> Observe -> Escalate -> Reassess.

## Structure
- `frontend/` — Phase 1, Vite-React household onboarding
- `backend/` — Phases 2, 4, 6, 7, 8, FastAPI + scheduling + notifications
- `agent/` — Phases 4, 5, 7, 8, LangGraph orchestration + RAG
- `ml/` — Phase 3, risk-scoring model training (working baseline included)
- `infra/` — deployment configs (Render, Vercel, docker-compose)
- `docs/` — architecture notes, API reference, report assets


## FOLDER STRUCTURE

```
sentinelhome/
│
├── frontend/                          # Phase 1 — Vite-React
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── HouseholdForm.jsx
│   │   │   ├── StatusDashboard.jsx
│   │   │   └── ui/                    # shared/reusable components
│   │   ├── pages/
│   │   │   ├── Onboarding.jsx
│   │   │   └── HouseholdStatus.jsx
│   │   ├── api/
│   │   │   └── client.js              # calls to FastAPI backend
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── tailwind.config.js
│
├── backend/                           # Phases 2, 4, 6, 7, 8 — FastAPI
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── households.py          # onboarding endpoints
│   │   │   ├── alerts.py              # webhook/status endpoints
│   │   │   └── admin.py
│   │   ├── core/
│   │   │   ├── config.py              # env vars, settings
│   │   │   └── database.py            # MongoDB/Redis connections
│   │   ├── models/
│   │   │   ├── household.py           # Pydantic + Mongo schemas
│   │   │   └── alert_log.py
│   │   ├── services/
│   │   │   ├── hazard_fetcher.py      # USGS + Open-Meteo polling (Phase 2)
│   │   │   ├── scoring_service.py     # calls the ML model (Phase 3)
│   │   │   ├── notification_service.py # Twilio SMS/call (Phase 6)
│   │   │   └── geocoding_service.py   # OpenStreetMap Nominatim
│   │   ├── scheduling/
│   │   │   ├── scheduler.py           # APScheduler/Celery setup
│   │   │   └── tasks.py               # periodic hazard-check jobs
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── agent/                             # Phases 4, 5, 7, 8 — LangChain/LangGraph
│   ├── graph/
│   │   ├── state.py                   # shared agent state schema
│   │   ├── nodes/
│   │   │   ├── threshold_check.py     # Phase 4
│   │   │   ├── guidance_composer.py   # Phase 5 (LLM + RAG + Maps)
│   │   │   ├── escalation.py          # Phase 7
│   │   │   └── reassessment.py        # Phase 8
│   │   └── build_graph.py             # LangGraph wiring
│   ├── rag/
│   │   ├── ingest.py                  # loads NDMA docs into Pinecone
│   │   ├── retriever.py
│   │   └── documents/                 # NDMA PDFs / source guideline docs
│   ├── prompts/
│   │   └── guidance_prompt.py
│   └── tools/
│       └── maps_tool.py               # shelter/route lookup tool
│
├── ml/                                # Phase 3 — model training
│   ├── data/
│   │   ├── raw/
│   │   │   ├── nepal_earthquake_train_values.csv
│   │   │   ├── nepal_earthquake_train_labels.csv
│   │   │   ├── nepal_earthquake_test_values.csv
│   │   │   ├── flood_risk_train.csv
│   │   │   ├── flood_risk_test.csv
│   │   │   └── social_vulnerability_index_2022_county.csv
│   │   └── processed/                 # cleaned/merged/feature-engineered
│   ├── notebooks/
│   │   └── eda.ipynb
│   ├── src/
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   ├── features.py
│   │   └── predict.py                 # loaded by scoring_service.py
│   └── models/
│       └── risk_model.pkl             # trained artifact
│
├── infra/
│   ├── docker-compose.yml             # local Mongo, Redis, backend, frontend
│   ├── render.yaml                    # backend deploy config
│   └── vercel.json                    # frontend deploy config
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── report/                        # your final project report assets
│
├── .env.example
├── .gitignore
└── README.md

```

## Getting started (ML baseline)
    cd ml
    pip install -r requirements.txt
    python src/train.py
    python src/predict.py   # smoke test
