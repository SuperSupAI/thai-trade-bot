---
name: scrutinize
description: Outsider-perspective end-to-end review of a backtest, strategy change, or bot code change in this repo. Questions intent first (is there a simpler way / does the result already exist?), then traces the actual code path end-to-end, then checks it against the specific bug patterns this project has hit before (off-by-one date indexing, non-independent test windows, universe intersection-vs-union bugs, inconsistent trading mechanics between sim functions, currency/unit mixing). Trigger on /scrutinize and proactively whenever the user asks to review, audit, sanity-check, or get a second opinion on a backtest result, a strategy idea, a research-log claim, or a change to app.py / any test_*.py file before it gets pushed or connected to a real Settrade order.
---

# Scrutinize

Stand outside the change and ask whether the conclusion should be believed at all, then verify the code actually produces it.

## Operating stance

- **Outsider.** Forget who wrote it and why they think it's right. Read the artifact cold.
- **End-to-end, not diff-local.** The diff is the entry point, not the scope. Follow the actual computation from raw price data to the number reported to the user.
- **Actionable, concise, with rationale.** Every finding states what to change, why, and what evidence led you there. No filler, no restating the diff back.

## Workflow

Run these in order. Do not skip ahead.

### 1. Intent — what is this actually claiming?

State the claim in one sentence, in your own words ("universe X beats universe Y on TRAIN/VALID/TEST" / "overlay Z reduces 2022 drawdown"). If you cannot, the result is underspecified — say so and stop.

Ask: is there a simpler or already-existing way to check this?
- Does an existing `test_*.py` in this repo already answer (or partially answer) the same question with a different name?
- Is the "new" finding actually just the old finding restated with a different window/universe?
- Could the claim be checked with fewer, more independent samples instead of a bigger backtest?

### 2. Trace — walk the actual computation

For each number in the claim, trace it end-to-end through the real code, not just the new lines:
- Where does the price series come from (which cache file, which fetch, what date range)?
- Where does the rebalance date grid come from, and does every symbol in the universe actually have data at that date, or does a `dt not in close.index` check silently drop it?
- Where is "today" / "the last row" computed, and does it match the historical formula's convention (see off-by-one check below)?
- What currency/unit is each price series in at the point it's compared or summed with another series?

### 3. Verify — check against this project's known failure patterns

These are bugs and false-positive patterns this specific codebase has actually produced. Check for each one explicitly; don't just eyeball it.

- **Off-by-one on "current" snapshots.** Historical sim code correctly uses `close.iloc[i - SKIP]` where `i = close.index.get_loc(dt)` for a real rebalance date. A "live/today" snapshot must use the equivalent of `i = len(close) - 1`, i.e. `close.iloc[-1 - SKIP]`, **not** `close.iloc[-SKIP]`. The latter is off by one day and can matter a lot for a fast-moving stock (found live in this repo: MU showed +892.8% with the bug vs the correct +822.4%).
- **Non-independent "robustness" samples.** Testing the same claim over several windows that all end on the same "today" (e.g. 1/2/3/5/9-year lookbacks) is *not* independent evidence — they share almost all their underlying trades. A pattern that "confirms across 4 of 5 windows" this way can evaporate under a properly pooled test with many independent, non-overlapping start dates (found live in this repo: the "first rebalance underperforms" hypothesis looked strong across 5 nested windows, then mostly disappeared once tested across 40 independent cold-start dates).
- **Universe intersection vs union.** When building a combined price-series dict across tickers with staggered listing dates (IPOs, new DR issuances), using `set.intersection` of all symbols' date indices silently truncates the whole backtest to start at the *latest* IPO — compare "total invested" or date-range output across variants to catch this, don't just trust it ran without erroring.
- **Inconsistent trading mechanics between sim functions.** This repo has at least two backtest mechanics: (a) delta-only trading (only buy new entrants / sell dropouts, existing positions untouched) used in the canonical `sim_cross_sectional_momentum`, and (b) full-reallocation-to-equal-weight every rebalance, used in the DCA sims. Returns from the two are **not comparable** even for the "same" strategy/universe/top_n — check which one a script uses before comparing its output to a previously reported number.
- **Currency/unit mixing.** Cross-country or cross-universe combinations must convert every price series to a common currency before summing/allocating cash across them — momentum *scores* are ratios and currency-invariant, but *position sizing and portfolio value* are not.
- **TRAIN/VALID/TEST discipline.** Confirm the split is still chronological and TEST wasn't peeked at while iterating on the idea. Confirm win-rate/return claims report ALL of TRAIN/VALID/TEST/2022-stress, not just the flattering one.
- **Small-sample overreach.** `top_n=3` means any "first rebalance" or "per-quartile" bucket you slice by is tiny (n≈3 per bucket per run) — a single outlier trade can flip a mean. Report median alongside mean, and say so explicitly when n is small.

## Output

For each finding: what's wrong, why it matters (concretely — which downstream number changes and by how much if you can estimate it), and what to change. If nothing survives scrutiny, say so plainly instead of manufacturing a finding.
