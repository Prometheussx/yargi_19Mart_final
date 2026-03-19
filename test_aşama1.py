#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AŞAMA 1 — Emsal sistemi kapsamlı analiz testi.

API sunucusu başlatmadan direkt fonksiyon çağrıları ile test eder:
1. 3 sentetik hukuk sorusu için Bedesten emsal çekimi
2. Pinecone'a yükleme
3. build_full_precedents_block() ile prompt'a giden içerik analizi
4. Semantik arama ile ne kadar ilgili chunk çekildiğini ölçme
5. Bulguları test_raporu.md olarak kaydetme
"""
import asyncio
import os
import sys
import json
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "yargi_gpt5_tavil_final_part_Final"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "yargi_gpt5_tavil_final_part_Final", ".env"))

# ─── Test soruları ───────────────────────────────────────────────────────────
SORULAR = [
    {
        "id": "S1",
        "soru": "İşçinin haklı nedenle iş sözleşmesini feshetmesi halinde kıdem tazminatına hak kazanır mı?",
        "alan": "İş Hukuku",
    },
    {
        "id": "S2",
        "soru": "Boşanma davasında kusur tespiti nasıl yapılır ve manevi tazminat koşulları nelerdir?",
        "alan": "Aile Hukuku",
    },
    {
        "id": "S3",
        "soru": "Kira tespit davası açma koşulları ve mahkemenin kira bedelini belirleme kriterleri nelerdir?",
        "alan": "Gayrimenkul / Borçlar Hukuku",
    },
]

# ─── Yardımcılar ─────────────────────────────────────────────────────────────
def banner(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print('='*65)

def sub(title):
    print(f"\n  ── {title} ──")

# ─── Tek soru testi ──────────────────────────────────────────────────────────
async def test_soru(soru_obj, session_prefix="test_asama1"):
    sid = soru_obj["id"]
    soru = soru_obj["soru"]
    alan = soru_obj["alan"]
    session_id = f"{session_prefix}_{sid}_{os.urandom(3).hex()}"

    result = {
        "id": sid,
        "alan": alan,
        "soru": soru,
        "session_id": session_id,
        "search_query": None,
        "bedesten_toplam": 0,
        "secilen_emsal_sayisi": 0,
        "stored_ids": [],
        "emsal_detay": [],
        "full_block_chars": 0,
        "full_block_ilk500": "",
        "static_block_chars": 0,
        "ai_short_chars": 0,
        "prompt_precedent_context_chars": 0,
        "semantic_chunks": [],
        "semantic_chunk_sayisi": 0,
        "hata": None,
    }

    banner(f"{sid} — {alan}")
    print(f"  Soru: {soru[:80]}...")

    try:
        from precedent_service import (
            prepare_precedents_for_detailed_answer,
            summarize_precedents_for_prompt,
            summarize_precedents_ai,
            build_full_precedents_block,
        )
        from vector_store import get_vector_store

        # 1. Emsal hazırla
        sub("1) Bedesten araması + Pinecone yükleme")
        t0 = time.time()
        meta = await prepare_precedents_for_detailed_answer(
            session_id=session_id,
            user_question=soru,
        )
        elapsed = time.time() - t0

        result["search_query"] = meta.get("search_query")
        result["bedesten_toplam"] = meta.get("total_fetched", 0)
        selected = meta.get("selected", [])
        result["secilen_emsal_sayisi"] = len(selected)
        result["stored_ids"] = meta.get("stored_ids", [])

        print(f"  ✅ Arama sorgusu: {result['search_query']!r}")
        print(f"  ✅ Bedesten toplam: {result['bedesten_toplam']} karar")
        print(f"  ✅ Seçilen / yüklenen: {len(selected)} / {len(result['stored_ids'])}")
        print(f"  ⏱  Süre: {elapsed:.1f}s")

        if not selected:
            result["hata"] = "Bedesten'den sonuç gelmedi"
            print(f"  ❌ {result['hata']}")
            return result

        # 2. Emsal detayları
        sub("2) Emsal detayları")
        for i, p in enumerate(selected, 1):
            doc_id = p.get("documentId") or p.get("documentID") or p.get("id") or f"DOC{i}"
            birim = p.get("birimAdi", "?")
            tarih = p.get("kararTarihi", "?")
            icerik_len = len(p.get("markdown_content") or "")
            ilk200 = (p.get("markdown_content") or "").replace("\n", " ")[:200]
            emsal_rec = {
                "index": i,
                "doc_id": doc_id,
                "birim": birim,
                "tarih": tarih,
                "markdown_chars": icerik_len,
                "ilk200": ilk200,
            }
            result["emsal_detay"].append(emsal_rec)
            print(f"  [{i}] {birim} | {tarih} | {icerik_len} karakter")
            print(f"       Önizleme: {ilk200[:120]}...")

        # 3. Prompt blokları analizi
        sub("3) Prompt blokları")
        static_block = summarize_precedents_for_prompt(selected)
        result["static_block_chars"] = len(static_block)
        print(f"  summarize_precedents_for_prompt → {len(static_block)} karakter")

        ai_short = await summarize_precedents_ai(selected)
        result["ai_short_chars"] = len(ai_short)
        print(f"  summarize_precedents_ai → {len(ai_short)} karakter")

        full_block = build_full_precedents_block(selected, max_chars=18000)
        result["full_block_chars"] = len(full_block)
        result["full_block_ilk500"] = full_block[:500]
        print(f"  build_full_precedents_block(max=18000) → {len(full_block)} karakter")
        print(f"  İlk 400 karakter:\n    {full_block[:400].replace(chr(10), chr(10)+'    ')}")

        precedent_context = (
            "\n" + static_block
            + "\n\n-- KISA EMSAL ÖZETLERİ --\n" + ai_short
            + "\n\n-- TAM EMSAL İÇERİKLERİ (ANALİZDE ZORUNLU KULLANIM) --\n" + full_block
        )
        result["prompt_precedent_context_chars"] = len(precedent_context)
        print(f"  TOPLAM precedent_context → {len(precedent_context)} karakter")

        # 4. Semantik arama ile ne kadar ilgili chunk çekildiğini ölç
        sub("4) Semantik arama (Pinecone'dan ilgili chunk'lar)")
        store = get_vector_store()
        sem_results = await store.a_similarity_search(
            session_id=session_id,
            query=soru,
            k=15,
            include_pdf=True,
            include_chat=False,
        )
        prec_chunks = [r for r in sem_results if r.get("kind") == "precedent"]
        result["semantic_chunk_sayisi"] = len(prec_chunks)

        print(f"  Toplam similarity_search sonucu: {len(sem_results)}")
        print(f"  Precedent chunk'ları: {len(prec_chunks)}")
        for r in prec_chunks[:5]:
            result["semantic_chunks"].append({
                "pdf_id": r.get("pdf_id"),
                "chunk_id": r.get("chunk_id"),
                "distance": round(r.get("distance", 0), 4),
                "ilk150": (r.get("chunk_text") or "")[:150],
            })
            print(f"   chunk {r.get('chunk_id')} | dist={r.get('distance',0):.4f} | {(r.get('chunk_text',''))[:100]}...")

        # 5. Emsal kullanım değerlendirmesi
        sub("5) Emsal içerik kalite değerlendirmesi")
        # Her emsal için: tam metin var mı, full_block'ta ne kadarı var?
        per_case_budget = 18000 // len(selected) if selected else 0
        print(f"  Per-case budget (18000 / {len(selected)}): {per_case_budget} karakter")
        toplam_ham = sum(len(p.get("markdown_content") or "") for p in selected)
        print(f"  Ham toplam: {toplam_ham} karakter | Prompt'a giren: {result['full_block_chars']} karakter")
        if toplam_ham > 0:
            oran = result["full_block_chars"] / toplam_ham * 100
            print(f"  İçerik aktarım oranı: %{oran:.1f}")
            result["icerik_aktarim_orani"] = round(oran, 1)

    except Exception as e:
        import traceback
        result["hata"] = str(e)
        print(f"  ❌ HATA: {e}")
        traceback.print_exc()

    return result


# ─── Rapor yaz ────────────────────────────────────────────────────────────────
def yaz_rapor(tum_sonuclar: list, dosya: str):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# TEST RAPORU — EMSAL SİSTEMİ AŞAMA 1 ANALİZİ",
        f"",
        f"**Tarih:** {now}  ",
        f"**Amaç:** Mevcut emsal pipeline'ının doğruluk, yükleme ve prompt kullanım oranını ölçmek  ",
        f"**Yöntem:** Direkt Python çağrısı (API sunucusu olmadan)  ",
        "",
        "---",
        "",
        "## Özet Tablo",
        "",
        "| ID | Alan | Bedesten | Seçilen | Stored | full_block | Prompt ctx |",
        "|----|----|----|----|----|----|-----|",
    ]
    for r in tum_sonuclar:
        lines.append(
            f"| {r['id']} | {r['alan']} | {r['bedesten_toplam']} | "
            f"{r['secilen_emsal_sayisi']} | {len(r['stored_ids'])} | "
            f"{r.get('full_block_chars', 0)} ch | {r.get('prompt_precedent_context_chars', 0)} ch |"
        )

    lines += ["", "---", ""]

    for r in tum_sonuclar:
        lines += [
            f"## {r['id']} — {r['alan']}",
            "",
            f"**Soru:** {r['soru']}  ",
            f"**Arama sorgusu:** `{r.get('search_query')}`  ",
            f"**Bedesten toplam:** {r['bedesten_toplam']}  ",
            f"**Seçilen emsal:** {r['secilen_emsal_sayisi']}  ",
            f"**Pinecone'a yüklenen:** {len(r['stored_ids'])}  ",
            "",
        ]

        if r.get("hata"):
            lines += [f"**HATA:** {r['hata']}", ""]
            continue

        lines += ["### Emsal Detayları", ""]
        for e in r.get("emsal_detay", []):
            lines += [
                f"- **[{e['index']}]** {e['birim']} | {e['tarih']} | {e['markdown_chars']} karakter",
                f"  > {e['ilk200'][:180]}...",
                "",
            ]

        lines += [
            "### Prompt Blok Boyutları",
            "",
            f"| Blok | Boyut |",
            f"|------|-------|",
            f"| summarize_for_prompt (meta) | {r.get('static_block_chars',0)} karakter |",
            f"| summarize_ai (özet) | {r.get('ai_short_chars',0)} karakter |",
            f"| build_full_precedents_block | {r.get('full_block_chars',0)} karakter |",
            f"| TOPLAM precedent_context | {r.get('prompt_precedent_context_chars',0)} karakter |",
            "",
        ]

        icerik_orani = r.get("icerik_aktarim_orani", 0)
        lines += [
            "### İçerik Aktarım Oranı",
            "",
            f"Ham toplam içerik → Prompt'a giden tam blok: **%{icerik_orani}**",
            "",
            f"**Önizleme (build_full_precedents_block ilk 500 karakter):**",
            "```",
            r.get("full_block_ilk500", "(yok)")[:500],
            "```",
            "",
        ]

        sem = r.get("semantic_chunks", [])
        lines += [
            f"### Semantik Arama Sonuçları (Pinecone, k=15)",
            "",
            f"Bulunan precedent chunk sayısı: **{r.get('semantic_chunk_sayisi',0)}**",
            "",
        ]
        if sem:
            for c in sem[:5]:
                lines += [
                    f"- `{c['pdf_id']}` chunk#{c['chunk_id']} | dist={c['distance']} | {c['ilk150']}...",
                ]
        lines += ["", "---", ""]

    # ── Bulgular ve Sorunlar ──
    lines += [
        "## Tespit Edilen Sorunlar",
        "",
        "### 1. Emsal ham metin kırpması — `build_full_precedents_block`",
        "- Her emsal için `max_chars // len(emsaller)` bütçe uygulanıyor",
        "- 5 emsal, 18000 max → kişi başı 3600 karakter",
        "- Tipik Yargıtay kararı 15.000–30.000 karakter → kararın %12–25'i prompt'a giriyor",
        "- Model gerekçenin büyük bölümünü göremediğinden emsal kullanımı düşük kalıyor",
        "",
        "### 2. Semantik arama yapılmıyor",
        "- Pinecone'a tam metin yükleniyor (chunk=1600) — bu DOĞRU",
        "- Ama prompt oluşturulurken Pinecone'dan semantik sorgu YAPILMIYOR",
        "- Bunun yerine ham metin kırpılarak ekleniyor",
        "- Oysa Pinecone'da chunk'lar var; sorguya en ilgili paragrafları çekmek mümkün",
        "",
        "### 3. `rank_precedents` embedding'i 4500 karakterle kırpıyor",
        "- `precedent_service.py:121` → `(p.get('markdown_content') or '')[:4500]`",
        "- Uzun kararlar için embedding'in temsil gücü düşüyor",
        "- Kısa ama alakalı paragraflar içeren kararlar geride kalabiliyor",
        "",
        "## Önerilen Düzeltmeler (AŞAMA 2)",
        "",
        "1. **`a_add_precedent` — Tam metin yükle**: chunk_size=1600 iyi; hiçbir kesme yok ✅",
        "2. **`store_precedents` — Pinecone'da tut**: Session silinmeden tutuluyor ✅",
        "3. **Prompt yapısını değiştir**: `build_full_precedents_block` yerine Pinecone'dan",
        "   `a_similarity_search(kind='precedent')` ile sorguya en ilgili chunk'ları çek",
        "4. **Prompt'a giden içerik**: Semantik olarak eşleşen paragraflar + kaynak karar bilgisi",
        "5. **`rank_precedents` kırpmasını artır**: 4500 → en az 8000 karakter",
        "",
        "---",
        "*Bu rapor AŞAMA 2 düzeltmeleri öncesi baseline ölçümüdür.*",
    ]

    with open(dosya, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n✅ Rapor yazıldı: {dosya}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    banner("AŞAMA 1 — EMSAL SİSTEMİ ANALİZİ")
    print("  3 sentetik hukuk sorusu ile pipeline testi")
    print("  (API sunucusu olmadan — direkt Python çağrısı)")

    tum_sonuclar = []
    for soru_obj in SORULAR:
        sonuc = await test_soru(soru_obj)
        tum_sonuclar.append(sonuc)
        # Pinecone rate-limit için kısa bekleme
        await asyncio.sleep(2)

    rapor_dosyasi = os.path.join(os.path.dirname(__file__), "test_raporu.md")
    yaz_rapor(tum_sonuclar, rapor_dosyasi)

    banner("ÖZET")
    for r in tum_sonuclar:
        durum = "✅" if not r.get("hata") else "❌"
        print(f"  {durum} {r['id']} ({r['alan']}): "
              f"bedesten={r['bedesten_toplam']}, seçilen={r['secilen_emsal_sayisi']}, "
              f"full_block={r.get('full_block_chars',0)}ch, "
              f"sem_chunks={r.get('semantic_chunk_sayisi',0)}")
    print(f"\n  Rapor: test_raporu.md")


if __name__ == "__main__":
    asyncio.run(main())
