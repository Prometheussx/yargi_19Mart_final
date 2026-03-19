#!/usr/bin/env python3
"""Tekil Hukuki Danışman AI - GPT-5 Optimized (YENİ)

ÖNCEKİ (KALDIRILDI): İki aşamalı evaluator + main model sistemi.
YENİ: Tek GPT-5 model; esnek kısa veya detaylı mod. Kalıp 11 başlık yok.

Mod seçimi:
  detail parametresi (kısa | concise | simple) => flex_concise
  detail parametresi (detaylı | detailed | uzun | full) => flex_detailed
"""

from __future__ import annotations
import asyncio
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from prompts import build_legal_analysis_prompt
from ai_guard import safe_main_ai_request
from formatting import standardize_output

load_dotenv()

DEFAULT_MAIN_MODEL = "gpt-5"           # Dava analizi ve detaylı yanıtlar
CONCISE_MODEL = "gpt-5"               # Kısa (concise) yanıtlar için

class SingleLegalAdvisor:
    def __init__(self):
        self.use_multi_token = True

    def _map_detail(self, detail: Optional[str]) -> str:
        if not detail:
            return "flex_concise"
        d = detail.lower()
        if d in {"detaylı", "detailed", "uzun", "full"}:
            return "flex_detailed"
        return "flex_concise"

    async def answer_question(self, query: str, detail: Optional[str] = None, context: str = "") -> str:
        mode = self._map_detail(detail)
        # Model seçimi: kısa (concise) için gpt-4o, detaylı için varsayılan gpt-5
        model = CONCISE_MODEL if mode == "flex_concise" else DEFAULT_MAIN_MODEL
        system_prompt = build_legal_analysis_prompt(
            user_question=query,
            context_snippet=context or "(Bağlam yok)",
            detail_level=detail or ("detaylı" if mode == "flex_detailed" else "kısa"),
            mode=mode
        )
        try:
            result = await safe_main_ai_request(
                system_prompt=system_prompt,
                user_message="Yukarıdaki esnek yönergelere göre cevabı üret.",
                model=model
            )
            if isinstance(result, dict) and "error" in result:
                return f"Hata: {result['error']}"
            raw = (result.get("response") if isinstance(result, dict) else str(result)).strip()
            return standardize_output(raw, kind="advisor")
        except Exception as e:
            return f"Sistem hatası: {e}"

    async def process_question(self, query: str, flex_mode: Optional[str] = None, context: str = "") -> Dict:
        # flex_mode geriye dönük parametre; doğrudan mod olarak kullan
        start = datetime.now()
        detail = "detaylı" if flex_mode == "flex_detailed" else "kısa"
        response = await self.answer_question(query, detail=detail, context=context)
        return {
            "query": query,
            "response": response,
            "mode": flex_mode or self._map_detail(detail),
            "total_time": (datetime.now() - start).total_seconds(),
            "timestamp": datetime.now().isoformat(),
        }

# Basit CLI
async def _cli():
    adv = SingleLegalAdvisor()
    print("Tekil Hukuki Danışman (çıkış: quit)")
    while True:
        q = input("Soru: ").strip()
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break
        ans = await adv.answer_question(q, detail="detaylı")
        print("\n--- YANIT ---\n" + ans + "\n--------------\n")

if __name__ == "__main__":
    asyncio.run(_cli())