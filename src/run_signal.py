"""Evaluate verified ETF bars and independent index context; NAV remains unavailable."""
import json
from pathlib import Path
import pandas as pd
from engine import load_prices,evaluate
from market import market_trend

BASE=Path(__file__).resolve().parents[1]
prices=load_prices(BASE/'data'/'prices.csv')
trend=None
index_file=BASE/'data'/'market.csv'
if index_file.exists():
    try:
        trend=market_trend(pd.read_csv(index_file),prices.timestamp.iloc[-1])
    except (ValueError,KeyError,TypeError):
        trend=None
out=evaluate(prices,market_trend=trend)
out['market_trend']=trend
out['market_source']='Yahoo Finance ^TWII, timestamp-checked' if trend else 'Unavailable or stale'
print(json.dumps(out,ensure_ascii=False,indent=2))
