/* Ana Uygulama JS - Gelişmiş çıktı görselleştirme */
let currentFiles = []; // Tek dosya yerine dosya listesi
let uploadedFiles = []; // Başarıyla yüklenen dosyalar {filename, size, chunks, id}
let isPetition = false;
let isLoading = false;
let streamingController = null;
let lastUserMessage = '';

const qs = s => document.querySelector(s);
const qsa = s => [...document.querySelectorAll(s)];

// Textarea auto resize
function autoResize(el){ el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,150)+'px'; }

// Enter göndermek
function handleKeyPress(e){ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(e); } }

// Dava analizi toggle
function updateChatDetailVisibility(){
  const container = qs('#chatDetailContainer');
  const select = qs('#chatDetailSelect');
  if(!container || !select) return;
  const hide = isPetition; // Dilekçe modunda yanıt modu seçimi olmayacak
  if(hide){
    container.style.display='none';
    // Seçim gönderilmeyecek; ama backend default 'concise' kullanır.
    select.disabled=true;
  } else {
    container.style.display='';
    select.disabled=false;
  }
}
function togglePetition(){
  const t=qs('#petitionToggle');
  isPetition=!isPetition;
  t.classList.toggle('active',isPetition);
  updateChatDetailVisibility();
}

// Yüklenen dosyalar listesini güncelle
function updateUploadedFilesList() {
    const container = qs('#uploadedFilesList');
    
    if (uploadedFiles.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = uploadedFiles.map(file => {
        // Dosya adını kısalt
        const displayName = truncateFileName(file.filename, 25);
        const fileSize = (file.size/1024/1024).toFixed(2);
        
        return `
        <div class="uploaded-file-item" data-file-id="${file.id}">
            <div class="uploaded-file-info">
                <div class="uploaded-file-name" title="${file.filename}">${displayName}</div>
                <div class="uploaded-file-size">${fileSize} MB • ${file.chunks} parça</div>
            </div>
            <button class="remove-file-btn" onclick="removeUploadedFile('${file.id}')" title="Dosyayı kaldır">×</button>
        </div>
        `;
    }).join('');
}

// Dosya adını akıllıca kısalt
function truncateFileName(filename, maxLength) {
    if (filename.length <= maxLength) return filename;
    
    const extension = filename.split('.').pop();
    const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'));
    const availableLength = maxLength - extension.length - 1; // -1 for the dot
    
    if (availableLength <= 3) {
        return filename.substring(0, maxLength - 3) + '...';
    }
    
    const truncatedName = nameWithoutExt.substring(0, availableLength - 3) + '...';
    return truncatedName + '.' + extension;
}

// Dosyayı kaldır
async function removeUploadedFile(fileId) {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (!file) return;
    
    try {
        console.log('Removing file:', file.filename);
        const sessionId = getSessionId();
        
        // Backend'den dosyayı kaldır
        const response = await fetch('/remove-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'session_id': sessionId
            },
            body: JSON.stringify({
                filename: file.filename,
                file_id: fileId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Listeden kaldır
            uploadedFiles = uploadedFiles.filter(f => f.id !== fileId);
            currentFiles = currentFiles.filter(f => f.name !== file.filename);
            updateUploadedFilesList();
            updateFileInfo();
            console.log('File removed successfully:', file.filename);
        } else {
            console.error('Failed to remove file:', result.error);
            alert('Dosya kaldırılamadı: ' + (result.error || 'Bilinmeyen hata'));
        }
    } catch (error) {
        console.error('Error removing file:', error);
        alert('Dosya kaldırma hatası: ' + error.message);
    }
}

// Dosya bilgisi metnini güncelle
function updateFileInfo() {
    const info = qs('#fileInfo');
    
    if (uploadedFiles.length === 0) {
        info.textContent = 'Dosya seçilmedi • PDF, TXT, DOC, DOCX desteklenir';
        info.classList.remove('has-file');
    } else if (uploadedFiles.length === 1) {
        const file = uploadedFiles[0];
        const displayName = truncateFileName(file.filename, 30);
        info.textContent = `✓ ${displayName} yüklendi`;
        info.classList.add('has-file');
    } else {
        const totalSize = uploadedFiles.reduce((sum, f) => sum + f.size, 0);
        const totalChunks = uploadedFiles.reduce((sum, f) => sum + f.chunks, 0);
        info.textContent = `✓ ${uploadedFiles.length} dosya yüklendi (${(totalSize/1024/1024).toFixed(2)} MB) • ${totalChunks} parça`;
        info.classList.add('has-file');
    }
}

// Çoklu dosya seçimi
function handleFileSelect(ev){ 
    console.log('handleFileSelect called', ev);
    const files = ev.target.files; // FileList objesi
    const info = qs('#fileInfo'); 
    console.log('Selected files:', files);
    
    if(files && files.length > 0){ 
        const newFiles = Array.from(files).filter(file => {
            // Zaten yüklü olan dosyaları filtrele
            return !uploadedFiles.some(uploaded => uploaded.filename === file.name);
        });
        
        if (newFiles.length === 0) {
            info.textContent = 'Seçilen dosyalar zaten yüklü';
            ev.target.value = ''; // Input'u temizle
            return;
        }
        
        currentFiles = [...currentFiles, ...newFiles];
        
        if(newFiles.length === 1) {
            info.textContent = `✓ ${newFiles[0].name} yükleniyor...`;
        } else {
            info.textContent = `✓ ${newFiles.length} dosya yükleniyor...`;
        }
        info.classList.add('has-file'); 
        
        // Her dosyayı ayrı ayrı sunucuya gönder
        console.log('Starting multiple file upload...');
        const sessionId = getSessionId();
        console.log('Session ID:', sessionId);
        
        let uploadedCount = 0;
        let uploadErrors = [];
        
        // Tüm dosyaları paralel olarak yükle
        const uploadPromises = newFiles.map((file, index) => {
            const fd = new FormData(); 
            fd.append('file', file);
            
            return fetch('/upload-file', { 
                method: 'POST', 
                body: fd, 
                headers: { 'session_id': sessionId }
            }).then(r => {
                console.log(`Upload response status for ${file.name}:`, r.status);
                return r.json();
            }).then(d => {
                console.log(`Upload response data for ${file.name}:`, d);
                if(d.success){ 
                    uploadedCount++;
                    
                    // Başarıyla yüklenen dosyayı listeye ekle
                    const uploadedFile = {
                        id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        filename: file.name,
                        size: file.size,
                        chunks: d.vector_store.chunks,
                        uploadedAt: new Date()
                    };
                    uploadedFiles.push(uploadedFile);
                    
                    return { success: true, filename: file.name, chunks: d.vector_store.chunks };
                } else { 
                    uploadErrors.push(`${file.name}: ${d.detail || 'Bilinmeyen hata'}`);
                    return { success: false, filename: file.name, error: d.detail };
                } 
            }).catch(err => {
                console.error(`Upload error for ${file.name}:`, err);
                uploadErrors.push(`${file.name}: ${err.message}`);
                return { success: false, filename: file.name, error: err.message };
            });
        });
        
        // Tüm yüklemelerin tamamlanmasını bekle
        Promise.all(uploadPromises).then(results => {
            updateUploadedFilesList();
            updateFileInfo();
            
            if (uploadErrors.length > 0) {
                console.warn('Upload errors:', uploadErrors);
            }
            
            // Input'u temizle
            ev.target.value = '';
        });
        
    } else { 
        currentFiles = []; 
        updateFileInfo();
    } 
}

// Basit metin kısaltma
function truncate(str,max=160){ return str.length>max ? str.slice(0,max)+'…' : str; }

// Assistant mesajı oluştur
function createAssistantMessageContainer(){ const wrap=document.createElement('div'); wrap.className='message assistant'; const bubble=document.createElement('div'); bubble.className='bubble'; const body=document.createElement('div'); body.className='assistant-body'; const meta=document.createElement('div'); meta.className='assistant-meta'; meta.innerHTML=`<span class="status-pill">AI</span><span data-role="time"></span>`; const actions=document.createElement('div'); actions.className='assistant-actions'; actions.innerHTML=`<button title="Kopyala" data-act="copy">📋</button><button title="TOC" data-act="toc">☰</button><button title="Daralt / Genişlet" data-act="collapse">↕</button>`; const toc=document.createElement('div'); toc.className='toc'; toc.innerHTML='<div class="toc-title">İÇİNDEKİLER</div><ul></ul>'; const content=document.createElement('div'); content.className='markdown-content'; body.append(meta,toc,content); bubble.append(actions,body); wrap.appendChild(bubble); // Eventler
  actions.addEventListener('click',e=>{ if(e.target.closest('button')) handleAssistantAction(e.target.closest('button'),wrap); }); return wrap; }

function handleAssistantAction(btn,wrap){ const act=btn.dataset.act; const content=wrap.querySelector('.markdown-content'); if(act==='copy'){ copyToClipboard(content.innerText); btn.textContent='✓'; setTimeout(()=>btn.textContent='📋',1200); } else if(act==='toc'){ wrap.querySelector('.toc').classList.toggle('active'); } else if(act==='collapse'){ toggleCollapse(wrap); } }

// İyileştirilmiş daraltma/genişletme fonksiyonu
function toggleCollapse(wrap) {
  const content = wrap.querySelector('.markdown-content');
  const collapsed = wrap.dataset.collapsed === '1';
  
  if (collapsed) {
    // Genişlet
    content.style.maxHeight = '';
    content.style.overflow = '';
    wrap.dataset.collapsed = '0';
    
    // Gradient butonunu kaldır
    const gradient = wrap.querySelector('.collapse-gradient');
    if (gradient) gradient.remove();
    
    // Buton metnini güncelle
    const collapseBtn = wrap.querySelector('[data-act="collapse"]');
    if (collapseBtn) {
      collapseBtn.textContent = '↕';
      collapseBtn.title = 'Daralt';
    }
  } else {
    // Daralt
    content.style.maxHeight = '300px';
    content.style.overflow = 'hidden';
    content.style.position = 'relative';
    
    if (!wrap.querySelector('.collapse-gradient')) {
      const g = document.createElement('div');
      g.className = 'collapse-gradient';
      g.innerHTML = '<button class="collapse-btn">📖 Devamını Göster</button>';
      
      g.querySelector('button').onclick = () => {
        content.style.maxHeight = '';
        content.style.overflow = '';
        wrap.dataset.collapsed = '0';
        g.remove();
        
        // Buton metnini güncelle
        const collapseBtn = wrap.querySelector('[data-act="collapse"]');
        if (collapseBtn) {
          collapseBtn.textContent = '↕';
          collapseBtn.title = 'Daralt';
        }
      };
      
      content.parentElement.appendChild(g);
    }
    
    wrap.dataset.collapsed = '1';
    
    // Buton metnini güncelle
    const collapseBtn = wrap.querySelector('[data-act="collapse"]');
    if (collapseBtn) {
      collapseBtn.textContent = '📖';
      collapseBtn.title = 'Genişlet';
    }
  }
}

// AI metnini görsel olarak daha temiz markdown'a dönüştür
function normalizeAIText(raw){
  if(!raw) return '';
  let txt = raw.slice();
  
  // Tüm satır sonlarını normalize
  txt = txt.replace(/\r\n?/g,'\n');
  
  // Unicode görünmezleri temizle (zero-width, BOM, NBSP)
  txt = txt.replace(/[\u200B\u200C\u200D\uFEFF]/g,'').replace(/\u00A0/g,' ');
  
  // Kod fence işaretlerini temizle (AI bazen boş ``` koyuyor)
  txt = txt.replace(/```+/g,'');
  
  // **YILDIZ FORMATLARINI DÜZELTELİM** - AI'nın yanlış formatlarını düzelt
  
  // Satır başında yıldızla başlayan paragrafları başlık yap: "*Metin." -> "### Metin"
  txt = txt.replace(/^\*([A-ZÇĞİÖŞÜ][^\n*]{10,200})\s*$/gm, '### $1');
  
  // Satır başında yıldızla başlayan kısa metinleri başlık yap: "*Başlık" -> "### Başlık" 
  txt = txt.replace(/^\*([A-ZÇĞİÖŞÜ][^\n*]{3,100}?)\.?\s*$/gm, '### $1');
  
  // Çok yıldızlı başlıkları düzelt: "***Başlık***" -> "## Başlık"
  txt = txt.replace(/^\*{2,}([A-ZÇĞİÖŞÜ][^*\n]{3,100})\*{2,}$/gm, '## $1');
  
  // Yıldızla çevrilmiş başlıkları düzelt: "*Başlık*" -> "### Başlık"
  txt = txt.replace(/^\*([A-ZÇĞİÖŞÜ][^*\n]{3,60})\*$/gm, '### $1');
  
  // Başlık sonundaki yıldızları temizle: "Başlık:***" -> "Başlık:"
  txt = txt.replace(/([A-ZÇĞİÖŞÜa-zçğıöşü\s]+):\*+/g, '$1:');
  
  // Satır sonundaki gereksiz yıldızları temizle
  txt = txt.replace(/\*+$/gm, '');
  
  // Paragraf başında ve sonunda kalan yıldızları temizle
  txt = txt.replace(/^\*+\s*/gm, '');
  txt = txt.replace(/\s*\*+$/gm, '');
  
  // **metni** -> kalın yapma (düzgün olanları koru)
  txt = txt.replace(/\*\*([^*\n]+)\*\*/g, '**$1**');
  
  // *metin* -> italik yapma (tek yıldız, başlık değilse)
  txt = txt.replace(/(?<!\*)\*([^*\n]{1,50})\*(?!\*)/g, '*$1*');
  
  // Başında 1-3 boşluk + # olan satırları sola yasla
  txt = txt.replace(/^[ \t\u00A0]{1,3}(#{1,6})\s+/gm,(m,h)=> h+' ');
  
  // Tek satırda yapışmış başlıkları ayır
  txt = txt.replace(/([^\n])\s+(#{2,6}\s)/g, (m, a, b)=> a+'\n\n'+b);
  
  // Aynı satırda art arda birden çok heading varsa aralarına boş satır koy
  txt = txt.replace(/(#{2,6}[^#\n]*?)\s+(#{3,6}\s)/g, (m,a,b)=> a.trim()+"\n\n"+b);
  
  // Başlık satırlarının öncesine en az bir boş satır ekle (ilk satır hariç)
  txt = txt.replace(/([^\n])\n(#{1,6}[^\n]+)/g, (m,a,b)=> a+'\n\n'+b);
  
  // 'Savunma ... Raporu' gibi ilk satırda başlık işareti yoksa ve 'Raporu' kelimesi varsa H1 yap
  txt = txt.replace(/^([A-ZÇĞİÖŞÜ].{5,60}Raporu)\s*$/m, (m,a)=> '# '+a.trim());
  
  // Büyük harfle başlayan ve ardından noktalı virgül olan satırları başlık yap
  txt = txt.replace(/^([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü\s]{5,80}):\s*$/gm, '### $1');
  
  // Madde işareti noktaları: • -> -
  txt = txt.replace(/^\s*[•·]\s+/gm,'- ');
  
  // Satır başında kalmış tire + boşluk sonrası başka tireleri normalize
  txt = txt.replace(/^-\s+-\s+/gm,'- ');
  
  // İç içe listelerde gereksiz boşlukları azalt
  txt = txt.replace(/^(\s{0,3})[-*]\s*(\n[-*]\s*)+/gm, m=> m.replace(/\n\s*/g,'\n'));
  
  // Art arda boş satırlar tek olsun
  txt = txt.replace(/\n{3,}/g,'\n\n');
  
  // Liste numaralarından önce boş satır yoksa ekle
  txt = txt.replace(/([^\n])\n(\d+\.\s)/g,(m,a,b)=> a+'\n\n'+b);
  
  // Sadece büyük başlayıp anlamlı uzunlukta olan ve ardından boş satır / liste gelen satırları H3 yap
  txt = txt.replace(/^(?!#+)([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜÖçğıüş0-9 \-]{8,90})(?:\:)?\n(?=\n|[-\d>•])/gm,(m,a)=>{
    // İçinde 2+ kelime varsa başlık kabul
    if(a.split(/\s+/).length >= 2) return '### '+a.trim()+"\n"; return m;
  });
  
  // Yalnız "### ###" tekrarlarını düzelt
  txt = txt.replace(/(###\s+[^\n]+)\n+(###\s)/g,'$1\n\n$2');
  
  // Liste işaretinden hemen sonra boş satırları temizle
  txt = txt.replace(/^(?:- |• )(.*)\n\n(- |\d+\. )/gm,(m)=> m.replace(/\n\n/,'\n'));
  
  // Başlık satırlarından sonra boş satır yoksa ekle
  txt = txt.replace(/(#{1,6}[^\n]*)(\n)(?!\n|[-\d*>])/g,'$1\n\n');
  
  // Numara ile başlayan ama heading olması gereken satırları tespit et
  txt = txt.replace(/^(\d+)\.\s+([A-ZÇĞİÖŞÜ][^\n]{4,80})$/gm,(m,n,rest)=> '### '+n+'. '+rest.trim());
  
  // Fazla boşlukları kırp
  txt = txt.trim();

  // === YENİ: YILDIZLI BAŞLIK BİRLEŞME ONARIMI ===
  // Örn: "Stratejik Yol Haritası* Devam Senaryosu:" -> iki ayrı başlık
  txt = txt.replace(/([A-ZÇĞİÖŞÜ][^\n]{4,80})\*\s+([A-ZÇĞİÖŞÜ][^\n]{3,80})(:)?/g,(m,a,b,c)=> `### ${a.trim()}\n\n#### ${b.trim()}${c||''}`);

  // Örn: "Risk-Fırsat Spektrumu* Fırsatlar:" -> Üst + alt başlık
  txt = txt.replace(/(Risk[- ]?Fırsat\s+Spektrumu)\*\s*(Fırsatlar|Riskler)\s*:/gi,(m,a,b)=> `### ${a.trim()}\n\n#### ${b.charAt(0).toUpperCase()+b.slice(1).toLowerCase()}:`);

  // Başında kalmış tek yıldızlı blokları temizle (örn *Taraf Konumu & ...)
  txt = txt.replace(/^\*+(?=\s*[A-ZÇĞİÖŞÜ])/gm,'');

  // Yıldız + rakam ile karışmış listeleri düzelt: "Piyasa ...\nPiyasa...** Uzlaşma" gibi yapışmaları ayır
  txt = txt.replace(/([0-9]+\. .*?)\*+\s+(Uzlaşma|Devam|Risk|Fırsatlar)/gi,(m,prev,next)=> prev+"\n\n#### "+next.charAt(0).toUpperCase()+next.slice(1));

  // 1 yerine 2-3 ile başlayan listeleri normalize (ilk satır 2. veya 3. ise başına 1. ekle)
  txt = txt.replace(/(?:^|\n)(2|3)\.\s+[^\n]+/g,(m,num,offset,str)=>{
    // Eğer hemen öncesinde numaralı madde yoksa 1. ekle
    const before = txt.slice(0, txt.indexOf(m)).split('\n').pop();
    if(!/^\d+\.\s/.test(before)) return '\n1. (Önceki madde eksik otomatik eklendi)\n'+m.trim();
    return m;
  });

  // Artık gereksiz birden fazla #### sırasını sadeleştir
  txt = txt.replace(/^(####\s+[^\n]+)\n+(####\s+)/gm,(m,a,b)=> a+'\n\n'+b);

  // Çift boşluk cleanup tekrar
  txt = txt.replace(/\n{3,}/g,'\n\n');

  // === EK DÜZELTMELER: Risk/Fırsatlar inline birleşmeleri ===
  // Örn: "Risk-Fırsat Spektrumu* Riskler:" zaten yukarıda ayrılmış olabilir; burada aynı satırda 'Riskler:' sonrası metin varsa yeni paragrafa taşı
  txt = txt.replace(/(Risk[- ]?Fırsat[^\n]*Riskler:)\s*(.+)/i,(m,head,rest)=> head+"\n\n"+rest.trim());
  txt = txt.replace(/(Risk[- ]?Fırsat[^\n]*Fırsatlar:)\s*(.+)/i,(m,head,rest)=> head+"\n\n"+rest.trim());

  // Merged pattern: "Risk-Fırsat Spektrumu* Riskler:" -> handled earlier; but if later 'Fırsatlar:' appears on same line after risk items
  txt = txt.replace(/(Riskler:[^\n]+?)\s+Fırsatlar:/g,(m,riskPart)=> riskPart+"\n\n#### Fırsatlar:");

  // Yol haritası numaralı başlık altındaki çıplak satırları listeye dönüştür
  txt = txt.replace(/(^|\n)(\d+)\.\s+([A-ZÇĞİÖŞÜ][^\n:]{3,80}):?\n((?:^(?!\d+\.|#{1,6}|\s*$).+\n?)+)/gm,(m,start,num,title,block)=>{
    // block içindeki her satırı - ile başlat (boş olanları atla)
    const items = block.split(/\n/).filter(l=>l.trim()).map(l=> '- '+l.trim());
    return `\n### ${num}. ${title.trim()}\n\n`+items.join('\n')+'\n\n';
  });

  // Son satırda Riskler maddeleri ile Fırsatlar başlığı yapışmışsa ayır
  txt = txt.replace(/(uzun yargılama süreci)\s+Fırsatlar:/i,'$1\n\n#### Fırsatlar:');

  // Başlık sonrası hemen liste yoksa ancak büyük harfle başlayan kısa satırlar varsa paragraf olarak bırak (önceki regexlerin yan etkilerini azaltmak için hafif düzeltme)
  txt = txt.replace(/(####\s+[A-ZÇĞİÖŞÜ][^\n]+)\n(-\s+[A-ZÇĞİÖŞÜ][^\n]+\n)(?=####|###|$)/g,(m,a,b)=> a+'\n'+b); // noop placeholder
  
  // Son: art arda gelen heading satırları arasına boş satır ekle
  txt = txt.replace(/(#{1,6}[^\n]*?)\n(#{1,6}[^\n]*?)/g,(m,a,b)=> a+'\n\n'+b);
  
  // === FİNAL KAPSAMLI DÜZELTMELER ===
  
  // Birden fazla büyük harfle başlayan kelimeden oluşan aynı satırda yapışmış başlıkları ayır
  txt = txt.replace(/([A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)/g, '$1\n\n### $2');
  
  // Paragraf ortasında kalmış yıldız işaretlerini temizle
  txt = txt.replace(/(\w)\*+(\w)/g, '$1$2');
  
  // Eksik numara düzeltmeleri - 3., 4. varsa ama 1., 2. yoksa otomatik düzelt
  const lines = txt.split('\n');
  for(let i = 0; i < lines.length; i++){
    const line = lines[i];
    const match = line.match(/^(\d+)\.\s+/);
    if(match){
      const num = parseInt(match[1]);
      if(num > 1){
        // Önceki satırlarda 1. var mı kontrol et
        let hasOne = false;
        for(let j = i-1; j >= Math.max(0, i-10); j--){
          if(lines[j].match(/^1\.\s+/)){
            hasOne = true;
            break;
          }
        }
        if(!hasOne && num <= 5){
          // 1. ekle
          lines.splice(i, 0, '1. (Önceki maddeler eksik - otomatik eklendi)');
          i++; // Eklediğimiz satırı atla
        }
      }
    }
  }
  txt = lines.join('\n');
  
  // Alt alta gelen yıldız işaretlerini temizle
  txt = txt.replace(/\*+\n\*+/g, '\n');
  
  // Başlık sonundaki gereksiz noktalama işaretlerini normalize et
  txt = txt.replace(/(#{1,6}\s+[^\n]+)[.,:;!?]+$/gm, '$1');
  
  // Son temizlik: gereksiz boşluklar
  txt = txt.replace(/[ \t]+$/gm, ''); // Satır sonundaki boşluklar
  txt = txt.replace(/\n{4,}/g, '\n\n\n'); // 4+ boş satır -> 3'e düşür
  
  return txt;
}

// Markdown render (Marked + DOMPurify + highlight.js) - dış scriptler yüklendikten sonra çalışır
function basicMarkdown(raw){ // Basit fallback
  let h = raw
    .replace(/^####\s+(.*)$/gm,'<h4>$1</h4>')
    .replace(/^###\s+(.*)$/gm,'<h3>$1</h3>')
    .replace(/^##\s+(.*)$/gm,'<h2>$1</h2>')
    .replace(/^#\s+(.*)$/gm,'<h1>$1</h1>')
    .replace(/^>\s+(.*)$/gm,'<blockquote>$1</blockquote>');
  // bullet
  h = h.replace(/^(?:- |• )(.*)$/gm,'<li>$1</li>');
  h = h.replace(/(<li>.*?<\/li>\n?)+/g,m=> '<ul>'+m.replace(/\n/g,'')+'</ul>');
  // numbered
  h = h.replace(/^(\d+)\.\s+(.*)$/gm,'<li>$1. $2</li>');
  h = h.replace(/(<li>\d+\. .*?<\/li>\n?)+/g,m=> '<ol>'+m.replace(/\n/g,'')+'</ol>');
  h = h.replace(/\n{2,}/g,'</p><p>');
  h = '<p>'+h+'</p>';
  return h;
}
function renderMarkdown(raw){ const normalized = normalizeAIText(raw); if(window.marked){ const html = DOMPurify.sanitize(marked.parse(normalized, { mangle:false, headerIds:true, breaks:true })); return html; } return basicMarkdown(normalized); }

// Replace [w1] style citations with anchor tags using provided map
function linkifyWebCitations(html, citations){
  try{
    if(!citations || !Array.isArray(citations) || !citations.length) return html;
    const map = Object.fromEntries(citations.map(c=> [String(c.index), c.url]));
    return html.replace(/\[w(\d+)\]/g, (m, idx)=>{
      const url = map[String(idx)];
      if(!url) return m;
      const safeUrl = DOMPurify.sanitize(url, {ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.-]|$))/i});
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">[w${idx}]</a>`;
    });
  }catch(_){ return html; }
}

// Auto-link law citations like [TMK m.166], [TBK m.49], [HMK m.119]
function linkifyLawCitations(html){
  try{
    // Map common Turkish law abbreviations to law numbers in mevzuat.gov.tr
    const LAW_MAP = {
      'TMK': '4721', // Türk Medeni Kanunu
      'TBK': '6098', // Türk Borçlar Kanunu
      'HMK': '6100', // Hukuk Muhakemeleri Kanunu
      'TCK': '5237', // Türk Ceza Kanunu
      'İİK': '2004', 'IİK': '2004', 'IIK': '2004', // İcra ve İflas Kanunu (normalize later)
      'TTK': '6102', // Türk Ticaret Kanunu
      'FSEK': '5846', // Fikir ve Sanat Eserleri Kanunu
      'SMK': '6769', // Sınai Mülkiyet Kanunu
      'KVKK': '6698' // Kişisel Verilerin Korunması Kanunu
    };
    // Normalize dotted I forms to a canonical key where possible
    function normalizeCode(code){
      if(code === 'IİK' || code === 'IIK') return 'İİK';
      return code;
    }
    // Use details page; specific article anchors are not reliably supported
    function lawUrl(lawNo){
      // Mevzuat: Kanun (Tur=1), Tertip=5 for current consolidated text
      return `https://www.mevzuat.gov.tr/Mevzuat?MevzuatNo=${encodeURIComponent(lawNo)}&MevzuatTur=1&MevzuatTertip=5`;
    }
    // Replace bracketed forms first (e.g., [TMK m.166]) possibly bold-wrapped by markdown to <strong>[TMK m.166]</strong>
    const bracketRe = /\[(TMK|TBK|HMK|TCK|İİK|IİK|IIK|TTK|FSEK|SMK|KVKK)\s*m\.?\s*(\d+[A-Za-z\-]*)\]/g;
    html = html.replace(bracketRe, (m, code, article)=>{
      const key = normalizeCode(code);
      const lawNo = LAW_MAP[key];
      if(!lawNo) return m;
      const url = DOMPurify.sanitize(lawUrl(lawNo), {ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.-]|$))/i});
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">[${key} m.${article}]</a>`;
    });
    // Also replace plain-text forms without brackets (e.g., TMK m.166) not already inside a link
    const plainRe = /(?![^<]*?>)(TMK|TBK|HMK|TCK|İİK|IİK|IIK|TTK|FSEK|SMK|KVKK)\s*m\.?\s*(\d+[A-Za-z\-]*)/g;
    html = html.replace(plainRe, (m, code, article)=>{
      const key = normalizeCode(code);
      const lawNo = LAW_MAP[key];
      if(!lawNo) return m;
      const url = DOMPurify.sanitize(lawUrl(lawNo), {ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.-]|$))/i});
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${key} m.${article}</a>`;
    });
    return html;
  }catch(_){ return html; }
}

// Heading tablosu
function buildTOC(container){ const toc=container.querySelector('.toc ul'); toc.innerHTML=''; const headings=container.querySelectorAll('.markdown-content h1, .markdown-content h2, .markdown-content h3'); headings.forEach(h=>{ if(!h.id){ h.id = 'h_'+Math.random().toString(36).slice(2,9); } const li=document.createElement('li'); const level=h.tagName==='H1'?0: h.tagName==='H2'?1:2; li.style.marginLeft= (level*8)+'px'; li.innerHTML=`<a href="#${h.id}">${truncate(h.textContent.trim(),80)}</a>`; toc.appendChild(li); }); if(headings.length>2) container.querySelector('.toc').classList.add('active'); }

// Güvenli kopyalama
function copyToClipboard(text){ navigator.clipboard.writeText(text).catch(()=>{}); }

// HTML kaçış
function escapeHtml(str){ 
  if (str == null || str == undefined) return '';
  if (typeof str !== 'string') str = String(str);
  return str.replace(/[&<>"']/g,s=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;' }[s])); 
}

// Kullanıcı mesajı ekle
function addUserMessage(text){ const container=qs('#messagesContainer'); const wrap=document.createElement('div'); wrap.className='message user'; const bubble=document.createElement('div'); bubble.className='bubble user-text'; bubble.textContent=text; wrap.appendChild(bubble); container.appendChild(wrap); scrollToBottom(); }

// Hata mesajı ekle
function addErrorMessage(text){ const container=qs('#messagesContainer'); const wrap=document.createElement('div'); wrap.className='message assistant error'; const bubble=document.createElement('div'); bubble.className='bubble error-text'; bubble.textContent=text; wrap.appendChild(bubble); container.appendChild(wrap); scrollToBottom(); }

// Sistem mesajı ekle
function addSystemMessage(text){ const container=qs('#messagesContainer'); const wrap=document.createElement('div'); wrap.className='message system'; const bubble=document.createElement('div'); bubble.className='bubble system-text'; bubble.textContent=text; wrap.appendChild(bubble); container.appendChild(wrap); scrollToBottom(); }

// Yükleme mesajı
function addLoadingMessage(customText = 'Düşünüyorum...'){ const container=qs('#messagesContainer'); const wrap=document.createElement('div'); wrap.className='message assistant'; const bubble=document.createElement('div'); bubble.className='loading-bubble'; bubble.innerHTML=`<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div><span>${customText}</span>`; wrap.appendChild(bubble); container.appendChild(wrap); scrollToBottom(); return wrap; }

// Kaydır
function scrollToBottom(){ const c=qs('#messagesContainer'); c.scrollTop=c.scrollHeight; }

// Streaming gönder
async function sendMessage(ev){
  ev && ev.preventDefault();
  if(isLoading) return;
  const input=qs('#messageInput');
  const val=input.value.trim();
  if(!val) return;
  lastUserMessage = val;
  
  addUserMessage(val);
  input.value='';
  autoResize(input);
  isLoading=true; qs('#sendButton').disabled=true; qs('#sendButton').classList.add('loading');
  const loadingWrap=addLoadingMessage();
  const formData=new FormData();
  formData.append('message',val);
  formData.append('is_petition',isPetition);
  // Normal sohbet çıktı stili
  const chatDetail = qs('#chatDetailSelect')?.value || 'concise';
  formData.append('chat_detail', chatDetail);
  // Opsiyonel taraf/durum bilgileri (detaylı sorular için)
  const partyInfo = qs('#partyInfo')?.value?.trim();
  const situationInfo = qs('#situationInfo')?.value?.trim();
  if(partyInfo) formData.append('party_info', partyInfo);
  if(situationInfo) formData.append('situation_info', situationInfo);
  
  // Dosya göndermeye gerek yok - zaten vector store'da var
  // Vector store'daki tüm dosyalar otomatik olarak aranacak
  
  let assistantWrap=null; let rawAcc=''; let currentSessionId = getSessionId();
  console.log('💬 Chat başlatılıyor, Session ID:', currentSessionId);
  console.log('📊 Yüklü dosyalar:', uploadedFiles.length);
  console.log('📄 Petition:', isPetition);
  
  // 10 dk AbortController - proxy timeout'a karşı ve kullanıcı iptali için
  const abortController = new AbortController();
  const abortTimeout = setTimeout(() => abortController.abort(), 600000);

  try {
    const sid = getSessionId();
    console.log('🔄 Final session ID check:', sid);
    const res= await fetch('/chat-stream',{ method:'POST', body: formData, headers: { 'session_id': sid }, signal: abortController.signal });
    if(!res.ok) throw new Error('Sunucu hatası');
    const reader=res.body.getReader();
    const decoder=new TextDecoder();
    while(true){
      const {done,value}= await reader.read();
      if(done) break;
      const chunk=decoder.decode(value,{stream:true});
      const lines=chunk.split('\n');
      for(let line of lines){
        line=line.trim();
        if(!line.startsWith('data:')) continue;
        line=line.slice(5).trim();
        try {
          const data=JSON.parse(line);
            // Heartbeat: sunucu canlı tutuyor, UI'da yoksay
            if(data.heartbeat){ console.log('💓 Heartbeat alındı'); continue; }
            if(data.error){
              if(!assistantWrap){ assistantWrap=createAssistantMessageContainer(); qs('#messagesContainer').appendChild(assistantWrap); }
              assistantWrap.querySelector('.markdown-content').innerHTML = `<div class=\"error-message\">${escapeHtml(data.error)}</div>`; scrollToBottom(); continue;
            }
            // Precedent meta event
            if(data.precedent_set_id && data.precedent_meta && !data.content){
              // Store meta temporarily to render after main content appears
              console.log('📚 Meta event received:', data);
              console.log('📚 Meta stored in window.__lastPrecedentMeta');
              window.__lastPrecedentMeta = data;
              continue;
            }
            if(data.content){
              console.log('📚 Content event received:', data.content.length, 'chars');
              rawAcc = data.content;
              if(!assistantWrap){ // İlk chunk
              loadingWrap.remove(); assistantWrap=createAssistantMessageContainer(); const tSpan=assistantWrap.querySelector('[data-role="time"]'); tSpan.textContent = new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'}); qs('#messagesContainer').appendChild(assistantWrap); }
            let html=renderMarkdown(rawAcc);
            if(data.web_citations){ html = linkifyWebCitations(html, data.web_citations); }
            html = linkifyLawCitations(html);
            assistantWrap.querySelector('.markdown-content').innerHTML=html; 
            buildTOC(assistantWrap); 
            // Eğer önce meta geldi ise burada accordion ekle
            if(window.__lastPrecedentMeta && window.__lastPrecedentMeta.precedent_set_id === data.precedent_set_id){
                console.log('📚 Injecting accordion with stored meta');
                injectPrecedentAccordion(assistantWrap, window.__lastPrecedentMeta);
                delete window.__lastPrecedentMeta;
            } else if(data.precedent_set_id){
                console.log('📚 Injecting accordion with fetch', data.precedent_set_id);
                // Meta content ile aynı eventte geldiyse fetch ile tamamını ekle
                fetchAndInsertAccordionAfterContent(assistantWrap, data.precedent_set_id);
            }
            
            // Uzun içerik için otomatik daraltma (2000 karakter veya 20'den fazla satır)
            const lineCount = rawAcc.split('\n').length;
            const shouldCollapse = (rawAcc.length > 2000 || lineCount > 20) && !assistantWrap.dataset.collapseInit;
            
            if(shouldCollapse) { 
              assistantWrap.dataset.collapseInit='1'; 
              toggleCollapse(assistantWrap); 
            }
            
            scrollToBottom(); }
            
      // Eğer normal sohbet ise ve çıktı tamamlandıysa, altına "Daha detaylı analiz et" butonu ekleyelim
      if (data.complete && !isPetition && assistantWrap) {
        addMoreDetailButton(assistantWrap, lastUserMessage);
      }
          }catch(e){ /* yoksay */ }
        }
      }
  } catch(err){
    clearTimeout(abortTimeout);
    loadingWrap.remove();
    const errWrap=createAssistantMessageContainer();
    const errMsg = err.name === 'AbortError'
      ? '⏱️ İstek zaman aşımına uğradı (10 dk). Lütfen soruyu kısaltarak tekrar deneyin.'
      : escapeHtml(err.message);
    errWrap.querySelector('.markdown-content').innerHTML = `<div class="error-message">${errMsg}</div>`;
    qs('#messagesContainer').appendChild(errWrap);
  } finally {
    clearTimeout(abortTimeout);
    // Stream bittiğinde eğer stored precedent meta varsa accordion inject et
    if (window.__lastPrecedentMeta && assistantWrap) {
      console.log('📚 Stream ended, injecting stored meta accordion');
      injectPrecedentAccordion(assistantWrap, window.__lastPrecedentMeta);
      delete window.__lastPrecedentMeta;
    }
    
    isLoading=false; qs('#sendButton').disabled=false; qs('#sendButton').classList.remove('loading'); scrollToBottom(); qs('#messageInput').focus();
    // Dava analizi modunu açık bırak - sadece manuel olarak kapatılsın
    // Artık otomatik kapanmayacak
  }
}

// Karşılama mesajı
function loadChatHistory(){
  const sid = getSessionId();
  // Pinecone'dan geçmiş konuşmaları yüklemeye çalış
  fetch(`/chat-history?session_id=${encodeURIComponent(sid)}`)
    .then(r => r.json())
    .then(data => {
      const history = data.chat_history || [];
      if(history.length > 0) {
        // Geçmiş mesajları UI'a ekle
        console.log(`📜 ${history.length} geçmiş mesaj Pinecone'dan yüklendi`);
        // Karşılama mesajı
        const welcomeWrap = createAssistantMessageContainer();
        const welcomeMd = `👋 **Tekrar hoş geldiniz!** Önceki konuşmanız yüklendi (${history.length} mesaj).\n\nDevam edebilirsiniz.`;
        welcomeWrap.querySelector('[data-role="time"]').textContent = new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'});
        welcomeWrap.querySelector('.markdown-content').innerHTML = renderMarkdown(welcomeMd);
        buildTOC(welcomeWrap);
        qs('#messagesContainer').appendChild(welcomeWrap);
        // Son 20 mesajı göster (çok eski mesajları atla)
        const recentHistory = history.slice(-20);
        for(const msg of recentHistory) {
          if(msg.role === 'user') {
            addUserMessage(msg.content);
          } else if(msg.role === 'assistant') {
            const aWrap = createAssistantMessageContainer();
            aWrap.querySelector('[data-role="time"]').textContent = '';
            let html = renderMarkdown(msg.content);
            html = linkifyLawCitations(html);
            aWrap.querySelector('.markdown-content').innerHTML = html;
            buildTOC(aWrap);
            // Uzun içerik daralt
            if(msg.content.length > 2000) { aWrap.dataset.collapseInit='1'; toggleCollapse(aWrap); }
            qs('#messagesContainer').appendChild(aWrap);
          }
        }
        scrollToBottom();
      } else {
        // İlk kez geliyor - karşılama mesajı göster
        showWelcomeMessage();
      }
    })
    .catch(err => {
      console.warn('Geçmiş yüklenemedi:', err);
      showWelcomeMessage();
    });
}

function showWelcomeMessage() {
  const wrap=createAssistantMessageContainer(); const md=`👋 **Merhaba!** Ben hukuki AI danışmanınızım.

### Yapabileceklerim
- Hukuki sorularınızı yanıtlamak
- Yüklediğiniz dosyalardan özet ve bilgi çıkarmak
- Mevzuat hakkında bilgi sağlamak

Detaylı modda emsal kararlar ve web kaynaklarıyla destekli yanıtlar üretebilirim. Dilekçe oluşturmak için 📝 Dilekçe modunu kullanabilirsiniz.

Hazırsanız başlayalım!`; wrap.querySelector('[data-role="time"]').textContent = new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'}); wrap.querySelector('.markdown-content').innerHTML=renderMarkdown(md); buildTOC(wrap); qs('#messagesContainer').appendChild(wrap); scrollToBottom();
}

// Kaydedilen tercihleri yükle
function loadPrefs(){ try { const s=JSON.parse(localStorage.getItem('yargi_ai_prefs')||'{}'); if(s.dark) document.body.classList.add('theme-dark'); }catch(_){} }
function savePrefs(){ localStorage.setItem('yargi_ai_prefs', JSON.stringify({ dark: document.body.classList.contains('theme-dark') })); }

// Tema değiştirici
function toggleTheme() {
  document.body.classList.toggle('theme-dark');
  savePrefs();
}

function getSessionId(){ 
    console.log('Getting session ID...');
    // Önce cookie'den kontrol et
    const cookieMatch = document.cookie.match(/session_id=([^;]+)/); 
    if(cookieMatch) {
        console.log('Session ID from cookie:', cookieMatch[1]);
        // localStorage'a da yaz (senkronizasyon için)
        localStorage.setItem('session_id', cookieMatch[1]);
        return cookieMatch[1]; 
    }
    
    // localStorage'dan kontrol et
    const localStorageId = localStorage.getItem('session_id');
    if(localStorageId) {
        console.log('Session ID from localStorage:', localStorageId);
        // Cookie'ye de yaz (senkronizasyon için)
        document.cookie = `session_id=${localStorageId}; path=/; samesite=Lax`;
        return localStorageId;
    }
    
    // Yeni ID oluştur
    const newId = crypto.randomUUID();
    console.log('Generated new session ID:', newId);
    localStorage.setItem('session_id', newId);
    document.cookie = `session_id=${newId}; path=/; samesite=Lax`;
    return newId;
}

document.addEventListener('DOMContentLoaded',()=>{ loadPrefs(); loadChatHistory(); updateChatDetailVisibility(); // session cookie yoksa yeni al
  if(!document.cookie.includes('session_id=')){ fetch('/session/new').then(r=>r.json()).then(d=>{ if(d.session_id){ document.cookie = 'session_id='+d.session_id+'; path=/; samesite=Lax'; localStorage.setItem('session_id', d.session_id); }}).catch(()=>{}); }
  qs('#messageInput').focus(); });

window.addEventListener('beforeunload',()=>{ /* Session verisi Pinecone'da kalıcı - silme yapılmaz */ });

// Global'a bağla
window.autoResize=autoResize; window.handleKeyPress=handleKeyPress; window.togglePetition=togglePetition; window.handleFileSelect=handleFileSelect; window.sendMessage=sendMessage; window.toggleTheme=toggleTheme;
window.getSessionId=getSessionId; window.copyToClipboard=copyToClipboard; window.removeUploadedFile=removeUploadedFile;
window.addMoreDetailButton=addMoreDetailButton;

/* ===== Modal İşlevleri ===== */

// Eski üst aksiyon kaynak butonu kaldırıldı (kullanıcı sadece alttaki tek butonu istedi)

// Modal fonksiyonları kaldırıldı (inline gösterim yeterli)

/* ===== Inline Açılır Emsal Karar Bölümü ===== */

/* === Normal sohbet için Daha Detaylı Analiz butonu === */
function addMoreDetailButton(assistantWrap, messageText){
  const body = assistantWrap.querySelector('.assistant-body');
  if(!body) return;
  if(body.querySelector('.more-detail-wrap')) return;
  const wrap = document.createElement('div');
  wrap.className='more-detail-wrap';
  const btn = document.createElement('button');
  btn.type='button';
  btn.className='more-detail-btn';
  btn.textContent='🔎 Daha detaylı analiz et';
  btn.onclick = () => reaskDetailed(messageText);
  wrap.appendChild(btn);
  body.appendChild(wrap);
}

async function reaskDetailed(text){
  // Kısa/Detaylı seçicisini detaylıya al ve gönder
  const sel = qs('#chatDetailSelect');
  if(sel) sel.value = 'detailed';
  // Normal akıştan gönderelim
  qs('#messageInput').value = text;
  await sendMessage(new Event('submit'));
}

function injectPrecedentAccordion(assistantWrap, meta){
  try {
    const mdContent = assistantWrap.querySelector('.markdown-content');
    if(!mdContent) return;
  const container = document.createElement('div');
    container.className = 'precedent-accordion-container';
  const header = document.createElement('div');
    header.className = 'precedent-accordion-header';
  const q = meta.precedent_search_query ? `Arama: "${escapeHtml(meta.precedent_search_query)}"` : 'Emsal Kararlar';
  const count = (meta.precedent_meta && meta.precedent_meta.length) ? meta.precedent_meta.length : (meta.precedent_count || '');
  header.innerHTML = `<strong>📚 ${q}</strong> <span class='precedent-count'>(${count} adet)</span>`;

    const listWrap = document.createElement('div');
    listWrap.className = 'precedent-fullcard-list';
    listWrap.innerHTML = '<div class="precedent-loading">Emsal kararlar yükleniyor...</div>';

    container.appendChild(header);
    container.appendChild(listWrap);
    mdContent.parentElement.appendChild(container);

    const precedentUrl = `/chat-precedents/${getSessionId()}/${meta.precedent_set_id}`;
    console.log('📚 Fetching precedents from:', precedentUrl);
  fetch(precedentUrl).then(r=>{
      console.log('📚 Precedent response status:', r.status);
      return r.json();
    }).then(full=>{
      console.log('📚 Precedent response data:', full);
      if(!full.precedents) {
        console.warn('📚 No precedents found in response');
        listWrap.innerHTML = '<div class="precedent-loading">Emsal kararlar bulunamadı</div>';
        return;
      }
      const all = full.precedents || [];
      console.log('📚 Rendering', all.length, 'precedents');
      listWrap.innerHTML = all.map((p, idx)=>{
        console.log('📚 Precedent', idx, ':', {id: p.id, birim: p.birim, tarih: p.tarih, tur: p.tur});
        const fullText = p.content || '';
        const safe = escapeHtml(p.id||'');
        return `<div class='precedent-full-card'>
          <div class='precedent-full-card-head'>
            <span class='precedent-badge'>#${p.index}</span>
            <div class='precedent-full-title'>${safe}</div>
            <div class='precedent-full-meta'>${escapeHtml(p.birim||'')} • ${escapeHtml(p.tarih||'')} • ${escapeHtml(p.tur||'Karar')}</div>
          </div>
          <div class='precedent-full-text'>${escapeHtml(fullText.length>30000?fullText.slice(0,30000)+"\n... (kısaltıldı)":fullText)}</div>
        </div>`;
      }).join('');
    }).catch((error)=>{ 
      console.error('📚 Precedent fetch error:', error);
      listWrap.innerHTML = '<div class="precedent-loading">Emsal kararlar alınamadı</div>'; 
    });
  } catch(err){ console.error('injectPrecedentAccordion error', err); }
}

function fetchAndInsertAccordionAfterContent(assistantWrap, precedentSetId){
  console.log('📚 Fetching full precedent data for set:', precedentSetId);
  fetch(`/chat-precedents/${getSessionId()}/${precedentSetId}`).then(r=>r.json()).then(full=>{
    if(!full.precedents) {
      console.warn('📚 No precedents in response');
      return;
    }
    console.log('📚 Received full precedents:', full.precedents.length);
    const meta = {
      precedent_set_id: precedentSetId,
      precedent_meta: full.precedents.map(p=>({index:p.index,id:p.id,birim:p.birim,tarih:p.tarih,tur:p.tur})) ,
      precedent_count: full.precedent_count,
      precedent_search_query: full.search_query
    };
    injectPrecedentAccordion(assistantWrap, meta);
  }).catch((err)=>{
    console.error('📚 Error fetching precedent data:', err);
  });
}

// Dava analizi fonksiyonları kaldırıldı

// Bildirim göster
function showNotification(message, type = 'info') {
    // Basit notification sistemi
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        max-width: 300px;
    `;
    
    switch (type) {
        case 'success':
            notification.style.backgroundColor = '#22c55e';
            break;
        case 'error':
            notification.style.backgroundColor = '#ef4444';
            break;
        case 'warning':
            notification.style.backgroundColor = '#f59e0b';
            break;
        default:
            notification.style.backgroundColor = '#3b82f6';
    }
    
    document.body.appendChild(notification);
    
    // 3 saniye sonra kaldır
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Prompt güzelleştirme fonksiyonu
async function enhancePrompt() {
    console.log('🎯 enhancePrompt fonksiyonu çağrıldı');
    
    const messageInput = qs('#messageInput');
    const enhanceBtn = qs('.enhance-prompt-btn');
    
    if (!messageInput.value.trim()) {
        showNotification('⚠️ Önce bir mesaj yazın', 'warning');
        return;
    }
    
    console.log('📝 Prompt:', messageInput.value.trim());
    
    // Buton durumunu güncelle
    const originalText = enhanceBtn.innerHTML;
    enhanceBtn.disabled = true;
    enhanceBtn.innerHTML = '⏳';
    
    try {
        const formData = new FormData();
        formData.append('prompt', messageInput.value.trim());
        
        console.log('🚀 API isteği gönderiliyor...');
        
        const response = await fetch('/enhance-prompt', {
            method: 'POST',
            headers: {
                'Session-Id': getSessionId()
            },
            body: formData
        });
        
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📊 Response data:', data);
        
        if (data.success && data.enhanced) {
            // Güzelleştirilmiş prompt'u textarea'ya yerleştir
            messageInput.value = data.enhanced;
            autoResize(messageInput);
            showNotification('✨ Prompt güzelleştirildi!', 'success');
        } else {
            showNotification(`❌ ${data.error || 'Prompt güzelleştirilemedi'}`, 'error');
        }
        
    } catch (error) {
        console.error('❌ Prompt güzelleştirme hatası:', error);
        showNotification('❌ Bağlantı hatası', 'error');
    } finally {
        // Buton durumunu eski haline getir
        enhanceBtn.disabled = false;
        enhanceBtn.innerHTML = originalText;
    }
}