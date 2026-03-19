#!/usr/bin/env python3
"""
Dava Dosyası Analiz AI Sistemi - YENİ TASARIM
Yeni Akış:
1. Dosya yükleme ve Vector DB
2. Kullanıcı sorusu -> AI arama metni üretir
3. 15 emsal karar bulunur ve Vector DB'ye eklenir
4. Frontend'de önce 15 emsal gösterilir
5. Sonra AI karşılaştırmalı analiz yapar
"""

import os
import asyncio
import json
import re
import sys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from prompts import build_case_search_prompt, build_legal_analysis_prompt  # centralized
from prompts import build_dynamic_party_case_prompt  # yeni: taraf & durum bazlı strateji
from formatting import standardize_output
from web_context import WebContextFetcher

# PDF ve dosya okuma desteği
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    print("⚠️  PyPDF2 kütüphanesi bulunamadı - PDF desteği yok")
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    print("⚠️  python-docx kütüphanesi bulunamadı - Word desteği yok")
    DOCX_AVAILABLE = False

# Bedesten emsal karar sistemi
try:
    from bedesten_mcp_module.client import BedestenApiClient
    BEDESTEN_AVAILABLE = True
except Exception:
    BEDESTEN_AVAILABLE = False

# AI Guard'dan multi-token fonksiyonları import et - ZORUNLU
from ai_guard import safe_search_ai_request, safe_case_analysis_ai_request

print("✅ Multi-token AI Guard sistemi yüklendi (Case Analysis)")

# Environment variables yükle
load_dotenv()

from vector_store import get_vector_store, new_session_id

class CaseAnalysisAI:
    """Yeni Dava Analiz AI Sistemi

    Yeni Akış:
    1. Kullanıcı dava dosyalarını yükler -> Vector DB'ye eklenir
    2. Kullanıcı soru sorar -> AI arama metni üretir  
    3. 15 emsal karar bulunur ve Vector DB'ye eklenir
    4. Frontend'de önce 15 emsal blok halinde gösterilir
    5. Sonra AI iki kaynağı (dava + emsaller) birleştirerek karşılaştırmalı analiz yapar
    """

    def __init__(self, session_id: Optional[str] = None):
        """AI sistemini başlat"""
        self.use_multi_token = True
        self.bedesten_client = BedestenApiClient() if BEDESTEN_AVAILABLE else None
        self.session_id = session_id or new_session_id()
        self.store = get_vector_store()
        print("✅ CaseAnalysisAI - Yeni Sistem Aktif")
        print(f"   🔹 Session: {self.session_id}")
        print("   🔹 Search Query AI: SEARCH_TOKEN")
        print("   🔹 Case Analysis AI: CASE_ANALYSIS_TOKEN")
        # Web search client (Tavily)
        self.web_fetcher = WebContextFetcher()

        # Arama metni üretme promptu
        self.search_query_prompt = """
Sen deneyimli bir Türk hukuk uzmanısın. Görevin kullanıcının sorusu ve dava dosyalarına dayanarak 
UYAP emsal dava sisteminde arama yapacak EN ETKİLİ arama metnini oluşturmak.

ARAMA METNİ STRATEJİSİ:
1. Kullanıcının sorusuna odaklan
2. Dava dosyasındaki ana olayları değerlendir
3. UYAP'ta sonuç getirecek anahtar kelimeler kullan
4. 5-12 kelimelik etkili arama metni

ARAMA METNİ İÇİN ÖNCELİKLER:
• Kullanıcının sorduğu ana konu
• Dava türü (tazminat, iş, ticaret vb.)
• Ana olay (kaza, ihmal, sözleşme ihlali vb.)
• Hukuki kavramlar (kusur, zarar, sorumluluk vb.)

ÇIKTI FORMATI (SADECE JSON):
{
    "search_text": "arama metni",
    "focus_area": "ana odak konusu", 
    "legal_concepts": ["kavram1", "kavram2"],
    "reasoning": "neden bu arama metni seçildi"
}
"""

    async def generate_search_query(self, case_text: str) -> Dict[str, Any]:
        """Dava metninden UYAP/Bedesten araması için arama cümlesi üretir.

        Dönüş: { 'search_query': str, ... } ya da { 'error': str }
        """
        try:
            prompt = build_case_search_prompt(case_text or "")
            # Search AI ile güvenli çağrı
            result = await safe_search_ai_request(
                system_prompt=prompt,
                user_message="Sadece tek satır JSON döndür.",
                model="gpt-5"
            )
            if isinstance(result, dict) and "error" in result:
                return {"error": result.get("error")}
            raw = (result.get("response") if isinstance(result, dict) else str(result)) or ""
            raw = raw.strip()
            # JSON parse et, code fence temizliği yap
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                cleaned = raw.replace('```json', '').replace('```', '').strip()
                data = json.loads(cleaned)
            # En azından search_query anahtarını bekliyoruz
            sq = (data.get("search_query") if isinstance(data, dict) else None)
            if not sq:
                return {"error": "search_query boş döndü", "raw": raw[:400]}
            out = {"search_query": sq}
            # Ek alanlar varsa geçir (geriye dönük uyumluluk için)
            for k in ("case_type", "main_subject", "legal_basis"):
                if k in data:
                    out[k] = data[k]
            return out
        except Exception as e:
            return {"error": f"Arama cümlesi üretim hatası: {str(e)}"}

    async def generate_search_text_from_question(self, user_question: str, case_content: str = "") -> Dict[str, Any]:
        """Kullanıcı sorusu ve dava dosyasından arama metni üret"""
        try:
            print("🔍 Kullanıcı sorusundan arama metni oluşturuluyor...")
            
            # Dava dosyası varsa kısalt
            case_summary = ""
            if case_content.strip():
                cleaned_case = self._clean_text(case_content)
                case_summary = cleaned_case[:2000]  # İlk 2000 karakter
            
            user_content = f"""
KULLANICI SORUSU:
{user_question}

DAVA DOSYASI ÖZETI (varsa):
{case_summary}

GÖREV: Bu kullanıcı sorusuna en uygun emsal kararları bulacak arama metnini oluştur.
UYAP'ın algoritması sonuçları getirecek, doğru anahtar kelimeler lazım.

SADECE JSON formatında yanıt ver.
"""
            
            response_text = ""
            
            # Multi-token sistemi ile arama metni üret
            if self.use_multi_token:
                try:
                    result = await safe_search_ai_request(
                        system_prompt=self.search_query_prompt,
                        user_message=user_content,
                        model="gpt-5"
                    )
                    
                    if "error" not in result:
                        response_text = result.get("response", "").strip()
                        print(f"✅ Arama metni AI yanıtı alındı")
                    else:
                        print(f"⚠️  Arama metni AI hatası: {result['error']}")
                except Exception as e:
                    print(f"⚠️  Arama metni AI exception: {e}")
            
            if not response_text:
                return {"error": "Arama metni üretilemedi", "stage": "search_text_generation"}
            
            # JSON parse et
            try:
                search_data = json.loads(response_text)
            except json.JSONDecodeError:
                cleaned = response_text.replace('```json', '').replace('```', '').strip()
                try:
                    search_data = json.loads(cleaned)
                except json.JSONDecodeError as je:
                    print(f"❌ JSON parse hatası: {je}")
                    return {"error": "JSON parse hatası", "detail": str(je), "raw": cleaned[:400]}
            
            return {
                "timestamp": datetime.now().isoformat(),
                "search_text": search_data.get("search_text", ""),
                "focus_area": search_data.get("focus_area", ""),
                "legal_concepts": search_data.get("legal_concepts", []),
                "reasoning": search_data.get("reasoning", "")
            }
            
        except Exception as e:
            return {"error": f"Arama metni oluşturma hatası", "detail": str(e)}

    async def fetch_15_precedents(self, search_text: str) -> Dict[str, Any]:
        """Bedesten'den emsal karar getir (15'ten 7'ye indirildi, daha hızlı)"""
        if not self.bedesten_client or not BEDESTEN_AVAILABLE:
            return {"error": "Bedesten sistemi kullanılamıyor", "precedents": []}

        try:
            print(f"🔍 Bedesten'den emsal karar alınıyor: '{search_text}'")

            # Bedesten'den arama yap
            raw = await self.bedesten_client.search_documents_phrase_only(search_text)
            base_items = raw.get('data', {}).get('emsalKararList', []) or []

            # İlk 7 kararı al (15'ten azaltıldı: 3 batch yerine 1 batch - ~3x hız artışı)
            selected = base_items[:7]

            print(f"✅ {len(selected)} karar bulundu, içerikleri paralel alınıyor...")

            # Her kararın içeriğini paralel al - semaphore 7'ye çıkarıldı (hepsi aynı anda)
            import asyncio as _asyncio
            sem = _asyncio.Semaphore(7)

            async def _fetch_one(i: int, item: dict):
                doc_id = item.get('documentId') or item.get('documentID') or item.get('id')
                entry = {
                    'index': i,
                    'documentId': doc_id,
                    'birimAdi': item.get('birimAdi', 'Bilinmeyen Birim'),
                    'kararTarihi': item.get('kararTarihi', 'Bilinmeyen Tarih'),
                    'itemType': item.get('itemType', {}).get('name') if isinstance(item.get('itemType'), dict) else item.get('itemType', 'Karar'),
                    'markdown_content': ''
                }
                if not doc_id:
                    return entry
                async with sem:
                    try:
                        md_doc = await self.bedesten_client.get_document_as_markdown(doc_id)
                        md_text = (md_doc.markdown_content or '').strip()
                        entry['markdown_content'] = md_text
                    except Exception as e:
                        entry['markdown_content'] = f'❌ Karar içeriği alınamadı: {str(e)}'
                        print(f"⚠️ Karar {doc_id} içeriği alınamadı: {e}")
                return entry

            tasks = [_asyncio.create_task(_fetch_one(i, item)) for i, item in enumerate(selected, 1)]
            # return_exceptions=True: tek bir fetch hatası tüm analizi çökertmez;
            # exception olan girişler None olarak işaretlenip skip edilir.
            raw_results = await _asyncio.gather(*tasks, return_exceptions=True)
            precedents = []
            for idx, res in enumerate(raw_results, 1):
                if isinstance(res, Exception):
                    print(f"⚠️ Karar {idx} fetch exception (atlandı): {res}")
                elif res is not None:
                    precedents.append(res)

            print(f"✅ {len(precedents)} emsal karar başarıyla alındı ({len(raw_results) - len(precedents)} hata atlandı)")

            return {
                'precedents': precedents,
                'total_found': len(precedents),
                'search_text': search_text,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ Bedesten arama hatası: {e}")
            return {"error": f"Emsal karar arama hatası: {str(e)}", "precedents": []}

    # Uyumluluk: app.py 'search_precedents' çağırıyor. Burada ham içerikleri dönen basit bir sarmalayıcı sağlıyoruz.
    async def search_precedents(self, search_query: str) -> Dict[str, Any]:
        """Compatibility method: returns raw precedents without any summarization or formatting."""
        res = await self.fetch_15_precedents(search_query)
        if "error" in res:
            return {"error": res["error"], "precedents": []}
        return {"precedents": res.get("precedents", []), "total_found": res.get("total_found", len(res.get("precedents") or [])), "search_text": res.get("search_text", search_query)}

    async def add_precedents_to_vector_db(self, precedents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """15 emsal kararı Vector DB'ye ekle"""
        try:
            print("🧮 Emsal kararları Vector DB'ye ekleniyor...")
            
            added_count = 0
            for precedent in precedents:
                doc_id = precedent.get('documentId')
                content = precedent.get('markdown_content', '')
                
                if doc_id and content.strip():
                    try:
                        await self.store.a_add_precedent(
                            session_id=self.session_id,
                            precedent_id=f"precedent_{doc_id}",
                            text=content
                        )
                        added_count += 1
                    except Exception as e:
                        print(f"⚠️ Emsal {doc_id} eklenemedi: {e}")
            
            print(f"✅ {added_count}/{len(precedents)} emsal karar Vector DB'ye eklendi")
            
            return {
                "success": True,
                "added_count": added_count,
                "total_precedents": len(precedents)
            }
            
        except Exception as e:
            return {"error": f"Vector DB ekleme hatası: {str(e)}"}

    def format_precedents_for_frontend(self, precedents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Emsal kararları frontend için formatla - tam içerik ile"""
        formatted = []
        
        for i, prec in enumerate(precedents, 1):
            # Tam içeriği al
            full_content = prec.get('markdown_content', '')
            
            # İlk birkaç paragrafı özetlemek için al (artık kullanılmayacak ama geriye dönük uyumluluk için)
            paragraphs = [p.strip() for p in full_content.split('\n\n') if p.strip()]
            summary = ''
            char_count = 0
            
            for para in paragraphs:
                if char_count + len(para) > 500:  # Kısa özet
                    break
                summary += para + '\n\n'
                char_count += len(para)
            
            if char_count < len(full_content):
                summary += "[...]"
            
            formatted.append({
                "index": i,
                "id": prec.get('documentId', f'karar_{i}'),
                "title": f"{prec.get('birimAdi', 'Bilinmeyen')} - {prec.get('kararTarihi', 'Tarih')}",
                "birim": prec.get('birimAdi', 'Bilinmeyen Birim'),
                "tarih": prec.get('kararTarihi', 'Bilinmeyen Tarih'),
                "tur": prec.get('itemType', 'Karar'),
                "summary": summary.strip(),
                "full_content": full_content,  # TAM İÇERİK - Bu artık direkt kullanılacak
                "is_expanded": False  # Frontend için
            })
        
        return formatted

    async def generate_comparative_analysis(
        self, 
        user_question: str, 
        case_content: str, 
        precedents: List[Dict[str, Any]],
        *,
        party: str = "tarafsız",
        status: str = "devam",
        web_sources: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Karşılaştırmalı analiz üret - Ana çıktı"""
        try:
            print("🔍 Karşılaştırmalı analiz üretiliyor...")
            
            # Dava dosyasını kısalt
            case_summary = self._clean_text(case_content)[:3000]
            
            # Emsal kararları özetle
            precedent_summaries = []
            for i, prec in enumerate(precedents, 1):
                content = prec.get('markdown_content', '')[:2000]  # Her emsal max 2000 kar
                summary = f"""
### EMSAL {i}: {prec.get('birimAdi', 'Bilinmeyen')} - {prec.get('kararTarihi', 'Tarih')}
**Tür:** {prec.get('itemType', 'Karar')}
**ID:** {prec.get('documentId', 'Bilinmeyen')}

**İçerik:**
{content}
"""
                precedent_summaries.append(summary)
            
            # Web kaynaklarını kısa özet haline getir
            web_section = ""
            if web_sources:
                lines = ["\n### 0. GÜNCEL MEVZUAT VE KAYNAKLAR"]
                for i, w in enumerate(web_sources[:6], 1):
                    title = (w.get('title') or '').strip() or 'Kaynak'
                    url = w.get('url') or ''
                    snippet = (w.get('content') or '')[:400]
                    lines.append(f"- ({i}) {title} — {url}\n  Özet: {snippet}")
                web_section = "\n".join(lines) + "\n\n"

            # Analiz promptu oluştur
            analysis_prompt = f"""
Sen kıdemli bir Türk hukuk uzmanısın. Görevin verilen dava dosyası ile emsal kararlar arasında 
KARŞILAŞTIRMALI ANALİZ yapmak.

ANALIZ PRENSİPLERİ:
1. "Davanızda bu vardı, bu emsal kararda şu vardı" şeklinde bağ kur
2. "Bu emsal şu yorumu yapıyor, sizin davanıza böyle uyarlanabilir" şeklinde öneriler sun
3. Gereksiz özet yapma, karşılaştırma ve uyarlama odaklı yaz
4. Her emsal için spesifik bağlantılar göster
5. Stratejik öneriler ver

KULLANICI SORUSU: {user_question}

DAVA DURUMU: {party} taraf, {status} aşamasında

ÇIKTIYı bu formatta ver:
## KARŞILAŞTIRMALI ANALİZ

{web_section}### 1. DAVA - EMSAL BAĞLANTILARI
[Her emsal için spesifik karşılaştırma]

### 2. EMSALLERİN YORUMLARI VE UYARLANMASI  
[Mahkeme yaklaşımları ve dava için uyarlama]

### 3. STRATEJİK ÖNERİLER
[Emsal temelli stratejiler]

### 4. RİSK DEĞERLENDİRMESİ
[Emsal kararlara dayalı riskler]
"""
            
            user_message = f"""
DAVA DOSYASI:
{case_summary}

EMSAL KARARLAR:
{"".join(precedent_summaries)}

GÜNCEL MEVZUAT KAYNAKLARI (web):
{web_section or '—'}

GÖREV: Bu dava dosyası ile emsal kararları karşılaştırarak yukarıda belirtilen formatta analiz üret.
"""
            
            # AI ile analiz üret
            result = await safe_case_analysis_ai_request(
                system_prompt=analysis_prompt,
                user_message=user_message,
                model="gpt-5"
            )
            
            if "error" in result:
                return {"error": f"Analiz üretimi hatası: {result['error']}"}
            
            analysis_text = result.get('response', '').strip()
            
            if not analysis_text:
                return {"error": "Analiz üretilemedi - boş yanıt"}
            
            # Standardize et
            try:
                analysis_text = standardize_output(analysis_text, kind="analysis")
            except Exception:
                pass
            
            return {
                "success": True,
                "analysis": analysis_text,
                "timestamp": datetime.now().isoformat(),
                "precedents_count": len(precedents),
                "user_question": user_question,
                "web_sources_used": bool(web_sources),
                "web_sources": web_sources or []
            }
            
        except Exception as e:
            return {"error": f"Karşılaştırmalı analiz hatası: {str(e)}"}

    async def full_pipeline(
        self, 
        user_question: str, 
        case_content: str = "",
        party: str = "tarafsız", 
        status: str = "devam"
    ) -> Dict[str, Any]:
        """Tam pipeline - yeni sistem akışı"""
        try:
            print("🚀 Yeni dava analiz sistemi başlatılıyor...")
            
            # 1. Dava dosyası Vector DB'ye eklenmiş olmalı (dışarıdan yapılır)

            # 2. Arama metni üretimi + Web bağlamı AYNI ANDA paralel başlat (hız optimizasyonu)
            web_query = WebContextFetcher.build_law_query(user_question, case_content[:800])

            async def _fetch_web():
                if self.web_fetcher and self.web_fetcher.enabled:
                    try:
                        return await self.web_fetcher.asearch(web_query, max_results=8, search_depth="advanced", days=3650)
                    except Exception as e:
                        return {"enabled": False, "error": str(e), "results": []}
                return {"enabled": False, "results": []}

            search_task = asyncio.create_task(self.generate_search_text_from_question(user_question, case_content))
            web_task = asyncio.create_task(_fetch_web())

            # İkisi paralel bekle
            search_result, web_data = await asyncio.gather(search_task, web_task)

            if "error" in search_result:
                return search_result

            search_text = search_result["search_text"]
            print(f"✅ Arama metni: {search_text}")

            # 3. Emsal karar bul (7 adet, hepsi aynı anda fetch edilir)
            precedents_result = await self.fetch_15_precedents(search_text)
            if "error" in precedents_result:
                return precedents_result

            precedents = precedents_result["precedents"]
            print(f"✅ {len(precedents)} emsal karar bulundu")

            if not precedents:
                return {"error": "Emsal karar bulunamadı"}

            # 4. Emsal kararları Vector DB'ye ekle
            vector_result = await self.add_precedents_to_vector_db(precedents)
            if "error" in vector_result:
                return vector_result
            
            # 5. Frontend için emsal formatla
            formatted_precedents = self.format_precedents_for_frontend(precedents)
            
            # 6. Karşılaştırmalı analiz üret
            analysis_result = await self.generate_comparative_analysis(
                user_question, case_content, precedents,
                party=party, status=status,
                web_sources=(web_data.get("results") if isinstance(web_data, dict) else None)
            )
            if "error" in analysis_result:
                return analysis_result
            
            print("✅ Yeni dava analiz sistemi tamamlandı")
            
            return {
                "success": True,
                "search_text": search_text,
                "search_reasoning": search_result.get("reasoning", ""),
                "precedents_raw": precedents,  # Ham emsal verisi
                "precedents_formatted": formatted_precedents,  # Frontend için
                "analysis": analysis_result["analysis"],  # Karşılaştırmalı analiz
                "web_sources": analysis_result.get("web_sources", []),
                "web_sources_used": analysis_result.get("web_sources_used", False),
                "precedents_count": len(precedents),
                "vector_added": vector_result["added_count"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Pipeline hatası: {str(e)}"}

    def read_file_content(self, file_path: str) -> str:
        """Dosya içeriğini oku - PDF, Word, TXT desteği"""
        try:
            file_path_obj = Path(file_path)
            file_extension = file_path_obj.suffix.lower()
            
            print(f"📄 Dosya okunuyor: {file_path_obj.name} ({file_extension})")
            
            if file_extension == '.pdf':
                return self._read_pdf(file_path)
            elif file_extension in ['.doc', '.docx']:
                return self._read_docx(file_path)
            elif file_extension in ['.txt', '.text']:
                return self._read_txt(file_path)
            else:
                # Varsayılan olarak text dosyası gibi oku
                return self._read_txt(file_path)
                
        except Exception as e:
            raise Exception(f"Dosya okuma hatası: {str(e)}")
    
    def _read_pdf(self, file_path: str) -> str:
        """PDF dosyasını oku"""
        if not PDF_AVAILABLE:
            raise Exception("PDF okuma desteği yok - PyPDF2 kütüphanesi gerekli")
        
        try:
            content = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                print(f"📄 PDF'de {len(pdf_reader.pages)} sayfa bulundu")
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            content += f"\n--- Sayfa {page_num} ---\n"
                            content += page_text
                    except Exception as e:
                        print(f"⚠️ Sayfa {page_num} okuma hatası: {e}")
                        
            if not content.strip():
                raise Exception("PDF'den metin çıkarılamadı")
                
            print(f"✅ PDF başarıyla okundu ({len(content)} karakter)")
            return content
            
        except Exception as e:
            raise Exception(f"PDF okuma hatası: {str(e)}")
    
    def _read_docx(self, file_path: str) -> str:
        """Word dosyasını oku"""
        if not DOCX_AVAILABLE:
            raise Exception("Word okuma desteği yok - python-docx kütüphanesi gerekli")
        
        try:
            doc = Document(file_path)
            content = ""
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content += paragraph.text + "\n"
            
            if not content.strip():
                raise Exception("Word dosyasından metin çıkarılamadı")
            
            print(f"✅ Word dosyası başarıyla okundu ({len(content)} karakter)")
            return content
            
        except Exception as e:
            raise Exception(f"Word okuma hatası: {str(e)}")
    
    def _read_txt(self, file_path: str) -> str:
        """Text dosyasını oku — UTF-8, cp1254 (Türkçe Windows), iso-8859-9, latin-1 sırasıyla dene"""
        encodings = ['utf-8', 'cp1254', 'iso-8859-9', 'latin-1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc, errors='strict') as f:
                    content = f.read()
                if not content.strip():
                    raise Exception("Dosya boş")
                print(f"✅ Text dosyası başarıyla okundu ({len(content)} karakter, encoding={enc})")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise Exception(f"Text okuma hatası: {str(e)}")
        raise Exception("Dosya hiçbir desteklenen encoding ile okunamadı (utf-8, cp1254, iso-8859-9, latin-1)")

    def _clean_text(self, text: str) -> str:
        """Metni temizle — Türkçe karakterleri koru."""
        if not text:
            return ""

        # Görünmez/kontrol karakterlerini kaldır (tab ve newline hariç)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Fazla boşlukları normalize et (satır sonlarını koru)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

# Ana işlem fonksiyonu - YENİ SİSTEM İÇİN
async def analyze_case_with_new_system(
    user_question: str,
    case_content: str = "",
    session_id: Optional[str] = None,
    *,
    party: str = "tarafsız",
    status: str = "devam"
) -> Dict[str, Any]:
    """Yeni sistemle dava analizi - Frontend entegrasyonu için"""
    try:
        # AI sistemini başlat
        analyzer = CaseAnalysisAI(session_id=session_id)

        # Tam pipeline çalıştır
        result = await analyzer.full_pipeline(
            user_question=user_question,
            case_content=case_content,
            party=party,
            status=status
        )

        return result
        
    except Exception as e:
        return {"error": f"Yeni sistem analiz hatası: {str(e)}"}


# ESKİ SİSTEM FONKSİYONLARI - GERİYE DÖNÜK UYUMLULUK İÇİN
async def analyze_case_file(
    file_path: str,
    session_id: Optional[str] = None,
    *,
    party: str = "tarafsız",
    status: str = "devam",
    user_question: str = ""
) -> Dict[str, Any]:
    """ESKİ SİSTEM - Geriye dönük uyumluluk için"""
    try:
        # Dosyayı oku
        analyzer = CaseAnalysisAI(session_id=session_id)
        case_content = analyzer.read_file_content(file_path)

        if not case_content.strip():
            return {"error": "Dava dosyası boş"}

        # Eğer kullanıcı sorusu yoksa varsayılan soru kullan
        if not user_question.strip():
            user_question = "Bu dava dosyasının detaylı analizi, riskler, fırsatlar ve stratejik öneriler nelerdir?"

        # Yeni sistemle analiz et
        result = await analyze_case_with_new_system(
            user_question=user_question,
            case_content=case_content,
            session_id=session_id,
            party=party,
            status=status
        )

        return result
        
    except Exception as e:
        return {"error": f"Dosya analiz hatası: {str(e)}"}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Kullanım: python case_analysis_ai_simple.py <dava_dosyasi_yolu>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    result = asyncio.run(analyze_case_file(file_path))
    
    if "error" in result:
        print(f"❌ Hata: {result['error']}")
    else:
        print(f"🎉 Başarılı!")
        print(f"📝 Analiz: {result.get('analysis', 'Analiz bulunamadı')[:200]}...")
        print(f"🔍 Emsal sayısı: {result.get('precedents_count', 0)}")
        print(f"📊 Arama metni: {result.get('search_text', 'Bulunamadı')}")
