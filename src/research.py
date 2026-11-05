"""Price-only research backtest; never authorizes a live trade."""
import argparse
import json
import numpy as np
import pandas as pd
from engine import CONFIG, indicators, load_prices

def stats(equity):
    values=np.asarray(equity,dtype=float)
    peak=np.maximum.accumulate(values)
    drawdown=np.min(values/peak-1) if len(values) else 0
    return {"return_pct":round((values[-1]/values[0]-1)*100,2),
            "max_drawdown_pct":round(float(drawdown)*100,2)}

def research(df, initial_cash=None, reserve=None):
    """Next-bar open entries, conservative cash-only sizing, no same-bar fills."""
    initial_cash=float(CONFIG["remaining_cash_assumption"] if initial_cash is None else initial_cash)
    reserve=float(CONFIG["reserve_cash"] if reserve is None else reserve)
    if initial_cash<=reserve or len(df)<45:
        return {"status":"INSUFFICIENT_DATA_OR_CAPITAL"}
    d=indicators(df).copy()
    d["ma20"]=d.close.rolling(20).mean()
    d["ma40"]=d.close.rolling(40).mean()
    d["volatility"]=d.close.pct_change().rolling(20).std()
    cash=initial_cash
    shares=0
    fees=float(CONFIG["buy_fee_rate"])
    equity=[initial_cash]
    trades=[]
    for i in range(40,len(d)-1):
        signal=d.iloc[i]
        execution=d.iloc[i+1]
        price=float(execution.open)
        if not np.isfinite(price) or price<=0:
            raise ValueError("Invalid execution price")
        trend=bool(signal.close>signal.ma20>signal.ma40)
        stable=bool(np.isfinite(signal.volatility) and signal.volatility<0.035)
        zone=any(z["low"]<=signal.close<=z["high"] for z in CONFIG["zones"])
        # One lot at a time, no leverage, limit the overall planned addition.
        if trend and stable and zone and shares<CONFIG["target_additional_shares"]:
            cost=1000*price*(1+fees)
            if cash-cost>=reserve:
                cash-=cost
                shares+=1000
                trades.append({"signal":signal.timestamp.isoformat(),
                               "execution":execution.timestamp.isoformat(),
                               "price":round(price,4),"shares":1000})
        equity.append(cash+shares*float(execution.close))
    # Baseline uses the same deployable cash and reserve, held without leverage.
    first=float(d.iloc[41].open)
    baseline_shares=int((initial_cash-reserve)//(first*1000))*1000
    baseline_cash=initial_cash-baseline_shares*first*(1+fees)
    while baseline_cash<reserve and baseline_shares>0:
        baseline_shares-=1000
        baseline_cash=initial_cash-baseline_shares*first*(1+fees)
    baseline=[initial_cash]+[baseline_cash+baseline_shares*float(x) for x in d.close.iloc[41:]]
    # Equity paths are aligned to bars 40 onward; comparison uses the same endpoint.
    return {"status":"RESEARCH_ONLY_NOT_VALIDATED",
            "bars":len(d),"trade_count":len(trades),"shares_added":shares,
            "cash_remaining":round(cash,2),
            "strategy":stats(equity),
            "buy_hold_baseline":stats(baseline),
            "trades":trades,
            "limitations":["Price-only research; no NAV, dividends, taxes, slippage or broker margin.",
                           "Parameters are illustrative, not walk-forward optimized.",
                           "No live trades permitted from this result."]}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--prices",required=True)
    args=ap.parse_args()
    print(json.dumps(research(load_prices(args.prices)),ensure_ascii=False,indent=2))
