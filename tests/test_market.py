import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from market import market_trend

def test_market_trend_up_and_stale():
    d=pd.DataFrame({'timestamp':pd.date_range('2026-11-05 00:00',periods=30,freq='30min',tz='UTC'),
                    'close':[100+i for i in range(30)]})
    assert market_trend(d,d.timestamp.iloc[-1])=='up'
    assert market_trend(d,d.timestamp.iloc[-1]+pd.Timedelta(hours=3)) is None
