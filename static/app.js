(() => {
  const EMOJI = { laptop: '💻', phone: '📱', tablet: '📟', default: '📦' };
  const CATEGORY_EMOJI = { laptop: '💻', phone: '📱', tablet: '📟' };

  let ws = null;
  let sessionId = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT = 5;

  // DOM refs
  const messagesEl = document.getElementById('chat-messages');
  const inputEl = document.getElementById('msg-input');
  const sendBtn = document.getElementById('send-btn');
  const sessionLabel = document.getElementById('session-label');
  const connBanner = document.getElementById('conn-banner');

  // ── WebSocket ──────────────────────────────────────────────────────────────
  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${protocol}://${location.host}/ws`);

    setBanner('connecting', '🔄 Đang kết nối...');

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
        setBanner('disconnected', `❌ Mất kết nối — thử lại sau ${Math.round(delay/1000)}s...`);
        setTimeout(connect, delay);
      } else {
        setBanner('disconnected', '❌ Không thể kết nối. Hãy tải lại trang.');
      }
    };

    ws.onerror = () => ws.close();
  }

  function handleServerEvent(data) {
    switch (data.type) {
      case 'connected':
        sessionId = data.session_id;
        sessionLabel.textContent = `Session: ${sessionId.slice(0, 8)}`;
        appendBotMessage(data.message);
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
    text = (text || inputEl.value).trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN || sendBtn.disabled) return;
    inputEl.value = '';
    appendUserMessage(text);
    setSendEnabled(false);
    ws.send(JSON.stringify({ message: text }));
  }

  window.send = send; // expose for quick-reply buttons

  // ── Render helpers ────────────────────────────────────────────────────────
  function appendUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'message user';
    el.innerHTML = `
      <div class="msg-avatar">🧑</div>
      <div class="bubble">${escHtml(text)}</div>`;
    messagesEl.appendChild(el);
    scrollBottom();
  }

  function appendBotMessage(text, meta) {
    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.flexDirection = 'column';
    wrap.style.gap = '8px';
    wrap.style.alignSelf = 'flex-start';
    wrap.style.animation = 'fadeIn 0.25s ease';

    // Main bubble
    const el = document.createElement('div');
    el.className = 'message bot';
    el.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="bubble">${formatText(text)}</div>`;
    wrap.appendChild(el);

    // Product cards
    if (meta?.products?.length) {
      const cards = buildProductCards(meta.products);
      wrap.appendChild(cards);
    }

    // Order confirmation card
    if (meta?.order?.status === 'confirmed') {
      wrap.appendChild(buildOrderCard(meta.order));
    }

    messagesEl.appendChild(wrap);
    scrollBottom();
  }

  function buildProductCards(products) {
    const grid = document.createElement('div');
    grid.className = 'product-cards';

    products.forEach((p, idx) => {
      const cat = detectCategory(p);
      const card = document.createElement('div');
      card.className = 'product-card';
      card.innerHTML = `
        <div class="card-emoji">${EMOJI[cat] || EMOJI.default}</div>
        <div class="card-name">${escHtml(p.name)}</div>
        <div class="card-price">${escHtml(p.price_display)}</div>
        <div class="card-rating">⭐ ${p.rating} | 🏪 Còn ${p.stock} cái</div>
        ${idx === 0 ? '<span class="card-badge">🏆 Đề xuất</span>' : ''}`;
      card.onclick = () => send(`Cho tôi biết thêm về ${p.name}`);
      grid.appendChild(card);
    });

    return grid;
  }

  function buildOrderCard(order) {
    const div = document.createElement('div');
    div.className = 'order-card';
    div.innerHTML = `
      <h3>🎉 ĐẶT HÀNG THÀNH CÔNG!</h3>
      <div class="order-row">🆔 Mã đơn: <span class="order-id">#${escHtml(order.order_id || '')}</span></div>
      <div class="order-row">📍 Giao đến: ${escHtml(order.address || '')}</div>
      <div class="order-row">📅 Dự kiến: 2-3 ngày làm việc</div>
      <div class="order-row">💳 Thanh toán: COD khi nhận hàng</div>`;
    return div;
  }

  // ── Typing indicator ───────────────────────────────────────────────────────
  let typingEl = null;

  function showTyping() {
    if (typingEl || streamingWrap) return;
    typingEl = document.createElement('div');
    typingEl.className = 'message bot';
    typingEl.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="typing-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
    messagesEl.appendChild(typingEl);
    scrollBottom();
  }

  function hideTyping() {
    if (typingEl) { typingEl.remove(); typingEl = null; }
  }

  // ── Streaming ──────────────────────────────────────────────────────────────
  let streamingWrap = null;
  let streamingContent = null;
  let streamingText = '';

  function handleStreamToken(delta) {
    hideTyping();
    if (!streamingWrap) {
      streamingWrap = document.createElement('div');
      streamingWrap.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-self:flex-start;animation:fadeIn 0.25s ease';
      const el = document.createElement('div');
      el.className = 'message bot';
      el.innerHTML = '<div class="msg-avatar">🤖</div><div class="bubble"><span class="stream-text"></span><span class="stream-cursor">▍</span></div>';
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
    messagesEl.innerHTML = '';
    sessionId = null;
    ws?.close();
    setTimeout(connect, 200);
  };

  // ── Utilities ─────────────────────────────────────────────────────────────
  function scrollBottom() {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function setSendEnabled(enabled) {
    sendBtn.disabled = !enabled;
    inputEl.disabled = !enabled;
    sendBtn.innerHTML = enabled ? '➤' : '<span class="btn-spinner"></span>';
    document.querySelectorAll('.quick-btn').forEach(b => b.disabled = !enabled);
  }

  function setBanner(type, text) {
    if (!type) {
      connBanner.className = 'conn-banner';
      connBanner.textContent = '';
      return;
    }
    connBanner.className = `conn-banner show ${type}`;
    connBanner.textContent = text;
  }

  function detectCategory(product) {
    const name = (product.name || '').toLowerCase();
    if (name.includes('macbook') || name.includes('laptop') || name.includes('thinkpad') ||
        name.includes('dell') || name.includes('asus') || name.includes('hp ') ||
        name.includes('acer')) return 'laptop';
    if (name.includes('ipad') || name.includes('tab') || name.includes('pad')) return 'tablet';
    return 'phone';
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatText(text) {
    // Convert markdown-ish to HTML
    return escHtml(text)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/━+/g, '<hr style="border-color:#e2e8f0;margin:6px 0">')
      .replace(/\n/g, '<br>');
  }

  // ── Event listeners ────────────────────────────────────────────────────────
  sendBtn.addEventListener('click', () => send());
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  // ── Init ───────────────────────────────────────────────────────────────────
  setSendEnabled(false);
  connect();
})();
