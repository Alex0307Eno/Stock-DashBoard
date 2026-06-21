from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from datetime import timedelta
from statistics import stdev
from typing import Any

from .analytics import format_large, long_short_label, recommendation, technical_indicators
from .data_sources import (
    finmind,
    bls_series,
    fred_series,
    get_twse_market_value,
    quote_from_exchange_rate,
    quote_from_finmind_stock,
    quote_from_nasdaq,
    quote_from_nasdaq_etf,
    quote_from_yahoo,
    ohlc_from_finmind,
    safe_call,
    series_from_finmind_stock,
    series_from_yahoo,
    today_tw,
    treasury_yield_curve,
    taiwan_stat_indicators,
    twse_index_quote,
    twse_index_series,
    twse_institutional_rows,
    twse_institutional_top5,
    twse_market_margin_summary,
    twse_margin_rows,
    twse_security_quote,
    twse_security_series,
    twse_valuation_metrics,
    twse_index_from_finmind,
    twse_index_series_from_finmind,
)


WATCHLIST = [
    ("^TWII", "台股加權", "台灣大盤"),
    ("2330.TW", "台積電", "半導體 / AI 供應鏈"),
    ("2317.TW", "鴻海", "AI 伺服器 / 電動車"),
    ("2454.TW", "聯發科", "IC 設計"),
    ("0050.TW", "元大台灣50", "台灣大型 ETF"),
    ("00878.TW", "國泰永續高股息", "高股息 ETF"),
]

US_HOT = [
    ("NVDA", "NVIDIA", "AI GPU / 資料中心"),
    ("AAPL", "Apple", "消費電子 / AI 裝置"),
    ("MSFT", "Microsoft", "雲端 / AI 軟體"),
    ("TSLA", "Tesla", "電動車 / 機器人"),
    ("AMD", "AMD", "AI 加速器 / CPU"),
    ("PLTR", "Palantir", "AI 軟體 / 國防資料"),
    ("AMZN", "Amazon", "雲端 / 電商"),
    ("META", "Meta", "社群 / AI 廣告"),
    ("GOOGL", "Alphabet", "搜尋 / AI 雲端"),
    ("AVGO", "Broadcom", "AI ASIC / 網通晶片"),
    ("SMCI", "Supermicro", "AI 伺服器"),
    ("MSTR", "MicroStrategy", "比特幣概念"),
    ("COIN", "Coinbase", "加密貨幣交易"),
    ("RIVN", "Rivian", "電動車"),
    ("SOFI", "SoFi", "金融科技"),
    ("INTC", "Intel", "半導體 / CPU"),
    ("MU", "Micron", "記憶體 / AI"),
    ("BAC", "Bank of America", "大型銀行"),
    ("F", "Ford", "汽車"),
    ("PFE", "Pfizer", "製藥"),
]

CURRENCIES = [
    ("USDTWD=X", "美元 / 台幣"),
    ("USDJPY=X", "美元 / 日圓"),
    ("USDCNH=X", "美元 / 離岸人民幣"),
    ("EURUSD=X", "歐元 / 美元"),
    ("GBPUSD=X", "英鎊 / 美元"),
    ("AUDUSD=X", "澳幣 / 美元"),
    ("NZDUSD=X", "紐幣 / 美元"),
    ("USDKRW=X", "美元 / 韓元"),
    ("USDSGD=X", "美元 / 新加坡幣"),
    ("USDHKD=X", "美元 / 港幣"),
    ("USDTHB=X", "美元 / 泰銖"),
    ("USDCHF=X", "美元 / 瑞郎"),
]

GLOBAL_MARKETS = [
    ("^GSPC", "S&P 500", "美國大型股"),
    ("^NDX", "NASDAQ 100", "美國科技大型股"),
    ("^DJI", "道瓊指數", "美國藍籌股"),
    ("^SOX", "費城半導體", "半導體景氣"),
    ("^RUT", "羅素 2000", "美國小型股"),
    ("^N225", "日經 225", "日本大盤"),
    ("^HSI", "恆生指數", "香港大盤"),
    ("^GDAXI", "德國 DAX", "歐洲景氣"),
    ("^FTSE", "英國 FTSE 100", "英國大型股"),
]

BOND_ETFS = [
    ("SHY", "短天期美債", "1-3 年美債 / 低利率敏感"),
    ("IEF", "中天期美債", "7-10 年美債 / 平衡利率風險"),
    ("TLT", "長天期美債", "20 年以上美債 / 高利率敏感"),
    ("BND", "總體債券", "美國綜合債市 / 核心配置"),
    ("LQD", "投資級公司債", "信用利差 / 投資級企業"),
    ("HYG", "高收益公司債", "信用風險 / 景氣敏感"),
]

TAIWAN_BOND_ETFS = [
    ("00679B", "元大美債20年", "長天期美債 / 台股掛牌"),
    ("00687B", "國泰20年美債", "長天期美債 / 台股掛牌"),
    ("00696B", "富邦美債20年", "長天期美債 / 台股掛牌"),
    ("00720B", "元大投資級公司債", "投資級公司債 / 台股掛牌"),
    ("00725B", "國泰投資級公司債", "投資級公司債 / 台股掛牌"),
    ("00751B", "元大AAA至A公司債", "高評級公司債 / 台股掛牌"),
]

HOT_ETFS = [
    ("0050", "元大台灣50", "大型權值 / 市值型"),
    ("006208", "富邦台50", "大型權值 / 低費用"),
    ("0056", "元大高股息", "高股息 / 季配息"),
    ("00878", "國泰永續高股息", "ESG 高股息 / 季配息"),
    ("00919", "群益台灣精選高息", "高息 ETF / 季配息"),
    ("00713", "元大台灣高息低波", "高息低波 / 季配息"),
    ("00929", "復華台灣科技優息", "科技高息 / 月配息"),
    ("00940", "元大台灣價值高息", "高息題材 / 月配息"),
]


def market_overview() -> dict[str, Any]:
    quote = safe_call(lambda: twse_index_quote(), safe_call(twse_index_from_finmind, fallback_quote("^TWII", "台股加權", "台灣大盤")))
    trade = safe_call(get_twse_market_value, {"date": "-", "trade_value": "-", "volume": "-", "transactions": "-", "source": "fallback"})
    series = safe_call(lambda: twse_index_series(30), safe_call(lambda: twse_index_series_from_finmind(30), []))
    signal = recommendation(quote["change_pct"], quote["volume"], series)
    return {"quote": quote, "trade": trade, "series": series, "signal": signal}


def quotes(stock_id: str = "") -> list[dict[str, Any]]:
    if not stock_id:
        return []
    fallback = safe_call(lambda sid=stock_id: quote_from_finmind_stock(sid, sid, "搜尋個股"), fallback_quote(f"{stock_id}.TW", stock_id, "搜尋個股"))
    return [safe_call(lambda sid=stock_id: quote_with_valuation(sid, "", "搜尋個股"), fallback)]


def quote_with_valuation(stock_id: str, name: str, topic: str) -> dict[str, Any]:
    quote = twse_security_quote(stock_id, name, topic)
    metrics = safe_call(lambda: twse_valuation_metrics(stock_id), {})
    return {**quote, **metrics}


def financial_report(stock_id: str = "") -> dict[str, Any]:
    if not stock_id:
        return {"stock_id": "", "latest": {}, "quarters": [], "source": ""}

    start = (today_tw() - timedelta(days=560)).isoformat()
    rows = safe_call(lambda: finmind("TaiwanStockFinancialStatements", data_id=stock_id, start_date=start), [])
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        date = str(row.get("date") or "")
        item_type = str(row.get("type") or "")
        if not date or not item_type:
            continue
        grouped.setdefault(date, {})[item_type] = float(row.get("value") or 0)

    if not grouped:
        return {"stock_id": stock_id, "latest": {}, "quarters": [], "source": ""}

    def pct(numerator: float, denominator: float) -> float | None:
        return round(numerator / denominator * 100, 2) if denominator else None

    def money(value: float | None) -> str:
        if value is None:
            return "-"
        abs_value = abs(value)
        if abs_value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:,.2f}兆元"
        if abs_value >= 100_000_000:
            return f"{value / 100_000_000:,.0f}億元"
        if abs_value >= 10_000:
            return f"{value / 10_000:,.0f}萬元"
        return f"{value:,.0f}元"

    quarters = []
    for date, values in sorted(grouped.items())[-6:]:
        revenue = values.get("Revenue", 0.0)
        gross_profit = values.get("GrossProfit", 0.0)
        operating_income = values.get("OperatingIncome", 0.0)
        net_income = values.get("IncomeAfterTaxes", values.get("EquityAttributableToOwnersOfParent", 0.0))
        eps = values.get("EPS")
        quarters.append(
            {
                "date": date,
                "revenue": money(revenue),
                "gross_profit": money(gross_profit),
                "operating_income": money(operating_income),
                "net_income": money(net_income),
                "eps": round(eps, 2) if eps is not None else None,
                "gross_margin": pct(gross_profit, revenue),
                "operating_margin": pct(operating_income, revenue),
                "net_margin": pct(net_income, revenue),
                "raw_revenue": revenue,
                "raw_eps": eps or 0,
            }
        )

    latest = quarters[-1]
    previous = quarters[-2] if len(quarters) >= 2 else None
    year_ago = quarters[-5] if len(quarters) >= 5 else None
    latest["revenue_qoq"] = pct(latest["raw_revenue"] - previous["raw_revenue"], previous["raw_revenue"]) if previous else None
    latest["revenue_yoy"] = pct(latest["raw_revenue"] - year_ago["raw_revenue"], year_ago["raw_revenue"]) if year_ago else None
    latest["eps_qoq"] = pct(latest["raw_eps"] - previous["raw_eps"], previous["raw_eps"]) if previous else None
    latest["eps_yoy"] = pct(latest["raw_eps"] - year_ago["raw_eps"], year_ago["raw_eps"]) if year_ago else None

    return {
        "stock_id": stock_id,
        "latest": latest,
        "quarters": quarters[-4:],
        "source": "FinMind TaiwanStockFinancialStatements",
    }


def fallback_quote(symbol: str, name: str, topic: str) -> dict[str, Any]:
    return {"symbol": symbol, "name": name, "price": 0, "change": 0, "change_pct": 0, "volume": 0, "topic": topic, "error": "資料暫不可用"}


def institutional_trades(stock_id: str = "2330") -> dict[str, Any]:
    twse_rows = twse_institutional_rows(stock_id)
    if twse_rows:
        normalized = []
        net_total = 0.0
        for row in twse_rows:
            net_total += row["net"]
            normalized.append(
                {
                    "date": row["date"],
                    "name": row["name"],
                    "buy": f"{format_large(row['buy'] / 1000)}張",
                    "sell": f"{format_large(row['sell'] / 1000)}張",
                    "net": f"{format_large(row['net'] / 1000)}張",
                    "raw_net": row["net"] / 1000,
                }
            )
        return {"stock_id": stock_id, "rows": normalized, "net_total": net_total, "summary": long_short_label(net_total), "source": "TWSE T86"}

    start = (today_tw() - timedelta(days=14)).isoformat()
    rows = safe_call(
        lambda: finmind("TaiwanStockInstitutionalInvestorsBuySell", data_id=stock_id, start_date=start),
        [],
    )
    recent = rows[-10:]
    normalized = []
    net_total = 0.0
    for row in recent:
        buy = float(row.get("buy", 0) or 0)
        sell = float(row.get("sell", 0) or 0)
        net = float(row.get("buy_sell", buy - sell) or 0)
        net_total += net
        normalized.append(
            {
                "date": row.get("date", ""),
                "name": row.get("name", row.get("Institutional_Investors", "")),
                "buy": f"{format_large(buy / 1000)}張",
                "sell": f"{format_large(sell / 1000)}張",
                "net": f"{format_large(net / 1000)}張",
                "raw_net": net / 1000,
            }
        )
    return {"stock_id": stock_id, "rows": normalized, "net_total": net_total, "summary": long_short_label(net_total), "source": "FinMind"}


def institutional_rankings() -> dict[str, Any]:
    ranking = safe_call(twse_institutional_top5, {"date": "", "source": "TWSE T86", "top_buy": [], "top_sell": []})
    def normalize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "code": row["code"],
                "name": row["name"],
                "net_lots": format_large(row["net"] / 1000),
                "raw_net": row["net"] / 1000,
                "unit": "張",
            }
            for row in rows
        ]
    return {
        "date": ranking.get("date", ""),
        "source": ranking.get("source", "TWSE T86"),
        "unit": "張數",
        "top_buy": normalize(ranking.get("top_buy", [])),
        "top_sell": normalize(ranking.get("top_sell", [])),
    }


def margin_trades(stock_id: str = "2330") -> dict[str, Any]:
    start = (today_tw() - timedelta(days=20)).isoformat()
    rows = safe_call(lambda: finmind("TaiwanStockMarginPurchaseShortSale", data_id=stock_id, start_date=start), [])
    if rows:
        normalized = []
        for row in rows[-7:]:
            margin_balance = row.get("MarginPurchaseTodayBalance") or row.get("margin_purchase_today_balance") or 0
            short_balance = row.get("ShortSaleTodayBalance") or row.get("short_sale_today_balance") or 0
            margin_previous = row.get("MarginPurchaseYesterdayBalance") or row.get("margin_purchase_yesterday_balance") or 0
            short_previous = row.get("ShortSaleYesterdayBalance") or row.get("short_sale_yesterday_balance") or 0
            margin_diff = float(margin_balance or 0) - float(margin_previous or 0)
            short_diff = float(short_balance or 0) - float(short_previous or 0)
            normalized.append(
                {
                    "date": row.get("date", ""),
                    "margin_change": f"{format_large(margin_diff)}張",
                    "short_change": f"{format_large(short_diff)}張",
                    "margin_balance": f"{format_large(margin_balance)}張",
                    "short_balance": f"{format_large(short_balance)}張",
                }
            )
        return {"stock_id": stock_id, "rows": normalized, "source": "FinMind TaiwanStockMarginPurchaseShortSale"}

    twse_rows = twse_margin_rows(stock_id)
    if twse_rows:
        normalized = []
        for row in twse_rows:
            normalized.append(
                {
                    "date": row["date"],
                    "margin_change": f"{format_large(row['margin_buy'] - row['margin_sell'] - row['margin_repay'])}張",
                    "short_change": f"{format_large(row['short_sell'] - row['short_buy'] - row['short_repay'])}張",
                    "margin_balance": f"{format_large(row['margin_balance'])}張",
                    "short_balance": f"{format_large(row['short_balance'])}張",
                }
            )
        return {"stock_id": stock_id, "rows": normalized, "source": "TWSE MI_MARGN"}

    return {"stock_id": stock_id, "rows": [], "source": ""}


def market_margin() -> dict[str, Any]:
    summary = safe_call(
        twse_market_margin_summary,
        {"date": "", "source": "TWSE MI_MARGN", "margin": {}, "short": {}, "margin_amount": {}},
    )

    def normalize(title: str, row: dict[str, Any], unit: str) -> dict[str, Any]:
        buy = float(row.get("buy") or 0)
        sell = float(row.get("sell") or 0)
        repay = float(row.get("repay") or 0)
        balance = float(row.get("balance") or 0)
        previous = float(row.get("previous_balance") or 0)
        change = balance - previous
        return {
            "title": title,
            "buy": f"{format_large(buy)}{unit}",
            "sell": f"{format_large(sell)}{unit}",
            "repay": f"{format_large(repay)}{unit}",
            "balance": f"{format_large(balance)}{unit}",
            "change": f"{format_large(change)}{unit}",
        }

    amount = summary.get("margin_amount", {})
    amount_balance = round(float(amount.get("balance") or 0) / 100000)
    amount_change = round((float(amount.get("balance") or 0) - float(amount.get("previous_balance") or 0)) / 100000)
    rows = [
        normalize("融資", summary.get("margin", {}), "張"),
        normalize("融券", summary.get("short", {}), "張"),
        {
            "title": "融資金額",
            "buy": "-",
            "sell": "-",
            "repay": "-",
            "balance": f"{amount_balance:,.0f}億元",
            "change": f"{amount_change:,.0f}億元",
        },
    ]
    return {
        "date": summary.get("date", ""),
        "source": summary.get("source", "TWSE MI_MARGN"),
        "rows": rows,
    }


def futures_position() -> dict[str, Any]:
    start = (today_tw() - timedelta(days=30)).isoformat()
    rows = safe_call(lambda: finmind("TaiwanFuturesInstitutionalInvestors", data_id="TX", start_date=start), [])
    if rows:
        latest_date = max(row.get("date", "") for row in rows)
        recent = [row for row in rows if row.get("date") == latest_date]
    else:
        latest_date = ""
        recent = []
    normalized = []
    net_total = 0.0
    open_interest = 0.0
    order = {"外資": 0, "投信": 1, "自營商": 2}
    for row in sorted(recent, key=lambda item: order.get(item.get("institutional_investors", ""), 99)):
        long_oi = float(
            row.get("long_open_interest_balance_volume")
            or row.get("long_open_interest", row.get("LongOpenInterest", 0))
            or 0
        )
        short_oi = float(
            row.get("short_open_interest_balance_volume")
            or row.get("short_open_interest", row.get("ShortOpenInterest", 0))
            or 0
        )
        net = long_oi - short_oi
        net_total += net
        open_interest += long_oi + short_oi
        normalized.append(
            {
                "date": latest_date,
                "name": row.get("institutional_investors", row.get("name", "法人")),
                "long_oi": f"{format_large(long_oi)}口",
                "short_oi": f"{format_large(short_oi)}口",
                "net": f"{format_large(net)}口",
                "raw_net": net,
            }
        )
    if not normalized:
        index = quote_from_yahoo("^TWII", "台股加權")
        net_total = index["change_pct"]
        open_interest = 0
    return {
        "rows": normalized,
        "net_total": net_total,
        "date": latest_date,
        "open_interest": f"{format_large(open_interest)}口",
        "bias": long_short_label(net_total),
        "unit": "口",
    }


def currencies() -> list[dict[str, Any]]:
    rows = []
    for symbol, name in CURRENCIES:
        rows.append(safe_call(lambda s=symbol, n=name: quote_from_exchange_rate(s, n), fallback_quote(symbol, name, "FX")))
    return rows


def _latest_fred_card(series_id: str, name: str, unit: str, topic: str = "", yoy: bool = False) -> dict[str, Any]:
    rows = fred_series(series_id)
    latest = rows[-1]
    previous = rows[-2] if len(rows) >= 2 else latest
    year_ago = rows[-13] if len(rows) >= 13 else None
    value = float(latest["value"])
    change = value - float(previous["value"])
    change_pct = (value - float(year_ago["value"])) / float(year_ago["value"]) * 100 if yoy and year_ago and year_ago["value"] else change
    display_value = round(change_pct, 2) if yoy else round(value, 2)
    return {
        "name": name,
        "value": display_value,
        "unit": "% YoY" if yoy else unit,
        "date": latest["date"],
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "topic": topic,
        "source": f"FRED {series_id}",
        "series": rows[-12:],
    }


def _bls_card(rows: list[dict[str, Any]], name: str, unit: str, topic: str = "", yoy: bool = False) -> dict[str, Any]:
    if not rows:
        return {"name": name, "value": "-", "unit": unit, "date": "-", "topic": topic, "source": "BLS", "series": []}
    latest = rows[-1]
    previous = rows[-2] if len(rows) >= 2 else latest
    year_ago = rows[-13] if len(rows) >= 13 else None
    value = float(latest["value"])
    change = value - float(previous["value"])
    change_pct = (value - float(year_ago["value"])) / float(year_ago["value"]) * 100 if yoy and year_ago and year_ago["value"] else change
    return {
        "name": name,
        "value": round(change_pct if yoy else value, 2),
        "unit": "% YoY" if yoy else unit,
        "date": latest.get("label") or latest.get("date", ""),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "topic": topic,
        "source": "BLS",
        "series": rows[-12:],
    }


def _taiwan_indicator_card(indicator: dict[str, Any], name: str, unit: str = "", topic: str = "") -> dict[str, Any]:
    rows = indicator.get("rows", [])
    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else latest
    value = float(latest["value"])
    change = value - float(previous["value"])
    return {
        "name": name,
        "value": round(value, 2),
        "unit": unit or indicator.get("unit", ""),
        "date": latest.get("label") or latest.get("date", ""),
        "change": round(change, 2),
        "change_pct": round(change, 2),
        "topic": topic,
        "source": "DGBAS Taiwan",
        "series": list(reversed(rows[:12])),
    }


def _find_indicator(indicators: list[dict[str, Any]], keyword: str) -> dict[str, Any] | None:
    keyword_lower = keyword.lower()
    return next((row for row in indicators if keyword_lower in str(row.get("title", "")).lower()), None)


def macro_economy() -> dict[str, Any]:
    year = today_tw().year
    bls_rows = safe_call(lambda: bls_series(["CUUR0000SA0", "WPUFD4", "LNS14000000", "CES0000000001", "CES0500000003"], year - 1, year), {})
    us_cards = [
        _bls_card(bls_rows.get("CUUR0000SA0", []), "美國 CPI", "%", "消費者物價年增率", True),
        _bls_card(bls_rows.get("WPUFD4", []), "美國 PPI", "%", "生產者物價年增率", True),
        _bls_card(bls_rows.get("LNS14000000", []), "美國失業率", "%", "勞動市場"),
        _bls_card(bls_rows.get("CES0000000001", []), "美國非農就業", "千人", "就業人數"),
        _bls_card(bls_rows.get("CES0500000003", []), "美國平均時薪", "美元", "薪資通膨"),
    ]

    def stat_page(sid: str, n: str) -> list[dict[str, Any]]:
        return safe_call(lambda: taiwan_stat_indicators(sid, n), [])

    pages: dict[str, list[dict[str, Any]]] = {}
    page_specs = {
        "prices": ("t.2", "4201"),
        "gdp": ("t.1", "4200"),
        "unemployment": ("t.3", "4202"),
        "industrial": ("t.5", "4204"),
        "export_orders": ("t.6", "4205"),
        "import_growth": ("t.7", "4206"),
        "export_growth": ("t.8", "4207"),
        "reserves": ("t.10", "4209"),
        "leading": ("t.11", "4210"),
    }
    executor = ThreadPoolExecutor(max_workers=8)
    future_map = {executor.submit(stat_page, sid, n): key for key, (sid, n) in page_specs.items()}
    done, pending = wait(future_map, timeout=8)
    for future in done:
        pages[future_map[future]] = future.result()
    for future in pending:
        future.cancel()
    executor.shutdown(wait=False, cancel_futures=True)

    price_rows = pages.get("prices", [])
    taiwan_cards = []
    card_specs = [
        (_find_indicator(price_rows, "CPI Change Rate"), "台灣 CPI", "% YoY", "消費者物價年增率"),
        (_find_indicator(price_rows, "PPI Change Rate"), "台灣 PPI", "% YoY", "生產者物價年增率"),
        (_find_indicator(price_rows, "Core CPI"), "台灣核心 CPI", "% YoY", "排除蔬果能源"),
        (_find_indicator(pages.get("gdp", []), "Economic Growth"), "台灣 GDP 成長率", "%", "經濟成長"),
        (_find_indicator(pages.get("unemployment", []), "Unemployment"), "台灣失業率", "%", "勞動市場"),
        (_find_indicator(pages.get("industrial", []), "Industrial Production Index Growth Rate"), "台灣工業生產", "%", "工業生產年增率"),
        (_find_indicator(pages.get("export_orders", []), "Export Orders"), "台灣外銷訂單", "億美元", "出口訂單"),
        (_find_indicator(pages.get("import_growth", []), "Import on customs basis Growth Rate"), "台灣進口成長", "%", "海關進口年增率"),
        (_find_indicator(pages.get("export_growth", []), "Export on customs basis Growth Rate"), "台灣出口成長", "%", "海關出口年增率"),
        (_find_indicator(pages.get("reserves", []), "Foreign Exchange"), "台灣外匯存底", "億美元", "央行外匯存底"),
        (_find_indicator(pages.get("leading", []), "Leading"), "台灣領先指標", "指數", "景氣領先指標"),
    ]
    for indicator, name, unit, topic in card_specs:
        if indicator:
            taiwan_cards.append(_taiwan_indicator_card(indicator, name, unit, topic))

    inflation_note = "通膨升溫" if any(float(card.get("value") or 0) > 3 for card in taiwan_cards[:2] + us_cards[:2] if card.get("value") != "-") else "通膨溫和"
    return {
        "updated_at": today_tw().isoformat(),
        "source": "BLS + DGBAS Taiwan",
        "summary": inflation_note,
        "us": us_cards,
        "taiwan": taiwan_cards,
    }


def global_markets() -> list[dict[str, Any]]:
    rows = []
    for symbol, name, topic in GLOBAL_MARKETS:
        rows.append(safe_call(lambda s=symbol, n=name, t=topic: quote_from_yahoo(s, n, t), fallback_quote(symbol, name, topic)))
    return rows


def us_hot_stocks() -> list[dict[str, Any]]:
    def fetch(symbol: str, name: str, topic: str) -> dict[str, Any]:
        yahoo_fallback = safe_call(lambda: quote_from_yahoo(symbol, name, topic), fallback_quote(symbol, name, topic))
        return safe_call(lambda: quote_from_nasdaq(symbol, name, topic), yahoo_fallback)

    rows = []
    executor = ThreadPoolExecutor(max_workers=10)
    future_map = {executor.submit(fetch, symbol, name, topic): symbol for symbol, name, topic in US_HOT}
    done, pending = wait(future_map, timeout=12)
    for future in done:
        rows.append(future.result())
    for future in pending:
        future.cancel()
    executor.shutdown(wait=False, cancel_futures=True)
    active_rows = [row for row in rows if int(row.get("volume") or 0) > 0]
    ranked = sorted(active_rows or rows, key=lambda row: int(row.get("volume") or 0), reverse=True)
    return ranked[:8]


def etf_dividends(stock_id: str) -> dict[str, Any]:
    start = (today_tw() - timedelta(days=730)).isoformat()
    rows = safe_call(lambda: finmind("TaiwanStockDividend", data_id=stock_id, start_date=start), [])
    today = today_tw()
    normalized = []
    for row in rows:
        cash = float(row.get("CashEarningsDistribution") or 0)
        ex_date = row.get("CashExDividendTradingDate") or row.get("date") or ""
        pay_date = row.get("CashDividendPaymentDate") or ""
        if cash <= 0:
            continue
        normalized.append(
            {
                "date": row.get("date", ""),
                "ex_date": ex_date,
                "pay_date": pay_date,
                "cash": cash,
            }
        )
    normalized = sorted(normalized, key=lambda row: row["ex_date"] or row["date"])
    recent = []
    for row in normalized:
        try:
            ex_day = today.fromisoformat(row["ex_date"])
        except ValueError:
            continue
        if today - timedelta(days=365) <= ex_day <= today:
            recent.append(row)
    if not recent:
        recent = normalized[-4:]
    annual_cash = sum(row["cash"] for row in recent)
    latest = normalized[-1] if normalized else {}
    return {
        "rows": normalized[-6:],
        "annual_cash": annual_cash,
        "latest_cash": latest.get("cash", 0),
        "latest_ex_date": latest.get("ex_date", ""),
        "latest_pay_date": latest.get("pay_date", ""),
        "source": "FinMind TaiwanStockDividend",
    }


def etf_risk_stats(symbol: str) -> dict[str, Any]:
    series = safe_call(lambda: series_from_yahoo(symbol, 35), [])
    closes = [float(row["close"]) for row in series if row.get("close")]
    returns = []
    for idx in range(1, len(closes)):
        previous = closes[idx - 1]
        if previous:
            returns.append((closes[idx] - previous) / previous * 100)
    volatility = stdev(returns) if len(returns) >= 2 else 0.0
    return {"volatility": round(volatility, 2), "series": series[-20:]}


def etf_score(quote: dict[str, Any], dividends: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    price = float(quote.get("price") or 0)
    volume = int(quote.get("volume") or 0)
    lots = volume / 1000
    annual_cash = float(dividends.get("annual_cash") or 0)
    dividend_yield = (annual_cash / price * 100) if price else 0
    change_pct = float(quote.get("change_pct") or 0)
    volatility = float(risk.get("volatility") or 0)
    raw = 0.0
    reasons = []

    if dividend_yield >= 7:
        raw += 2
        reasons.append("配息率高")
    elif dividend_yield >= 4:
        raw += 1
        reasons.append("配息率中上")
    elif dividend_yield > 0:
        reasons.append("配息率偏低")
    else:
        raw -= 1
        reasons.append("近一年未抓到現金配息")

    if change_pct >= 1:
        raw += 1
        reasons.append("價格動能偏強")
    elif change_pct <= -1:
        raw -= 1
        reasons.append("價格動能偏弱")

    if lots >= 20000:
        raw += 1
        reasons.append("成交張數高")
    elif lots >= 5000:
        raw += 0.5
        reasons.append("成交張數足夠")
    else:
        raw -= 0.5
        reasons.append("成交張數偏低")

    if volatility and volatility <= 1.2:
        raw += 1
        reasons.append("近月波動較低")
    elif volatility >= 2.5:
        raw -= 1
        reasons.append("近月波動偏高")

    score = max(0, min(100, round(60 + raw * 10)))
    if score >= 85:
        grade = "A"
        label = "高分"
    elif score >= 75:
        grade = "B"
        label = "可觀察"
    elif score >= 65:
        grade = "C"
        label = "普通"
    else:
        grade = "D"
        label = "偏弱"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "dividend_yield": round(dividend_yield),
        "lots": round(lots, 0),
        "volatility": volatility,
        "reasons": reasons[:4],
    }


def hot_etfs() -> dict[str, Any]:
    rows = []
    for code, name, topic in HOT_ETFS:
        symbol = f"{code}.TW"
        quote = safe_call(lambda s=symbol, n=name, t=topic: quote_from_yahoo(s, n, t), fallback_quote(symbol, name, topic))
        dividends = etf_dividends(code)
        risk = etf_risk_stats(symbol)
        score = etf_score(quote, dividends, risk)
        rows.append(
            {
                **quote,
                "code": code,
                "annual_cash": round(float(dividends.get("annual_cash") or 0)),
                "latest_cash": round(float(dividends.get("latest_cash") or 0)),
                "latest_ex_date": dividends.get("latest_ex_date", ""),
                "latest_pay_date": dividends.get("latest_pay_date", ""),
                "dividend_source": dividends.get("source", ""),
                "score": score,
            }
        )
    rows = sorted(rows, key=lambda row: row["score"]["score"], reverse=True)
    return {
        "source": "Yahoo Finance + FinMind TaiwanStockDividend",
        "unit": "現金配息為每受益權單位新台幣元；成交量顯示張數",
        "rows": rows,
    }


def bond_signal(curve: dict[str, Any], etfs: list[dict[str, Any]]) -> dict[str, Any]:
    spread_2y10y = float(curve.get("spread_2y10y_bps", 0) or 0)
    spread_3m10y = float(curve.get("spread_3m10y_bps", 0) or 0)
    ten_year = float(curve.get("ten_year", 0) or 0)
    long_bond = next((row for row in etfs if row["symbol"] == "TLT"), None)
    high_yield = next((row for row in etfs if row["symbol"] == "HYG"), None)

    reasons = []
    score = 0
    if spread_2y10y < 0 or spread_3m10y < 0:
        score -= 1
        reasons.append("殖利率曲線倒掛，景氣風險偏高")
    else:
        score += 1
        reasons.append("殖利率曲線正斜率，期限補償較正常")
    if ten_year >= 4.5:
        score += 1
        reasons.append("10 年期殖利率偏高，債券收益墊較厚")
    elif ten_year and ten_year < 3.5:
        score -= 1
        reasons.append("10 年期殖利率偏低，收益保護較薄")
    if long_bond and float(long_bond.get("change_pct", 0) or 0) > 0:
        score += 1
        reasons.append("長天期債 ETF 價格轉強")
    if high_yield and float(high_yield.get("change_pct", 0) or 0) < -0.5:
        score -= 1
        reasons.append("高收益債轉弱，信用風險升溫")

    if score >= 2:
        action = "偏多 / 可分批配置債券"
        tone = "buy"
    elif score <= -1:
        action = "偏保守 / 縮短天期與降低信用風險"
        tone = "sell"
    else:
        action = "中性 / 以短中天期為主"
        tone = "hold"
    return {"action": action, "tone": tone, "score": score, "reasons": reasons[:4]}


def bond_analysis() -> dict[str, Any]:
    curve = safe_call(
        treasury_yield_curve,
        {
            "date": "-",
            "curve": [],
            "ten_year": 0,
            "two_year": 0,
            "thirty_year": 0,
            "spread_2y10y_bps": 0,
            "spread_3m10y_bps": 0,
            "spread_10y30y_bps": 0,
            "source": "fallback",
        },
    )
    def fetch_overseas_bond_etf(symbol: str, name: str, topic: str) -> dict[str, Any]:
        yahoo_fallback = safe_call(lambda: quote_from_yahoo(symbol, name, topic), fallback_quote(symbol, name, topic))
        return safe_call(lambda: quote_from_nasdaq_etf(symbol, name, topic), yahoo_fallback)

    def fetch_taiwan_bond_etf(code: str, name: str, topic: str) -> dict[str, Any]:
        return safe_call(lambda: quote_with_valuation(code, name, topic), fallback_quote(f"{code}.TW", name, topic))

    etfs = []
    tw_etfs = []
    executor = ThreadPoolExecutor(max_workers=12)
    futures = []
    for symbol, name, topic in BOND_ETFS:
        futures.append(("overseas", executor.submit(fetch_overseas_bond_etf, symbol, name, topic)))
    for code, name, topic in TAIWAN_BOND_ETFS:
        futures.append(("taiwan", executor.submit(fetch_taiwan_bond_etf, code, name, topic)))

    future_map = {future: group for group, future in futures}
    done, pending = wait(future_map, timeout=14)
    for future in done:
        group = future_map[future]
        try:
            row = future.result()
        except Exception:
            row = None
        if not row:
            continue
        if group == "overseas":
            etfs.append(row)
        else:
            tw_etfs.append(row)
    for future in pending:
        future.cancel()
    executor.shutdown(wait=False, cancel_futures=True)

    if len(etfs) < len(BOND_ETFS):
        loaded = {row.get("symbol") for row in etfs}
        for symbol, name, topic in BOND_ETFS:
            if symbol not in loaded:
                etfs.append(fallback_quote(symbol, name, topic))
    if len(tw_etfs) < len(TAIWAN_BOND_ETFS):
        loaded = {str(row.get("symbol", "")).split(".")[0] for row in tw_etfs}
        for code, name, topic in TAIWAN_BOND_ETFS:
            if code not in loaded:
                tw_etfs.append(fallback_quote(f"{code}.TW", name, topic))

    return {
        "curve": curve,
        "etfs": etfs,
        "tw_etfs": tw_etfs,
        "signal": bond_signal(curve, etfs),
        "notes": [
            "利率上升時，長天期債券價格通常承壓較大",
            "高收益債更接近信用風險資產，景氣轉弱時需降曝險",
            "短天期債波動較低，適合作為現金管理替代觀察",
        ],
    }


def symbol_detail(symbol: str) -> dict[str, Any]:
    stock_id = symbol.split(".")[0] if symbol.endswith(".TW") else symbol
    if symbol.endswith(".TW") or stock_id.isdigit():
        fallback_quote_data = safe_call(lambda: quote_from_finmind_stock(stock_id, symbol), fallback_quote(symbol, symbol, ""))
        fallback_series = safe_call(lambda: series_from_finmind_stock(stock_id, 60), [])
        quote = safe_call(lambda: quote_with_valuation(stock_id, "", ""), fallback_quote_data)
        series = safe_call(lambda: twse_security_series(stock_id, 60), fallback_series)
    else:
        quote = quote_from_yahoo(symbol, symbol)
        series = series_from_yahoo(symbol, 60)
    inst = institutional_trades(stock_id)
    signal = recommendation(quote["change_pct"], quote["volume"], series, inst["net_total"])
    return {**quote, "quote": quote, "series": series, "institutional": inst, "signal": signal}


def technical_panel(stock_id: str = "") -> dict[str, Any]:
    market_candles = safe_call(lambda: ohlc_from_finmind("TAIEX", 90), [])
    panel = {
        "market": {
            "name": "台股加權",
            "symbol": "TAIEX",
            "candles": market_candles[-60:],
            "indicators": technical_indicators(market_candles),
            "source": "FinMind TaiwanStockPrice",
        },
        "stock": None,
    }
    if stock_id:
        stock_candles = safe_call(lambda: ohlc_from_finmind(stock_id, 90), [])
        panel["stock"] = {
            "name": stock_id,
            "symbol": f"{stock_id}.TW",
            "candles": stock_candles[-60:],
            "indicators": technical_indicators(stock_candles),
            "source": "FinMind TaiwanStockPrice",
        }
    return panel


def dashboard_payload(stock_id: str = "") -> dict[str, Any]:
    stock_id = stock_id.strip()
    overview = safe_call(market_overview, {"quote": fallback_quote("^TWII", "台股加權", ""), "trade": {}, "series": [], "signal": {}})
    has_stock = bool(stock_id)
    inst = institutional_trades(stock_id) if has_stock else {"stock_id": "", "rows": [], "net_total": 0, "summary": "", "source": ""}
    return {
        "updated_at": today_tw().isoformat(),
        "stock_searched": has_stock,
        "stock_id": stock_id,
        "market": overview,
        "quotes": quotes(stock_id),
        "institutional": inst,
        "institutional_rankings": institutional_rankings(),
        "market_margin": market_margin(),
        "margin": margin_trades(stock_id) if has_stock else {"stock_id": "", "rows": [], "source": ""},
        "futures": futures_position(),
        "hot_etfs": hot_etfs(),
        "global_markets": global_markets(),
        "currencies": currencies(),
        "us_hot": us_hot_stocks(),
        "bonds": bond_analysis(),
        "technical": technical_panel(stock_id),
    }


def dashboard_payload(stock_id: str = "") -> dict[str, Any]:
    stock_id = stock_id.strip()
    has_stock = bool(stock_id)
    empty_inst = {"stock_id": "", "rows": [], "net_total": 0, "summary": "", "source": ""}
    empty_margin = {"stock_id": "", "rows": [], "source": ""}
    fallbacks: dict[str, Any] = {
        "market": {"quote": fallback_quote("^TWII", "大盤", ""), "trade": {}, "series": [], "signal": {}},
        "quotes": [],
        "institutional": empty_inst,
        "institutional_rankings": {"date": "", "source": "TWSE T86", "unit": "張數", "top_buy": [], "top_sell": []},
        "market_margin": {"date": "", "source": "TWSE MI_MARGN", "rows": []},
        "margin": empty_margin,
        "financials": {"stock_id": "", "latest": {}, "quarters": [], "source": ""},
        "futures": {"rows": [], "net_total": 0, "date": "", "open_interest": "-", "bias": "", "unit": "口"},
        "hot_etfs": {"source": "", "unit": "現金配息為每受益權單位新台幣元；成交量顯示張數", "rows": []},
        "global_markets": [],
        "currencies": [],
        "us_hot": [],
        "bonds": {"curve": {}, "etfs": [], "tw_etfs": [], "signal": {}, "notes": []},
        "macro": {"updated_at": "", "source": "", "summary": "", "us": [], "taiwan": []},
        "technical": {"market": {"candles": [], "indicators": {}, "source": ""}, "stock": None},
    }
    tasks = {
        "market": market_overview,
        "quotes": lambda: quotes(stock_id),
        "institutional": (lambda: institutional_trades(stock_id)) if has_stock else (lambda: empty_inst),
        "institutional_rankings": institutional_rankings,
        "market_margin": market_margin,
        "margin": (lambda: margin_trades(stock_id)) if has_stock else (lambda: empty_margin),
        "financials": (lambda: financial_report(stock_id)) if has_stock else (lambda: {"stock_id": "", "latest": {}, "quarters": [], "source": ""}),
        "futures": futures_position,
        "hot_etfs": hot_etfs,
        "global_markets": global_markets,
        "currencies": currencies,
        "us_hot": us_hot_stocks,
        "bonds": bond_analysis,
        "macro": macro_economy,
        "technical": lambda: technical_panel(stock_id),
    }
    results = dict(fallbacks)
    executor = ThreadPoolExecutor(max_workers=16)
    future_map = {executor.submit(func): key for key, func in tasks.items()}
    done, pending = wait(future_map, timeout=45)
    for future in done:
        key = future_map[future]
        try:
            results[key] = future.result()
        except Exception:
            results[key] = fallbacks[key]
    for future in pending:
        future.cancel()
    executor.shutdown(wait=False, cancel_futures=True)
    return {
        "updated_at": today_tw().isoformat(),
        "stock_searched": has_stock,
        "stock_id": stock_id,
        **results,
    }
