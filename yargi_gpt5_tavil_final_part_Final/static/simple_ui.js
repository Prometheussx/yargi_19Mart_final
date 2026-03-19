// Basit Yargı AI arayüz scripti
// Özellikler: otomatik session, dosya upload, chat, dilekçe; emsal paneli

const el = s => document.querySelector(s);
const els = s => [...document.querySelectorAll(s)];

let STATE = {
  sessionId: null,
  mode: { petition: false },
  files: [], // {name,size}
  precedents: [],
  loading: false
};

function log(...a){ console.log('[UI]', ...a); }

// Session yönetimi: her sayfa yenilemede yeni session istendi -> sunucudan alınır
async function initSession(forceNew=false){
  try {
    if(forceNew){
      const r = await fetch('/session/new');
      const d = await r.json();
      STATE.sessionId = d.session_id;
      document.cookie = 'session_id='+STATE.sessionId+'; path=/; samesite=Lax';
      localStorage.setItem('session_id', STATE.sessionId);
    } else {
      const r = await fetch('/session/new'); // her refresh yeni olsun isteniyor
      const d = await r.json();
      STATE.sessionId = d.session_id;
      document.cookie = 'session_id='+STATE.sessionId+'; path=/; samesite=Lax';
      localStorage.setItem('session_id', STATE.sessionId);
    }
    el('#sessionId').textContent = 'session: '+STATE.sessionId.slice(0,8);
  } catch(e){ log('session error', e); }
}

function addMessage(role, text){
  const wrap = document.createElement('div');
  wrap.className = 'msg '+role;
  const bubble = document.createElement('div');
  bubble.className = 'bubble markdown';
  bubble.innerHTML = role==='assistant' ? renderMarkdown(text) : escapeHtml(text);
  wrap.appendChild(bubble);
  el('#messages').appendChild(wrap);
  el('#messages').scrollTop = el('#messages').scrollHeight;
}

function escapeHtml(str){
  return str.replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[s]));
}

function renderMarkdown(md){
  if(!md) return '';
  const raw = marked.parse(md);
  // DOMPurify varsa XSS temizliği yap; yoksa temel tag whitelist ile fallback
  if(typeof DOMPurify !== 'undefined'){
    return DOMPurify.sanitize(raw, {
      ALLOWED_TAGS: ['p','br','strong','em','b','i','ul','ol','li','h1','h2','h3','h4',
                     'blockquote','code','pre','hr','a','table','thead','tbody','tr','th','td'],
      ALLOWED_ATTR: ['href','target','rel']
    });
  }
  // DOMPurify yüklü değilse script/iframe etiketlerini kaldır (minimal koruma)
  return raw.replace(/<script[\s\S]*?<\/script>/gi, '')
            .replace(/<iframe[\s\S]*?<\/iframe>/gi, '')
            .replace(/on\w+="[^"]*"/gi, '');
}

function setStatus(msg){ el('#statusLine').textContent = msg||''; }

function refreshFileList(){
  const c = el('#filesList');
  c.innerHTML = STATE.files.map(f => `<div class="file-item"><span class="name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span><button type="button" data-rm="${escapeHtml(f.name)}">×</button></div>`).join('');
}

async function uploadFiles(fileList){
  if(!fileList.length) return;
  for(const file of fileList){
    const fd = new FormData(); fd.append('file', file);
    setStatus('Yüklüyor: '+file.name);
    try {
      const r = await fetch('/upload-file', { method:'POST', body: fd, headers: { 'session_id': STATE.sessionId }});
      const d = await r.json();
      if(d.success){
        STATE.files.push({ name: file.name, size: file.size });
      } else {
        addMessage('assistant', '❌ Dosya yükleme hatası: '+(d.detail || d.error || file.name));
      }
    } catch(e){ addMessage('assistant','❌ Bağlantı hatası: '+e.message); }
  }
  refreshFileList();
  setStatus('Dosyalar yükleme bitti');
  // Dava modu kaldırıldı
}

function toggleMode(which){
  if(which==='petition'){ STATE.mode.petition = !STATE.mode.petition; }
  el('#togglePetition').classList.toggle('active', STATE.mode.petition);
}

async function sendChat(){
  if(STATE.loading) return;
  const txt = el('#msgInput').value.trim();
  if(!txt) return;

  // Mesaj uzunluk kontrolü (backend ile uyumlu)
  if(txt.length > 12000){
    addMessage('assistant', '❌ Mesaj çok uzun (max 12.000 karakter). Lütfen kısaltın.');
    return;
  }

  // Double-submit engelle: butonu hemen devre dışı bırak
  const sendBtn = el('#inputForm button[type="submit"]') || el('#inputForm');
  if(sendBtn && sendBtn.tagName === 'BUTTON') sendBtn.disabled = true;

  addMessage('user', txt);
  el('#msgInput').value='';
  STATE.loading=true;

  const detail = el('#detailSelect').value;
  const scan = el('#scanPrecedents')?.checked;
  const party = (el('#partyInfo')?.value || '').trim();
  const situation = (el('#situationInfo')?.value || '').trim();

  const fd = new FormData();
  fd.append('message', txt);
  fd.append('is_petition', STATE.mode.petition);
  fd.append('chat_detail', detail);
  fd.append('scan_precedents', detail === 'detailed' ? (!!scan).toString() : 'false');
  if(party) fd.append('party_info', party);
  if(situation) fd.append('situation_info', situation);

  // Streaming mesaj balonu oluştur
  const wrap = document.createElement('div');
  wrap.className = 'msg assistant';
  const bubble = document.createElement('div');
  bubble.className = 'bubble markdown';
  bubble.textContent = '⏳ Yanıt hazırlanıyor...';
  wrap.appendChild(bubble);
  el('#messages').appendChild(wrap);
  el('#messages').scrollTop = el('#messages').scrollHeight;

  // AbortController: detaylı modda 8 dk, kısa modda 3 dk
  const detail = el('#detailSelect')?.value || 'concise';
  const timeoutMs = detail === 'detailed' ? 480000 : 180000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let startTime = Date.now();
  let statusInterval = setInterval(() => {
    const secs = Math.round((Date.now() - startTime) / 1000);
    setStatus(`⏳ ${secs} sn — yanıt hazırlanıyor...`);
  }, 1000);

  try {
    const r = await fetch('/chat-stream', {
      method: 'POST',
      body: fd,
      headers: { 'session_id': STATE.sessionId },
      signal: controller.signal
    });

    if(!r.ok || !r.body){
      bubble.innerHTML = renderMarkdown('❌ Sunucu bağlantı hatası: ' + r.status);
      return;
    }

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    let firstContent = false;
    let pendingPrecedentSetId = null;

    while(true){
      const { done, value } = await reader.read();
      if(done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE: her satır "data: {...}\n\n" formatında
      const lines = buffer.split('\n');
      buffer = lines.pop(); // son tamamlanmamış satırı beklet

      for(const line of lines){
        if(!line.startsWith('data:')) continue;
        const jsonStr = line.slice(5).trim();
        if(!jsonStr) continue;
        let parsed;
        try { parsed = JSON.parse(jsonStr); } catch(_){ continue; }

        // Heartbeat: sunucu bağlantıyı canlı tutuyor, atlıyoruz
        if(parsed.heartbeat) continue;

        // Loading mesajı
        if(parsed.loading && !firstContent) {
          bubble.textContent = parsed.content || '⏳ İşleniyor...';
          continue;
        }

        // Emsal metadata
        if(parsed.precedent_meta || parsed.precedent_set_id){
          pendingPrecedentSetId = parsed.precedent_set_id || pendingPrecedentSetId;
          continue;
        }

        // Ana içerik
        if(parsed.content){
          firstContent = true;
          fullContent = parsed.content;
          bubble.innerHTML = renderMarkdown(fullContent);
          el('#messages').scrollTop = el('#messages').scrollHeight;
          if(parsed.precedent_set_id) pendingPrecedentSetId = parsed.precedent_set_id;
        }

        // Hata
        if(parsed.error){
          bubble.innerHTML = renderMarkdown('❌ Hata: ' + parsed.error);
        }

        // Tamamlandı
        if(parsed.done) break;
      }
    }

    // Emsal varsa yükle
    if(pendingPrecedentSetId){
      await loadChatPrecedentSet(pendingPrecedentSetId);
    }
  } catch(e){
    if(e.name === 'AbortError'){
      bubble.innerHTML = renderMarkdown('⏱️ İstek zaman aşımına uğradı (10 dk). Lütfen tekrar deneyin veya soruyu kısaltın.');
    } else {
      bubble.innerHTML = renderMarkdown('❌ Bağlantı hatası: ' + e.message);
    }
  } finally {
    clearTimeout(timeoutId);
    clearInterval(statusInterval);
    STATE.loading = false;
    setStatus('');
    // Gönder butonunu tekrar aktif et
    if(sendBtn && sendBtn.tagName === 'BUTTON') sendBtn.disabled = false;
  }
}

async function loadChatPrecedentSet(precedentSetId){
  try { const r = await fetch(`/chat-precedents/${STATE.sessionId}/${precedentSetId}`); const d = await r.json(); if(d.precedents){ renderPrecedents(d.precedents.slice(0,25), d.search_query); } } catch(_){}
}


function renderPrecedents(list, searchQuery){
  const panel = el('#precedents');
  if(!list || !list.length){
    panel.innerHTML = '<div class="tagline">Emsal bulunamadı</div>';
    return;
  }
  panel.innerHTML = '';
  if(searchQuery){
    const h = document.createElement('div');
    h.className = 'tagline';
    h.textContent = 'Arama: ' + searchQuery;
    panel.appendChild(h);
  }
  list.forEach((p,i)=>{
    const div = document.createElement('div');
    div.className = 'precedent';
    const code = p.id || p.document_id || ('DOC'+(i+1));
    const title = (p.title || '').trim() || 'Karar';
    const meta = [p.birim||p.birimAdi, p.tarih||p.kararTarihi, p.tur||p.itemType].filter(Boolean).join(' • ');
    const full = (p.full_content || p.content || p.markdown_content || p.text || '').toString();
  // Emsal içerikleri H A M göster (markdown render etme)
  const fullHtml = '<pre style="white-space:pre-wrap; margin:0">'+escapeHtml(full)+'</pre>';

    div.innerHTML = `
      <h4>[${escapeHtml(code)}] ${escapeHtml(title)}</h4>
      <div class="tagline">${escapeHtml(meta)}</div>
      <div class="markdown" style="margin-top:6px;">${fullHtml}</div>
    `;
    panel.appendChild(div);
  });
}


async function enhancePrompt(){
  const val = el('#msgInput').value.trim(); if(!val) return;
  const fd = new FormData(); fd.append('prompt', val);
  try { const r = await fetch('/enhance-prompt', { method:'POST', body: fd, headers:{'session_id':STATE.sessionId} }); const d = await r.json(); if(d.success && d.enhanced){ el('#msgInput').value = d.enhanced; addMessage('assistant','✨ Prompt iyileştirildi.'); } else { addMessage('assistant','❌ Prompt iyileştirilemedi'); } } catch(e){ addMessage('assistant','❌ Prompt iyileştirme hatası: '+e.message); }
}

function bindEvents(){
  el('#fileInput').addEventListener('change', e=>{ uploadFiles(e.target.files); e.target.value=''; });
  el('#filesList').addEventListener('click', async e=>{
    const btn = e.target.closest('button[data-rm]'); if(!btn) return; const name = btn.dataset.rm; // backend'den sil
    try { const res = await fetch('/remove-file', { method:'POST', headers:{'Content-Type':'application/json','session_id':STATE.sessionId}, body: JSON.stringify({ filename: name })}); const d = await res.json(); if(d.success){ STATE.files = STATE.files.filter(f=>f.name!==name); refreshFileList(); } } catch(_){ }
  });
  el('#togglePetition').addEventListener('click', ()=> toggleMode('petition'));
  // Detay seçimi concise olduğunda emsal checkbox pasif olsun
  el('#detailSelect').addEventListener('change', ()=>{
    const det = el('#detailSelect').value;
    const cb = el('#scanPrecedents');
    if(cb){
      cb.disabled = (det !== 'detailed');
      if(det !== 'detailed') cb.checked = false; else cb.checked = true;
    }
  });
  el('#inputForm').addEventListener('submit', e=>{ e.preventDefault(); sendChat(); });
  el('#msgInput').addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendChat(); }});
  el('#clearBtn').addEventListener('click', ()=>{ el('#messages').innerHTML=''; addMessage('assistant','Yeni bir sohbet başlattınız.'); });
  el('#enhanceBtn').addEventListener('click', enhancePrompt);
  // Full pipeline kaldırıldı
  el('#newSessionBtn').addEventListener('click', async ()=>{ await initSession(true); el('#messages').innerHTML=''; addMessage('assistant','Yeni session oluşturuldu.'); STATE.files=[]; refreshFileList(); el('#precedents').innerHTML=''; });
}

function welcome(){
  addMessage('assistant', 'Merhaba! Dosya yükleyin ve mesaj yazın. Dilekçe modu için 📝 butonunu kullanabilirsiniz.');
}

// Dava modu için hızlı emsal önizleme çağrısı
// Dava önizleme kaldırıldı

// Başlat
window.addEventListener('DOMContentLoaded', async ()=>{
  await initSession();
  bindEvents();
  welcome();
});
