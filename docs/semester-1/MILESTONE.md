# Semester 1 Milestone: Research Prototype

## Objective
Deliver a working, transparent foundation for an autonomous financial research platform without making ungrounded live-market or investment-advice claims.

## Demonstrable features
- React research terminal with dashboard, company, portfolio, document, and methodology workflows.
- FastAPI API with company discovery, price overview, portfolio concentration analysis, and multi-agent research endpoints.
- Technical calculations: moving-average trend, RSI, historical volatility, and maximum drawdown.
- Bounded orchestrator with explicit Market, Fundamentals, News, Risk, Critic, and Explanation stages.
- Offline deterministic provider for reproducible demonstrations and tests.

## Evaluation demo
1. Open the dashboard and navigate to Company Research.
2. Select a company and create an evidence-scoped research run.
3. Show the six agent stages and explain the critic’s data-quality warnings.
4. Use Portfolio Lab to vary a position and observe the concentration classification.
5. Explain the document workflow and identify Qdrant retrieval as a Semester 2 milestone.

## Honest limitations
The current dataset is not live market data. Filings, document embeddings, authentication, database persistence, news ingestion, ML forecasting, and backtesting are deliberately deferred to Semester 2.
