const $ = (id) => document.getElementById(id);
let currentDashboard = null;
let activeSection = 'overviewSection';

function toneClass(value) {
  const number = Number(value || 0);
  if (number > 0) return 'up';
  if (number < 0) return 'down';
  return 'flat';
}

function formatInteger(value) {
  const number = Number(value || 0);
  if (!number) return '-';
  return Math.round(number).toLocaleString('zh-TW');
}

function formatPrice(value) {
  const number = Number(value || 0);
  if (!number) return '-';
  return number.toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatSigned(value, unit = '') {
  const number = Number(value || 0);
  const sign = number > 0 ? '+' : '';
  return `${sign}${Math.round(number).toLocaleString('zh-TW')}${unit}`;
}

function formatSignedDecimal(value, unit = '') {
  const number = Number(value || 0);
  const sign = number > 0 ? '+' : '';
  return `${sign}${number.toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${unit}`;
}

function formatCompact(value) {
  const number = Number(value || 0);
  const abs = Math.abs(number);
  const sign = number < 0 ? '-' : '';
  if (!abs) return '-';
  if (abs >= 1000000000000) return `${sign}${Math.round(abs / 1000000000000)}兆`;
  if (abs >= 100000000) return `${sign}${Math.round(abs / 100000000)}億`;
  if (abs >= 10000) return `${sign}${Math.round(abs / 10000)}萬`;
  return `${sign}${Math.round(abs).toLocaleString('zh-TW')}`;
}

function formatLotsFromShares(value) {
  const lots = Number(value || 0) / 1000;
  if (!lots) return '-';
  return `${formatCompact(lots)}張`;
}

function parseNumberText(value) {
  return Number(String(value || '0').replace(/,/g, '').replace(/[^\d.-]/g, '')) || 0;
}

function numberFromLarge(text) {
  if (typeof text === 'number') return text;
  const raw = String(text || '0').replace(/,/g, '').replace('張', '').trim();
  if (raw.endsWith('兆')) return Number(raw.slice(0, -1)) * 1000000000000;
  if (raw.endsWith('億')) return Number(raw.slice(0, -1)) * 100000000;
  if (raw.endsWith('萬')) return Number(raw.slice(0, -1)) * 10000;
  return Number(raw) || 0;
}

function numberFromLotsText(value) {
  if (typeof value === 'number') return value;
  const raw = String(value || '0').replace(/,/g, '').trim();
  const number = Number(raw.replace(/[^\d.-]/g, '')) || 0;
  if (raw.includes('兆')) return number * 1000000000000;
  if (raw.includes('億')) return number * 100000000;
  if (raw.includes('萬')) return number * 10000;
  return number;
}

function metricIcon(kind) {
  const labels = { price: '價', change: '漲', volume: '量', count: '筆' };
  return `<i class="metric-icon icon-${kind}" aria-hidden="true">${labels[kind] || ''}</i>`;
}

function statPill(kind, label, value, tone = '') {
  return `<span class="stat-pill ${tone}" title="${label}">
    ${metricIcon(kind)}<b>${value}</b><small>${label}</small>
  </span>`;
}

function quoteStats(row) {
  const changeTone = toneClass(row.change_pct);
  const change = `${formatSignedDecimal(row.change)} / ${formatSignedDecimal(row.change_pct, '%')}`;
  return `<div class="visual-stats">
    ${statPill('price', '價格', row.price ? formatPrice(row.price) : '-')}
    ${statPill('change', '漲跌幅', change, changeTone)}
    ${statPill('volume', '成交張數', formatLotsFromShares(row.volume))}
  </div>`;
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value ?? '-';
}

function setMetric(id, value, divisor, unit) {
  const number = parseNumberText(value);
  setText(id, number ? `${Math.round(number / divisor).toLocaleString('zh-TW')} ${unit}` : '-');
}

function formatMoneyTwd(value) {
  const number = parseNumberText(value);
  const abs = Math.abs(number);
  if (!abs) return '-';
  if (abs >= 1000000000000) return `${Math.round(number / 1000000000000).toLocaleString('zh-TW')} 兆元`;
  if (abs >= 100000000) return `${Math.round(number / 100000000).toLocaleString('zh-TW')} 億元`;
  if (abs >= 10000) return `${Math.round(number / 10000).toLocaleString('zh-TW')} 萬元`;
  return `${Math.round(number).toLocaleString('zh-TW')} 元`;
}

function setActiveSection(sectionId) {
  activeSection = sectionId;
  document.querySelectorAll('.category-section').forEach((section) => {
    section.classList.toggle('active', section.id === sectionId);
  });
  document.querySelectorAll('.tab-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.target === sectionId);
  });
  window.setTimeout(redrawVisibleCharts, 80);
}

function marketQuickStats(rows) {
  const closes = (rows || []).map((row) => Number(row.close)).filter(Boolean);
  if (!closes.length) {
    setText('marketLatestClose', '-');
    setText('marketHigh', '-');
    setText('marketLow', '-');
    return;
  }
  setText('marketLatestClose', formatInteger(closes.at(-1)));
  setText('marketHigh', formatInteger(Math.max(...closes)));
  setText('marketLow', formatInteger(Math.min(...closes)));
}

function quoteCard(row) {
  const eps = row.eps === null || row.eps === undefined ? '-' : formatInteger(row.eps);
  const pe = row.pe === null || row.pe === undefined ? '-' : formatInteger(row.pe);
  const pb = row.pb === null || row.pb === undefined ? '-' : formatInteger(row.pb);
  return `<article class="quote-card">
    <div class="card-head"><h3>${row.name || row.symbol}</h3><small>${row.symbol || ''}</small></div>
    ${quoteStats(row)}
    <div class="valuation">
      <span><b>${eps}</b><i>EPS</i></span>
      <span><b>${pe}</b><i>本益比</i></span>
      <span><b>${pb}</b><i>股淨比</i></span>
    </div>
    <p class="topic">${row.topic || ''}</p>
  </article>`;
}

function stockMiniBars(rows, valueKey, toneKey = 'close') {
  const values = (rows || []).map((row) => Number(row[valueKey] || 0)).filter((value) => Number.isFinite(value) && value !== 0);
  if (!values.length) return '<p class="muted">走勢資料暫不可用</p>';
  const min = Math.min(...values);
  const max = Math.max(...values);
  return (rows || []).slice(-34).map((row) => {
    const value = Number(row[valueKey] || 0);
    const base = max === min ? 38 : 12 + ((value - min) / Math.max(1, max - min)) * 64;
    const open = Number(row.open || value);
    const close = Number(row[toneKey] || value);
    const tone = close >= open ? 'up' : 'down';
    return `<i class="${tone}" style="height:${Math.max(4, base)}px" title="${row.date || ''} ${formatInteger(value)}"></i>`;
  }).join('');
}

function stockOverview(data) {
  const row = (data.quotes || [])[0];
  if (!row) return '';
  const candles = (data.technical?.stock?.candles || []).slice(-60);
  const closes = candles.map((item) => Number(item.close || 0)).filter(Boolean);
  const latest = closes.length ? closes.at(-1) : Number(row.price || 0);
  const high = closes.length ? Math.max(...closes) : 0;
  const low = closes.length ? Math.min(...closes) : 0;
  const first = closes.length ? closes[0] : latest;
  const rangePct = high > low ? Math.max(0, Math.min(100, (latest - low) / (high - low) * 100)) : 50;
  const rangeLabel = rangePct >= 75 ? '靠近區間高檔' : rangePct <= 25 ? '靠近區間低檔' : '位於區間中段';
  const priceTone = latest >= first ? 'up' : 'down';
  const priceChangePct = first ? (latest - first) / first * 100 : 0;
  const instLots = Number(data.institutional?.net_total || 0) / 1000;
  const instTone = toneClass(instLots);
  const latestMargin = (data.margin?.rows || [])[0] || {};
  const techSignal = data.technical?.stock?.indicators?.signal || {};
  const volumeLots = Number(row.volume || 0) / 1000;
  const summary = `${rangeLabel}，近 60 日${priceChangePct >= 0 ? '上漲' : '下跌'} ${Math.abs(priceChangePct).toFixed(2)}%，法人${instLots >= 0 ? '買超' : '賣超'} ${formatCompact(Math.abs(instLots))}張。`;
  return `${quoteCard(row)}
    <article class="stock-overview-visual">
      <div class="stock-story-head">
        <div>
          <span>近 60 日價格與籌碼摘要</span>
          <h3>${rangeLabel}</h3>
          <p>${candles[0]?.date || '-'} 至 ${candles.at(-1)?.date || '-'}</p>
        </div>
        <strong>${formatPrice(latest)}</strong>
      </div>
      <div class="range-meter">
        <div class="range-meter-labels">
          <span>區間低 ${formatPrice(low)}</span>
          <b>目前位置 ${formatInteger(rangePct)}%</b>
          <span>區間高 ${formatPrice(high)}</span>
        </div>
        <i><em style="width:${rangePct}%"></em></i>
      </div>
      <div class="mini-chart-title"><b>價格走勢</b><span>紅色代表收漲，綠色代表收跌</span></div>
      <div class="stock-mini-bars price-bars">${stockMiniBars(candles, 'close')}</div>
      <div class="mini-chart-title compact">
        <div><b>成交量</b><span>每柱為日成交張數</span></div>
        <strong>${formatLotsFromShares(row.volume)}</strong>
      </div>
      <div class="stock-mini-bars volume-bars">${stockMiniBars(candles, 'volume')}</div>
      <div class="stock-brief-grid">
        <div><span>60日漲跌</span><b class="${priceTone}">${formatSignedDecimal(priceChangePct, '%')}</b></div>
        <div><span>成交張數</span><b>${formatCompact(volumeLots)}張</b></div>
        <div><span>法人淨買賣</span><b class="${instTone}">${formatCompact(instLots)}張</b></div>
        <div><span>技術判斷</span><b>${techSignal.action || '-'}</b></div>
      </div>
      <div class="stock-flow-notes">
        <span>融資增減 <b>${latestMargin.margin_change || '-'}</b></span>
        <span>融券增減 <b>${latestMargin.short_change || '-'}</b></span>
      </div>
      <div class="stock-readable-summary">
        <b>解讀</b>
        <p>${summary}</p>
      </div>
    </article>`;
}

function compactItem(row) {
  return `<article class="compact-item">
    <div class="card-head"><h3>${row.name || row.symbol}</h3><small>${row.symbol || ''}</small></div>
    ${quoteStats(row)}
    <p class="topic">${row.topic || ''}</p>
  </article>`;
}

function fxRegion(symbol = '') {
  if (symbol.includes('TWD')) return '台幣';
  if (symbol.includes('JPY') || symbol.includes('KRW') || symbol.includes('SGD') || symbol.includes('HKD') || symbol.includes('THB') || symbol.includes('CNH')) return '亞洲';
  if (symbol.includes('EUR') || symbol.includes('GBP') || symbol.includes('CHF')) return '歐洲';
  if (symbol.includes('AUD') || symbol.includes('NZD')) return '商品貨幣';
  return '外匯';
}

function fxCard(row) {
  const tone = toneClass(row.change_pct || row.change);
  const price = formatPrice(row.price);
  const change = `${formatSignedDecimal(row.change)} / ${formatSignedDecimal(row.change_pct, '%')}`;
  const pair = String(row.symbol || '').replace('=X', '');
  return `<article class="fx-card ${tone}">
    <div class="fx-card-head">
      <div>
        <span>${fxRegion(row.symbol || '')}</span>
        <h3>${row.name || pair}</h3>
        <small>${pair}</small>
      </div>
      <strong>${price}</strong>
    </div>
    <div class="fx-change ${tone}">
      <b>${change}</b>
      <span>日內漲跌</span>
    </div>
    <p>${row.topic || '每日匯率'}</p>
  </article>`;
}

function usHotVolumeCard(row, index, maxVolume) {
  const tone = toneClass(row.change_pct);
  const volumeLots = Number(row.volume || 0) / 1000;
  const pct = Math.max(5, Math.min(100, Number(row.volume || 0) / Math.max(1, maxVolume) * 100));
  return `<article class="us-volume-card">
    <div class="us-volume-rank">${index + 1}</div>
    <div class="us-volume-main">
      <div class="us-volume-head">
        <div>
          <h3>${row.name || row.symbol}</h3>
          <small>${row.symbol || ''}</small>
        </div>
        <strong class="${tone}">${formatSignedDecimal(row.change_pct, '%')}</strong>
      </div>
      <div class="us-volume-price">
        <span>股價 <b>${formatPrice(row.price)}</b></span>
        <span>漲跌 <b class="${tone}">${formatSignedDecimal(row.change)}</b></span>
        <span>成交量 <b>${formatCompact(volumeLots)}張</b></span>
      </div>
      <div class="us-volume-bar"><i><em class="${tone}" style="width:${pct}%"></em></i></div>
      <p>${row.topic || ''}</p>
    </div>
  </article>`;
}

function renderUsHotStocks(rows) {
  const sorted = (rows || []).slice().sort((a, b) => Number(b.volume || 0) - Number(a.volume || 0));
  const maxVolume = Math.max(...sorted.map((row) => Number(row.volume || 0)), 1);
  $('usHot').innerHTML = sorted.length
    ? sorted.map((row, index) => usHotVolumeCard(row, index, maxVolume)).join('')
    : '<p class="muted">美股成交量資料暫不可用</p>';
}

function marketRegion(symbol = '') {
  if (['^GSPC', '^NDX', '^DJI', '^SOX', '^RUT'].includes(symbol)) return '美股';
  if (['^N225', '^HSI'].includes(symbol)) return '亞洲';
  if (['^GDAXI', '^FTSE'].includes(symbol)) return '歐洲';
  return '全球';
}

function marketIndexCard(row) {
  const changeTone = toneClass(row.change_pct);
  const changeAbs = Math.min(100, Math.max(6, Math.abs(Number(row.change_pct || 0)) * 18));
  const volumeLots = formatLotsFromShares(row.volume);
  return `<article class="market-index-card">
    <div class="market-index-head">
      <span>${marketRegion(row.symbol)}</span>
      <small>${row.symbol || ''}</small>
    </div>
    <h3>${row.name || row.symbol}</h3>
    <div class="market-index-price">
      <b>${formatPrice(row.price)}</b>
      <strong class="${changeTone}">${formatSignedDecimal(row.change)} / ${formatSignedDecimal(row.change_pct, '%')}</strong>
    </div>
    <div class="market-index-pulse">
      <span>動能</span>
      <i><em class="${changeTone}" style="width:${changeAbs}%"></em></i>
      <b>${volumeLots}</b>
    </div>
    <p>${row.topic || ''}</p>
  </article>`;
}

function etfCard(row) {
  const score = row.score || {};
  const scoreValue = Number(score.score || 0);
  const tone = scoreValue >= 80 ? 'up' : scoreValue >= 65 ? 'flat' : 'down';
  const yieldText = score.dividend_yield === undefined ? '-' : `${formatInteger(score.dividend_yield)}%`;
  const annualCash = Number(row.annual_cash || 0) ? `${formatInteger(row.annual_cash)}元` : '-';
  const latestCash = Number(row.latest_cash || 0) ? `${formatInteger(row.latest_cash)}元` : '-';
  const scorePct = Math.max(4, Math.min(100, scoreValue || 0));
  const yieldPct = Math.max(4, Math.min(100, Number(score.dividend_yield || 0) * 8));
  const volumePct = Math.max(4, Math.min(100, Number(score.lots || 0) / 25000 * 100));
  const reasons = (score.reasons || []).map((reason) => `<span>${reason}</span>`).join('');
  return `<article class="etf-card">
    <div class="etf-card-head">
      <div>
        <small>${row.code}</small>
        <h3>${row.name}</h3>
        <p>${row.topic || ''}</p>
      </div>
      <span class="score-badge ${tone}" style="--score:${scorePct}%"><b>${scoreValue || '-'}</b><small>${score.grade || '-'}</small></span>
    </div>

    <div class="etf-hero-metrics">
      <div><b>${formatPrice(row.price)}</b><span>價格</span></div>
      <div class="${toneClass(row.change_pct)}"><b>${formatSigned(row.change_pct, '%')}</b><span>漲跌幅</span></div>
      <div><b>${yieldText}</b><span>估算殖利率</span></div>
    </div>

    <div class="etf-flow">
      <div><span>評分</span><i><em class="${tone}" style="width:${scorePct}%"></em></i><b>${scoreValue || '-'} 分</b></div>
      <div><span>殖利率</span><i><em class="up" style="width:${yieldPct}%"></em></i><b>${yieldText}</b></div>
      <div><span>成交張數</span><i><em class="flat" style="width:${volumePct}%"></em></i><b>${formatCompact(score.lots || 0)}張</b></div>
    </div>

    <div class="etf-dividend-strip">
      <span><small>近一年配息</small><b>${annualCash}</b></span>
      <span><small>最近配息</small><b>${latestCash}</b><em>${row.latest_ex_date || '-'}</em></span>
    </div>
    <div class="score-reasons">${reasons}</div>
  </article>`;
}

function dataCard(title, items) {
  return `<article class="data-card">
    <h3>${title}</h3>
    ${items.map((item) => `<div><span>${item.label}</span><b>${item.value || '-'}</b></div>`).join('')}
  </article>`;
}

function macroValue(card) {
  if (card.value === null || card.value === undefined || card.value === '') return '-';
  const unit = card.unit || '';
  const value = Number(card.value || 0).toLocaleString('zh-TW', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return `${value}${unit.includes('%') ? '%' : ''}`;
}

function macroCard(card) {
  const series = card.series || [];
  const values = series.map((row) => Number(row.value)).filter((value) => Number.isFinite(value));
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const bars = series.slice(-12).map((row) => {
    const value = Number(row.value || 0);
    const height = max === min ? 38 : 16 + ((value - min) / Math.max(1, max - min)) * 46;
    return `<i style="height:${height}px" title="${row.date || row.label || ''} ${formatInteger(value)}"></i>`;
  }).join('');
  const tone = toneClass(card.change_pct || card.change || 0);
  return `<article class="macro-card">
    <div class="macro-card-head">
      <div><h3>${card.name}</h3><small>${card.date || '-'}</small></div>
      <b class="${tone}">${macroValue(card)}</b>
    </div>
    <div class="macro-spark">${bars}</div>
    <p>${card.topic || ''}<span>${card.unit || ''}</span></p>
  </article>`;
}

function renderMacro(macro) {
  setText('macroSummary', macro?.summary ? `${macro.summary} · ${macro.source || ''}` : '美國與台灣 CPI、PPI 與主要總經指標');
  setText('macroUsSource', macro?.source || '');
  setText('macroTaiwanSource', macro?.source || '');
  $('macroUsCards').innerHTML = (macro?.us || []).map(macroCard).join('') || '<p class="muted">美國總經資料暫不可用</p>';
  $('macroTaiwanCards').innerHTML = (macro?.taiwan || []).map(macroCard).join('') || '<p class="muted">台灣總經資料暫不可用</p>';
}

function formatPercent(value) {
  if (value === null || value === undefined || value === '') return '-';
  return `${formatSignedDecimal(value, '%')}`;
}

function changeBadge(label, value) {
  if (value === null || value === undefined || value === '') {
    return `<span class="financial-change flat"><small>${label}</small><b>-</b></span>`;
  }
  const tone = toneClass(value);
  return `<span class="financial-change ${tone}"><small>${label}</small><b>${formatPercent(value)}</b></span>`;
}

function financialCard(label, value, sub = '', changes = []) {
  const changeHtml = changes.length
    ? `<div class="financial-changes">${changes.map((item) => changeBadge(item.label, item.value)).join('')}</div>`
    : `<small>${sub || ''}</small>`;
  return `<article class="financial-card">
    <span>${label}</span>
    <b>${value || '-'}</b>
    ${changeHtml}
  </article>`;
}

function renderFinancials(data) {
  const latest = data?.latest || {};
  const quarters = data?.quarters || [];
  setText('financialSource', data?.source ? `${data.source} ${latest.date || ''}` : '');
  if (!latest.date) {
    $('financialCards').innerHTML = '<p class="muted">財報資料暫不可用</p>';
    $('financialQuarters').innerHTML = '';
    return;
  }
  $('financialCards').innerHTML = [
    financialCard('營業收入', latest.revenue, '', [
      { label: 'QoQ', value: latest.revenue_qoq },
      { label: 'YoY', value: latest.revenue_yoy },
    ]),
    financialCard('毛利率', latest.gross_margin === null ? '-' : `${formatInteger(latest.gross_margin)}%`, 'Gross margin'),
    financialCard('營業利益率', latest.operating_margin === null ? '-' : `${formatInteger(latest.operating_margin)}%`, 'Operating margin'),
    financialCard('稅後淨利', latest.net_income, 'Income after tax'),
    financialCard('EPS', latest.eps === null || latest.eps === undefined ? '-' : formatPrice(latest.eps), '', [
      { label: 'QoQ', value: latest.eps_qoq },
      { label: 'YoY', value: latest.eps_yoy },
    ]),
    financialCard('淨利率', latest.net_margin === null ? '-' : `${formatInteger(latest.net_margin)}%`, 'Net margin'),
  ].join('');

  const maxEps = Math.max(...quarters.map((row) => Math.abs(Number(row.raw_eps || 0))), 1);
  $('financialQuarters').innerHTML = quarters.map((row) => {
    const eps = Number(row.raw_eps || 0);
    const width = Math.max(4, Math.abs(eps) / maxEps * 100);
    return `<article class="quarter-item">
      <div><b>${row.date}</b><span>EPS ${row.eps === null || row.eps === undefined ? '-' : formatInteger(row.eps)}</span></div>
      <div class="quarter-bar"><i class="${eps >= 0 ? 'up' : 'down'}" style="width:${width}%"></i></div>
    </article>`;
  }).join('');
}

function renderMarketMarginCards(data) {
  const rows = (data?.rows || []).filter((row) => [row.buy, row.sell, row.repay].some((value) => {
    const text = String(value || '').trim();
    return text && text !== '-';
  }));
  setText('marketMarginSource', `${data?.source || ''} ${data?.date || ''}`.trim());
  $('marketMarginCards').innerHTML = rows.length
    ? rows.map((row) => dataCard(row.title, [
      { label: '買進張數', value: row.buy },
      { label: '賣出張數', value: row.sell },
      { label: '償還張數', value: row.repay },
    ])).join('')
    : '<p class="muted">大盤融資融券資料暫不可用</p>';
}

function renderMarginBars(rows) {
  const target = $('marginCards');
  if (!rows || !rows.length) {
    target.innerHTML = '<p class="muted">融資融券資料暫不可用</p>';
    return;
  }
  const ordered = rows.slice().reverse();
  const maxAbs = Math.max(...ordered.flatMap((row) => [
    Math.abs(numberFromLarge(row.margin_change)),
    Math.abs(numberFromLarge(row.short_change)),
  ]), 1);
  target.innerHTML = ordered.map((row) => {
    const margin = numberFromLarge(row.margin_change);
    const short = numberFromLarge(row.short_change);
    return `<article class="margin-day">
      <h3>${row.date}</h3>
      <div class="margin-bar-row">
        <span>融資增減</span>
        <div class="margin-track"><i class="${margin >= 0 ? 'up' : 'down'}" style="width:${Math.max(3, Math.abs(margin) / maxAbs * 100)}%"></i></div>
        <b class="${margin >= 0 ? 'up' : 'down'}">${row.margin_change}</b>
      </div>
      <div class="margin-bar-row">
        <span>融券增減</span>
        <div class="margin-track"><i class="${short >= 0 ? 'up' : 'down'}" style="width:${Math.max(3, Math.abs(short) / maxAbs * 100)}%"></i></div>
        <b class="${short >= 0 ? 'up' : 'down'}">${row.short_change}</b>
      </div>
    </article>`;
  }).join('');
}

function renderRankingList(id, rows, tone, label) {
  const target = $(id);
  if (!rows || !rows.length) {
    target.innerHTML = '<p class="muted">資料暫不可用</p>';
    return;
  }
  const maxAbs = Math.max(...rows.map((row) => Math.abs(Number(row.raw_net || numberFromLarge(row.net_lots || row.net)))), 1);
  target.innerHTML = rows.map((row, idx) => {
    const value = Number(row.raw_net || numberFromLarge(row.net_lots || row.net));
    const pct = Math.max(6, Math.abs(value) / maxAbs * 100);
    const shown = row.net_lots || row.net || '-';
    return `<article class="ranking-item">
      <div class="rank-head">
        <b>${idx + 1}. ${row.code} ${row.name}</b>
        <span class="${tone}"><small>${label}</small>${shown}張</span>
      </div>
      <div class="rank-bar"><i class="${tone}" style="width:${pct}%"></i></div>
    </article>`;
  }).join('');
}

function renderInstitutionalSummary(rankings, futures) {
  const target = $('institutionalSummaryCards');
  const note = $('institutionalSummaryNote');
  if (!target || !note) return;
  const topBuy = (rankings?.top_buy || [])[0] || {};
  const topSell = (rankings?.top_sell || [])[0] || {};
  const futureRows = futures?.rows || [];
  const netTotal = Number(futures?.net_total || 0);
  const futureTone = netTotal > 0 ? 'up' : netTotal < 0 ? 'down' : 'flat';
  const buyText = topBuy.code ? `${topBuy.code} ${topBuy.name}` : '-';
  const sellText = topSell.code ? `${topSell.code} ${topSell.name}` : '-';
  const buyValue = topBuy.net_lots ? `${topBuy.net_lots}張` : '-';
  const sellValue = topSell.net_lots ? `${topSell.net_lots}張` : '-';
  const strongestFuture = futureRows.slice().sort((a, b) => Math.abs(Number(b.raw_net || 0)) - Math.abs(Number(a.raw_net || 0)))[0] || {};
  const futureText = strongestFuture.name
    ? `${strongestFuture.name} ${Number(strongestFuture.raw_net || 0) >= 0 ? '偏多' : '偏空'} ${strongestFuture.net || ''}`
    : '-';
  const summaryText = netTotal > 0
    ? '期貨端三大法人整體偏多，若買超排行榜同步集中在權值或高成交 ETF，代表籌碼對大盤較有支撐。'
    : netTotal < 0
      ? '期貨端三大法人整體偏空，若賣超排行榜集中在權值股，代表短線避險或調節壓力較高。'
      : '期貨端多空接近，籌碼方向暫時中性，需觀察買賣超排行是否延續。';
  setText('institutionalSummarySource', `${rankings?.source || 'TWSE T86'} ${rankings?.date || ''}`.trim());
  target.innerHTML = `
    <article class="institutional-summary-card up">
      <span>買超焦點</span>
      <b>${buyText}</b>
      <strong>${buyValue}</strong>
      <small>法人今日淨買超最大，紅色代表資金流入。</small>
    </article>
    <article class="institutional-summary-card down">
      <span>賣超焦點</span>
      <b>${sellText}</b>
      <strong>${sellValue}</strong>
      <small>法人今日淨賣超最大，綠色代表資金流出。</small>
    </article>
    <article class="institutional-summary-card ${futureTone}">
      <span>期貨方向</span>
      <b>${futures?.bias || '-'}</b>
      <strong>${futures?.open_interest || '-'}</strong>
      <small>未平倉合計，最大淨部位：${futureText}</small>
    </article>`;
  note.innerHTML = `<b>解讀</b><p>${summaryText}</p>`;
}

function renderEtfRankings(rows) {
  const sorted = (rows || []).slice().sort((a, b) => Number(b.score?.score || 0) - Number(a.score?.score || 0));
  $('etfRankList').innerHTML = sorted.length ? sorted.map((row, idx) => {
    const score = Number(row.score?.score || 0);
    const tone = score >= 80 ? 'up' : score >= 65 ? 'flat' : 'down';
    return `<article class="ranking-item">
      <div class="rank-head"><b>${idx + 1}. ${row.code} ${row.name}</b><span class="${tone}"><small>ETF 評分</small>${score || '-'} 分</span></div>
      <div class="rank-bar"><i class="${tone}" style="width:${Math.max(4, Math.min(100, score))}%"></i></div>
    </article>`;
  }).join('') : '<p class="muted">ETF 評分資料暫不可用</p>';
}

function renderFuturesCards(data) {
  const rows = data?.rows || [];
  setText('futureBias', data?.bias || '-');
  setText('futureOi', data?.open_interest || '-');
  const target = $('futuresCards');
  if (!rows.length) {
    target.innerHTML = '<p class="muted">期貨未平倉資料暫不可用</p>';
    return;
  }
  const maxOi = Math.max(...rows.flatMap((row) => [
    Math.abs(numberFromLotsText(row.long_oi)),
    Math.abs(numberFromLotsText(row.short_oi)),
  ]), 1);
  const totalNet = Number(data?.net_total || 0);
  const summaryTone = totalNet > 0 ? 'up' : totalNet < 0 ? 'down' : 'flat';
  const summaryText = totalNet > 0
    ? '三大法人整體多方未平倉高於空方，代表台指期籌碼偏多。'
    : totalNet < 0
      ? '三大法人整體空方未平倉高於多方，代表台指期籌碼偏空。'
      : '三大法人多空未平倉接近，代表台指期籌碼中性。';
  target.innerHTML = `
    <div class="future-summary-card ${summaryTone}">
      <div>
        <span>整體判讀</span>
        <b>${data?.bias || '-'}</b>
      </div>
      <p>${summaryText}</p>
      <small>資料日期 ${data?.date || '-'}，單位：${data?.unit || '口'}，統計標的：台指期 TX。</small>
    </div>
    <div class="futures-position-grid">
      ${rows.map((row) => {
        const longValue = Math.abs(numberFromLotsText(row.long_oi));
        const shortValue = Math.abs(numberFromLotsText(row.short_oi));
        const netValue = Number(row.raw_net || numberFromLotsText(row.net));
        const tone = netValue > 0 ? 'up' : netValue < 0 ? 'down' : 'flat';
        const longPct = Math.max(4, longValue / maxOi * 100);
        const shortPct = Math.max(4, shortValue / maxOi * 100);
        const netText = netValue > 0
          ? '多方口數大於空方，偏多布局。'
          : netValue < 0
            ? '空方口數大於多方，偏空避險或放空。'
            : '多空口數接近，中性觀望。';
        return `<article class="futures-position-card ${tone}">
          <div class="futures-card-head">
            <div>
              <h3>${row.name || '法人'}</h3>
              <small>${row.date || data?.date || '-'}</small>
            </div>
            <strong>${row.net || '-'}</strong>
          </div>
          <div class="future-bars">
            <div class="future-bar-line">
              <span>多方未平倉</span>
              <i><em class="up" style="width:${longPct}%"></em></i>
              <b>${row.long_oi || '-'}</b>
            </div>
            <div class="future-bar-line">
              <span>空方未平倉</span>
              <i><em class="down" style="width:${shortPct}%"></em></i>
              <b>${row.short_oi || '-'}</b>
            </div>
          </div>
          <div class="future-readout">
            <span>淨部位</span>
            <b class="${tone}">${row.net || '-'}</b>
            <p>${netText}</p>
          </div>
        </article>`;
      }).join('')}
    </div>`;
}

function renderYieldCurve(rows) {
  const target = $('yieldCurve');
  const values = (rows || []).map((row) => Number(row.yield)).filter((value) => Number.isFinite(value));
  if (!values.length) {
    target.innerHTML = '<p class="muted">殖利率資料暫不可用</p>';
    return;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  target.innerHTML = rows.map((row) => {
    const value = Number(row.yield || 0);
    const height = max === min ? 48 : 24 + ((value - min) / (max - min)) * 86;
    return `<div class="curve-point"><span>${formatInteger(value)}%</span><i style="height:${height}px"></i><b>${row.tenor}</b></div>`;
  }).join('');
}

function bondEtfCard(row) {
  const pct = Number(row.change_pct || 0);
  const tone = toneClass(pct);
  const pulse = Math.max(6, Math.min(100, Math.abs(pct) * 20));
  return `<article class="bond-etf-card">
    <div class="bond-etf-head">
      <div><h3>${row.name || row.symbol}</h3><small>${row.symbol || ''}</small></div>
      <b class="${tone}">${formatSigned(pct, '%')}</b>
    </div>
    <div class="bond-price-row">
      <strong>${formatPrice(row.price)}</strong>
      <span>${formatLotsFromShares(row.volume)}</span>
    </div>
    <div class="bond-pulse"><i><em class="${tone}" style="width:${pulse}%"></em></i></div>
    <p>${row.topic || ''}</p>
  </article>`;
}

function renderIndicators(id, indicators) {
  const kd = indicators?.kd || {};
  const macd = indicators?.macd || {};
  $(id).innerHTML = [
    ['K', kd.k], ['D', kd.d], ['RSI', indicators?.rsi],
    ['DIF', macd.dif], ['DEA', macd.dea], ['MACD', macd.histogram],
  ].map(([label, value]) => `<div><b>${formatInteger(value)}</b><span>${label}</span></div>`).join('');
}

function computeGuideLines(candles) {
  const valid = (candles || []).filter((row) => Number(row.high) && Number(row.low) && Number(row.close));
  if (valid.length < 3) return null;
  const recent = valid.slice(-Math.min(30, valid.length));
  const offset = valid.length - recent.length;
  const support = Math.min(...recent.map((row) => Number(row.low)));
  const resistance = Math.max(...recent.map((row) => Number(row.high)));
  const swingLows = recent.map((row, idx) => ({ index: offset + idx, value: Number(row.low) })).filter((point, idx, arr) => {
    const prev = arr[Math.max(0, idx - 1)].value;
    const next = arr[Math.min(arr.length - 1, idx + 1)].value;
    return point.value <= prev && point.value <= next;
  });
  const lows = swingLows.length >= 2 ? swingLows : recent.map((row, idx) => ({ index: offset + idx, value: Number(row.low) }));
  let start = lows[0];
  let end = lows[lows.length - 1];
  for (let idx = lows.length - 1; idx > 0; idx -= 1) {
    const current = lows[idx];
    const previous = lows.slice(0, idx).reverse().find((point) => current.index - point.index >= 3 && current.value >= point.value);
    if (previous) {
      start = previous;
      end = current;
      break;
    }
  }
  const slope = (end.value - start.value) / Math.max(1, end.index - start.index);
  const trendEndIndex = valid.length - 1;
  return {
    support,
    resistance,
    trendStart: start.value,
    trendStartIndex: start.index,
    trendAnchor: end.value,
    trendAnchorIndex: end.index,
    trendEnd: start.value + slope * (trendEndIndex - start.index),
    trendEndIndex,
    trendTone: slope > 0 ? '上升' : slope < 0 ? '下降' : '盤整',
    window: recent.length,
  };
}

function drawGuideLine(ctx, y, label, value, color, width, pad) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1.4;
  ctx.setLineDash([6, 5]);
  ctx.beginPath();
  ctx.moveTo(pad.left, y);
  ctx.lineTo(width - pad.right, y);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.font = '12px Segoe UI, Arial';
  ctx.textAlign = 'right';
  ctx.fillText(`${label} ${formatInteger(value)}`, width - pad.right - 4, y - 6);
  ctx.restore();
}

function renderLineGuide(id, guide) {
  const target = $(id);
  if (!guide) {
    target.innerHTML = '<p class="muted">支撐、壓力與趨勢資料不足</p>';
    return;
  }
  target.innerHTML = `
    <div class="guide-item support"><b>支撐線</b><span>近 ${guide.window} 根 K 線低點，約 ${formatInteger(guide.support)}</span></div>
    <div class="guide-item resistance"><b>壓力線</b><span>近 ${guide.window} 根 K 線高點，約 ${formatInteger(guide.resistance)}</span></div>
    <div class="guide-item trend"><b>趨勢線</b><span>沿低點 K 棒連線，目前偏 ${guide.trendTone}</span></div>`;
}

function renderTradeLevels(targetId, candles, price) {
  const target = $(targetId);
  if (!target) return;
  const guide = computeGuideLines(candles || []);
  const current = Number(price || 0);
  if (!guide || !current) {
    target.innerHTML = '<p class="muted">買賣點位需要足夠 K 線資料</p>';
    return;
  }
  const buyLow = guide.support;
  const buyHigh = guide.support * 1.01;
  const sellLow = guide.resistance * 0.99;
  const sellHigh = guide.resistance;
  const stopLoss = guide.support * 0.97;
  const distanceToBuy = (current - buyHigh) / current * 100;
  const distanceToSell = (sellLow - current) / current * 100;
  const buyNote = current <= buyHigh
    ? '接近支撐，可小量分批。'
    : `距離買入區約 ${formatSignedDecimal(-distanceToBuy, '%')}。`;
  const sellNote = current >= sellLow
    ? '接近壓力，留意減碼。'
    : `距離賣出區約 ${formatSignedDecimal(distanceToSell, '%')}。`;
  target.innerHTML = `
    <div class="trade-level-card buy">
      <span>分批買入區</span>
      <b>${formatInteger(buyLow)} - ${formatInteger(buyHigh)}</b>
      <small>參考支撐線，跌到附近再分批，不追高。</small>
      <p>${buyNote}</p>
    </div>
    <div class="trade-level-card sell">
      <span>減碼 / 賣出區</span>
      <b>${formatInteger(sellLow)} - ${formatInteger(sellHigh)}</b>
      <small>參考壓力線，接近前高壓力先控風險。</small>
      <p>${sellNote}</p>
    </div>
    <div class="trade-level-card stop">
      <span>跌破停損線</span>
      <b>${formatInteger(stopLoss)}</b>
      <small>跌破支撐 3% 視為支撐失守。</small>
      <p>若收盤跌破，降低部位或停止加碼。</p>
    </div>`;
}

function renderMarketTradeLevels(candles, price) {
  renderTradeLevels('marketTradeLevels', candles, price);
}

function renderKline(canvasId, guideId, candles) {
  const canvas = $(canvasId);
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(320, rect.width || canvas.clientWidth || 720);
  const height = 360;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  if (!candles || !candles.length) {
    ctx.fillStyle = '#6b7280';
    ctx.fillText('K 線資料暫不可用', 18, 32);
    renderLineGuide(guideId, null);
    return;
  }

  const guide = computeGuideLines(candles);
  const pad = { left: 52, right: 18, top: 18, bottom: 28 };
  const volumeH = 58;
  const gap = 16;
  const priceH = height - pad.top - pad.bottom - volumeH - gap;
  const chartW = width - pad.left - pad.right;
  const guidePrices = guide ? [guide.support, guide.resistance, guide.trendStart, guide.trendAnchor, guide.trendEnd] : [];
  const maxPrice = Math.max(...candles.map((row) => Number(row.high)), ...guidePrices);
  const minPrice = Math.min(...candles.map((row) => Number(row.low)), ...guidePrices);
  const maxVol = Math.max(...candles.map((row) => Number(row.volume || 0)), 1);
  const scaleY = (price) => pad.top + (maxPrice - price) / Math.max(1, maxPrice - minPrice) * priceH;
  const volumeBase = pad.top + priceH + gap + volumeH;
  const step = chartW / candles.length;
  const bodyW = Math.max(3, Math.min(11, step * 0.56));

  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad.top + priceH * i / 4;
    const price = maxPrice - (maxPrice - minPrice) * i / 4;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillStyle = '#64748b';
    ctx.font = '12px Segoe UI, Arial';
    ctx.fillText(formatInteger(price), 8, y + 4);
  }

  candles.forEach((row, idx) => {
    const x = pad.left + idx * step + step / 2;
    const open = Number(row.open);
    const high = Number(row.high);
    const low = Number(row.low);
    const close = Number(row.close);
    const up = close >= open;
    const color = up ? '#d0443f' : '#0b8a62';
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, scaleY(high));
    ctx.lineTo(x, scaleY(low));
    ctx.stroke();
    const top = scaleY(Math.max(open, close));
    const bottom = scaleY(Math.min(open, close));
    ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(2, bottom - top));

    const volH = Number(row.volume || 0) / maxVol * volumeH;
    ctx.fillStyle = up ? 'rgba(208,68,63,.35)' : 'rgba(11,138,98,.35)';
    ctx.fillRect(x - bodyW / 2, volumeBase - volH, bodyW, Math.max(1, volH));
  });

  if (guide) {
    drawGuideLine(ctx, scaleY(guide.resistance), '壓力', guide.resistance, '#a36d12', width, pad);
    drawGuideLine(ctx, scaleY(guide.support), '支撐', guide.support, '#1f5f99', width, pad);
    const startX = pad.left + guide.trendStartIndex * step + step / 2;
    const endX = pad.left + guide.trendEndIndex * step + step / 2;
    ctx.strokeStyle = '#6554a6';
    ctx.fillStyle = '#6554a6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(startX, scaleY(guide.trendStart));
    ctx.lineTo(endX, scaleY(guide.trendEnd));
    ctx.stroke();
    ctx.font = '12px Segoe UI, Arial';
    ctx.fillText(`趨勢 ${guide.trendTone}`, Math.min(endX + 6, width - 86), scaleY(guide.trendEnd) - 6);
  }

  ctx.fillStyle = '#64748b';
  ctx.font = '12px Segoe UI, Arial';
  ctx.fillText('成交量（張）', pad.left, pad.top + priceH + 12);
  ctx.fillText(candles[0]?.date || '', pad.left, height - 9);
  ctx.fillText(candles.at(-1)?.date || '', Math.max(pad.left, width - pad.right - 86), height - 9);
  renderLineGuide(guideId, guide);
}

function renderTechnical(prefix, panel) {
  if (!panel) return;
  const indicators = panel.indicators || {};
  const signal = indicators.signal || {};
  setText(`${prefix}TechSource`, `${panel.symbol || ''} · ${panel.source || ''}`);
  renderKline(`${prefix}Kline`, `${prefix}LineGuide`, panel.candles || []);
  if (prefix === 'stock') {
    const candles = panel.candles || [];
    const latest = candles.at(-1);
    renderTradeLevels('stockTradeLevels', candles, latest?.close);
  }
  renderIndicators(`${prefix}Indicators`, indicators);
  setText(`${prefix}TechSignal`, signal.action || '-');
  $(`${prefix}TechSignal`).className = `signal compact-signal ${signal.tone === 'buy' ? 'up' : signal.tone === 'sell' ? 'down' : 'flat'}`;
  $(`${prefix}TechReasons`).innerHTML = (signal.reasons || []).map((reason) => `<li>${reason}</li>`).join('');
}

function renderInstitutionalChart(rows) {
  const canvas = $('institutionalChart');
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(320, rect.width || canvas.clientWidth || 720);
  const height = 320;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, width, height);
  if (!rows || !rows.length) {
    ctx.fillStyle = '#64748b';
    ctx.fillText('法人資料暫不可用', 18, 32);
    return;
  }
  const grouped = {};
  rows.forEach((row) => {
    grouped[row.name] = (grouped[row.name] || 0) + Number(row.raw_net || numberFromLarge(row.net));
  });
  const entries = Object.entries(grouped);
  const maxAbs = Math.max(...entries.map(([, value]) => Math.abs(value)), 1);
  ctx.font = '13px Segoe UI, Arial';
  const valueLabels = entries.map(([, value]) => `${formatCompact(value)}張`);
  const maxLabelW = Math.max(...valueLabels.map((label) => ctx.measureText(label).width), 44);
  const pad = { left: 112, right: maxLabelW + 22, top: 22, bottom: 18 };
  const rowH = (height - pad.top - pad.bottom) / entries.length;
  const centerX = pad.left + (width - pad.left - pad.right) / 2;
  ctx.strokeStyle = '#d9e2ec';
  ctx.beginPath();
  ctx.moveTo(centerX, pad.top - 4);
  ctx.lineTo(centerX, height - pad.bottom);
  ctx.stroke();
  entries.forEach(([name, value], idx) => {
    const y = pad.top + idx * rowH + rowH * 0.5;
    const barW = Math.abs(value) / maxAbs * ((width - pad.left - pad.right) / 2 - 12);
    const label = `${formatCompact(value)}張`;
    ctx.fillStyle = '#17202b';
    ctx.font = '13px Segoe UI, Arial';
    ctx.textAlign = 'left';
    ctx.fillText(name, 10, y + 4);
    ctx.fillStyle = value >= 0 ? '#d0443f' : '#0b8a62';
    if (value >= 0) ctx.fillRect(centerX, y - 9, barW, 18);
    else ctx.fillRect(centerX - barW, y - 9, barW, 18);
    if (value >= 0) {
      const labelX = Math.min(centerX + barW + 6, width - 10);
      ctx.textAlign = labelX >= width - maxLabelW - 12 ? 'right' : 'left';
      ctx.fillText(label, labelX, y + 4);
    } else {
      const labelX = Math.max(centerX - barW - 6, pad.left + maxLabelW + 6);
      ctx.textAlign = labelX <= pad.left + maxLabelW + 8 ? 'left' : 'right';
      ctx.fillText(label, labelX, y + 4);
    }
  });
}

function showStockPanels(hasStock) {
  $('stockLoadingPanel').hidden = true;
  $('stockEmptyPanel').hidden = hasStock;
  document.querySelectorAll('.stock-only').forEach((node) => {
    node.hidden = !hasStock;
  });
  setText('stockSectionHint', hasStock ? `${currentDashboard.stock_id} 個股資料` : '搜尋股票代號後才顯示');
}

function showStockLoading(stock) {
  setActiveSection('stockSection');
  $('stockEmptyPanel').hidden = true;
  $('stockLoadingPanel').hidden = false;
  document.querySelectorAll('.stock-only').forEach((node) => {
    node.hidden = true;
  });
  setText('stockSectionHint', `${stock} 搜尋中`);
  setText('stockLoadingText', `正在抓取 ${stock} 的報價、K 線、法人與融資融券資料`);
}

function renderDashboard(data) {
  currentDashboard = data;
  const quote = data.market?.quote || {};
  const signal = data.market?.signal || {};
  const marketCandles = data.technical?.market?.candles || [];
  const latestMarketCandle = marketCandles.at(-1) || {};
  const displayMarketPrice = Number(quote.price || 0) || Number(latestMarketCandle.close || 0);
  const displayMarketChange = Number(quote.change || 0);
  const displayMarketPct = Number(quote.change_pct || 0);
  setText('updatedAt', data.updated_at || '-');
  setText('marketPrice', formatInteger(displayMarketPrice));
  setText('headerMarketValue', formatInteger(displayMarketPrice));
  setText('headerUpdated', data.updated_at ? `更新 ${data.updated_at}` : '-');
  setText('marketDelta', `${formatSignedDecimal(displayMarketChange)} / ${formatSignedDecimal(displayMarketPct, '%')}`);
  $('marketDelta').className = `delta ${toneClass(displayMarketPct)}`;
  marketQuickStats((data.market?.series || []).length ? data.market.series : marketCandles);
  setText('signalAction', signal.action || '-');
  $('signalAction').className = `signal ${signal.tone === 'buy' ? 'up' : signal.tone === 'sell' ? 'down' : 'flat'}`;
  $('signalReasons').innerHTML = (signal.reasons || []).map((reason) => `<li>${reason}</li>`).join('');
  renderMarketTradeLevels(marketCandles, displayMarketPrice);
  setText('marketSource', data.market?.trade?.source || '');
  setText('tradeValue', formatMoneyTwd(data.market?.trade?.trade_value));
  setMetric('tradeVolume', data.market?.trade?.volume, 1000, '張');
  setMetric('transactions', data.market?.trade?.transactions, 10000, '萬筆');
  renderMarketMarginCards(data.market_margin || {});
  renderTechnical('market', data.technical?.market);

  const hasStock = Boolean(data.stock_searched);
  showStockPanels(hasStock);
  $('quotes').innerHTML = hasStock ? stockOverview(data) : '';
  if (hasStock) {
    renderFinancials(data.financials || {});
    renderTechnical('stock', data.technical?.stock);
    setText('instSummary', `${data.institutional?.stock_id || ''} · ${data.institutional?.summary || ''}`);
    renderInstitutionalChart(data.institutional?.rows || []);
    renderMarginBars(data.margin?.rows || []);
  }

  const etfRows = data.hot_etfs?.rows || [];
  setText('etfSource', data.hot_etfs?.source || '');
  setText('etfUnit', data.hot_etfs?.unit || '評分與配息');
  $('hotEtfs').innerHTML = etfRows.length ? etfRows.map(etfCard).join('') : '<p class="muted">ETF 資料暫不可用</p>';
  renderEtfRankings(etfRows);

  const rankings = data.institutional_rankings || {};
  setText('topBuySource', `${rankings.source || ''} ${rankings.date || ''}`.trim());
  setText('topSellSource', `${rankings.source || ''} ${rankings.date || ''}`.trim());
  renderInstitutionalSummary(rankings, data.futures || {});
  renderRankingList('topBuyList', rankings.top_buy || [], 'up', '買超張數');
  renderRankingList('topSellList', rankings.top_sell || [], 'down', '賣超張數');
  renderFuturesCards(data.futures || {});

  const bonds = data.bonds || {};
  setText('bondSource', bonds.curve?.source || '');
  setText('bond10y', bonds.curve?.ten_year ? `${formatInteger(bonds.curve.ten_year)}%` : '-');
  setText('bond2s10s', bonds.curve?.spread_2s10s ? `${formatSigned(bonds.curve.spread_2s10s)}bp` : '-');
  setText('bond3m10y', bonds.curve?.spread_3m10y ? `${formatSigned(bonds.curve.spread_3m10y)}bp` : '-');
  renderYieldCurve(bonds.curve?.rows || []);
  setText('bondSignal', bonds.signal?.action || '-');
  $('bondSignal').className = `signal compact-signal ${bonds.signal?.tone === 'buy' ? 'up' : bonds.signal?.tone === 'sell' ? 'down' : 'flat'}`;
  $('bondReasons').innerHTML = (bonds.signal?.reasons || []).map((reason) => `<li>${reason}</li>`).join('');
  $('bondEtfs').innerHTML = (bonds.etfs || []).map(bondEtfCard).join('');
  $('twBondEtfs').innerHTML = (bonds.tw_etfs || []).map(bondEtfCard).join('');
  $('bondNotes').innerHTML = (bonds.notes || []).map((note) => `<li>${note}</li>`).join('');

  renderMacro(data.macro || {});
  $('globalMarkets').innerHTML = (data.global_markets || []).map(marketIndexCard).join('');
  $('currencies').innerHTML = (data.currencies || []).map(fxCard).join('');
  renderUsHotStocks(data.us_hot || []);
  redrawVisibleCharts();
}

async function loadDashboard(stock = '') {
  const searchedStock = stock.trim();
  document.body.classList.add('loading');
  $('reloadBtn').disabled = true;
  $('reloadBtn').textContent = searchedStock ? '搜尋中' : '更新中';
  if (searchedStock) showStockLoading(searchedStock);
  try {
    const query = searchedStock ? `?stock=${encodeURIComponent(searchedStock)}` : '';
    const response = await fetch(`/api/dashboard${query}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderDashboard(data);
    if (searchedStock) setActiveSection('stockSection');
  } catch (error) {
    console.error(error);
    $('stockLoadingPanel').hidden = true;
    if (searchedStock) {
      $('stockEmptyPanel').hidden = false;
      setText('stockSectionHint', `${searchedStock} 搜尋失敗`);
    }
    alert('資料載入失敗，請稍後再試');
  } finally {
    document.body.classList.remove('loading');
    $('reloadBtn').disabled = false;
    $('reloadBtn').textContent = '搜尋';
  }
}

function redrawVisibleCharts() {
  if (!currentDashboard) return;
  if (activeSection === 'overviewSection') renderTechnical('market', currentDashboard.technical?.market);
  if (activeSection === 'stockSection' && currentDashboard.stock_searched) {
    renderTechnical('stock', currentDashboard.technical?.stock);
    renderInstitutionalChart(currentDashboard.institutional?.rows || []);
  }
}

window.appSetActiveSection = setActiveSection;
window.appLoadDashboard = () => loadDashboard($('stockInput').value.trim());

document.addEventListener('click', (event) => {
  const tabButton = event.target.closest?.('.tab-button');
  if (tabButton?.dataset?.target) {
    event.preventDefault();
    setActiveSection(tabButton.dataset.target);
    return;
  }
  if (event.target.closest?.('#reloadBtn')) {
    event.preventDefault();
    window.appLoadDashboard();
  }
});

$('stockInput').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') window.appLoadDashboard();
});
window.addEventListener('resize', () => window.setTimeout(redrawVisibleCharts, 100));

loadDashboard();
