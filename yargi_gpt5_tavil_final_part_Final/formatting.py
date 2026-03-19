"""Merkezi çıktı formatlama katmanı.

Amaç: Tüm modüllerde (legal advisor, case analysis, petition) tutarlı ve
profesyonel Markdown çıktısı üretmek.

Katmanlar:
 1. Normalizasyon (görünmez karakter, satır sonları)
 2. Başlık hiyerarşisi sadeleştirme (#, ##, ###)
 3. Numara & liste biçim birliği (1) / 2) / - madde)
 4. Gereksiz tekrar temizliği (aynı başlık ardışık, üçten fazla boş satır)
 5. (Kaldırıldı) Eski hukuki analiz yapısı tamamlama katmanı
 6. Dilekçe yasal uyarı ekleme (artık bu dosyada basit kontrolle yapılabilir)

Not: Çok agresif regex uygulamalarını sınırda tutar; temel düzeni bozmadan
okunabilirliği artırır.
"""
from __future__ import annotations
import re
from typing import Literal

# post_processing.py kaldırıldığı için ilgili fonksiyonlar çıkarıldı

OutputKind = Literal["analysis", "advisor", "petition", "generic"]

_MULTI_NL = re.compile(r"\n{3,}")
_TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)

def _basic_normalize(text: str) -> str:
    if not text:
        return text
    # Satır sonları & görünmez karakterler
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", text)
    text = text.replace('\u00A0', ' ')
    return text

def _unify_headings(text: str) -> str:
    # Başlık başlangıcında gereksiz yıldız / sayısal önekleri sadeleştir
    def fix(line: str) -> str:
        raw = line.strip()
        if not raw:
            return line
        # *Başlık -> ### Başlık
        if raw.startswith('*') and len(raw) > 3 and raw[1].isalpha():
            raw = '### ' + raw.lstrip('*').strip()
        # 1. BAŞLIK -> ### 1) BAŞLIK (liste ile karışmasın)
        if re.match(r"^\d+\.\s+[A-ZÇĞİÖŞÜ]", raw):
            raw = re.sub(r"^(\d+)\.\s+", r"### \1) ", raw)
        return raw
    lines = [fix(l) for l in text.split('\n')]
    return '\n'.join(lines)

def _collapse_spaces(text: str) -> str:
    text = _MULTI_NL.sub('\n\n', text)
    text = _TRAILING_SPACE.sub('', text)
    return text.strip() + '\n'

def standardize_output(text: str, kind: OutputKind = "generic") -> str:
    """Merkezi standart çıktı üreticisi.

    kind:
      - analysis: Case analysis geniş çıktı (yapı + emsal placeholder olabilir)
      - advisor: Soru-cevap hukuki danışman
      - petition: Dilekçe taslağı
      - generic: Diğer kısa yanıtlar
    """
    if not text:
        return text
    original = text
    text = _basic_normalize(text)
    text = _unify_headings(text)
    # Eski temizleyici ile ince temizlik
    # Temel görsel markdown temizliği (eski clean_visual_markdown yerine basit regexler)
    text = re.sub(r"\n{4,}", "\n\n", text)
    text = re.sub(r"```+(\w+)?\n\n", "```\n", text)

    if kind in {"analysis", "advisor"}:
        # Eski ensure_legal_analysis_structure fonksiyonu kaldırıldı; ek işlem yok
        pass
    # Eski ensure_legal_analysis_structure kaldırıldı
    if kind == "petition":
        # Basit yasal uyarı eklemesi (post_processing kaldırıldı)
        if "hukuki danışmanlık" not in text.lower():
            text += "\n\n> Not: Bu çıktı hukuki danışmanlık değildir; nihai değerlendirme için yetkili bir avukata başvurulmalıdır.\n"
    # Bölünmüş başlık birleştirme (model iki satıra böldüyse)
    lines = text.split('\n')
    merged_lines: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        nxt = lines[i+1].strip() if i + 1 < len(lines) else ''
        # Başlık prefix'lerini sök
        def base(h: str) -> str:
            return h.lstrip('#').strip()
        cur_base = base(cur).lower()
        nxt_base = base(nxt).lower()
        if cur_base == 'çekirdek hukuki' and nxt_base == 'çekişme':
            merged_lines.append('### Çekirdek Hukuki Çekişme')
            i += 2
            continue
        merged_lines.append(lines[i])
        i += 1
    text = '\n'.join(merged_lines)
    # Son boşluk normalizasyonu
    text = _collapse_spaces(text)
    # Eğer tamamen kaybolduysa orijinali döndür (fail-safe)
    return text or original

__all__ = ["standardize_output", "OutputKind"]
