# FinAgent

Financial research and decision-support platform for Indian equities. FinAgent produces evidence-led research, model-derived signals, and risk analytics; it is not investment advice.

## Local quick start (Windows)

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

### Backend
Install Python 3.11+ from [python.org](https://www.python.org/downloads/windows/), then:
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Copy `.env.example` to `.env` before configuring OpenAI or Ollama. The API stays usable without either provider.

## Optional infrastructure
```powershell
docker compose up -d postgres redis qdrant
```

## Current capabilities
- Company discovery and deterministic NSE-style demo market data.
- Technical indicators, risk metrics, portfolio concentration analysis, and transparent warnings.
- Iterative multi-agent research workflow: market, fundamentals, news, risk, critic, and explanation.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/AGENTS.md](docs/AGENTS.md), and [PROJECT_STATUS.md](PROJECT_STATUS.md).
