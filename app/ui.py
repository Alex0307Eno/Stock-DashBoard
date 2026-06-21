from __future__ import annotations


def page_html() -> str:
    return """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Python Market Desk</title>
  <link rel="stylesheet" href="/static/styles.css?v=20260617-17">
</head>
<body>
  <header class="topbar">
    <div class="product-brand">
      <div class="brand-mark"><span>PM</span></div>
      <div class="brand-block">
        <p class="eyebrow">Python Market Desk</p>
        <h1>市場分析工作台</h1>
        <p class="subtitle">台股、美股、ETF、籌碼、債券與總經資料</p>
      </div>
    </div>
    <div class="topbar-tools">
      <div class="market-status-pill">
        <span>TAIEX</span>
        <b id="headerMarketValue">-</b>
        <small id="headerUpdated">-</small>
      </div>
      <div class="search">
        <label for="stockInput">股票代號</label>
        <input id="stockInput" placeholder="例如 2330" aria-label="股票代號">
        <button id="reloadBtn">搜尋</button>
      </div>
    </div>
  </header>

  <main>
    <nav class="category-nav" aria-label="資料分類">
      <button class="tab-button active" data-target="overviewSection">大盤</button>
      <button class="tab-button" data-target="stockSection">個股</button>
      <button class="tab-button" data-target="etfSection">ETF</button>
      <button class="tab-button" data-target="chipsSection">法人籌碼</button>
      <button class="tab-button" data-target="bondsSection">債券</button>
      <button class="tab-button" data-target="macroSection">總體經濟</button>
      <button class="tab-button" data-target="globalSection">全球市場</button>
    </nav>

    <section class="category-section active" id="overviewSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Market</p>
          <h2>大盤總覽</h2>
        </div>
        <span>只顯示大盤資訊</span>
      </div>

      <div class="hero-grid">
        <article class="panel market-panel">
          <div class="section-title"><span>台股加權</span><small id="updatedAt">-</small></div>
          <div class="market-number" id="marketPrice">-</div>
          <div class="delta" id="marketDelta">-</div>
          <div class="market-quick-stats">
            <div><span>最新收盤</span><b id="marketLatestClose">-</b></div>
            <div><span>30日高點</span><b id="marketHigh">-</b></div>
            <div><span>30日低點</span><b id="marketLow">-</b></div>
          </div>
        </article>

        <article class="panel signal-panel">
          <div class="section-title"><span>大盤建議</span><small>動能、量能、法人估算</small></div>
          <div class="signal" id="signalAction">-</div>
          <ul id="signalReasons"></ul>
          <div class="trade-levels" id="marketTradeLevels"></div>
        </article>

        <article class="panel">
          <div class="section-title"><span>成交概況</span><small id="marketSource"></small></div>
          <div class="metrics">
            <div class="metric-row">
              <span class="metric-label"><i class="metric-icon icon-price" aria-hidden="true">價</i><span>成交金額</span></span>
              <span class="metric-value"><b id="tradeValue">-</b><small id="tradeValueRaw"></small></span>
            </div>
            <div class="metric-row">
              <span class="metric-label"><i class="metric-icon icon-volume" aria-hidden="true">量</i><span>成交量</span></span>
              <span class="metric-value"><b id="tradeVolume">-</b><small id="tradeVolumeRaw"></small></span>
            </div>
            <div class="metric-row">
              <span class="metric-label"><i class="metric-icon icon-count" aria-hidden="true">筆</i><span>成交筆數</span></span>
              <span class="metric-value"><b id="transactions">-</b><small id="transactionsRaw"></small></span>
            </div>
          </div>
        </article>
      </div>

      <article class="panel wide">
        <div class="section-title"><span>大盤技術分析</span><small id="marketTechSource"></small></div>
        <canvas class="kline-chart" id="marketKline" width="720" height="360"></canvas>
        <div class="kline-guide" id="marketLineGuide"></div>
        <div class="indicator-grid" id="marketIndicators"></div>
        <div class="signal compact-signal" id="marketTechSignal">-</div>
        <ul id="marketTechReasons"></ul>
      </article>

      <article class="panel wide">
        <div class="section-title"><span>大盤融資融券</span><small id="marketMarginSource"></small></div>
        <div class="data-card-grid" id="marketMarginCards"></div>
      </article>
    </section>

    <section class="category-section" id="stockSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Stock</p>
          <h2>個股分析</h2>
        </div>
        <span id="stockSectionHint">搜尋股票代號後才顯示</span>
      </div>

      <article class="panel stock-empty" id="stockEmptyPanel">
        <div>
          <h3>請先搜尋股票代號</h3>
          <p>例如 2330、2317、0050。搜尋後才會顯示報價、EPS、本益比、K 線、法人買賣超與融資融券。</p>
        </div>
      </article>

      <article class="panel stock-loading-panel" id="stockLoadingPanel" hidden>
        <div class="loader-ring" aria-hidden="true"></div>
        <div>
          <h3>搜尋中</h3>
          <p id="stockLoadingText">正在抓取個股報價、K 線、法人與融資融券資料</p>
        </div>
      </article>

      <article class="panel wide stock-only" id="stockOverviewPanel" hidden>
        <div class="section-title"><span>個股報價與估值</span><small>搜尋結果</small></div>
        <div class="quote-grid" id="quotes"></div>
      </article>

      <article class="panel wide stock-only" id="stockFinancialPanel" hidden>
        <div class="section-title"><span>財報重點</span><small id="financialSource"></small></div>
        <div class="financial-grid" id="financialCards"></div>
        <div class="quarter-strip" id="financialQuarters"></div>
      </article>

      <div class="layout stock-only" id="stockDetailGrid" hidden>
        <article class="panel" id="stockTechnicalPanel">
          <div class="section-title"><span>個股技術分析</span><small id="stockTechSource"></small></div>
          <canvas class="kline-chart" id="stockKline" width="720" height="360"></canvas>
          <div class="kline-guide" id="stockLineGuide"></div>
          <div class="trade-levels stock-trade-levels" id="stockTradeLevels"></div>
          <div class="indicator-grid" id="stockIndicators"></div>
          <div class="signal compact-signal" id="stockTechSignal">-</div>
          <ul id="stockTechReasons"></ul>
        </article>

        <article class="panel" id="stockInstitutionalPanel">
          <div class="section-title"><span>三大法人最近交易</span><small id="instSummary"></small></div>
          <canvas class="bar-chart" id="institutionalChart" width="720" height="320"></canvas>
          <div class="chart-legend"><span class="legend-up">買超</span><span class="legend-down">賣超</span></div>
        </article>
      </div>

      <article class="panel wide stock-only" id="stockMarginPanel" hidden>
        <div class="section-title"><span>融資融券增減</span><small>紅色融資、綠色融券，單位：張</small></div>
        <div class="margin-change-chart" id="marginCards"></div>
      </article>
    </section>

    <section class="category-section" id="etfSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">ETF</p>
          <h2>熱門 ETF 配息與評分</h2>
        </div>
        <span>價格、張數、配息與評分</span>
      </div>
      <article class="panel wide">
        <div class="section-title"><span>熱門 ETF</span><small id="etfSource"></small></div>
        <div class="etf-card-grid" id="hotEtfs"></div>
      </article>
      <article class="panel wide etf-rank-panel">
        <div class="section-title"><span>ETF 評分排序</span><small id="etfUnit"></small></div>
        <div class="ranking-list" id="etfRankList"></div>
      </article>
    </section>

    <section class="category-section" id="chipsSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Institutional</p>
          <h2>法人籌碼</h2>
        </div>
        <span>買賣超排行與期貨部位</span>
      </div>
      <article class="panel institutional-summary-panel">
        <div class="section-title"><span>法人籌碼總覽</span><small id="institutionalSummarySource"></small></div>
        <div class="institutional-summary-grid" id="institutionalSummaryCards"></div>
        <div class="institutional-summary-note" id="institutionalSummaryNote"></div>
      </article>
      <div class="layout">
        <article class="panel">
          <div class="section-title"><span>法人買超前五名</span><small id="topBuySource"></small></div>
          <div class="ranking-list" id="topBuyList"></div>
        </article>
        <article class="panel">
          <div class="section-title"><span>法人賣超前五名</span><small id="topSellSource"></small></div>
          <div class="ranking-list" id="topSellList"></div>
        </article>
      </div>
      <article class="panel">
        <div class="section-title"><span>三大法人倉位與未平倉</span><small id="futureBias"></small></div>
        <div class="future-head"><b id="futureOi">-</b><span>未平倉合計</span></div>
        <div class="futures-dashboard" id="futuresCards"></div>
      </article>
    </section>

    <section class="category-section" id="bondsSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Bonds</p>
          <h2>債券分析</h2>
        </div>
        <span>利率曲線、美債與台股債券 ETF</span>
      </div>
      <div class="bond-dashboard">
        <article class="panel bond-rate-panel">
          <div class="section-title"><span>利率與曲線</span><small id="bondSource"></small></div>
          <div class="bond-summary">
            <div><b id="bond10y">-</b><span>美債 10Y 殖利率</span></div>
            <div><b id="bond2s10s">-</b><span>2Y / 10Y 利差</span></div>
            <div><b id="bond3m10y">-</b><span>3M / 10Y 利差</span></div>
          </div>
          <div class="yield-curve" id="yieldCurve"></div>
          <div class="signal compact-signal" id="bondSignal">-</div>
          <ul id="bondReasons"></ul>
        </article>

        <article class="panel bond-etf-panel">
          <div class="section-title"><span>海外債券 ETF</span><small>美債、投資級與高收益</small></div>
          <div class="bond-card-grid" id="bondEtfs"></div>
        </article>
      </div>

      <article class="panel wide bond-tw-panel">
        <div class="section-title"><span>台股主要債券 ETF</span><small>台灣掛牌，成交量以張數顯示</small></div>
        <div class="bond-card-grid tw-bond-grid" id="twBondEtfs"></div>
      </article>

      <article class="panel wide bond-note-panel">
          <div class="section-title"><span>債券提醒</span><small>利率、信用與匯率風險</small></div>
          <ul class="risk-notes" id="bondNotes"></ul>
      </article>
    </section>

    <section class="category-section" id="macroSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Macro</p>
          <h2>總體經濟</h2>
        </div>
        <span id="macroSummary">美國與台灣 CPI、PPI 與主要總經指標</span>
      </div>
      <article class="panel wide">
        <div class="section-title"><span>美國總經</span><small id="macroUsSource"></small></div>
        <div class="macro-grid" id="macroUsCards"></div>
      </article>
      <article class="panel wide macro-panel-gap">
        <div class="section-title"><span>台灣總經</span><small id="macroTaiwanSource"></small></div>
        <div class="macro-grid" id="macroTaiwanCards"></div>
      </article>
    </section>

    <section class="category-section" id="globalSection">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Global</p>
          <h2>全球市場</h2>
        </div>
        <span>全球大盤、匯率與美股熱門股</span>
      </div>
      <article class="panel wide global-market-panel">
        <div class="section-title"><span>全球主要大盤</span><small>美股、亞洲、歐洲指數</small></div>
        <div class="market-index-grid" id="globalMarkets"></div>
      </article>
      <article class="panel wide fx-panel">
        <div class="section-title"><span>貨幣匯率</span><small>主要幣種，即時匯率與漲跌</small></div>
        <div class="fx-grid" id="currencies"></div>
      </article>
      <article class="panel wide us-hot-panel">
        <div class="section-title"><span>美股熱門股</span><small>依成交量排序，顯示漲跌與題材</small></div>
        <div class="compact-list us-hot-list" id="usHot"></div>
      </article>
    </section>
  </main>
  <script src="/static/app.js?v=20260617-20"></script>
</body>
</html>"""
