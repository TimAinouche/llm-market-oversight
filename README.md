# Autonomy under oversight: emergent manipulation by LLM trading agents in a simulated order book

**Research questions**
1. Do LLM trading agents develop harmful market behaviour (tacit collusion, spoofing, wash trading) **without being instructed to**?
2. Does this risk grow with their **autonomy** (communication, decision horizon, capital)?
3. Can a **monitor model** detect these behaviours from the agents' logs and reasoning, and when is human intervention needed?

**Why a market?** In AI safety, "harmful behaviour" is often hard to define and measure. Markets provide ground truth: manipulation has legal definitions (e.g. EU Market Abuse Regulation) and measurable effects (spread, depth, deviation from fundamental value, other participants' P&L).

**Related work.** Calvano et al. (*AER*, 2020) show that simple Q-learning pricing algorithms learn to collude tacitly. Fish, Gonczarowski & Shorrer (2024) find similar behaviour with LLM pricing agents. This project moves the question to a limit order book, treats autonomy as an experimental variable, and adds a monitoring layer.

## Design
- **Prompts are neutral.** LLM agents are only told to maximise profit; they are never told to manipulate, or not to. A unit test enforces that the prompt contains no such wording.
- **Control group.** Every LLM result is compared with a baseline market of non-LLM agents (a market maker and zero-intelligence traders, Gode & Sunder 1993).
- **Full logging.** Every decision is logged with the prompt, the model's reasoning and its actions, including rejected ones.
- **Reproducibility.** Fixed random seeds; same seed, same baseline result.

## Project structure
```
market/       order book (price-time priority), baseline agents, simulation loop
agents/       LLM trading agent, LLM clients (Gemma via Google AI Studio, offline mock)
experiments/  run_baseline.py, run_llm.py
tests/        unit tests
figures/      generated figures
```

## Progress
- [x] Order book: limit / market orders, cancels, price-time priority
- [x] Baseline market (zero-intelligence traders + market maker)
- [x] LLM trading agents (Gemma), with optional communication channel
- [ ] Experiment: autonomy levels × seeds, manipulation detectors
- [ ] Monitor model
- [ ] Results and write-up

## Baseline market
```bash
python3 -m experiments.run_baseline
```
![Baseline market](figures/baseline.png)

## LLM agents
Create a `.env` file at the project root with a free Google AI Studio key: `GEMINI_API_KEY=...`
```bash
python3 -m experiments.run_llm --mock     # offline dry run, no API calls
python3 -m experiments.run_llm            # LLM agents, no communication
python3 -m experiments.run_llm --comm     # LLM agents can message each other
```

## Setup and tests
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest
```
