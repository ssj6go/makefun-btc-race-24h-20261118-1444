"""Dip-recovery BTC trading bot for make.fun btc-race-24h-20261118-1444.

Strategy: buy the recovery after a sharp dip, ride it with a take-profit and a
trailing stop, and otherwise stay in cash. Long only, one position, full size.

Entry (flat): the close is at least 1.5% below the highest close of the last
120 bars (a real dip, not noise) AND the fast EMA(5) of closes is back above
the slow EMA(13) (the recovery has started, so we buy the turn, not the knife).

Exit (holding): the first of
  - stop-loss: close 1.0% under the fill price,
  - take-profit: close 1.5% over the fill price,
  - trailing stop: close 1.2% under the highest close since entry.
No exit on the EMA cross back: in a choppy climb the fast cross flips long
before the move is over and hands the profit back in fees.

Costs shape everything: a full-size round trip pays about 32 bps in fees,
slippage and price impact, so the bot trades rarely (2 fills on the dev
window) and only for moves several times that cost.

Deterministic: every decision is a pure function of the bars seen so far
(float64 EMAs, integer prices). No clock, no environment, no randomness.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
LOOKBACK = 120          # bars for the dip reference high
DROP = 0.015            # entry: close this far under the 120-bar high
FAST_SPAN = 5           # recovery confirmation: EMA(5) above EMA(13)
SLOW_SPAN = 13
STOP = 0.010            # exit: 1.0% under the fill price
TAKE_PROFIT = 0.015     # exit: 1.5% over the fill price
TRAIL = 0.012           # exit: 1.2% under the peak close since entry
MAX_SLIPPAGE_BPS = 100  # 1% past the close the order was decided on


class Ema:
    """An EMA seeded by the mean of its first span of closes, then alpha-weighted."""

    def __init__(self, span):
        self.span = span
        self.warm = []
        self.value = None

    def step(self, close):
        if self.value is not None:
            self.value += (2 / (self.span + 1)) * (close - self.value)
            return
        self.warm.append(close)
        if len(self.warm) == self.span:
            self.value = sum(self.warm) / self.span


# Closes seen so far, oldest first (ints at price_scale 5).
history = []
fast = Ema(FAST_SPAN)
slow = Ema(SLOW_SPAN)
# The fill price of the open position and the highest close since it (ints).
entry_price = None
peak_since_entry = None


def on_batch(state, batch):
    global entry_price, peak_since_entry
    # Fills of the orders decided on the previous batch: record the entry price
    # of a buy that filled, clear it on a sell that filled.
    for fill in batch["fills"]:
        if fill["symbol"] != SYMBOL or fill["status"] != "filled":
            continue
        if fill["side"] == "buy":
            entry_price = int(fill["price"])
            peak_since_entry = entry_price
        else:
            entry_price = None
            peak_since_entry = None

    close = None
    for bar in batch["bars"]:
        if bar["symbol"] != SYMBOL:
            continue
        close = int(bar["c"])
        if entry_price is not None and close > peak_since_entry:
            peak_since_entry = close
        fast.step(close)
        slow.step(close)
        history.append(close)
    if close is None or state.warming_up:
        return []

    held = state.positions.get(SYMBOL)
    if held is not None:
        if entry_price is None:
            # Held without a recorded fill price: the process restarted
            # mid-race and lost its memory while the position survived.
            # Rebuild the entry from the position's cost basis so the
            # stop-loss / take-profit / trailing-stop exits below still run
            # instead of holding forever. cost is in quote units (scale 6,
            # fees included), qty at scale 8, prices at scale 5, so
            # price = cost * 10**7 // qty.
            if held.qty > 0:
                entry_price = held.cost * 10**7 // held.qty
                peak_since_entry = max(entry_price, close)
            else:
                return []
        if close <= entry_price * (1 - STOP):
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if close >= entry_price * (1 + TAKE_PROFIT):
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if peak_since_entry is not None and close <= peak_since_entry * (1 - TRAIL):
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    # Flat: a dip plus a confirmed recovery.
    if len(history) < LOOKBACK + 1:
        return []
    high = max(history[-LOOKBACK - 1:-1])
    if fast.value is None or slow.value is None:
        return []
    if close <= high * (1 - DROP) and fast.value > slow.value:
        if state.cash >= 1_000_000:  # at least the 1 USDC minimum notional
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
