import argparse, json, math, os
from pathlib import Path
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
CONFIG=json.loads((BASE/'config.json').read_text(encoding='utf-8'))

def load_prices(path):
    df=pd.read_csv(path)
    needed={'timestamp','open','high','low','close','volume'}
    if not needed.issubset(df.columns): raise ValueError('Missing OHLCV fields')
    df['timestamp']=pd.to_datetime(df.timestamp,utc=True,errors='raise')
    df=df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
    for col in ['open','high','low','close','volume']: df[col]=pd.to_numeric(df[col],errors='raise')
    if df.empty or (df[['open','high','low','close']]<=0).any().any() or (df.volume<0).any(): raise ValueError('Invalid prices')
    return df

def indicators(df):
    d=df.copy()
    c=d.close
    d['ma5']=c.rolling(5).mean(); d['ma10']=c.rolling(10).mean()
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    d['rsi']=100-100/(1+gain/loss.replace(0,float('nan')))
    d['vol5']=d.volume.rolling(5).mean()
    return d

def risk(price,loan,shares=30000):
    return {'maintenance_pct':round(price*shares/loan*100,2) if loan>0 else None,'call_reference_price':round(1.3*loan/shares,3) if loan>0 else 0}

def evaluate(df, nav=None, nav_timestamp=None, market_trend=None, loan=None, cash=None, acquired=0, now=None):
    cfg=CONFIG; loan=cfg['original_loan'] if loan is None else loan
    cash=cfg['remaining_cash_assumption'] if cash is None else cash
    d=indicators(df); last=d.iloc[-1]; price=float(last.close)
    ts=last.timestamp; now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if now.tzinfo is None: now=now.tz_localize('UTC')
    age=(now-ts).total_seconds()/60
    r=risk(price,loan)
    reasons=[]; score=None; premium=None
    if len(d)<20: reasons.append('INSUFFICIENT_HISTORY')
    if age<0 or age>cfg['max_quote_age_minutes']: reasons.append('STALE_PRICE')
    if nav is None or nav_timestamp is None: reasons.append('NAV_UNAVAILABLE')
    elif not math.isfinite(nav) or nav<=0: reasons.append('INVALID_NAV')
    else:
        nt=pd.Timestamp(nav_timestamp)
        if nt.tzinfo is None: nt=nt.tz_localize('Asia/Taipei')
        if abs((ts-nt).total_seconds())/60>cfg['max_nav_age_minutes']: reasons.append('STALE_NAV')
        else: premium=(price/nav-1)*100
    if market_trend is None: reasons.append('MARKET_UNAVAILABLE')
    if r['maintenance_pct'] is not None and r['maintenance_pct']<cfg['minimum_maintenance_pct']: reasons.append('MARGIN_GUARD')
    if r['maintenance_pct'] is not None and r['maintenance_pct']<130: reasons.append('MARGIN_CALL_REFERENCE')
    if cash<cfg['reserve_cash']: reasons.append('RESERVE_GUARD')
    if acquired>=cfg['target_additional_shares']: reasons.append('POSITION_LIMIT')
    if not reasons:
        # Explicit, inspectable prototype weights; not calibrated to historical returns.
        trend=25 if price>last.ma5>last.ma10 else 12 if price>last.ma5 else 0
        volume=20 if price>=float(d.iloc[-2].close) and last.volume>=last.vol5 else 10 if price>=float(d.iloc[-2].close) else 0
        navscore=20 if premium<=0 else 10 if premium<=0.5 else 0
        marketscore=20 if market_trend=='up' else 10 if market_trend=='flat' else 0
        relative=15 if float(last.rsi)>=45 and float(last.rsi)<=65 else 7 if float(last.rsi)>=35 else 0
        score=trend+volume+navscore+marketscore+relative
    action='NO_NEW_BUY'
    if not reasons and score>=70:
        zone=next((z for z in cfg['zones'] if z['low']<=price<=z['high']),None)
        affordable=max(0,int((cash-cfg['reserve_cash'])//(price*1000*(1+cfg['buy_fee_rate']))))
        lots=min(5 if score>=85 else 2,affordable,(cfg['target_additional_shares']-acquired)//1000)
        if zone and lots>0: action=f'REVIEW_BUY_{lots}_LOTS'
        else: action='WAIT_PRICE_ZONE_OR_CAPACITY'
    return {'timestamp_utc':ts.isoformat(),'quote_age_minutes':round(age,1),'price':price,'nav':nav,'premium_pct':None if premium is None else round(premium,3),'score':score,'action':action,'blocked_reasons':reasons,'margin':r,'cash_assumption':cash,'loan_assumption':loan,'additional_shares':acquired,'note':'Advisory only; no broker orders. NAV must be point-in-time and timestamp-matched.'}

def backtest(df):
    # Price-only reference strategy with next-bar execution, not a validated total-return backtest.
    d=indicators(df)
    cash=CONFIG['remaining_cash_assumption']; reserve=CONFIG['reserve_cash']; added=0; orders=[]
    for i in range(20,len(d)-1):
        row=d.iloc[i]; following=d.iloc[i+1]
        # Daily-only conservative proxy, explicitly NOT the live score strategy.
        signal=bool(row.close>row.ma5>row.ma10 and 40<=row.rsi<=65)
        if not signal: continue
        zone=next((z for z in CONFIG['zones'] if z['low']<=row.close<=z['high']),None)
        if zone is None: continue
        lots=min(1,int((cash-reserve)//(following.open*1000)),(CONFIG['target_additional_shares']-added)//1000)
        if lots<=0: continue
        cost=lots*1000*following.open*(1+CONFIG['buy_fee_rate'])
        if cash-cost<reserve: continue
        cash-=cost; added+=lots*1000
        orders.append({'signal_time':row.timestamp.isoformat(),'execution_time':following.timestamp.isoformat(),'execution_price':float(following.open),'shares':lots*1000,'cost':round(cost,2)})
    final=float(d.iloc[-1].close)
    total_value=cash+added*final
    return {'status':'PROXY_ONLY_NOT_VALIDATED','bars':len(d),'trades':orders,'new_shares':added,'cash_remaining':round(cash,2),'incremental_portfolio_value':round(total_value,2),'incremental_pnl':round(total_value-CONFIG['remaining_cash_assumption'],2),'limitations':['Does not model margin changes, dividend cashflows, NAV premium, market score, taxes, sell orders, or intrabar stop fills.','Historical OHLCV may be adjusted; ensure point-in-time adjusted dividends before comparing total returns.','Next-bar execution avoids same-bar lookahead; fees approximated.']}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['signal','backtest'],required=True); ap.add_argument('--prices',required=True); ap.add_argument('--nav',type=float); ap.add_argument('--nav-timestamp'); ap.add_argument('--market-trend',choices=['up','flat','down']); ap.add_argument('--loan',type=float); ap.add_argument('--cash',type=float); ap.add_argument('--acquired',type=int,default=0); ap.add_argument('--now'); args=ap.parse_args()
    d=load_prices(args.prices)
    result=backtest(d) if args.mode=='backtest' else evaluate(d,args.nav,args.nav_timestamp,args.market_trend,args.loan,args.cash,args.acquired,args.now)
    print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
if __name__=='__main__':main()
