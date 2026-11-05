"""Create a self-contained, mobile-friendly HTML report from verified run JSON."""
import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

REASONS = {
    "NAV_UNAVAILABLE": "缺少基金淨值：無法確認折溢價",
    "MARKET_UNAVAILABLE": "缺少大盤資料：無法完成趨勢評分",
    "MARGIN_GUARD": "融資維持率低於策略設定的 150% 防護線",
    "MARGIN_CALL_REFERENCE": "估算維持率低於 130% 參考線，請立即向券商確認",
    "STALE_PRICE": "行情時間過舊，不可當作即時報價",
    "INVALID_NAV": "基金淨值資料不合理",
    "STALE_NAV": "基金淨值與價格時間不一致",
    "INSUFFICIENT_HISTORY": "歷史資料不足",
    "RESERVE_GUARD": "可用現金低於預留額度",
    "POSITION_LIMIT": "已達計畫加碼上限",
}
def num(value, decimals=2):
    return "尚無資料" if value is None else f"{float(value):,.{decimals}f}"
def esc(value):
    return html.escape(str(value),quote=True)
def render(signal, research, prices=None):
    chart="<p class=muted>價格歷史圖表資料尚未取得。</p>"
    if prices is not None and len(prices)>2:
        rows=prices.tail(100)
        vals=[float(v) for v in rows.close]
        low=min(vals); high=max(vals); spread=max(high-low,0.01)
        pts=" ".join(f"{i*760/(len(vals)-1):.1f},{190-(v-low)/spread*160:.1f}" for i,v in enumerate(vals))
        chart=f"<svg viewBox='0 0 760 220' role='img' aria-label='最近100根K棒收盤價格走勢' style='width:100%;height:auto'><line x1='0' y1='200' x2='760' y2='200' stroke='#dce5f0'/><polyline fill='none' stroke='#1355a2' stroke-width='3' points='{pts}'/></svg><p class='muted'>圖表範圍：{low:.2f}–{high:.2f} 元；最近 {len(vals)} 根30分鐘K棒。非即時報價。</p>"
    price=signal.get("price")
    margin=signal.get("margin",{}).get("maintenance_pct")
    loan=signal.get("loan_assumption")
    shares=30000
    threshold150=1.5*loan/shares if loan else None
    threshold130=1.3*loan/shares if loan else None
    blocked=signal.get("blocked_reasons",[])
    decision="暫停新增買進" if signal.get("action")=="NO_NEW_BUY" else "僅供人工審核"
    stamp=signal.get("timestamp_utc","")
    try:
        from zoneinfo import ZoneInfo
        local=datetime.fromisoformat(stamp).astimezone(ZoneInfo("Asia/Taipei")).strftime("%Y/%m/%d %H:%M")
    except (ValueError,TypeError):
        local=stamp
    reasons="".join(f"<li>{esc(REASONS.get(r,r))}</li>" for r in blocked) or "<li>未觸發資料或風控封鎖，仍須人工判斷。</li>"
    zones=[(7.75,7.85),(7.40,7.55),(7.00,7.20)]
    zone_rows="".join(f"<tr><td>{lo:.2f}–{hi:.2f} 元</td><td>{'已進入觀察區' if price is not None and lo<=price<=hi else '未進入'}</td></tr>" for lo,hi in zones)
    no_trades=research.get("trade_count")==0
    rs=research.get("strategy",{})
    base=research.get("buy_hold_baseline",{})
    strategy_return="未建立部位" if no_trades else f"{num(rs.get('return_pct'))}%"
    strategy_drawdown="無交易，無法評估" if no_trades else f"{num(rs.get('max_drawdown_pct'))}%"
    research_status="本期無交易：策略績效不可與持有基準直接比較" if no_trades else "研究性回測，未經樣本外驗證"
    freshness="報價延遲或不完整" if "STALE_PRICE" in blocked else "非即時行情，請核對時間"
    disclaimer="研究基準只使用剩餘現金、採無槓桿買入持有；不含原有融資部位，亦未計股息、稅金與滑價。兩種策略的市場曝險不同，不能直接推論優劣。"
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>00406A｜風險監控中心</title>
<style>
:root{{--bg:#f4f7fb;--ink:#17253a;--muted:#62748b;--card:#fff;--border:#dce5f0;--red:#b42336;--blue:#1355a2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",sans-serif;color:var(--ink);line-height:1.55}}
main{{max-width:1060px;margin:auto;padding:22px 16px 56px}}header{{display:flex;justify-content:space-between;gap:12px;align-items:start;flex-wrap:wrap;margin-bottom:20px}}
h1{{font-size:clamp(24px,5vw,34px);margin:0}}h2{{font-size:19px;margin:0 0 12px}}p{{margin:6px 0}}small,.muted{{color:var(--muted)}}.stamp{{font-size:13px;color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:19px;margin-bottom:14px;box-shadow:0 2px 9px #1b355008}}
.kpi{{font-size:clamp(25px,5vw,34px);font-weight:750;letter-spacing:-.5px;margin:4px 0}}.danger{{color:var(--red)}}.pill{{display:inline-block;border-radius:999px;background:#fde8e9;color:#9c1c2a;padding:5px 12px;font-weight:700;font-size:14px}}
.summary{{border-left:5px solid var(--red);padding-left:14px}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:11px 4px;text-align:left;border-bottom:1px solid var(--border)}}th{{color:var(--muted);font-size:13px}}ul{{padding-left:22px;margin:8px 0}}li{{margin:7px 0}}
.track{{height:12px;border-radius:999px;background:#e7eef7;overflow:hidden;margin:8px 0}}.fill{{height:100%;background:#e28b40;border-radius:999px}}.footer{{font-size:13px;color:var(--muted)}}
details summary{{cursor:pointer;color:var(--blue);font-weight:650}}pre{{white-space:pre-wrap;word-break:break-word;background:#eef3f9;padding:12px;border-radius:10px;font-size:12px}}
@media(max-width:700px){{.grid,.split{{grid-template-columns:1fr}}main{{padding:16px 12px 40px}}.card{{padding:16px}}}}
/* Dashboard visual refresh */
:root{{--bg:#eef2f7;--ink:#17243a;--muted:#65748a;--border:#dfe6ef;--red:#ae2942;--blue:#245db6}}
body{{background:linear-gradient(180deg,#e8eef7 0,#f5f7fa 330px);font-size:15px}}
main{{max-width:1160px;padding:30px 24px 65px}}
header{{padding:24px 26px;border-radius:20px;background:#122844;color:white;box-shadow:0 10px 30px #1429441c}}
header h1{{font-size:clamp(26px,3.3vw,38px);letter-spacing:.2px}}
header .muted{{color:#c1d2e5}}
h2{{font-size:18px;letter-spacing:.1px}}
.card{{border:1px solid #e3e9f0;border-radius:18px;box-shadow:0 4px 18px #19344a09;padding:23px}}
.summary{{background:#fffaf9;border-left:5px solid #c64657}}
.kpi{{font-size:clamp(26px,3.3vw,37px)}}
.pill{{background:#fbe6ea;color:#92213c;white-space:nowrap}}
.navbar{{display:flex;gap:9px;flex-wrap:wrap;margin:18px 0 20px}}
.navbar a{{text-decoration:none;color:#234b82;background:#fff;border:1px solid #dce5f0;padding:9px 14px;border-radius:12px;font-size:14px;font-weight:650}}
.navbar a:hover{{background:#e6eefb}}
.sectionlabel{{font-size:12px;color:#71839a;font-weight:750;letter-spacing:1px;text-transform:uppercase;margin:23px 0 10px}}
.alert-note{{border-radius:12px;background:#fff0df;padding:12px 14px;color:#7d4a14;font-size:14px;margin-top:14px}}
.source-note{{display:inline-flex;gap:6px;align-items:center;border:1px solid #dfe8f1;border-radius:8px;padding:4px 9px;background:#f6f9fd;color:#596d85;font-size:12px}}
footer{{margin-top:16px}}
html{{scroll-behavior:smooth}}
@media(max-width:700px){{main{{padding:12px 11px 40px}}header{{padding:19px 16px}}.card{{padding:17px}}.navbar{{gap:6px}}.navbar a{{font-size:12px;padding:8px 10px}}}}
</style></head><body><main>
<header><div><h1>00406A 量化監控</h1><p class="muted">繁體中文風險與策略儀表板 · 僅供參考，不自動下單</p></div><span class="pill">策略訊號：{esc(decision)}</span></header>
<nav class="navbar" aria-label="快速導覽"><a href="#decision">操作結論</a><a href="#risk">融資風險</a><a href="#trend">價格走勢</a><a href="#zones">觀察區</a><a href="#research">策略回測</a><a href="#data">資料狀態</a></nav>
<div class="sectionlabel">01 / 當前決策</div>
<div id="decision" class="card summary"><h2>目前最重要的事</h2><p>目前資料顯示 <b>{esc(decision)}</b>。先確認券商的實際融資維持率、基金淨值與大盤資料，勿僅因價格進入觀察區就加碼。</p><p class="stamp">行情K棒時間：{esc(local)}（台灣時間） · {esc(freshness)} · 資料來源：Yahoo Finance</p></div>
<div class="sectionlabel">02 / 市場與持倉快覽</div>
<div class="grid">
<section class="card"><small>最近一根K棒收盤價</small><div class="kpi">{num(price)} <small>元</small></div><small>非即時報價</small></section>
<section class="card"><small>估算融資維持率</small><div class="kpi danger">{num(margin)}%</div><small>以30,000股、借款{num(loan,0)}元估算，非券商正式數字</small></section>
<section class="card"><small>量化評分</small><div class="kpi">{num(signal.get("score"),0)}</div><small>資料不足時不計分，不是0分</small></section>
</div>
<div class="sectionlabel">03 / 市場趨勢</div>
<section id="trend" class="card"><h2>價格走勢</h2>{chart}</section>
<div class="split">
<section class="card"><h2>為什麼暫停買進？</h2><ul>{reasons}</ul></section>
<section id="risk" class="card"><h2>融資安全距離</h2><p>策略防護線 150% 對應股價約 <b>{num(threshold150)} 元</b></p><p>130% 參考線對應股價約 <b>{num(threshold130)} 元</b></p>
<div class="track"><div class="fill" style="width:{min(100,max(0,(margin or 0)/200*100)):.1f}%"></div></div>
<p class="muted">本估算未納入其他擔保品、融資餘額變動與券商規則。130% 並非所有帳戶的實際追繳條件。</p></section>
</div>
<div class="split">
<section id="zones" class="card"><h2>價格觀察區</h2><table><thead><tr><th>觀察價格</th><th>目前狀態</th></tr></thead><tbody>{zone_rows}</tbody></table><p class="muted">進入觀察區 ≠ 建議買進。</p></section>
<section class="card"><h2>可用資金假設</h2><p>剩餘現金假設：<b>{num(signal.get("cash_assumption"),0)} 元</b></p><p>計畫預留現金：<b>30,000 元</b></p><p>新增部位：<b>{num(signal.get("additional_shares"),0)} 股</b></p><p class="muted">以上是策略設定，不是銀行或券商即時餘額。</p></section>
</div>
<div class="sectionlabel">04 / 策略研究</div>
<section id="research" class="card"><h2>歷史研究比較</h2><div class="alert-note">{esc(research_status)}</div><div class="grid">
<div><small>研究策略報酬</small><div class="kpi">{esc(strategy_return)}</div></div>
<div><small>買入持有基準報酬</small><div class="kpi">{num(base.get("return_pct"))}%</div></div>
<div><small>策略最大回撤</small><div class="kpi">{esc(strategy_drawdown)}</div></div>
</div><p>研究樣本：{esc(research.get("bars","—"))} 根30分鐘K棒；策略成交：{esc(research.get("trade_count","—"))} 次；新增股數：{esc(research.get("shares_added","—"))} 股。</p>
<p class="muted">{esc(disclaimer)}</p></section>
<div class="sectionlabel">05 / 資料與可信度</div>
<section id="data" class="card"><h2>資料完整性</h2><table><tbody><tr><td>市場價格K棒</td><td>已取得，需檢查延遲</td></tr><tr><td>基金淨值及折溢價</td><td>尚未整合</td></tr><tr><td>大盤趨勢</td><td>{esc(signal.get("market_trend") or "資料缺失／時間過舊")}</td></tr><tr><td>券商實際維持率</td><td>尚未連接</td></tr><tr><td>樣本外回測</td><td>尚未驗證</td></tr></tbody></table></section>
<section class="card"><details><summary>查看原始量化資料（進階）</summary><h2>訊號 JSON</h2><pre>{esc(json.dumps(signal,ensure_ascii=False,indent=2))}</pre><h2>研究 JSON</h2><pre>{esc(json.dumps(research,ensure_ascii=False,indent=2))}</pre></details></section>
<p class="footer">本HTML為單次報告快照，不會自動刷新；使用本機監控服務時，瀏覽器每5分鐘檢查最新成功報告。非交易所即時報價。投資決策請以券商與官方資料為準。</p>
</main></body></html>"""
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--signal",required=True)
    ap.add_argument("--research",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--prices")
    args=ap.parse_args()
    signal=json.loads(Path(args.signal).read_text(encoding="utf-8"))
    research=json.loads(Path(args.research).read_text(encoding="utf-8"))
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    prices=None
    if args.prices:
        from engine import load_prices
        prices=load_prices(args.prices)
    path.write_text(render(signal,research,prices),encoding="utf-8")
    print("HTML dashboard created:",path)
if __name__=="__main__":
    main()
