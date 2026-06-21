# Python ETF 與市場儀表板

前端與後端都由 Python 專案提供：後端使用標準函式庫 `http.server` 提供 API，前端 HTML 由 Python 產生並由同一個服務輸出。

## 功能

- 大盤：台股加權報價、成交金額、成交量、成交筆數、近 30 日走勢
- 個股 / ETF：預設追蹤台積電、鴻海、聯發科、0050、00878，並顯示 EPS、本益比、股價淨值比
- 三大法人：最近交易、買進、賣出、買賣超
- 建議買入或賣出：用價格動能、20 日均價、成交量、法人買賣超給出偏多 / 偏空 / 觀望
- 融資融券：融資融券增減與餘額
- 期貨：未平倉與多空判斷
- 貨幣匯率：美元台幣、美元日圓、歐元美元、美元離岸人民幣
- 美股熱門股：漲跌幅與題材
- 債券分析：美債殖利率曲線、2Y/10Y 與 3M/10Y 利差、債券 ETF、配置建議
- 技術分析：大盤與個股 K 線圖、KD、RSI、MACD 與技術面多空判斷

## 啟動

```powershell
python run.py
```

若本機 `python` 尚未安裝，可用 Codex 內建 runtime：

```powershell
& "C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" run.py
```

開啟：

```text
http://127.0.0.1:8088
```

## API

- `GET /api/dashboard?stock=2330`
- `GET /api/symbol?symbol=2330.TW`

## 資料來源

- TWSE 公開資料：大盤、上市個股、ETF、成交量、EPS 估算、本益比、股價淨值比、三大法人、融資融券
- U.S. Treasury 公開 XML feed：美債殖利率曲線
- Nasdaq 公開 quote endpoint：美股熱門股與債券 ETF 報價
- Open Exchange Rate API：主要匯率
- FinMind API：TWSE 沒有資料或暫時不可用時的台股備援，以及期貨法人未平倉備援
- FinMind API：歷史 OHLC K 線與技術分析資料

匿名 FinMind 有流量限制。若要提高備援資料穩定度，可設定：

```powershell
$env:FINMIND_TOKEN="你的 FinMind token"
python run.py
```

本網站提供研究用訊號，不構成投資建議。


## Render 免費部署設定

本版本已支援 Render 的 PORT 環境變數，會自動綁定 0.0.0.0。

Render 設定：

- Service type: Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `python run.py`
- Plan: Free

如果有 FinMind token，可以在 Render 的 Environment Variables 新增：

- `FINMIND_TOKEN` = 你的 token

