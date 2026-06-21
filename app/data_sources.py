from __future__ import annotations

import csv
import html as html_lib
import io
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "python-etf-dashboard/1.0"


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheItem] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item or item.expires_at < time.time():
            self._items.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> Any:
        self._items[key] = CacheItem(value=value, expires_at=time.time() + ttl_seconds)
        return value


cache = TTLCache()


def http_json(url: str, ttl_seconds: int = 900, headers: dict[str, str] | None = None) -> Any:
    cached = cache.get(url)
    if cached is not None:
        return cached
    request = Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urlopen(request, timeout=6) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return cache.set(url, payload, ttl_seconds)


def http_text(url: str, ttl_seconds: int = 900) -> str:
    cached = cache.get(url)
    if cached is not None:
        return cached
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=6) as response:
        payload = response.read().decode("utf-8", errors="ignore")
    return cache.set(url, payload, ttl_seconds)


def parse_number(value: Any) -> float:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = text.replace(",", "").replace("+", "").replace("%", "").strip()
    if text in {"", "-", "--", "X", "除權", "除息"}:
        return 0.0
    return float(text)


def parse_optional_number(value: Any) -> float | None:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = text.replace(",", "").replace("+", "").replace("%", "").strip()
    if text in {"", "-", "--", "X", "除權", "除息"}:
        return None
    return float(text)


def today_tw() -> date:
    return datetime.utcnow().date()


def recent_dates(days: int = 10) -> list[date]:
    current = today_tw()
    return [current - timedelta(days=offset) for offset in range(days)]


def finmind(dataset: str, **params: str) -> list[dict[str, Any]]:
    query = {"dataset": dataset, **params}
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else None
    url = f"https://api.finmindtrade.com/api/v4/data?{urlencode(query)}"
    payload = http_json(url, ttl_seconds=1800, headers=headers)
    if payload.get("status") != 200:
        raise RuntimeError(payload.get("msg") or f"FinMind error for {dataset}")
    return payload.get("data", [])


def fred_series(series_id: str, ttl_seconds: int = 3600) -> list[dict[str, Any]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    cached = cache.get(url)
    if cached is not None:
        payload = cached
    else:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=18) as response:
            payload = response.read().decode("utf-8", errors="ignore")
        cache.set(url, payload, ttl_seconds)
    reader = csv.DictReader(io.StringIO(payload))
    rows: list[dict[str, Any]] = []
    for row in reader:
        value = row.get(series_id, "")
        if value in {"", "."}:
            continue
        try:
            number = float(value)
        except ValueError:
            continue
        rows.append({"date": row.get("observation_date", ""), "value": number})
    return rows


def bls_series(series_ids: list[str], start_year: int, end_year: int, ttl_seconds: int = 3600) -> dict[str, list[dict[str, Any]]]:
    body = json.dumps({"seriesid": series_ids, "startyear": str(start_year), "endyear": str(end_year)}).encode("utf-8")
    cache_key = f"https://api.bls.gov/publicAPI/v2/timeseries/data/::{','.join(series_ids)}::{start_year}-{end_year}"
    cached = cache.get(cache_key)
    if cached is not None:
        payload = cached
    else:
        request = Request(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            data=body,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        cache.set(cache_key, payload, ttl_seconds)

    result: dict[str, list[dict[str, Any]]] = {}
    for series in payload.get("Results", {}).get("series", []):
        series_id = series.get("seriesID", "")
        rows = []
        for row in series.get("data", []):
            value = row.get("value")
            if value in {"", "-"}:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            period = str(row.get("period", ""))
            month = period[1:] if period.startswith("M") else "01"
            rows.append(
                {
                    "date": f"{row.get('year', '')}-{month.zfill(2)}-01",
                    "label": f"{row.get('periodName', '')} {row.get('year', '')}".strip(),
                    "value": number,
                }
            )
        result[series_id] = list(reversed(rows))
    return result


def taiwan_stat_indicators(sid: str, n: str, ttl_seconds: int = 3600) -> list[dict[str, Any]]:
    url = f"https://eng.stat.gov.tw/Point.aspx?n={n}&sid={sid}&sms=11713"
    cached = cache.get(url)
    if cached is not None:
        payload = cached
    else:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=18) as response:
            payload = response.read().decode("utf-8", errors="ignore")
        cache.set(url, payload, ttl_seconds)
    payload = html_lib.unescape(payload)
    indicators: list[dict[str, Any]] = []
    pattern = re.compile(r'\{"Title":"([^"]+)".*?"Unit":"([^"]*)".*?"data":\[(.*?)\]\}', re.S)
    for match in pattern.finditer(payload):
        title = match.group(1)
        unit = match.group(2)
        try:
            rows = json.loads(f"[{match.group(3)}]")
        except json.JSONDecodeError:
            continue
        clean_rows = []
        for row in rows:
            try:
                value = float(row.get("Value", ""))
            except (TypeError, ValueError):
                continue
            clean_rows.append(
                {
                    "date": row.get("Date", ""),
                    "label": row.get("Title", row.get("Date", "")),
                    "value": value,
                }
            )
        if clean_rows:
            indicators.append({"title": title, "unit": unit, "rows": clean_rows})
    return indicators


def twse_date_string(day: date) -> str:
    return day.strftime("%Y%m%d")


def twse_json(path: str, ttl_seconds: int = 900, **params: str) -> dict[str, Any]:
    query = urlencode({**params, "response": "json"})
    url = f"https://www.twse.com.tw/rwd/zh/{path}?{query}"
    return http_json(url, ttl_seconds=ttl_seconds)


def twse_latest_payload(path: str, max_days: int = 14, **params: str) -> dict[str, Any]:
    last_error = ""
    for day in recent_dates(max_days):
        payload = twse_json(path, date=twse_date_string(day), **params)
        if payload.get("stat") == "OK" or payload.get("tables"):
            return payload
        last_error = payload.get("stat", "")
    raise RuntimeError(last_error or f"TWSE {path} unavailable")


def twse_table_rows(payload: dict[str, Any], title_keyword: str | None = None) -> tuple[list[str], list[list[str]]]:
    tables = payload.get("tables") or []
    if not tables and payload.get("fields") and payload.get("data"):
        return payload["fields"], payload["data"]
    for table in tables:
        title = table.get("title", "")
        if title_keyword is None or title_keyword in title:
            return table.get("fields", []), table.get("data", [])
    return [], []


def row_to_dict(fields: list[str], row: list[str]) -> dict[str, str]:
    return {field: row[idx] if idx < len(row) else "" for idx, field in enumerate(fields)}


def twse_market_snapshot(day: date | None = None) -> dict[str, Any]:
    if day is None:
        return twse_latest_payload("afterTrading/MI_INDEX", type="ALLBUT0999", max_days=14)
    return twse_json("afterTrading/MI_INDEX", ttl_seconds=1800, date=twse_date_string(day), type="ALLBUT0999")


def twse_index_quote() -> dict[str, Any]:
    payload = twse_market_snapshot()
    fields, rows = twse_table_rows(payload, "價格指數")
    for row in rows:
        item = row_to_dict(fields, row)
        if item.get("指數") == "發行量加權股價指數":
            sign = "-" if "-" in item.get("漲跌(+/-)", "") else "+"
            change = parse_number(item.get("漲跌點數")) * (-1 if sign == "-" else 1)
            return {
                "symbol": "TAIEX",
                "name": "台股加權",
                "price": round(parse_number(item.get("收盤指數")), 2),
                "change": round(change, 2),
                "change_pct": round(parse_number(item.get("漲跌百分比(%)")) * (-1 if sign == "-" else 1), 2),
                "volume": 0,
                "topic": "TWSE 大盤",
                "source": "TWSE MI_INDEX",
            }
    raise RuntimeError("TWSE TAIEX quote unavailable")


def twse_index_series(days: int = 30) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for day in recent_dates(max(days * 2, 20)):
        try:
            payload = twse_market_snapshot(day)
            fields, rows = twse_table_rows(payload, "價格指數")
            for row in rows:
                item = row_to_dict(fields, row)
                if item.get("指數") == "發行量加權股價指數":
                    series.append({"date": day.isoformat(), "close": round(parse_number(item.get("收盤指數")), 2), "volume": 0})
                    break
        except Exception:
            continue
    return sorted(series, key=lambda row: row["date"])[-days:]


def twse_security_quote(stock_id: str, label: str, topic: str = "") -> dict[str, Any]:
    payload = twse_market_snapshot()
    fields, rows = twse_table_rows(payload, "每日收盤行情")
    for row in rows:
        item = row_to_dict(fields, row)
        if item.get("證券代號") == stock_id:
            sign = "-" if "-" in item.get("漲跌(+/-)", "") else "+"
            change = parse_number(item.get("漲跌價差")) * (-1 if sign == "-" else 1)
            price = parse_number(item.get("收盤價"))
            previous = price - change
            change_pct = (change / previous * 100) if previous else 0
            return {
                "symbol": f"{stock_id}.TW",
                "name": label or item.get("證券名稱", stock_id).strip(),
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(parse_number(item.get("成交股數"))),
                "topic": topic,
                "source": "TWSE MI_INDEX",
            }
    raise RuntimeError(f"TWSE quote unavailable for {stock_id}")


def twse_valuation_metrics(stock_id: str) -> dict[str, Any]:
    payload = twse_latest_payload("afterTrading/BWIBBU_d", selectType="ALL", max_days=14)
    fields, rows = twse_table_rows(payload)
    for row in rows:
        item = row_to_dict(fields, row)
        if item.get("證券代號") != stock_id:
            continue
        price = parse_optional_number(item.get("收盤價"))
        pe = parse_optional_number(item.get("本益比"))
        eps = round(price / pe, 2) if price and pe else None
        dividend_yield = parse_optional_number(item.get("殖利率(%)"))
        pb = parse_optional_number(item.get("股價淨值比"))
        return {
            "pe": round(pe, 2) if pe is not None else None,
            "eps": eps,
            "pb": round(pb, 2) if pb is not None else None,
            "dividend_yield": round(dividend_yield, 2) if dividend_yield is not None else None,
            "fiscal_period": item.get("財報年/季", ""),
            "valuation_source": "TWSE BWIBBU_d",
            "eps_method": "price / PE",
        }
    raise RuntimeError(f"TWSE valuation unavailable for {stock_id}")


def twse_security_series(stock_id: str, days: int = 30) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for day in recent_dates(max(days * 2, 20)):
        try:
            payload = twse_market_snapshot(day)
            fields, rows = twse_table_rows(payload, "每日收盤行情")
            for row in rows:
                item = row_to_dict(fields, row)
                if item.get("證券代號") == stock_id:
                    series.append(
                        {
                            "date": day.isoformat(),
                            "close": round(parse_number(item.get("收盤價")), 2),
                            "volume": int(parse_number(item.get("成交股數"))),
                        }
                    )
                    break
        except Exception:
            continue
    return sorted(series, key=lambda row: row["date"])[-days:]


def twse_institutional_rows(stock_id: str, max_days: int = 14) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for day in recent_dates(max_days):
        try:
            payload = twse_json("fund/T86", ttl_seconds=1800, date=twse_date_string(day), selectType="ALLBUT0999")
            if payload.get("stat") != "OK":
                continue
            fields, rows = twse_table_rows(payload)
            for row in rows:
                item = row_to_dict(fields, row)
                if item.get("證券代號") != stock_id:
                    continue
                result.extend(
                    [
                        {
                            "date": day.isoformat(),
                            "name": "外陸資",
                            "buy": parse_number(item.get("外陸資買進股數(不含外資自營商)")),
                            "sell": parse_number(item.get("外陸資賣出股數(不含外資自營商)")),
                            "net": parse_number(item.get("外陸資買賣超股數(不含外資自營商)")),
                        },
                        {
                            "date": day.isoformat(),
                            "name": "投信",
                            "buy": parse_number(item.get("投信買進股數")),
                            "sell": parse_number(item.get("投信賣出股數")),
                            "net": parse_number(item.get("投信買賣超股數")),
                        },
                        {
                            "date": day.isoformat(),
                            "name": "自營商",
                            "buy": parse_number(item.get("自營商買進股數(自行買賣)")) + parse_number(item.get("自營商買進股數(避險)")),
                            "sell": parse_number(item.get("自營商賣出股數(自行買賣)")) + parse_number(item.get("自營商賣出股數(避險)")),
                            "net": parse_number(item.get("自營商買賣超股數")),
                        },
                    ]
                )
                break
        except Exception:
            continue
    return sorted(result, key=lambda row: row["date"])[-12:]


def twse_institutional_top5() -> dict[str, Any]:
    payload = twse_latest_payload("fund/T86", selectType="ALLBUT0999", max_days=14)
    fields, rows = twse_table_rows(payload)
    ranked = []
    for row in rows:
        item = row_to_dict(fields, row)
        code = item.get("證券代號", "").strip()
        name = item.get("證券名稱", "").strip()
        net = parse_number(item.get("三大法人買賣超股數"))
        if not code or not name or net == 0:
            continue
        ranked.append({"code": code, "name": name, "net": net})
    top_buy = sorted((row for row in ranked if row["net"] > 0), key=lambda row: row["net"], reverse=True)[:5]
    top_sell = sorted((row for row in ranked if row["net"] < 0), key=lambda row: row["net"])[:5]
    return {
        "date": payload.get("date", ""),
        "source": "TWSE T86",
        "top_buy": top_buy,
        "top_sell": top_sell,
    }


def twse_margin_rows(stock_id: str, max_days: int = 14) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for day in recent_dates(max_days):
        try:
            payload = twse_json("marginTrading/MI_MARGN", ttl_seconds=1800, date=twse_date_string(day), selectType="ALL")
            if payload.get("stat") != "OK":
                continue
            fields, rows = twse_table_rows(payload, "融資融券彙總")
            for row in rows:
                item = row_to_dict(fields, row)
                if item.get("代號") != stock_id:
                    continue
                result.append(
                    {
                        "date": day.isoformat(),
                        "margin_buy": parse_number(row[2] if len(row) > 2 else 0),
                        "margin_sell": parse_number(row[3] if len(row) > 3 else 0),
                        "margin_repay": parse_number(row[4] if len(row) > 4 else 0),
                        "margin_balance": parse_number(row[6] if len(row) > 6 else 0),
                        "short_buy": parse_number(row[8] if len(row) > 8 else 0),
                        "short_sell": parse_number(row[9] if len(row) > 9 else 0),
                        "short_repay": parse_number(row[10] if len(row) > 10 else 0),
                        "short_balance": parse_number(row[12] if len(row) > 12 else 0),
                    }
                )
                break
        except Exception:
            continue
    return sorted(result, key=lambda row: row["date"])[-7:]


def twse_market_margin_summary() -> dict[str, Any]:
    payload = twse_latest_payload("marginTrading/MI_MARGN", selectType="ALL", max_days=14)
    fields, rows = twse_table_rows(payload, "信用交易統計")
    summary: dict[str, dict[str, float]] = {}
    for row in rows:
        if not row:
            continue
        item = row[0]
        summary[item] = {
            "buy": parse_number(row[1] if len(row) > 1 else 0),
            "sell": parse_number(row[2] if len(row) > 2 else 0),
            "repay": parse_number(row[3] if len(row) > 3 else 0),
            "previous_balance": parse_number(row[4] if len(row) > 4 else 0),
            "balance": parse_number(row[5] if len(row) > 5 else 0),
        }
    return {
        "date": payload.get("date", ""),
        "source": "TWSE MI_MARGN 信用交易統計",
        "margin": summary.get("融資(交易單位)", {}),
        "short": summary.get("融券(交易單位)", {}),
        "margin_amount": summary.get("融資金額(仟元)", {}),
    }


def yahoo_chart(symbol: str, range_: str = "1mo", interval: str = "1d") -> dict[str, Any]:
    encoded = symbol.replace("^", "%5E")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_}&interval={interval}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    payload = http_json(url, ttl_seconds=300, headers=headers)
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError(f"Yahoo chart has no data for {symbol}")
    return result[0]


def quote_from_yahoo(symbol: str, label: str, topic: str = "") -> dict[str, Any]:
    chart = yahoo_chart(symbol, range_="5d", interval="1d")
    meta = chart.get("meta", {})
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
    closes = [x for x in quote.get("close", []) if isinstance(x, (int, float))]
    volumes = [x for x in quote.get("volume", []) if isinstance(x, (int, float))]
    price = float(meta.get("regularMarketPrice") or (closes[-1] if closes else 0))
    previous = float(meta.get("previousClose") or (closes[-2] if len(closes) > 1 else price))
    change = price - previous
    change_pct = (change / previous * 100) if previous else 0
    return {
        "symbol": symbol,
        "name": label,
        "price": round(price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(volumes[-1]) if volumes else 0,
        "topic": topic,
    }


def _parse_market_number(value: Any) -> float:
    text = str(value or "0").replace("$", "").replace(",", "").replace("%", "").replace("+", "").strip()
    if text in {"", "N/A", "--"}:
        return 0.0
    return float(text)


def quote_from_nasdaq(symbol: str, label: str, topic: str = "") -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }
    url = f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=stocks"
    payload = http_json(url, ttl_seconds=120, headers=headers)
    data = payload.get("data") or {}
    primary = data.get("primaryData") or {}
    secondary = data.get("secondaryData") or {}
    quote = primary if primary.get("lastSalePrice") not in (None, "", "N/A") else secondary
    price = _parse_market_number(quote.get("lastSalePrice"))
    change = _parse_market_number(quote.get("netChange"))
    pct_text = str(quote.get("percentageChange") or "0").replace("%", "")
    change_pct = _parse_market_number(pct_text)
    if str(quote.get("netChange", "")).strip().startswith("-") and change > 0:
        change = -change
    if str(quote.get("percentageChange", "")).strip().startswith("-") and change_pct > 0:
        change_pct = -change_pct
    return {
        "symbol": symbol,
        "name": label,
        "price": round(price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(_parse_market_number(quote.get("volume"))),
        "topic": topic,
    }


def quote_from_nasdaq_etf(symbol: str, label: str, topic: str = "") -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }
    url = f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass=etf"
    payload = http_json(url, ttl_seconds=120, headers=headers)
    data = payload.get("data") or {}
    primary = data.get("primaryData") or {}
    secondary = data.get("secondaryData") or {}
    quote = primary if primary.get("lastSalePrice") not in (None, "", "N/A") else secondary
    price = _parse_market_number(quote.get("lastSalePrice"))
    change = _parse_market_number(quote.get("netChange"))
    change_pct = _parse_market_number(str(quote.get("percentageChange") or "0").replace("%", ""))
    if str(quote.get("netChange", "")).strip().startswith("-") and change > 0:
        change = -change
    if str(quote.get("percentageChange", "")).strip().startswith("-") and change_pct > 0:
        change_pct = -change_pct
    return {
        "symbol": symbol,
        "name": label,
        "price": round(price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(_parse_market_number(quote.get("volume"))),
        "topic": topic,
        "source": "Nasdaq",
    }


def treasury_yield_curve() -> dict[str, Any]:
    current = today_tw().replace(day=1)
    months = []
    for offset in range(4):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year}{month:02d}")

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
        "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    }
    latest: dict[str, Any] | None = None
    for month in months:
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
            f"?data=daily_treasury_yield_curve&field_tdr_date_value_month={month}"
        )
        xml_text = http_text(url, ttl_seconds=1800)
        root = ET.fromstring(xml_text)
        for props in root.findall(".//m:properties", ns):
            row: dict[str, Any] = {}
            for child in list(props):
                key = child.tag.split("}", 1)[-1]
                row[key] = child.text or ""
            if row.get("NEW_DATE"):
                latest = row
        if latest:
            break

    if not latest:
        raise RuntimeError("Treasury yield curve unavailable")

    def rate(field: str) -> float:
        value = latest.get(field, "")
        return round(float(value), 2) if value not in {"", None} else 0.0

    curve = [
        {"tenor": "3M", "yield": rate("BC_3MONTH")},
        {"tenor": "1Y", "yield": rate("BC_1YEAR")},
        {"tenor": "2Y", "yield": rate("BC_2YEAR")},
        {"tenor": "5Y", "yield": rate("BC_5YEAR")},
        {"tenor": "10Y", "yield": rate("BC_10YEAR")},
        {"tenor": "30Y", "yield": rate("BC_30YEAR")},
    ]
    ten_year = rate("BC_10YEAR")
    two_year = rate("BC_2YEAR")
    three_month = rate("BC_3MONTH")
    thirty_year = rate("BC_30YEAR")
    return {
        "date": str(latest.get("NEW_DATE", ""))[:10],
        "curve": curve,
        "ten_year": ten_year,
        "two_year": two_year,
        "thirty_year": thirty_year,
        "spread_2y10y_bps": round((ten_year - two_year) * 100, 1),
        "spread_3m10y_bps": round((ten_year - three_month) * 100, 1),
        "spread_10y30y_bps": round((thirty_year - ten_year) * 100, 1),
        "source": "U.S. Treasury",
    }


def exchange_rates() -> dict[str, float]:
    url = "https://open.er-api.com/v6/latest/USD"
    payload = http_json(url, ttl_seconds=1800)
    if payload.get("result") != "success":
        raise RuntimeError("exchange-rate-api unavailable")
    return payload.get("rates") or {}


def quote_from_exchange_rate(symbol: str, label: str) -> dict[str, Any]:
    rates = exchange_rates()
    mapping = {
        "USDTWD=X": ("TWD", False),
        "USDJPY=X": ("JPY", False),
        "USDCNH=X": ("CNY", False),
        "EURUSD=X": ("EUR", True),
        "GBPUSD=X": ("GBP", True),
        "AUDUSD=X": ("AUD", True),
        "NZDUSD=X": ("NZD", True),
        "USDKRW=X": ("KRW", False),
        "USDSGD=X": ("SGD", False),
        "USDHKD=X": ("HKD", False),
        "USDTHB=X": ("THB", False),
        "USDCHF=X": ("CHF", False),
    }
    code, invert = mapping[symbol]
    rate = float(rates.get(code) or 0)
    if invert and rate:
        rate = 1 / rate
    return {
        "symbol": symbol,
        "name": label,
        "price": round(rate, 4),
        "change": 0,
        "change_pct": 0,
        "volume": 0,
        "topic": "每日匯率",
    }


def quote_from_finmind_stock(stock_id: str, label: str, topic: str = "") -> dict[str, Any]:
    start = (today_tw() - timedelta(days=14)).isoformat()
    rows = finmind("TaiwanStockPrice", data_id=stock_id, start_date=start)
    rows = [row for row in rows if row.get("close") not in (None, "")]
    if not rows:
        raise RuntimeError(f"FinMind has no price rows for {stock_id}")
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else latest
    price = float(latest.get("close") or 0)
    previous_close = float(previous.get("close") or price)
    change = price - previous_close
    change_pct = (change / previous_close * 100) if previous_close else 0
    return {
        "symbol": f"{stock_id}.TW",
        "name": label,
        "price": round(price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(latest.get("Trading_Volume") or 0),
        "topic": topic,
    }


def series_from_finmind_stock(stock_id: str, days: int = 30) -> list[dict[str, Any]]:
    start = (today_tw() - timedelta(days=max(days * 2, 20))).isoformat()
    rows = finmind("TaiwanStockPrice", data_id=stock_id, start_date=start)
    series = []
    for row in rows:
        if row.get("close") in (None, ""):
            continue
        series.append(
            {
                "date": row.get("date", ""),
                "close": round(float(row.get("close") or 0), 2),
                "volume": int(row.get("Trading_Volume") or 0),
            }
        )
    return series[-days:]


def ohlc_from_finmind(stock_id: str, days: int = 90) -> list[dict[str, Any]]:
    start = (today_tw() - timedelta(days=max(days * 2, 120))).isoformat()
    rows = finmind("TaiwanStockPrice", data_id=stock_id, start_date=start)
    candles = []
    for row in rows:
        if row.get("close") in (None, ""):
            continue
        candles.append(
            {
                "date": row.get("date", ""),
                "open": round(float(row.get("open") or 0), 2),
                "high": round(float(row.get("max") or 0), 2),
                "low": round(float(row.get("min") or 0), 2),
                "close": round(float(row.get("close") or 0), 2),
                "volume": int(row.get("Trading_Volume") or 0),
            }
        )
    return candles[-days:]


def twse_index_from_finmind() -> dict[str, Any]:
    start = (today_tw() - timedelta(days=14)).isoformat()
    rows = finmind("TaiwanStockPrice", data_id="TAIEX", start_date=start)
    rows = [row for row in rows if row.get("close") not in (None, "")]
    if not rows:
        raise RuntimeError("FinMind has no TAIEX rows")
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else latest
    price = float(latest.get("close") or 0)
    previous_close = float(previous.get("close") or price)
    change = price - previous_close
    change_pct = (change / previous_close * 100) if previous_close else 0
    return {
        "symbol": "TAIEX",
        "name": "台股加權",
        "price": round(price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(latest.get("Trading_Volume") or 0),
        "topic": "台灣大盤",
    }


def twse_index_series_from_finmind(days: int = 30) -> list[dict[str, Any]]:
    start = (today_tw() - timedelta(days=max(days * 2, 20))).isoformat()
    rows = finmind("TaiwanStockPrice", data_id="TAIEX", start_date=start)
    series = []
    for row in rows:
        if row.get("close") in (None, ""):
            continue
        series.append(
            {
                "date": row.get("date", ""),
                "close": round(float(row.get("close") or 0), 2),
                "volume": int(row.get("Trading_Volume") or 0),
            }
        )
    return series[-days:]


def series_from_yahoo(symbol: str, days: int = 30) -> list[dict[str, Any]]:
    chart = yahoo_chart(symbol, range_=f"{max(days, 5)}d", interval="1d")
    timestamps = chart.get("timestamp", [])
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])
    rows: list[dict[str, Any]] = []
    for idx, ts in enumerate(timestamps):
        close = closes[idx] if idx < len(closes) else None
        if not isinstance(close, (int, float)) or math.isnan(close):
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                "close": round(float(close), 2),
                "volume": int(volumes[idx] or 0) if idx < len(volumes) else 0,
            }
        )
    return rows[-days:]


def get_twse_market_value() -> dict[str, Any]:
    for d in recent_dates(12):
        query = urlencode({"date": d.strftime("%Y%m%d"), "response": "json"})
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?{query}"
        payload = http_json(url, ttl_seconds=1800)
        rows = payload.get("data") or []
        if rows:
            latest = rows[-1]
            return {
                "date": latest[0],
                "trade_value": latest[1],
                "volume": latest[2],
                "transactions": latest[3],
                "source": "TWSE FMTQIK",
            }
    raise RuntimeError("TWSE market value unavailable")


def safe_call(func, fallback: Any) -> Any:
    try:
        return func()
    except Exception as exc:  # Keep dashboard usable when a provider throttles or has no holiday data.
        if isinstance(fallback, dict):
            return {**fallback, "error": str(exc)}
        return fallback
