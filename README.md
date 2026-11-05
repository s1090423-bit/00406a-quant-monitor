# 00406A Cloud Quant V1 — advisory-only prototype

**Status:** source code + automated tests; NOT a validated trading strategy, NOT deployed, NOT live trading. No brokerage connectivity.

## Run locally

```bash
pip install -r requirements.txt
pytest -q
python src/fetch.py
python src/engine.py --mode backtest --prices data/prices.csv
python src/engine.py --mode signal --prices data/prices.csv
```

Signal defaults to **NO_NEW_BUY** unless a recent, time-aligned NAV and independent market-trend input are supplied. Example (only with genuine verified inputs):

```bash
python src/engine.py --mode signal --prices data/prices.csv --nav 7.80 --nav-timestamp '2026-11-05T09:30:00+08:00' --market-trend flat --loan 162000 --cash 192000
```

The example NAV is illustrative, **not** a market observation. Do not use as an actual trade recommendation.

## GitHub Actions

Create a private repository, upload these files, enable Actions, and manually trigger `00406A quant monitoring` once. Cron is configured at Taiwan 09:00/09:30 through 13:00 (9 runs) on weekdays, subject to GitHub scheduling delays. Holidays are NOT prefiltered; no trades or alerts are generated on stale quotes. Check Actions artifacts for JSON output. **No push notification or messaging integration is configured.** The workflow may fail if Yahoo does not support this ticker.

## Data requirements for real validation

1. Confirm the exact exchange code/ticker and reliable 30-minute OHLCV history from a licensed provider.
2. Supply point-in-time ETF indicative NAV (iNAV) with timestamp and methodology; daily end-of-day NAV is **not** suitable for same-session 30-minute premium signals.
3. Supply timestamped TAIEX bars and compute market trend, relative strength and market stress, not a manual guess.
4. Use dated dividends, splits, fee and tax schedules, broker margin agreement, and historical financing rates.
5. Add broker execution simulation, next-bar fill/slippage, and out-of-sample validation. Current `backtest` is only a **daily/30m price-only proxy**, not the 100-point live strategy.
6. Set actual available cash, repayments, purchased lots, collateral recognition, and account-wide margin in a secure position state store. The JSON config is a starting assumption, not an account ledger.

## Guardrails and known limitations

- Initial 300,000 TWD budget **includes** 108,000 TWD original equity; therefore assumed incremental cash = 192,000 TWD. This must be verified before use.
- Maintenance ratio is modeled as `original 30,000 shares * price / remaining loan`, excluding other collateral, interest, distributions and broker rules. 130% is a **reference**, 150% is an internal no-new-buy guard.
- New cash shares do not automatically count as collateral for the original loan.
- Position sizing is capped by cash less 30,000 TWD reserve and 30,000 additional shares.
- Scoring weights are uncalibrated heuristic rules. Insufficient data, stale data, absent NAV, absent market trend, weak margin or insufficient reserve blocks buying.
- GitHub Actions is a best-effort scheduler, **not a guaranteed 30-minute execution service**. Use a paid managed scheduler if hard timing is required.
- No historical performance, win rate or expected return is claimed.

## 中文儀表板（Mac 本機）

在 Mac 啟動 `python3 src/local_dashboard.py`，瀏覽器開啟 `http://127.0.0.1:18765`。服務只監聽本機，利用已授權的 GitHub CLI 每5分鐘檢查最新一次成功的 GitHub Actions 報告。瀏覽器每5分鐘重新整理。電腦關機、休眠或服務停止時不會更新；GitHub排程也可能延遲。這不是公開網站，不能直接在外網手機連入。

目前沒有可驗證的時間對齊 iNAV、完整股息調整與券商實際擔保品資料；策略仍是研究用途，不能宣稱已通過樣本外驗證或可自動交易。歷史價格型研究有0筆成交時，0%報酬不是策略勝率或優勢證明。
