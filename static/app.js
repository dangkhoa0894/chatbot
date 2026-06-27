(() => {
  const EMOJI = { laptop: '💻', phone: '📱', tablet: '📟', default: '📦' };
  const SESSION_KEY = 'techshop_session_id';

  let ws = null;
  let sessionId = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT = 5;

  const BOT_SVG = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 100 20A10 10 0 0012 2zm-1 13H9V9h2v6zm4 0h-2V9h2v6z"/></svg>`;

  // DOM refs
  const messagesEl = document.getElementById('chat-messages');
  const inputEl    = document.getElementById('msg-input');
  const sendBtn    = document.getElementById('send-btn');
  const sessionLabel = document.getElementById('session-label');
  const connBanner   = document.getElementById('conn-banner');

  // ── Textarea auto-resize ───────────────────────────────────────────────────
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  });

  // ── WebSocket ──────────────────────────────────────────────────────────────
  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const savedId  = localStorage.getItem(SESSION_KEY) || '';
    const url = savedId
      ? `${protocol}://${location.host}/ws?session_id=${encodeURIComponent(savedId)}`
      : `${protocol}://${location.host}/ws`;

    ws = new WebSocket(url);
    setBanner('connecting', 'Đang kết nối...');

    ws.onopen = () => {
      reconnectAttempts = 0;
      setBanner(null);
      setSendEnabled(true);
    };

    ws.onmessage = (evt) => {
      let data;
      try { data = JSON.parse(evt.data); } catch { return; }
      handleServerEvent(data);
    };

    ws.onclose = () => {
      setSendEnabled(false);
      if (reconnectAttempts < MAX_RECONNECT) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts, 15000);
        reconnectAttempts++;
        setBanner('disconnected', `Mất kết nối — thử lại sau ${Math.round(delay / 1000)}s...`);
        setTimeout(connect, delay);
      } else {
        setBanner('disconnected', 'Không thể kết nối. Hãy tải lại trang.');
      }
    };

    ws.onerror = () => ws.close();
  }

  function handleServerEvent(data) {
    switch (data.type) {
      case 'connected':
        sessionId = data.session_id;
        localStorage.setItem(SESSION_KEY, sessionId);
        sessionLabel.textContent = sessionId.slice(0, 8);

        if (data.resumed && data.history?.length) {
          renderHistory(data.history);
        } else {
          appendBotMessage(data.message);
        }
        break;

      case 'typing':
        if (data.is_typing) showTyping(); else hideTyping();
        break;

      case 'token':
        handleStreamToken(data.delta);
        break;

      case 'message':
        finalizeStream(data.content, data.metadata);
        setSendEnabled(true);
        break;

      case 'csat_prompt':
        showCsatWidget(data.context, data.turn_count);
        break;

      case 'error':
        hideTyping();
        clearStream();
        setSendEnabled(true);
        appendBotMessage(`⚠️ ${data.content}`);
        break;
    }
  }

  // ── Send ───────────────────────────────────────────────────────────────────
  function send(text) {
    text = (text !== undefined ? text : inputEl.value).trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN || sendBtn.disabled) return;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    appendUserMessage(text);
    setSendEnabled(false);
    ws.send(JSON.stringify({ message: text }));
  }

  window.send = send;

  // ── Render helpers ─────────────────────────────────────────────────────────
  function appendUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'message user';
    el.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
    messagesEl.appendChild(el);
    scrollBottom();
  }

  function appendBotMessage(text, meta) {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-self:flex-start;animation:fadeSlide 0.2s ease;max-width:85%';

    const el = document.createElement('div');
    el.className = 'message bot';
    el.innerHTML = `
      <div class="msg-avatar">${BOT_SVG}</div>
      <div class="bubble">${formatText(text)}</div>`;
    wrap.appendChild(el);

    if (meta?.products?.length) wrap.appendChild(buildProductCards(meta.products));
    if (meta?.order?.status === 'confirmed') wrap.appendChild(buildOrderCard(meta.order));

    messagesEl.appendChild(wrap);
    scrollBottom();
  }

  function renderHistory(history) {
    history.forEach(msg => {
      if (msg.role === 'user') {
        const el = document.createElement('div');
        el.className = 'message user';
        el.innerHTML = `<div class="bubble">${escHtml(msg.content)}</div>`;
        messagesEl.appendChild(el);
      } else if (msg.role === 'assistant') {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-self:flex-start;max-width:85%';
        const el = document.createElement('div');
        el.className = 'message bot';
        el.innerHTML = `<div class="msg-avatar">${BOT_SVG}</div><div class="bubble">${formatText(msg.content)}</div>`;
        wrap.appendChild(el);
        messagesEl.appendChild(wrap);
      }
    });

    const divider = document.createElement('div');
    divider.className = 'history-divider';
    divider.textContent = 'Hội thoại đã được khôi phục';
    messagesEl.appendChild(divider);

    scrollBottom();
  }

  function buildProductCards(products) {
    const grid = document.createElement('div');
    grid.className = 'product-cards';

    products.forEach((p, idx) => {
      const cat  = detectCategory(p);
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <div class="card-emoji">${EMOJI[cat] || EMOJI.default}</div>
        <div class="card-name">${escHtml(p.name)}</div>
        <div class="card-price">${escHtml(p.price_display)}</div>
        <div class="card-rating">⭐ ${p.rating} · Còn ${p.stock}</div>
        ${idx === 0 ? '<span class="card-badge">Đề xuất</span>' : ''}`;
      card.onclick = () => send(`Cho tôi biết thêm về ${p.name}`);
      grid.appendChild(card);
    });

    return grid;
  }

  function buildOrderCard(order) {
    const div = document.createElement('div');
    div.className = 'order-card';
    div.innerHTML = `
      <h3>🎉 Đặt hàng thành công!</h3>
      <div class="order-row">Mã đơn: <span class="order-id">#${escHtml(order.order_id || '')}</span></div>
      <div class="order-row">📍 Giao đến: ${escHtml(order.address || '')}</div>
      <div class="order-row">📅 Dự kiến: 2–3 ngày làm việc</div>
      <div class="order-row">💳 Thanh toán: COD khi nhận hàng</div>`;
    return div;
  }

  // ── Typing indicator ───────────────────────────────────────────────────────
  let typingEl = null;

  function showTyping() {
    if (typingEl || streamingWrap) return;
    const row = document.createElement('div');
    row.className = 'message bot';
    row.innerHTML = `
      <div class="msg-avatar">${BOT_SVG}</div>
      <div class="typing-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
    typingEl = row;
    messagesEl.appendChild(typingEl);
    scrollBottom();
  }

  function hideTyping() {
    if (typingEl) { typingEl.remove(); typingEl = null; }
  }

  // ── Streaming ──────────────────────────────────────────────────────────────
  let streamingWrap    = null;
  let streamingContent = null;
  let streamingText    = '';

  function handleStreamToken(delta) {
    hideTyping();
    if (!streamingWrap) {
      streamingWrap = document.createElement('div');
      streamingWrap.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-self:flex-start;animation:fadeSlide 0.2s ease;max-width:85%';
      const el = document.createElement('div');
      el.className = 'message bot';
      el.innerHTML = `<div class="msg-avatar">${BOT_SVG}</div><div class="bubble"><span class="stream-text"></span><span class="stream-cursor">▍</span></div>`;
      streamingWrap.appendChild(el);
      messagesEl.appendChild(streamingWrap);
      streamingContent = el.querySelector('.stream-text');
    }
    streamingText += delta;
    streamingContent.innerHTML = formatText(streamingText);
    scrollBottom();
  }

  function finalizeStream(fullText, meta) {
    if (streamingWrap) {
      streamingWrap.remove();
      streamingWrap = null; streamingContent = null; streamingText = '';
    }
    hideTyping();
    appendBotMessage(fullText, meta);
  }

  function clearStream() {
    if (streamingWrap) {
      streamingWrap.remove();
      streamingWrap = null; streamingContent = null; streamingText = '';
    }
  }

  // ── Session clear ──────────────────────────────────────────────────────────
  window.clearSession = async () => {
    if (!confirm('Xóa toàn bộ cuộc trò chuyện?')) return;
    if (sessionId) {
      await fetch(`/api/session/${sessionId}`, { method: 'DELETE' }).catch(() => {});
    }
    localStorage.removeItem(SESSION_KEY);
    messagesEl.innerHTML = '';
    sessionId = null;
    ws?.close();
    setTimeout(connect, 200);
  };

  // ── Utilities ──────────────────────────────────────────────────────────────
  function scrollBottom() {
    requestAnimationFrame(() => { messagesEl.scrollTop = messagesEl.scrollHeight; });
  }

  function setSendEnabled(enabled) {
    sendBtn.disabled  = !enabled;
    inputEl.disabled  = !enabled;
    sendBtn.innerHTML = enabled
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 2L15 22 11 13 2 9l20-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
      : '<span class="btn-spinner"></span>';
  }

  function setBanner(type, text) {
    if (!type) { connBanner.className = 'conn-banner'; connBanner.textContent = ''; return; }
    connBanner.className = `conn-banner show ${type}`;
    connBanner.textContent = text;
  }

  function detectCategory(product) {
    const n = (product.name || '').toLowerCase();
    if (n.includes('macbook') || n.includes('laptop') || n.includes('thinkpad') ||
        n.includes('dell') || n.includes('asus') || n.includes('hp ') || n.includes('acer')) return 'laptop';
    if (n.includes('ipad') || n.includes('tab') || n.includes('pad')) return 'tablet';
    return 'phone';
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatText(text) {
    return escHtml(text)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/━+/g, '<hr style="border:none;border-top:1px solid #e4e4e7;margin:8px 0">')
      .replace(/\n/g, '<br>');
  }

  // ── CSAT widget ───────────────────────────────────────────────────────────
  let _csatContext   = '';
  let _csatTurnCount = 0;
  let _csatSubmitted = false;

  function showCsatWidget(context, turnCount) {
    if (_csatSubmitted) return;
    _csatContext   = context;
    _csatTurnCount = turnCount;

    const widget = document.createElement('div');
    widget.id = 'csat-widget';
    widget.className = 'csat-widget';
    widget.innerHTML = `
      <div class="csat-title">Bạn hài lòng với trải nghiệm không?</div>
      <div class="csat-buttons">
        <button class="csat-btn" onclick="submitCsat(5)">👍 Hài lòng</button>
        <button class="csat-btn" onclick="submitCsat(1)">👎 Chưa hài lòng</button>
      </div>
      <button class="csat-skip" onclick="dismissCsat()">Bỏ qua</button>`;
    messagesEl.appendChild(widget);
    scrollBottom();
  }

  window.submitCsat = async function(rating) {
    if (_csatSubmitted) return;
    _csatSubmitted = true;
    const widget = document.getElementById('csat-widget');
    if (widget) {
      widget.innerHTML = `<div class="csat-thanks">${rating === 5 ? '🙏 Cảm ơn bạn đã đánh giá!' : '🙏 Cảm ơn! Chúng tôi sẽ cải thiện.'}</div>`;
      setTimeout(() => widget.remove(), 3000);
    }
    try {
      await fetch('/api/csat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, rating, context: _csatContext, turn_count: _csatTurnCount }),
      });
    } catch { /* best-effort */ }
  };

  window.dismissCsat = function() {
    _csatSubmitted = true;
    document.getElementById('csat-widget')?.remove();
  };

  // ── Event listeners ────────────────────────────────────────────────────────
  sendBtn.addEventListener('click', () => send());
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  // ── Init ───────────────────────────────────────────────────────────────────
  setSendEnabled(false);
  connect();
})();
