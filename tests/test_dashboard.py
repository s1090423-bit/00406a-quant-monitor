import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dashboard import render

def test_dashboard_safe_and_explains_missing_data():
    signal={'price':7.52,'margin':{'maintenance_pct':139.26},'loan_assumption':162000,'blocked_reasons':['NAV_UNAVAILABLE','MARGIN_GUARD'],'action':'NO_NEW_BUY','timestamp_utc':'2026-11-05T03:00:00+00:00'}
    research={'bars':257,'trade_count':0,'shares_added':0,'strategy':{'return_pct':0,'max_drawdown_pct':0},'buy_hold_baseline':{'return_pct':-19.62}}
    page=render(signal,research)
    assert '暫停新增買進' in page and '基金淨值' in page
    assert '139.26%' in page and '7.52' in page
    assert 'width=device-width' in page
    assert '不會自動刷新' in page

def test_dashboard_escapes_untrusted_data():
    signal={'action':'NO_NEW_BUY','blocked_reasons':['<script>alert(1)</script>']}
    page=render(signal,{})
    assert '<script>' not in page
    assert '&lt;script&gt;' in page
