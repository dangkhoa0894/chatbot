(() => {
  const CAT_ICON = { laptop: '💻', phone: '📱', tablet: '📟', default: '📦' };
  const SESSION_KEY = 'techshop_session_id';

  let ws = null;
  let sessionId = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT = 5;

  const BOT_AVATAR_SVG = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M8 9.5C8 8.12 9.12 7 10.5 7S13 8.12 13 9.5 11.88 12 10.5 12 8 10.88 8 9.5z" fill="white" opacity="0.95"/>
      <path d="M12.5 15.5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5S16.38 18 15 18s-2.5-1.12-2.5-2.5z" fill="white" opacity="0.95"/>
      <path d="M10.5 12v1.5M13 9.5h2" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
    </svg>`;

  const SEND_ICON = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 19V5M5 12l7-7 7 7" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;

  // DOM refs
  const messagesEl  = document.getElementById('chat-messages');
  const inputEl     = document.getElementById('msg-input');
  const sendBtn     = document.getElementById('send-btn');
  const sessionLabel = document.getElementById('session-label');
  const connBanner   = document.getElementById('conn-banner');
  const welcomeEl    = document.getElementById('welcome-state');

  // ── Textarea auto-resize ─────────────────────────────────────────
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
    // enable send if there's text
    sendBtn.disabled = !inputEl.value.trim() || !ws || ws.readyState !== WebSocket.OPEN;
  });

  // ── WebSocket ────────────────────────────────────────────────────
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
    };

    ws.onmessage = (evt) => {
      let data;
      try { data = JSON.parse(evt.data); } catch { return; }
      handleEvent(data);
    };

    ws.onclose = () => {
      setInputEnabled(false);
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

  function handleEvent(data) {
    switch (data.type) {
      case 'connected':
        sessionId = data.session_id;
        localStorage.setItem(SESSION_KEY, sessionId);
        sessionLabel.textContent = sessionId.slice(0, 8);
        setInputEnabled(true);

        if (data.resumed && data.history?.length) {
          renderHistory(data.history);
        } else {
          appendBot(data.message);
        }
        break;

      case 'typing':
        if (data.is_typing) showTyping(); else hideTyping();
        break;

      case 'token':
        handleToken(data.delta);
        break;

      case 'message':
        finalizeStream(data.content, data.metadata);
        setInputEnabled(true);
        break;

      case 'csat_prompt':
        showCsat(data.context, data.turn_count);
        break;

      case 'error':
        hideTyping();
        clearStream();
        setInputEnabled(true);
        appendBot(`⚠️ ${data.content}`);
        break;
    }
  }

  // ── Send ─────────────────────────────────────────────────────────
  function send(text) {
    text = (text !== undefined ? text : inputEl.value).trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    sendBtn.disabled = true;
    hideWelcome();
    appendUser(text);
    setInputEnabled(false);
    ws.send(JSON.stringify({ message: text }));
  }
  window.send = send;

  // ── Render: user ─────────────────────────────────────────────────
  function appendUser(text) {
    const turn = document.createElement('div');
    turn.className = 'msg-turn user';
    turn.innerHTML = `<div class="user-bubble">${escHtml(text)}</div>`;
    messagesEl.appendChild(turn);
    scrollBottom();
  }

  // ── Render: bot ──────────────────────────────────────────────────
  function makeBotTurn(html) {
    const turn = document.createElement('div');
    turn.className = 'msg-turn bot';
    turn.innerHTML = `
      <div class="msg-avatar">${BOT_AVATAR_SVG}</div>
      <div class="msg-body"><div class="text">${html}</div></div>`;
    return turn;
  }

  function appendBot(text, meta) {
    hideWelcome();
    const turn = makeBotTurn(formatText(text));
    messagesEl.appendChild(turn);
    if (meta?.products?.length) messagesEl.appendChild(buildCards(meta.products));
    if (meta?.order?.status === 'confirmed') messagesEl.appendChild(buildOrder(meta.order));
    scrollBottom();
  }

  // ── Render: history ──────────────────────────────────────────────
  function renderHistory(history) {
    hideWelcome();
    history.forEach(msg => {
      if (msg.role === 'user') {
        appendUser(msg.content);
      } else if (msg.role === 'assistant') {
        messagesEl.appendChild(makeBotTurn(formatText(msg.content)));
      }
    });
    const div = document.createElement('div');
    div.className = 'history-divider';
    div.textContent = 'Hội thoại đã được khôi phục';
    messagesEl.appendChild(div);
    scrollBottom();
  }

  // ── Product cards ────────────────────────────────────────────────
  function buildCards(products) {
    const grid = document.createElement('div');
    grid.className = 'product-cards';
    products.forEach((p, i) => {
      const cat = detectCat(p);
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <div class="card-icon">${CAT_ICON[cat] || CAT_ICON.default}</div>
        <div class="card-name">${escHtml(p.name)}</div>
        <div class="card-price">${escHtml(p.price_display)}</div>
        <div class="card-meta">⭐ ${p.rating} · Còn ${p.stock}</div>
        ${i === 0 ? '<span class="card-badge">Đề xuất</span>' : ''}`;
      card.onclick = () => send(`Cho tôi biết thêm về ${p.name}`);
      grid.appendChild(card);
    });
    return grid;
  }

  function buildOrder(order) {
    const div = document.createElement('div');
    div.className = 'order-card';
    div.innerHTML = `
      <h3>🎉 Đặt hàng thành công!</h3>
      <div class="order-row">Mã đơn: <span class="order-id">#${escHtml(order.order_id || '')}</span></div>
      <div class="order-row">📍 ${escHtml(order.address || '')}</div>
      <div class="order-row">📅 Giao trong 2–3 ngày · 💳 COD</div>`;
    return div;
  }

  // ── Typing indicator ─────────────────────────────────────────────
  let typingEl = null;

  function showTyping() {
    if (typingEl || streamWrap) return;
    const turn = document.createElement('div');
    turn.className = 'msg-turn bot';
    turn.innerHTML = `
      <div class="msg-avatar">${BOT_AVATAR_SVG}</div>
      <div class="msg-body">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>`;
    typingEl = turn;
    messagesEl.appendChild(typingEl);
    scrollBottom();
  }

  function hideTyping() {
    typingEl?.remove();
    typingEl = null;
  }

  // ── Streaming ────────────────────────────────────────────────────
  let streamWrap    = null;
  let streamTextEl  = null;
  let streamText    = '';

  function handleToken(delta) {
    hideTyping();
    hideWelcome();
    if (!streamWrap) {
      streamWrap = document.createElement('div');
      streamWrap.className = 'msg-turn bot';
      streamWrap.innerHTML = `
        <div class="msg-avatar">${BOT_AVATAR_SVG}</div>
        <div class="msg-body"><div class="text"><span class="stext"></span><span class="cursor"></span></div></div>`;
      messagesEl.appendChild(streamWrap);
      streamTextEl = streamWrap.querySelector('.stext');
    }
    streamText += delta;
    streamTextEl.innerHTML = formatText(streamText);
    scrollBottom();
  }

  function finalizeStream(fullText, meta) {
    streamWrap?.remove();
    streamWrap = null; streamTextEl = null; streamText = '';
    hideTyping();
    appendBot(fullText, meta);
  }

  function clearStream() {
    streamWrap?.remove();
    streamWrap = null; streamTextEl = null; streamText = '';
  }

  // ── Welcome state ────────────────────────────────────────────────
  function hideWelcome() {
    if (welcomeEl && welcomeEl.parentNode) {
      welcomeEl.style.display = 'none';
    }
  }

  // ── CSAT ─────────────────────────────────────────────────────────
  let _csatCtx = '', _csatTurns = 0, _csatDone = false;

  function showCsat(ctx, turns) {
    if (_csatDone) return;
    _csatCtx = ctx; _csatTurns = turns;
    const w = document.createElement('div');
    w.id = 'csat-widget';
    w.className = 'csat-wrap';
    w.innerHTML = `
      <p class="csat-q">Bạn hài lòng với trải nghiệm không?</p>
      <div class="csat-btns">
        <button class="csat-btn" onclick="submitCsat(5)">👍 Hài lòng</button>
        <button class="csat-btn" onclick="submitCsat(1)">👎 Chưa hài lòng</button>
      </div>
      <button class="csat-skip" onclick="dismissCsat()">Bỏ qua</button>`;
    messagesEl.appendChild(w);
    scrollBottom();
  }

  window.submitCsat = async (rating) => {
    if (_csatDone) return;
    _csatDone = true;
    const w = document.getElementById('csat-widget');
    if (w) {
      w.innerHTML = `<p class="csat-thanks">${rating === 5 ? '🙏 Cảm ơn bạn!' : '🙏 Cảm ơn! Chúng tôi sẽ cải thiện.'}</p>`;
      setTimeout(() => w.remove(), 3000);
    }
    try {
      await fetch('/api/csat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, rating, context: _csatCtx, turn_count: _csatTurns }),
      });
    } catch { /* best-effort */ }
  };

  window.dismissCsat = () => {
    _csatDone = true;
    document.getElementById('csat-widget')?.remove();
  };

  // ── Session clear ─────────────────────────────────────────────────
  window.clearSession = async () => {
    if (!confirm('Xóa toàn bộ cuộc trò chuyện?')) return;
    if (sessionId) await fetch(`/api/session/${sessionId}`, { method: 'DELETE' }).catch(() => {});
    localStorage.removeItem(SESSION_KEY);
    messagesEl.innerHTML = '';
    // re-add welcome state
    const w = document.createElement('div');
    w.className = 'welcome-wrap';
    w.id = 'welcome-state';
    w.innerHTML = welcomeEl ? welcomeEl.innerHTML : '';
    messagesEl.appendChild(w);
    _csatDone = false;
    sessionId = null;
    ws?.close();
    setTimeout(connect, 200);
  };

  // ── Utilities ─────────────────────────────────────────────────────
  function scrollBottom() {
    requestAnimationFrame(() => { messagesEl.scrollTop = messagesEl.scrollHeight; });
  }

  function setInputEnabled(enabled) {
    inputEl.disabled = !enabled;
    sendBtn.innerHTML = enabled ? SEND_ICON : '<span class="btn-spinner"></span>';
    if (enabled) {
      sendBtn.disabled = !inputEl.value.trim();
    } else {
      sendBtn.disabled = true;
    }
  }

  function setBanner(type, text) {
    if (!type) { connBanner.className = 'conn-banner'; connBanner.textContent = ''; return; }
    connBanner.className = `conn-banner show ${type}`;
    connBanner.textContent = text;
  }

  function detectCat(p) {
    const n = (p.name || '').toLowerCase();
    if (n.includes('macbook') || n.includes('laptop') || n.includes('thinkpad') ||
        n.includes('dell') || n.includes('asus') || n.includes('hp') || n.includes('acer')) return 'laptop';
    if (n.includes('ipad') || n.includes('tab') || n.includes('pad')) return 'tablet';
    return 'phone';
  }

  function escHtml(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatText(t) {
    return escHtml(t)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/━+/g, '<hr>')
      .replace(/\n/g, '<br>');
  }

  // ── Event listeners ────────────────────────────────────────────────
  sendBtn.addEventListener('click', () => send());
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  // ── Boot ───────────────────────────────────────────────────────────
  setInputEnabled(false);
  connect();
})();
