[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/ssj6go/makefun-btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/ssj6go/makefun-btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

# Dip-recovery BTC bot

A long-only cbBTC/USDC trading bot for the make.fun 24-hour BTC race
(`btc-race-24h-20261118-1444`). It speaks `agent-fun/bars-replay/v1` over
stdin/stdout (Python 3.13, standard library only) using the kit's
`vendor/makefun_bars.py` shim.

**Strategy — buy the recovery, not the knife.** The bot stays in cash until
the close falls at least 1.5% below the highest close of the last 120 bars
(a real dip) *and* the fast EMA(5) of closes crosses back above EMA(13)
(the recovery has started). It then buys the full cash balance and exits on
the first of: a 1.0% stop-loss under the fill price, a 1.5% take-profit over
it, or a 1.2% trailing stop under the peak close since entry. It never exits
on the EMA cross back — in a choppy climb that flips long before the move is
over and hands the profit back in fees. A full-size round trip costs about
32 bps in fees, slippage and price impact, so the bot trades rarely and only
for moves several times that cost.

**Dev window (local replay, official fill model): net PnL +$13.22, 2 trades,
max drawdown 0.74%.** Two runs produce byte-identical action logs.

## Files

- `main.py` — the bot (entrypoint; deterministic, no clock, no randomness)
- `vendor/makefun_bars.py` — the kit's protocol shim, byte-identical
