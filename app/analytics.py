from __future__ import annotations

from statistics import mean
from typing import Any


def format_large(value: int | float | str | None) -> str:
    if value is None:
        return "-"
    try:
        number = float(str(value).replace(",", ""))
    except ValueError:
        return str(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000_000:
        return f"{sign}{number / 1_000_000_000_000:.0f}兆"
    if number >= 100_000_000:
        return f"{sign}{number / 100_000_000:.0f}億"
    if number >= 10_000:
        return f"{sign}{number / 10_000:.0f}萬"
    return f"{sign}{number:,.0f}"


def recommendation(change_pct: float, volume: int, series: list[dict[str, Any]], institutional_net: float = 0) -> dict[str, Any]:
    closes = [float(row["close"]) for row in series[-20:] if row.get("close") is not None]
    volumes = [int(row["volume"]) for row in series[-20:] if row.get("volume") is not None]
    avg_close = mean(closes) if closes else 0
    avg_volume = mean(volumes) if volumes else 0

    score = 0
    reasons: list[str] = []
    price = closes[-1] if closes else 0
    if change_pct > 1:
        score += 1
        reasons.append("價格動能偏強")
    elif change_pct < -1:
        score -= 1
        reasons.append("短線價格轉弱")
    if avg_close and price > avg_close:
        score += 1
        reasons.append("站上 20 日均價")
    elif avg_close and price < avg_close:
        score -= 1
        reasons.append("跌破 20 日均價")
    if avg_volume and volume > avg_volume * 1.25:
        score += 1 if change_pct >= 0 else -1
        reasons.append("成交量明顯放大")
    if institutional_net > 0:
        score += 1
        reasons.append("法人近期偏買超")
    elif institutional_net < 0:
        score -= 1
        reasons.append("法人近期偏賣超")

    if score >= 2:
        action = "偏多 / 可分批買入"
        tone = "buy"
    elif score <= -2:
        action = "偏空 / 建議減碼"
        tone = "sell"
    else:
        action = "觀望 / 等待訊號"
        tone = "hold"

    return {"action": action, "tone": tone, "score": score, "reasons": reasons[:3]}


def long_short_label(value: float) -> str:
    if value > 0:
        return "偏多"
    if value < 0:
        return "偏空"
    return "中性"


def ema(values: list[float], period: int) -> list[float | None]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    result: list[float | None] = []
    current: float | None = None
    for idx, value in enumerate(values):
        if idx < period - 1:
            result.append(None)
            continue
        if current is None:
            current = mean(values[idx - period + 1 : idx + 1])
        else:
            current = value * alpha + current * (1 - alpha)
        result.append(current)
    return result


def technical_indicators(candles: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [float(row["close"]) for row in candles if row.get("close") is not None]
    highs = [float(row["high"]) for row in candles if row.get("high") is not None]
    lows = [float(row["low"]) for row in candles if row.get("low") is not None]
    if len(closes) < 15:
        return {"kd": {}, "rsi": None, "macd": {}, "signal": {"action": "資料不足", "tone": "hold", "reasons": []}}

    k_values: list[float | None] = []
    d_values: list[float | None] = []
    k = 50.0
    d = 50.0
    for idx, close in enumerate(closes):
        if idx < 8:
            k_values.append(None)
            d_values.append(None)
            continue
        high_n = max(highs[idx - 8 : idx + 1])
        low_n = min(lows[idx - 8 : idx + 1])
        rsv = 50.0 if high_n == low_n else (close - low_n) / (high_n - low_n) * 100
        k = (2 / 3) * k + (1 / 3) * rsv
        d = (2 / 3) * d + (1 / 3) * k
        k_values.append(k)
        d_values.append(d)

    gains: list[float] = []
    losses: list[float] = []
    for idx in range(1, len(closes)):
        diff = closes[idx] - closes[idx - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    rsi = None
    if len(gains) >= 14:
        avg_gain = mean(gains[-14:])
        avg_loss = mean(losses[-14:])
        rsi = 100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif_values: list[float | None] = []
    for fast, slow in zip(ema12, ema26):
        dif_values.append(None if fast is None or slow is None else fast - slow)
    dea_values = ema([value for value in dif_values if value is not None], 9)
    latest_dif = next((value for value in reversed(dif_values) if value is not None), None)
    latest_dea = next((value for value in reversed(dea_values) if value is not None), None)
    histogram = latest_dif - latest_dea if latest_dif is not None and latest_dea is not None else None

    latest_k = next((value for value in reversed(k_values) if value is not None), None)
    latest_d = next((value for value in reversed(d_values) if value is not None), None)
    reasons: list[str] = []
    score = 0
    if latest_k is not None and latest_d is not None:
        if latest_k > latest_d:
            score += 1
            reasons.append("KD 黃金交叉或 K 值高於 D 值")
        else:
            score -= 1
            reasons.append("KD 偏弱或 K 值低於 D 值")
    if rsi is not None:
        if rsi >= 70:
            score -= 1
            reasons.append("RSI 過熱，追價風險提高")
        elif rsi <= 30:
            score += 1
            reasons.append("RSI 偏低，短線反彈機率提高")
        elif rsi > 50:
            score += 1
            reasons.append("RSI 位於多方區")
        else:
            reasons.append("RSI 位於中性偏弱區")
    if histogram is not None:
        if histogram > 0:
            score += 1
            reasons.append("MACD 柱狀體為正")
        else:
            score -= 1
            reasons.append("MACD 柱狀體為負")

    if score >= 2:
        action = "技術面偏多"
        tone = "buy"
    elif score <= -2:
        action = "技術面偏空"
        tone = "sell"
    else:
        action = "技術面中性"
        tone = "hold"

    return {
        "kd": {"k": round(latest_k, 2) if latest_k is not None else None, "d": round(latest_d, 2) if latest_d is not None else None},
        "rsi": round(rsi, 2) if rsi is not None else None,
        "macd": {
            "dif": round(latest_dif, 2) if latest_dif is not None else None,
            "dea": round(latest_dea, 2) if latest_dea is not None else None,
            "histogram": round(histogram, 2) if histogram is not None else None,
        },
        "signal": {"action": action, "tone": tone, "score": score, "reasons": reasons[:4]},
    }
