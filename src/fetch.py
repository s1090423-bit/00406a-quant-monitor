"""Best-effort public quote retrieval. Fails closed if provider does not support ticker."""
import os, sys
from pathlib import Path
import pandas as pd
import yfinance as yf
BASE=Path(__file__).resolve().parents[1]
symbol=os.getenv('TICKER','00406A.TW')
raw=yf.download(symbol,period='30d',interval='30m',auto_adjust=False,progress=False,threads=False)
if raw.empty: sys.exit(f'NO_DATA: {symbol} unavailable from Yahoo; do not issue trading signal')
if isinstance(raw.columns,pd.MultiIndex): raw.columns=raw.columns.get_level_values(0)
raw=raw.reset_index().rename(columns={'Datetime':'timestamp','Date':'timestamp','Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
raw['timestamp']=pd.to_datetime(raw['timestamp'],utc=True)
raw[['timestamp','open','high','low','close','volume']].to_csv(BASE/'data'/'prices.csv',index=False)
print('Downloaded',len(raw),'bars; latest',raw.timestamp.iloc[-1]); print('Source: Yahoo Finance via yfinance; verify quote delay and ticker coverage')
