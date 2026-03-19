#!/usr/bin/env python3
"""
Emsal (precedent) sistemi test scripti.
Ne test eder:
1. Bedesten API bağlantısı ve arama
2. /chat endpoint - concise mod (emsal beklenmez)
3. /chat endpoint - detailed mod (emsal beklenir)
4. prepare_precedents_for_detailed_answer direkt çağrısı
"""
import asyncio
import sys
import os
import json
import requests
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "yargi_gpt5_tavil_final_part_Final"))

API_BASE = "http://localhost:8080"
TEST_SESSION = "test-emsal-" + os.urandom(4).hex()
TEST_QUESTION = "İşçinin kıdem tazminatı hakkı ne zaman doğar?"

def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ──────────────────────────────────────────────────────────────
# TEST 1: Bedesten API direkt bağlantı testi
# ──────────────────────────────────────────────────────────────
async def test_bedesten_direct():
    sep("TEST 1: Bedesten API direkt bağlantı")
    try:
        from bedesten_mcp_module.client import BedestenApiClient
        client = BedestenApiClient()
        print(f"✅ BedestenApiClient oluşturuldu")

        print(f"🔍 Arama yapılıyor: '{TEST_QUESTION[:50]}'")
        result = await client.search_documents_phrase_only(TEST_QUESTION)

        items = result.get("data", {}).get("emsalKararList", []) or []
        print(f"📊 Bulunan karar sayısı: {len(items)}")

        if items:
            print(f"✅ Bedesten çalışıyor! İlk karar:")
            p = items[0]
            print(f"   - birimAdi: {p.get('birimAdi')}")
            print(f"   - kararTarihi: {p.get('kararTarihi')}")
            print(f"   - documentId: {p.get('documentId') or p.get('documentID')}")

            # İlk kararın markdown içeriğini al
            doc_id = p.get("documentId") or p.get("documentID") or p.get("id")
            if doc_id:
                print(f"\n📄 Markdown içerik alınıyor: {doc_id}")
                md = await client.get_document_as_markdown(doc_id)
                content = md.markdown_content or ""
                print(f"   - İçerik uzunluğu: {len(content)} karakter")
                print(f"   - İlk 200 karakter: {content[:200]!r}")
            return True
        else:
            print(f"❌ Bedesten'den sonuç gelmedi! data: {str(result)[:300]}")
            return False
    except Exception as e:
        print(f"❌ Bedesten bağlantı hatası: {e}")
        traceback.print_exc()
        return False
    finally:
        try:
            await client.close_client_session()
        except:
            pass

# ──────────────────────────────────────────────────────────────
# TEST 2: prepare_precedents_for_detailed_answer direkt test
# ──────────────────────────────────────────────────────────────
async def test_prepare_precedents():
    sep("TEST 2: prepare_precedents_for_detailed_answer direkt")
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "yargi_gpt5_tavil_final_part_Final", ".env"))

        from precedent_service import prepare_precedents_for_detailed_answer

        print(f"🔍 Emsal hazırlanıyor: '{TEST_QUESTION}'")
        result = await prepare_precedents_for_detailed_answer(
            session_id=TEST_SESSION + "_direct",
            user_question=TEST_QUESTION
        )

        sq = result.get("search_query")
        selected = result.get("selected", [])
        stored = result.get("stored_ids", [])
        fallback = result.get("fallback_used")

        print(f"\n📊 Sonuçlar:")
        print(f"   - search_query: {sq!r}")
        print(f"   - selected count: {len(selected)}")
        print(f"   - stored_ids count: {len(stored)}")
        print(f"   - fallback_used: {fallback}")
        print(f"   - fallback_reason: {result.get('fallback_reason')}")
        print(f"   - total_fetched: {result.get('total_fetched')}")

        if selected:
            print(f"\n✅ Emsal kararlar bulundu!")
            for i, p in enumerate(selected[:3], 1):
                content = (p.get("markdown_content") or "")[:100]
                print(f"   [{i}] {p.get('birimAdi','?')} | {p.get('kararTarihi','?')} | içerik={len(p.get('markdown_content',''))}char")
            return True
        else:
            print(f"❌ Emsal karar bulunamadı!")
            print(f"   Tam result: {json.dumps(result, ensure_ascii=False, default=str)[:500]}")
            return False
    except Exception as e:
        print(f"❌ prepare_precedents hatası: {e}")
        traceback.print_exc()
        return False

# ──────────────────────────────────────────────────────────────
# TEST 3: /chat endpoint - concise mod
# ──────────────────────────────────────────────────────────────
def test_chat_concise():
    sep("TEST 3: /chat endpoint - CONCISE mod (emsal beklenmez)")
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            data={
                "message": TEST_QUESTION,
                "is_petition": "false",
                "chat_detail": "concise",
                "scan_precedents": "true",
            },
            headers={"session_id": TEST_SESSION + "_concise"},
            timeout=60
        )

        print(f"HTTP Status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"❌ Hata: {resp.text[:300]}")
            return False

        data = resp.json()
        response_obj = data.get("response", {})

        print(f"✅ Yanıt alındı (concise)")
        print(f"   - type: {response_obj.get('type')}")
        print(f"   - precedent_count: {response_obj.get('precedent_count', 'YOK')}")
        print(f"   - precedents_meta: {response_obj.get('precedents_meta', 'YOK')}")
        print(f"   - BEKLENEN: emsal YOK (concise modda emsal aranmaz)")

        has_prec = "precedent_count" in response_obj
        print(f"   - Emsal var mı: {has_prec} (concise modda olmamalı)")
        return True
    except Exception as e:
        print(f"❌ concise chat hatası: {e}")
        traceback.print_exc()
        return False

# ──────────────────────────────────────────────────────────────
# TEST 4: /chat endpoint - detailed mod
# ──────────────────────────────────────────────────────────────
def test_chat_detailed():
    sep("TEST 4: /chat endpoint - DETAILED mod (emsal beklenir)")
    print(f"⏳ Bu test 30-90 saniye sürebilir (Bedesten + AI çağrısı)...")
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            data={
                "message": TEST_QUESTION,
                "is_petition": "false",
                "chat_detail": "detailed",
                "scan_precedents": "true",
            },
            headers={"session_id": TEST_SESSION + "_detailed"},
            timeout=180
        )

        print(f"HTTP Status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"❌ Hata: {resp.text[:500]}")
            return False

        data = resp.json()
        response_obj = data.get("response", {})

        print(f"✅ Yanıt alındı (detailed)")
        print(f"   - type: {response_obj.get('type')}")

        prec_count = response_obj.get("precedent_count")
        prec_meta = response_obj.get("precedents_meta")
        prec_sq = response_obj.get("precedent_search_query")
        prec_set_id = response_obj.get("precedent_set_id")

        print(f"\n📊 Emsal bilgileri:")
        print(f"   - precedent_count: {prec_count!r}")
        print(f"   - precedent_search_query: {prec_sq!r}")
        print(f"   - precedent_set_id: {prec_set_id!r}")

        if prec_meta:
            print(f"   - precedents_meta ({len(prec_meta)} adet):")
            for p in prec_meta:
                print(f"     * [{p.get('index')}] {p.get('id')} | {p.get('birim')} | {p.get('tarih')}")
        else:
            print(f"   - precedents_meta: YOK ← SORUN BURADA")

        # Yanıt metninde emsal geçiyor mu?
        content = response_obj.get("content", "")
        emsal_keywords = ["emsal", "yargıtay", "kararı", "dairesi", "içtihat"]
        found_kw = [kw for kw in emsal_keywords if kw.lower() in content.lower()]
        print(f"\n   - Yanıtta emsal anahtar kelimeleri: {found_kw}")
        print(f"   - Yanıt uzunluğu: {len(content)} karakter")
        print(f"   - Yanıt önizleme: {content[:300]!r}")

        if prec_count and prec_count > 0:
            print(f"\n✅ EMSAL ÇALIŞIYOR: {prec_count} emsal bulundu")
            return True
        else:
            print(f"\n❌ EMSAL BULUNAMADI (detailed modda olması gerekiyordu)")
            print(f"\n   Tam response JSON (kısaltılmış):")
            safe_data = {k: v for k, v in data.items() if k != "chat_history"}
            print(json.dumps(safe_data, ensure_ascii=False, default=str, indent=2)[:1500])
            return False
    except requests.Timeout:
        print(f"❌ Timeout: 180 saniye içinde yanıt gelmedi")
        return False
    except Exception as e:
        print(f"❌ detailed chat hatası: {e}")
        traceback.print_exc()
        return False

# ──────────────────────────────────────────────────────────────
# TEST 5: safe_search_ai_request direkt test
# ──────────────────────────────────────────────────────────────
async def test_search_ai():
    sep("TEST 5: safe_search_ai_request - arama sorgusu üretimi")
    try:
        from ai_guard import safe_search_ai_request
        result = await safe_search_ai_request(
            system_prompt="Sen Türk hukuk uzmanısın. Tek satır JSON döndür: {\"search_query\": \"...\"}",
            user_message=f"Soru: {TEST_QUESTION}",
            model="gpt-4o-mini"
        )
        print(f"Sonuç: {result}")
        if "error" in result:
            print(f"❌ AI hatası: {result['error']}")
            return False
        print(f"✅ AI yanıtı: {result.get('response', '')[:200]}")
        return True
    except Exception as e:
        print(f"❌ safe_search_ai_request hatası: {e}")
        traceback.print_exc()
        return False

# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
async def main():
    print(f"\n{'#'*60}")
    print(f"  EMSAL SİSTEMİ KAPSAMLI TESTİ")
    print(f"  Session: {TEST_SESSION}")
    print(f"  API: {API_BASE}")
    print(f"  Soru: {TEST_QUESTION}")
    print(f"{'#'*60}")

    results = {}

    # 1. Bedesten direkt
    results["bedesten_direct"] = await test_bedesten_direct()

    # 2. AI search query
    results["search_ai"] = await test_search_ai()

    # 3. prepare_precedents direkt (sadece Bedesten çalışıyorsa)
    if results["bedesten_direct"]:
        results["prepare_precedents"] = await test_prepare_precedents()
    else:
        print("\n⚠️ Bedesten çalışmıyor, prepare_precedents testi atlandı")
        results["prepare_precedents"] = False

    # 4. API chat concise
    results["chat_concise"] = test_chat_concise()

    # 5. API chat detailed
    results["chat_detailed"] = test_chat_detailed()

    # Özet
    sep("TEST ÖZETI")
    all_ok = True
    for name, ok in results.items():
        status = "✅ GEÇTI" if ok else "❌ BAŞARISIZ"
        print(f"  {status}: {name}")
        if not ok:
            all_ok = False

    print(f"\n{'='*60}")
    if all_ok:
        print("✅ TÜM TESTLER BAŞARILI")
    else:
        print("❌ BAZI TESTLER BAŞARISIZ — yukarıdaki detaylara bakın")
    print('='*60)

if __name__ == "__main__":
    asyncio.run(main())
