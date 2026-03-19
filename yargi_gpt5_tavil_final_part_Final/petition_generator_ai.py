#!/usr/bin/env python3
"""Dilekçe (Hukuki Başvuru / Dava Dilekçesi) Oluşturucu AI Modülü - Multi-Token Destekli

Bu modül kullanıcıdan ve önceki analiz çıktılarından elde edilen bilgileri kullanarak
Türkçe formatlı, profesyonel bir dava dilekçesi taslağı üretir.

KULLANIM:
    from petition_generator_ai import PetitionGeneratorAI
    ai = PetitionGeneratorAI()
    result = await ai.generate_petition(user_prompt, file_content=file_content)

GİRDİ KAYNAKLARI:
1. Kullanıcının son mesajı (amacı / talebi / dava türü)
2. Yüklenen dosya içeriği (dava raporu, ek belgeler vb.)

ÇIKTI:
    {
       "petition": "...markdown formatlı dilekçe...",
    "used_sections": {...},  # (Kullanılan bağlam bilgisi - artık sadece dosya var)
       "timestamp": "..."
    }

NOT: Çıktı sadece taslaktır; nihai hukuki kontrol gerektirir.

MULTI-TOKEN SİSTEMİ:
Bu modül PETITION_TOKEN kullanır, farklı dilekçe türleri için ayrı tokenlar eklenebilir.
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# AI Guard'dan petition token fonksiyonu import et - ZORUNLU
from ai_guard import safe_petition_ai_request
from prompts import build_petition_prompt
# post_processing kaldırıldı: dilekçe uyarısı formatting.standardize_output içinde sağlanıyor
from formatting import standardize_output

print("✅ Multi-token AI Guard sistemi yüklendi (Petition)")

load_dotenv()

_LEGACY_SYSTEM_PROMPT_REMOVED = "Merkezi prompts.build_petition_prompt kullanılıyor"


class PetitionGeneratorAI:
    """Dilekçe üretiminden sorumlu AI sarmalayıcı sınıf - Multi-Token Zorunlu"""

    def __init__(self):
        """Multi-token sistemi zorunlu"""
        self.use_multi_token = True  # Her zaman multi-token
        
        print("✅ PetitionGeneratorAI - Multi-token sistemi aktif (PETITION_TOKEN)")

    async def generate_petition(
        self,
        user_prompt: str,
        file_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dilekçe taslağı üret - Multi-token destekli

        Parametreler:
            user_prompt: Kullanıcının bu istekte belirttiği özel talep / yönlendirme
            file_content: Yüklenen dosyanın metni (dava raporu vb.)
        """
        try:
            # Sadece dosya içeriğini sınırlı ekle (chat geçmişi kaldırıldı)
            limited_file = (file_content or "")[:6000]

            # Merkezi prompt builder
            petition_prompt = build_petition_prompt(user_prompt=user_prompt, context_snippet=limited_file or "")
            
            petition_text = ""
            
            # Multi-token sistemi - zorunlu
            try:
                result = await safe_petition_ai_request(
                    system_prompt=petition_prompt,
                    user_message="Sadece dilekçe metnini üret.",
                    model="gpt-4o"
                )
                
                if "error" not in result:
                    petition_text = result.get("response", "").strip()
                    print(f"✅ Petition AI (Multi-Token) dilekçe oluşturuldu")
                else:
                    print(f"⚠️  Multi-token petition hatası: {result['error']}")
                    return {"error": f"Petition AI hatası: {result['error']}"}
            except Exception as e:
                print(f"⚠️  Multi-token petition exception: {e}")
                return {"error": f"Petition AI sistemi hatası: {str(e)}"}
            
            if not petition_text:
                return {"error": "Petition AI yanıt alamadı"}

            # ensure_petition_disclaimer kaldırıldı (post_processing silindi); standardize_output içinde ele alınacak
            petition_text = standardize_output(petition_text, kind="petition")
            return {
                "timestamp": datetime.now().isoformat(),
                "petition": petition_text,
                "used_sections": {"file_included": bool(file_content)},
                "meta": {"central_prompt": True}
            }
            
        except Exception as e:
            return {"error": f"Dilekçe oluşturma hatası: {str(e)}"}
