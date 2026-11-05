import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import pandas as pd
from research import research

def prices(n=80):
    t=pd.date_range("2026-01-01",periods=n,freq="30min",tz="UTC")
    return pd.DataFrame({"timestamp":t,"open":[7.5]*n,"high":[7.6]*n,
                         "low":[7.4]*n,"close":[7.5]*n,"volume":[1000]*n})

def test_research_respects_reserve_and_position_limit():
    r=research(prices())
    assert r["status"]=="RESEARCH_ONLY_NOT_VALIDATED"
    assert r["cash_remaining"]>=30000
    assert r["shares_added"]<=30000

def test_research_requires_history():
    assert research(prices(25))["status"]=="INSUFFICIENT_DATA_OR_CAPITAL"

def test_research_flat_market_does_not_buy():
    r=research(prices())
    assert r["trade_count"]==0
    assert r["strategy"]["return_pct"]==0
