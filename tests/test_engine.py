import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import engine
import pandas as pd

def sample():
    ts=pd.date_range('2026-11-03 01:00',periods=25,freq='30min',tz='UTC')
    return pd.DataFrame({'timestamp':ts,'open':[7.8]*25,'high':[7.9]*25,'low':[7.7]*25,'close':[7.8]*25,'volume':[1000]*25})

def test_call_price():
    assert engine.risk(7.02,162000)['maintenance_pct']==130

def test_stale_blocks():
    d=sample(); out=engine.evaluate(d,now='2026-11-05T00:00:00Z')
    assert out['action']=='NO_NEW_BUY' and 'STALE_PRICE' in out['blocked_reasons']

def test_missing_nav_blocks():
    d=sample(); out=engine.evaluate(d,now=d.timestamp.iloc[-1],market_trend='up')
    assert 'NAV_UNAVAILABLE' in out['blocked_reasons']

def test_margin_blocks():
    d=sample(); out=engine.evaluate(d,nav=7.8,nav_timestamp=d.timestamp.iloc[-1],market_trend='up',now=d.timestamp.iloc[-1])
    assert 'MARGIN_GUARD' in out['blocked_reasons']

def test_backtest_never_exceeds_budget():
    out=engine.backtest(sample())
    assert out['cash_remaining']>=engine.CONFIG['reserve_cash']
    assert out['new_shares']<=30000
