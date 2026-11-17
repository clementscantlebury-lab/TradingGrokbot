# Solana Memecoin Paper Trading Desk

Six-agent pipeline (**SCOUT → FILTER → ANALYST → EXECUTOR → RISK → LOGGER**) for **paper trading only**. There is **no live trading code path** and **no wallet private key** handling.

Based on the Grok multi-agent blueprint (DexScreener / GeckoTerminal discovery, RugCheck safety, xAI Grok analyst, 8% sizing, −6% / +12% risk rules), with three configurable fixes for the vulnerabilities called out in blueprint §4.

## Agents

| Agent | Role |
|--------|------|
| **RISK** | Runs **first** each cycle: TWAP/1m stop evaluation, exit slippage |
| **SCOUT** | DexScreener latest profiles + GeckoTerminal new/trending pools |
| **FILTER** | Deterministic gate (never LLM): authorities, LP, holders, activity, cluster |
| **ANALYST** | Grok JSON score (optional) or **rule-based** fallback if `XAI_API_KEY` missing |
| **EXECUTOR** | Paper fills only (~1.5% entry slippage/fees) |
| **LOGGER** | SQLite + Rich terminal UI + morning recap |

## Blueprint §4 fixes (all configurable via env)

### 1. Volume lag trap

Fixed $50k 1h volume buys after the spike. Default **smart activity gate** uses:

- Lower absolute floor (`ACTIVITY_MIN_VOLUME_USD_H1`, default $8k)
- Volume ÷ liquidity ratio (`ACTIVITY_MIN_VOL_TO_LIQ_RATIO`)
- Buy/sell ratio cap (`ACTIVITY_MAX_BUY_SELL_RATIO`)
- Minimum buys proxy (`ACTIVITY_MIN_UNIQUE_BUYERS`)
- **Parabolic guard**: reject if price is too far above 1h low (`ACTIVITY_MAX_PRICE_ABOVE_RECENT_LOW_PCT`)

Set `FILTER_USE_LEGACY_50K_VOLUME=true` to reproduce the original strict gate.

### 2. Stop-loss whipsaw

Stops use **TWAP** (`RISK_STOP_EVAL_MODE=twap`, window `RISK_TWAP_WINDOW_SEC`) or **1m candle** close, not a single tick. Exits apply extra slippage (`RISK_EXIT_SLIPPAGE_BPS`, default 250 bps).

### 3. Bundled insider wallets

**Holder cluster check** uses RugCheck insider/bundle/fresh-wallet fields. If `CLUSTER_CHECK_REQUIRED=true` (default) and the check cannot run, the token is **rejected**.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Optional: XAI_API_KEY, SOLANA_RPC_URL
```

### Environment variables

See [`.env.example`](.env.example). Important:

- `XAI_API_KEY` — optional; without it, analyst uses **RULE_BASED_ANALYST**
- `SOLANA_RPC_URL` — optional Helius/QuickNode; tokens needing RPC verification are **rejected** if unavailable
- **Never** add a private key; the desk does not support one

## Run

```bash
# Live public API paper loop (Ctrl+C to stop; recap prints on exit)
paper-desk

# Short smoke (e.g. CI / agent)
paper-desk --cycles 3 --no-live-ui

# Replay recorded snapshots
paper-desk --replay

# Morning recap from SQLite
paper-desk --recap-only
```

### Overnight

```bash
nohup paper-desk --no-live-ui >> logs/desk.log 2>&1 &
```

In the morning:

```bash
paper-desk --recap-only
```

Recap includes scan count, rejections, fills, last equity, and top rejection reasons.

## Tests

```bash
pytest -q
```

## Replay fixtures

Drop JSON arrays under `fixtures/replay/` (see `cycle_01.json`). Each file is one pipeline cycle’s candidate list.

## Safety

- `DeskSettings.paper_mode_only` is always `True`
- Executor simulates fills locally; no Jupiter swap signing
- Filter rule: **if a condition cannot be verified, reject**

## Project layout

```
src/desk/
  agents/       # SCOUT, FILTER, ANALYST, EXECUTOR, RISK, LOGGER
  clients/      # DexScreener, GeckoTerminal, RugCheck, RPC
  filter/       # Activity gate + cluster check
  risk/         # TWAP / trailing stops
  storage/      # SQLite
  ui/           # Rich dashboard
tests/
fixtures/replay/
```