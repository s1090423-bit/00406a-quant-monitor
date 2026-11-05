"""Independent Taiwan market context, guarded for stale or missing data."""
import json
from pathlib import Path
import pandas as pd
import yfinance as yf
BASE=Path(__file__).resolve().parents[1]

def market_trend(index_bars, latest_etf_ts):
    d=index_bars.copy()
    if d.empty or len(d)<25: return None
    d=d.sort_values('timestamp')
    d['timestamp']=pd.to_datetime(d.timestamp,utc=True)
    ts=pd.Timestamp(latest_etf_ts)
    if ts.tzinfo is None: ts=ts.tz_localize('UTC')
    d=d[d.timestamp<=ts]
    if len(d)<25: return None
    if abs((ts-d.timestamp.iloc[-1]).total_seconds())>60*90: return None
    c=pd.to_numeric(d.close,errors='coerce')
    if c.isna().any() or (c<=0).any(): return None
    ma10=c.tail(10).mean(); ma25=c.tail(25).mean()
    last=float(c.iloc[-1])
    return 'up' if last>ma10>ma25 else 'down' if last<ma10<ma25 else 'flat'

def fetch():
    try:
        bars=yf.download('^TWII',period='30d',interval='30m',auto_adjust=False,progress=False,threads=False,timeout=20)
        if bars.empty: raise ValueError('Index data unavailable')
        if isinstance(bars.columns,pd.MultiIndex):bars.columns=bars.columns.get_level_values(0)
        bars=bars.reset_index().rename(columns={'Datetime':'timestamp','Date':'timestamp','Close':'close'})
        bars['timestamp']=pd.to_datetime(bars.timestamp,utc=True)
        output=BASE/'data'/'market.csv'
        output.parent.mkdir(parents=True,exist_ok=True)
        bars[['timestamp','close']].to_csv(output,index=False)
        print('Market bars downloaded:',len(bars))
    except Exception as e:
        print('Market unavailable; fail closed:',type(e).__name__,str(e)[:180])
        (BASE/'data'/'market.csv').unlink(missing_ok=True)

if __name__=='__main__':fetch()
