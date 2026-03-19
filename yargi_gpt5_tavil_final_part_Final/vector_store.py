"""Session scoped Pinecone vector store.

ÖNCEKİ: FAISS tabanlı `SessionFAISSStore` vardı. Bu dosya tamamen
Pinecone tabanlı hale getirildi ve aynı halka açık fonksiyon imzaları
korundu (geri uyum için).

Sağlanan API:
    - get_vector_store()
    - new_session_id()
    - add_pdf / a_add_pdf
    - add_chat_message / a_add_chat_message
    - add_chat_history / a_add_chat_history
    - get_chat_history
    - similarity_search / a_similarity_search
    - remove_pdf / a_remove_pdf
    - delete_session / a_delete_session

Yeni yardımcı:
    - trim_session_vectors_top_k(session_id, keep_ids)

ENV değişkenleri:
    OPENAI_API_KEY (zorunlu)
    PINECONE_API_KEY (zorunlu)
    PINECONE_INDEX_NAME (varsayılan: yargi-ai)
    PINECONE_REGION (varsayılan: eu-west-1)
    PINECONE_CLOUD (varsayılan: aws)
"""

from __future__ import annotations

import os
import uuid
import asyncio
import re
import hashlib
import time
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
import sqlite3
import json as _json

from dotenv import load_dotenv  # type: ignore

load_dotenv()

try:
    from openai import OpenAI, AsyncOpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore
    AsyncOpenAI = None  # type: ignore

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
except Exception:  # pragma: no cover
    RecursiveCharacterTextSplitter = None  # type: ignore

try:
    from pinecone import Pinecone, ServerlessSpec  # type: ignore
except Exception:  # pragma: no cover
    Pinecone = None  # type: ignore
    ServerlessSpec = None  # type: ignore

EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")  # 3072 (large) / 1536 (small)
DEFAULT_INDEX = os.getenv("PINECONE_INDEX_NAME", "yargiaifinall")
EMBED_CACHE_PATH = os.getenv("EMBEDDING_CACHE_PATH", os.path.join(os.getcwd(), "emb_cache.sqlite"))


class PineconeSessionStore:
    def __init__(self):
        # Pinecone client & basic state
        if Pinecone is None:
            raise RuntimeError("pinecone-client kurulu değil. requirements.txt'e ekleyin.")
        if not os.getenv("PINECONE_API_KEY"):
            raise RuntimeError("PINECONE_API_KEY tanımlı değil.")
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = DEFAULT_INDEX
        self._index = None
        self._embedding_dim = None  # type: Optional[int]
        self._id_map = {}  # orijinal -> sanitized (original -> safe)
        # Reusable OpenAI clients for embeddings
        self._emb_client = None
        self._emb_async_client = None
        # Initialize embedding cache (sqlite)
        self._emb_cache_conn = None
        try:
            self._emb_cache_conn = sqlite3.connect(EMBED_CACHE_PATH, check_same_thread=False)
            cur = self._emb_cache_conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS emb_cache (
                  k TEXT PRIMARY KEY,
                  model TEXT NOT NULL,
                  created_at INTEGER NOT NULL,
                  embedding TEXT NOT NULL
                )
                """
            )
            self._emb_cache_conn.commit()
        except Exception as _e:
            print(f"[VectorStore] Embedding cache devre dışı: {_e}")
            self._emb_cache_conn = None

    # -------------- Batched Upsert Helpers (Pinecone 4MB limit) --------------
    _UPSERT_BATCH_SIZE = 50  # vectors per batch – keeps well under 4 MB

    def _batched_upsert(self, vectors: list) -> None:
        """Synchronous upsert in batches to stay under Pinecone message-size limit."""
        bs = self._UPSERT_BATCH_SIZE
        for start in range(0, len(vectors), bs):
            self._index.upsert(vectors=vectors[start:start + bs])  # type: ignore

    async def _a_batched_upsert(self, vectors: list) -> None:
        """Async upsert in batches to stay under Pinecone message-size limit.

        Tüm batch'ler asyncio.gather ile aynı anda gönderilir; sıralı bekleme yerine
        paralel upsert ile gecikme düşer.
        """
        bs = self._UPSERT_BATCH_SIZE
        batches = [vectors[start:start + bs] for start in range(0, len(vectors), bs)]
        await asyncio.gather(
            *[asyncio.to_thread(self._index.upsert, vectors=b) for b in batches]  # type: ignore
        )

    @staticmethod
    def _get_openai_key_for_embeddings() -> Optional[str]:
        """Embedding için uygun OpenAI API key'i bulur.

        Öncelik sırası:
        1) OPENAI_API_KEY
        2) OPENAI_API_KEY_GENERAL
        3) OPENAI_API_KEY_MAIN
        4) OPENAI_API_KEY_SEARCH
        5) OPENAI_API_KEY_CASE_ANALYSIS
        6) OPENAI_API_KEY_PETITION
        """
        candidate_envs = [
            "OPENAI_API_KEY",
            "OPENAI_API_KEY_GENERAL",
            "OPENAI_API_KEY_MAIN",
            "OPENAI_API_KEY_SEARCH",
            "OPENAI_API_KEY_CASE_ANALYSIS",
            "OPENAI_API_KEY_PETITION",
        ]
        for name in candidate_envs:
            val = os.getenv(name)
            if val and not val.strip().startswith("sk-YOUR-"):
                return val.strip()
        return None

    def _get_emb_clients(self):
        """Create and cache OpenAI embedding clients once per process."""
        key = PineconeSessionStore._get_openai_key_for_embeddings()
        if not key:
            raise RuntimeError(
                "OpenAI API anahtarı bulunamadı. Lütfen .env dosyanıza 'OPENAI_API_KEY' veya 'OPENAI_API_KEY_GENERAL' (ya da MAIN/SEARCH/CASE_ANALYSIS/PETITION) ekleyin."
            )
        if self._emb_client is None and OpenAI is not None:
            self._emb_client = OpenAI(api_key=key)
        if self._emb_async_client is None and AsyncOpenAI is not None:
            self._emb_async_client = AsyncOpenAI(api_key=key)
        return self._emb_client, self._emb_async_client

    # -------------- Embedding cache helpers --------------
    def _emb_cache_make_key(self, text: str) -> str:
        h = hashlib.sha1((EMBED_MODEL + "\n" + text).encode("utf-8")).hexdigest()
        return h

    def _emb_cache_get_many(self, keys: List[str]) -> Dict[str, List[float]]:
        if not self._emb_cache_conn or not keys:
            return {}
        try:
            cur = self._emb_cache_conn.cursor()
            qmarks = ",".join(["?"] * len(keys))
            cur.execute(f"SELECT k, embedding FROM emb_cache WHERE k IN ({qmarks})", keys)
            rows = cur.fetchall()
            out: Dict[str, List[float]] = {}
            for k, emb_s in rows:
                try:
                    out[k] = _json.loads(emb_s)
                except Exception:
                    continue
            return out
        except Exception:
            return {}

    def _emb_cache_put_many(self, items: Dict[str, List[float]]):
        if not self._emb_cache_conn or not items:
            return
        try:
            cur = self._emb_cache_conn.cursor()
            data = [(k, EMBED_MODEL, int(time.time()), _json.dumps(v)) for k, v in items.items()]
            cur.executemany("INSERT OR REPLACE INTO emb_cache (k, model, created_at, embedding) VALUES (?, ?, ?, ?)", data)
            self._emb_cache_conn.commit()
        except Exception:
            pass

    # -------------- Embedding --------------
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if OpenAI is None:
            raise RuntimeError("openai paketi yok")
        # We will reuse a single client and a disk cache
        client, _ = self._get_emb_clients()
        # Cache lookup
        keys = [self._emb_cache_make_key(t) for t in texts]
        cached = self._emb_cache_get_many(keys)
        out: List[Optional[List[float]]] = [None] * len(texts)
        missing_idx: List[int] = []
        for idx, k in enumerate(keys):
            if k in cached:
                out[idx] = cached[k]
            else:
                missing_idx.append(idx)
        # Fetch missing in batches
        bs = 64
        to_store: Dict[str, List[float]] = {}
        for i in range(0, len(missing_idx), bs):
            part_idx = missing_idx[i:i+bs]
            if not part_idx:
                continue
            batch = [texts[j] for j in part_idx]
            _last_exc: Optional[Exception] = None
            for _retry in range(3):
                try:
                    resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
                    emb_list = [d.embedding for d in resp.data]  # type: ignore
                    for local, j in enumerate(part_idx):
                        out[j] = emb_list[local]
                        to_store[keys[j]] = emb_list[local]
                    _last_exc = None
                    break
                except Exception as _e:
                    _last_exc = _e
                    if any(t in str(_e).lower() for t in ["429", "rate limit", "quota", "overloaded"]):
                        _wait = 2 ** (_retry + 1)
                        print(f"[VectorStore] Embedding 429 — retry {_retry+1}/3, {_wait}s bekleniyor")
                        time.sleep(_wait)
                    else:
                        raise
            if _last_exc:
                raise _last_exc
        # Persist new items
        if to_store:
            self._emb_cache_put_many(to_store)
        # None kalan konumları tespit et — konum kayması olmaması için sıfır vektör ile doldur
        none_positions = [i for i, e in enumerate(out) if e is None]
        if none_positions:
            dim = next((len(e) for e in out if e is not None), 0)
            for i in none_positions:
                out[i] = [0.0] * dim if dim else []
            print(f"[VectorStore] ⚠️  embed_texts: {len(none_positions)} konum None kaldı; sıfır vektör eklendi (positions={none_positions})")
        return out  # type: ignore

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        _, aclient = self._get_emb_clients()
        # Cache lookup
        keys = [self._emb_cache_make_key(t) for t in texts]
        cached = self._emb_cache_get_many(keys)
        out: List[Optional[List[float]]] = [None] * len(texts)
        missing_idx: List[int] = []
        for idx, k in enumerate(keys):
            if k in cached:
                out[idx] = cached[k]
            else:
                missing_idx.append(idx)
        to_store: Dict[str, List[float]] = {}
        if aclient is not None:
            bs = 64
            for i in range(0, len(missing_idx), bs):
                part_idx = missing_idx[i:i+bs]
                if not part_idx:
                    continue
                batch = [texts[j] for j in part_idx]
                _last_exc2: Optional[Exception] = None
                for _retry2 in range(3):
                    try:
                        resp = await aclient.embeddings.create(model=EMBED_MODEL, input=batch)
                        emb_list = [d.embedding for d in resp.data]  # type: ignore
                        for local, j in enumerate(part_idx):
                            out[j] = emb_list[local]
                            to_store[keys[j]] = emb_list[local]
                        _last_exc2 = None
                        break
                    except Exception as _e2:
                        _last_exc2 = _e2
                        if any(t in str(_e2).lower() for t in ["429", "rate limit", "quota", "overloaded"]):
                            _wait2 = 2 ** (_retry2 + 1)
                            print(f"[VectorStore] Async embedding 429 — retry {_retry2+1}/3, {_wait2}s bekleniyor")
                            await asyncio.sleep(_wait2)
                        else:
                            raise
                if _last_exc2:
                    raise _last_exc2
        else:
            # Fallback to sync path in thread
            def _sync(ch: List[str]) -> List[List[float]]:
                return self.embed_texts(ch)
            synced = await asyncio.to_thread(_sync, [texts[j] for j in missing_idx])
            for local, j in enumerate(missing_idx):
                out[j] = synced[local]
                to_store[keys[j]] = synced[local]
        if to_store:
            self._emb_cache_put_many(to_store)
        # None kalan konumları tespit et — konum kayması olmaması için sıfır vektör ile doldur
        none_positions = [i for i, e in enumerate(out) if e is None]
        if none_positions:
            dim = next((len(e) for e in out if e is not None), 0)
            for i in none_positions:
                out[i] = [0.0] * dim if dim else []
            print(f"[VectorStore] ⚠️  a_embed_texts: {len(none_positions)} konum None kaldı; sıfır vektör eklendi (positions={none_positions})")
        return out  # type: ignore

    # -------------- Index helper --------------
    def _ensure_index(self, dimension: int):
        """Ensure pinecone index exists with correct dimension.

        Eğer mevcut index farklı boyutta ise:
        - Eğer ALLOW_INDEX_AUTO_RECREATE / PINECONE_AUTO_RECREATE env true -> index silinir ve doğru boyutta yeniden oluşturulur.
        - Aksi halde açıklayıcı RuntimeError fırlatılır.
        """
        if self._index is not None:
            return
        existing_indexes = list(self.pc.list_indexes())  # type: ignore
        existing_names = {idx["name"] for idx in existing_indexes}
        if self.index_name in existing_names:
            # Boyut kontrolü dene
            index_info = None
            try:  # Yeni pinecone client describe
                index_info = self.pc.describe_index(self.index_name)  # type: ignore
            except Exception:
                # fallback: list_indexes içinden dimension alanı varsa kullan
                try:
                    for item in existing_indexes:
                        if item.get("name") == self.index_name:
                            index_info = item
                            break
                except Exception:
                    index_info = None
            existing_dim = None
            try:
                if index_info:
                    existing_dim = index_info.get("dimension") if isinstance(index_info, dict) else getattr(index_info, "dimension", None)
            except Exception:
                existing_dim = None
            if existing_dim and existing_dim != dimension:
                auto = os.getenv("ALLOW_INDEX_AUTO_RECREATE") or os.getenv("PINECONE_AUTO_RECREATE") or "false"
                auto = auto.lower() in {"1", "true", "yes", "on"}
                if not auto:
                    raise RuntimeError(
                        f"Pinecone index '{self.index_name}' dimension mismatch: index={existing_dim} embedding_model={dimension}. \n"
                        "Çözüm seçenekleri: \n"
                        "1) EMBEDDING_MODEL env değiştirerek {existing_dim} boyutlu modele geçin (ör: text-embedding-3-small=1536)\n"
                        "2) ALLOW_INDEX_AUTO_RECREATE=1 ayarlayın (index silinir ve {dimension} boyutuyla yeniden oluşturulur)\n"
                        "3) Manuel olarak pinecone dashboard'da index'i silip yeniden oluşturun."
                    )
                # Otomatik yeniden oluştur
                try:
                    print(f"[VectorStore] UYARI: '{self.index_name}' index boyutu {existing_dim} ≠ {dimension}. Otomatik yeniden oluşturuluyor...")
                    self.pc.delete_index(self.index_name)  # type: ignore
                except Exception as de:  # pragma: no cover
                    raise RuntimeError(f"Index silinemedi: {de}")
                # Yeni oluştur
                if ServerlessSpec is not None:
                    cloud = os.getenv("PINECONE_CLOUD", "aws")
                    region = os.getenv("PINECONE_REGION", "eu-west-1")
                    spec = ServerlessSpec(cloud=cloud, region=region)
                else:  # pragma: no cover
                    spec = None
                self.pc.create_index(name=self.index_name, dimension=dimension, metric="cosine", spec=spec)
            # Var olan ve uyumlu index
        else:
            if ServerlessSpec is not None:
                cloud = os.getenv("PINECONE_CLOUD", "aws")
                region = os.getenv("PINECONE_REGION", "eu-west-1")
                spec = ServerlessSpec(cloud=cloud, region=region)
            else:  # pragma: no cover
                spec = None
            self.pc.create_index(name=self.index_name, dimension=dimension, metric="cosine", spec=spec)
        self._index = self.pc.Index(self.index_name)

    # -------------- Pinecone list / fetch helpers (RAM-free) --------------
    def _list_vector_ids(self, prefix: str) -> List[str]:
        """Pinecone list API ile verilen prefix'e sahip tüm vektör ID'lerini döndürür."""
        if self._index is None:
            return []
        all_ids: List[str] = []
        try:
            for page in self._index.list(prefix=prefix):
                if hasattr(page, 'vectors'):
                    # page.vectors is list of dicts with 'id' key  (v5 SDK)
                    all_ids.extend(v['id'] if isinstance(v, dict) else v for v in page.vectors)
                elif isinstance(page, (list, tuple)):
                    all_ids.extend(page)
                else:
                    # Some SDK versions yield id strings directly
                    all_ids.append(str(page))
        except Exception as e:
            print(f"[VectorStore] _list_vector_ids('{prefix}') hata: {e}")
        return all_ids

    def _fetch_vectors(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Pinecone fetch API ile vektör metadata'larını 100'lü batch'ler halinde çeker.
        Dönen dict: { vector_id: { 'metadata': {...}, ... } }"""
        if self._index is None or not ids:
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        bs = 100
        for start in range(0, len(ids), bs):
            batch = ids[start:start + bs]
            try:
                resp = self._index.fetch(ids=batch)
                if hasattr(resp, 'vectors') and resp.vectors:
                    for vid, vec in resp.vectors.items():
                        meta = vec.metadata if hasattr(vec, 'metadata') else (vec.get('metadata') if isinstance(vec, dict) else {})
                        result[vid] = {"metadata": meta or {}}
            except Exception as e:
                print(f"[VectorStore] _fetch_vectors batch hata: {e}")
        return result

    # -------------- Internal helpers --------------
    def _next_chat_id(self, session_id: str) -> int:
        """Timestamp tabanlı chat ID — Pinecone round-trip gerektirmez."""
        return int(time.time() * 1000)

    @staticmethod
    def _sanitize_component(value: str, max_len: int = 60) -> str:
        """Convert an arbitrary string to ASCII-safe Pinecone id component.

        Steps:
          - Normalize (NFKD) and strip combining marks.
          - Lowercase.
          - Replace whitespace with single underscore.
          - Keep only [a-z0-9._-]. Other chars -> '-'.
          - Collapse multiple dashes/underscores.
          - Trim length; append 6-char hash if truncated or empty.
        """
        if not value:
            return "empty"  # will be hashed below anyway
        # Basic transliteration for common Turkish characters before normalization
        translit_table = str.maketrans({
            "ç": "c", "Ç": "c",
            "ğ": "g", "Ğ": "g",
            "ı": "i", "İ": "i",
            "ö": "o", "Ö": "o",
            "ş": "s", "Ş": "s",
            "ü": "u", "Ü": "u",
        })
        value = value.translate(translit_table)
        # Normalize & remove combining marks
        nfkd = unicodedata.normalize("NFKD", value)
        ascii_only = ''.join(ch for ch in nfkd if not unicodedata.combining(ch))
        lower = ascii_only.lower()
        replaced = re.sub(r"\s+", "_", lower)
        cleaned = re.sub(r"[^a-z0-9._-]", "-", replaced)
        collapsed = re.sub(r"[-_]{2,}", "_", cleaned).strip("-_.")
        if not collapsed:
            collapsed = "id"
        truncated = collapsed[:max_len]
        # Add short hash to ensure uniqueness vs collisions after truncation
        h = hashlib.sha1(value.encode('utf-8')).hexdigest()[:6]
        if truncated != collapsed:
            truncated = f"{truncated}-{h}"
        elif len(truncated) < len(value) or truncated != collapsed:
            truncated = f"{truncated}-{h}"
        return truncated

    def _safe_pdf_id(self, original: str) -> str:
        safe = self._id_map.get(original)
        if safe:
            return safe
        safe = self._sanitize_component(original)
        self._id_map[original] = safe
        if safe != original:
            print(f"[VectorStore] ID sanitize: '{original}' -> '{safe}'")
        return safe

    # -------------- Add PDF --------------
    def add_pdf(self, session_id: str, pdf_id: str, text: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> Dict[str, Any]:
        if RecursiveCharacterTextSplitter is None:
            raise RuntimeError("langchain_text_splitters yüklenemedi")
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", " ", ""])  # type: ignore
        chunks = [c for c in splitter.split_text(text) if c.strip()]
        if not chunks:
            raise RuntimeError("Boş içerik")
        embeddings = self.embed_texts(chunks)
        self._embedding_dim = len(embeddings[0])
        self._ensure_index(self._embedding_dim)
        vectors = []
        safe_pdf_id = self._safe_pdf_id(pdf_id)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vid = f"{session_id}:{safe_pdf_id}:{i}"
            vectors.append({
                "id": vid,
                "values": emb,
                "metadata": {
                    "session_id": session_id,
                    "pdf_id": safe_pdf_id,
                    "chunk_id": i,
                    "kind": "pdf",
                    "text": chunk[:39000],
                }
            })
        if vectors:
            self._batched_upsert(vectors)
        return {"chunks": len(chunks), "added": len(vectors)}

    # -------------- Add Precedent (single doc convenience) --------------
    async def a_add_precedent(self, session_id: str, precedent_id: str, text: str, chunk_size: int = 1600, chunk_overlap: int = 120, extra_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Emsal karar ekleme (kind=precedent). PDF ile aynı mantık ancak kind farklı.
        Tek bir uzun markdown içerik chunk'lara bölünür.
        extra_meta: Bedesten API'den gelen karar dict'i (birimAdi, kararTarihi vb.)
        Bu bilgilerden mahkeme_tipi, daire_alan, karar_yili metadata'ya eklenir.
        """
        if RecursiveCharacterTextSplitter is None:
            raise RuntimeError("langchain_text_splitters yüklenemedi")
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", " ", ""])  # type: ignore
        chunks = [c for c in splitter.split_text(text) if c.strip()]
        if not chunks:
            return {"added": 0}
        embeddings = await self.a_embed_texts(chunks)
        self._embedding_dim = len(embeddings[0])
        self._ensure_index(self._embedding_dim)
        vectors = []
        safe_prec_id = self._safe_pdf_id(precedent_id)
        # Metadata zenginleştirmesi: mahkeme tipi, daire alanı, karar yılı
        birim = (extra_meta or {}).get("birimAdi", "") or ""
        birim_lower = birim.lower()
        if "yargıtay" in birim_lower or "yargitay" in birim_lower:
            mahkeme_tipi = "yargitay"
        elif "danıştay" in birim_lower or "danistay" in birim_lower:
            mahkeme_tipi = "danistay"
        elif any(x in birim_lower for x in ["asliye", "sulh", "ağır", "agir"]):
            mahkeme_tipi = "ilk_derece"
        else:
            mahkeme_tipi = "diger"
        daire_alan = "genel"
        if any(x in birim_lower for x in ["9. hukuk", "22. hukuk", "7. hukuk"]):
            daire_alan = "is_hukuku"
        elif "2. hukuk" in birim_lower:
            daire_alan = "aile"
        elif any(x in birim_lower for x in ["3. hukuk", "6. hukuk"]):
            daire_alan = "kira"
        elif "ceza" in birim_lower:
            daire_alan = "ceza"
        elif any(x in birim_lower for x in ["ticaret", "11. hukuk", "12. hukuk"]):
            daire_alan = "ticaret"
        elif any(x in birim_lower for x in ["17. hukuk", "4. hukuk"]):
            daire_alan = "trafik"
        karar_yili = 0
        tarih_str = (extra_meta or {}).get("kararTarihi", "") or ""
        if tarih_str and len(tarih_str) >= 4:
            try:
                karar_yili = int(tarih_str[:4])
            except Exception:
                pass
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vid = f"{session_id}:{safe_prec_id}:{i}"
            vectors.append({
                "id": vid,
                "values": emb,
                "metadata": {
                    "session_id": session_id,
                    "pdf_id": safe_prec_id,
                    "chunk_id": i,
                    "kind": "precedent",
                    "text": chunk[:39000],
                    "mahkeme_tipi": mahkeme_tipi,
                    "daire_alan": daire_alan,
                    "karar_yili": karar_yili,
                }
            })
        if vectors:
            await self._a_batched_upsert(vectors)
        return {"chunks": len(chunks), "added": len(vectors), "precedent_id": precedent_id}

    async def a_add_pdf(self, session_id: str, pdf_id: str, text: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> Dict[str, Any]:
        if RecursiveCharacterTextSplitter is None:
            raise RuntimeError("langchain_text_splitters yüklenemedi")
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", " ", ""])  # type: ignore
        chunks = [c for c in splitter.split_text(text) if c.strip()]
        if not chunks:
            raise RuntimeError("Boş içerik")
        embeddings = await self.a_embed_texts(chunks)
        self._embedding_dim = len(embeddings[0])
        self._ensure_index(self._embedding_dim)
        vectors = []
        safe_pdf_id = self._safe_pdf_id(pdf_id)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vid = f"{session_id}:{safe_pdf_id}:{i}"
            vectors.append({
                "id": vid,
                "values": emb,
                "metadata": {
                    "session_id": session_id,
                    "pdf_id": safe_pdf_id,
                    "chunk_id": i,
                    "kind": "pdf",
                    "text": chunk[:39000],
                }
            })
        if vectors:
            await self._a_batched_upsert(vectors)
        return {"chunks": len(chunks), "added": len(vectors)}

    # -------------- Temp/Web Document --------------
    async def a_add_temp_document(
        self,
        session_id: str,
        doc_id: str,
        text: str,
        *,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 120,
    ) -> Dict[str, Any]:
        """Add an ad-hoc temporary document (e.g., web page) to the store.

        Stored with kind="temp" so it can be filtered/trimmed later.
        """
        if not text or not text.strip():
            return {"added": 0}
        if RecursiveCharacterTextSplitter is None:
            raise RuntimeError("langchain_text_splitters yüklenemedi")
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", " ", ""])  # type: ignore
        chunks = [c for c in splitter.split_text(text) if c.strip()]
        if not chunks:
            return {"added": 0}
        embeddings = await self.a_embed_texts(chunks)
        self._embedding_dim = len(embeddings[0])
        self._ensure_index(self._embedding_dim)
        vectors = []
        safe_doc_id = self._safe_pdf_id(doc_id)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vid = f"{session_id}:{safe_doc_id}:{i}"
            vectors.append({
                "id": vid,
                "values": emb,
                "metadata": {
                    "session_id": session_id,
                    "pdf_id": safe_doc_id,
                    "chunk_id": i,
                    "kind": "temp",
                    "source_url": source_url or "",
                    "title": title or "",
                    "text": chunk[:39000],
                }
            })
        if vectors:
            await self._a_batched_upsert(vectors)
        return {"chunks": len(chunks), "added": len(vectors), "doc_id": doc_id}

    # -------------- Chat --------------
    def add_chat_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        if not content.strip():
            return {"added": 0}
        emb = self.embed_texts([content])[0]
        self._embedding_dim = len(emb)
        self._ensure_index(self._embedding_dim)
        cid = self._next_chat_id(session_id)
        vid = f"{session_id}:__chat__:{cid}"
        self._index.upsert(vectors=[{  # type: ignore
            "id": vid,
            "values": emb,
            "metadata": {
                "session_id": session_id,
                "pdf_id": "__chat__",
                "chunk_id": cid,
                "kind": "chat",
                "role": role,
                "text": content[:39000],
            }
        }])
        return {"added": 1, "message_index": cid}

    async def a_add_chat_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        if not content.strip():
            return {"added": 0}
        emb = (await self.a_embed_texts([content]))[0]
        self._embedding_dim = len(emb)
        self._ensure_index(self._embedding_dim)
        cid = self._next_chat_id(session_id)
        vid = f"{session_id}:__chat__:{cid}"
        await asyncio.to_thread(self._index.upsert, vectors=[{  # type: ignore
            "id": vid,
            "values": emb,
            "metadata": {
                "session_id": session_id,
                "pdf_id": "__chat__",
                "chunk_id": cid,
                "kind": "chat",
                "role": role,
                "text": content[:39000],
            }
        }])
        return {"added": 1, "message_index": cid}

    def add_chat_history(self, session_id: str, messages: List[Tuple[str, str]]) -> Dict[str, Any]:
        filtered = [(r, c) for r, c in messages if c and c.strip()]
        if not filtered:
            return {"added": 0}
        roles, contents = zip(*filtered)
        embeddings = self.embed_texts(list(contents))
        self._embedding_dim = len(embeddings[0])
        self._ensure_index(self._embedding_dim)
        upserts = []
        for i, (role, content, emb) in enumerate(zip(roles, contents, embeddings)):
            cid = self._next_chat_id(session_id) + i
            vid = f"{session_id}:__chat__:{cid}"
            upserts.append({
                "id": vid,
                "values": emb,
                "metadata": {
                    "session_id": session_id,
                    "pdf_id": "__chat__",
                    "chunk_id": cid,
                    "kind": "chat",
                    "role": role,
                    "text": content[:39000],
                }
            })
        if upserts:
            self._batched_upsert(upserts)
        return {"added": len(upserts)}

    async def a_add_chat_history(self, session_id: str, messages: List[Tuple[str, str]]) -> Dict[str, Any]:
        filtered = [(r, c) for r, c in messages if c and c.strip()]
        if not filtered:
            return {"added": 0}
        roles, contents = zip(*filtered)
        embeddings = await self.a_embed_texts(list(contents))
        self._embedding_dim = len(embeddings[0])
        self._ensure_index(self._embedding_dim)
        upserts = []
        for i, (role, content, emb) in enumerate(zip(roles, contents, embeddings)):
            cid = self._next_chat_id(session_id) + i
            vid = f"{session_id}:__chat__:{cid}"
            upserts.append({
                "id": vid,
                "values": emb,
                "metadata": {
                    "session_id": session_id,
                    "pdf_id": "__chat__",
                    "chunk_id": cid,
                    "kind": "chat",
                    "role": role,
                    "text": content[:39000],
                }
            })
        if upserts:
            await self._a_batched_upsert(upserts)
        return {"added": len(upserts)}

    # -------------- Chat History --------------
    def get_chat_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Pinecone'dan session'a ait chat mesajlarını çeker."""
        ids = self._list_vector_ids(f"{session_id}:__chat__:")
        if not ids:
            return []
        fetched = self._fetch_vectors(ids)
        chats: List[Dict[str, Any]] = []
        for vid, data in fetched.items():
            meta = data.get("metadata", {})
            if meta.get("kind") != "chat":
                continue
            raw_cid = meta.get("chunk_id")
            cid = int(raw_cid) if raw_cid is not None else 0
            chats.append({
                "role": meta.get("role"),
                "content": meta.get("text", ""),
                "index": cid,
            })
        chats.sort(key=lambda r: r["index"])
        if limit is not None:
            chats = chats[-limit:]
        return chats

    # -------------- Similarity --------------
    def similarity_search(self, session_id: str, query: str, k: int = 5, include_pdf: bool = True, include_chat: bool = True) -> List[Dict[str, Any]]:
        # Sorgu embedding'ini oluştur (Pinecone'da veri olabilir)
        q_emb = self.embed_texts([query])[0]
        self._embedding_dim = len(q_emb)
        self._ensure_index(self._embedding_dim)
        filter_meta: Dict[str, Any] = {"session_id": {"$eq": session_id}}
        if include_pdf and include_chat:
            pass
        elif include_pdf:
            filter_meta["kind"] = {"$in": ["pdf", "precedent", "temp"]}
        elif include_chat:
            filter_meta["kind"] = {"$in": ["chat"]}
        else:
            return []
        res = self._index.query(vector=q_emb, top_k=min(k, 50), filter=filter_meta, include_metadata=True)  # type: ignore
        results: List[Dict[str, Any]] = []
        for m in res.matches:  # type: ignore
            meta = m.metadata or {}
            kind = meta.get("kind", "pdf")
            if kind == "pdf" and not include_pdf:
                continue
            if kind == "chat" and not include_chat:
                continue
            # chunk_id tipi düzelt (Pinecone float dönebilir)
            raw_chunk_id = meta.get("chunk_id")
            chunk_id_int = int(raw_chunk_id) if raw_chunk_id is not None else None
            text = meta.get("text") or ""
            results.append({
                "session_id": session_id,
                "pdf_id": meta.get("pdf_id"),
                "chunk_id": chunk_id_int,
                "chunk_text": text or "(içerik alınamadı)",
                "distance": 1 - m.score if m.score is not None else 0.0,
                "kind": kind,
                "role": meta.get("role"),
            })
        results.sort(key=lambda r: r["distance"])
        return results[:k]

    async def a_similarity_search(self, session_id: str, query: str, k: int = 5, include_pdf: bool = True, include_chat: bool = True) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.similarity_search, session_id, query, k, include_pdf, include_chat)

    def precedent_similarity_search(self, session_id: str, query: str, k: int = 15, pdf_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Yalnızca kind='precedent' chunk'larını semantik olarak arar.

        Pinecone'a yüklenmiş emsal kararların chunk'ları içinden sorguya en benzer
        paragrafları döndürür. Her chunk kendi kaynak kararın (pdf_id) bilgisini taşır.

        pdf_ids: Sadece bu analize ait pdf_id'lerle sınırla. Verilmezse session'daki
                 TÜM precedent chunk'ları taranır (eski analizlerden kalanlar dahil).
        """
        q_emb = self.embed_texts([query])[0]
        self._embedding_dim = len(q_emb)
        self._ensure_index(self._embedding_dim)
        filter_meta: Dict[str, Any] = {
            "session_id": {"$eq": session_id},
            "kind": {"$eq": "precedent"},
        }
        if pdf_ids:
            # Pinecone metadata'da safe_prec_id (sanitize edilmiş) saklanıyor; eşleştir
            safe_ids = [self._sanitize_component(pid) for pid in pdf_ids]
            filter_meta["pdf_id"] = {"$in": safe_ids}
            print(f"[VectorStore] Precedent search filtered to {len(safe_ids)} pdf_ids for current analysis")
        res = self._index.query(vector=q_emb, top_k=min(k, 100), filter=filter_meta, include_metadata=True)  # type: ignore
        results: List[Dict[str, Any]] = []
        for m in res.matches:  # type: ignore
            meta = m.metadata or {}
            raw_chunk_id = meta.get("chunk_id")
            results.append({
                "session_id": session_id,
                "pdf_id": meta.get("pdf_id"),
                "chunk_id": int(raw_chunk_id) if raw_chunk_id is not None else None,
                "chunk_text": meta.get("text") or "(içerik alınamadı)",
                "distance": 1 - m.score if m.score is not None else 0.0,
                "kind": "precedent",
            })
        results.sort(key=lambda r: r["distance"])
        return results[:k]

    async def a_precedent_similarity_search(self, session_id: str, query: str, k: int = 15, pdf_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Async wrapper for precedent_similarity_search."""
        return await asyncio.to_thread(self.precedent_similarity_search, session_id, query, k, pdf_ids)

    # -------------- Removal --------------
    def remove_pdf(self, session_id: str, pdf_id: str) -> Dict[str, Any]:
        # Allow removal using original or sanitized name
        target = self._id_map.get(pdf_id, pdf_id)
        ids = self._list_vector_ids(f"{session_id}:{target}:")
        if not ids:
            # Sanitize edilmemiş adla da dene
            safe = self._sanitize_component(pdf_id)
            if safe != target:
                ids = self._list_vector_ids(f"{session_id}:{safe}:")
        if not ids:
            return {"removed_chunks": 0, "message": f"'{pdf_id}' bulunamadı"}
        # Batch delete (Pinecone max 1000 per call)
        for start in range(0, len(ids), 1000):
            self._index.delete(ids=ids[start:start+1000])  # type: ignore
        return {"removed_chunks": len(ids), "message": f"'{pdf_id}' kaldırıldı"}

    async def a_remove_pdf(self, session_id: str, pdf_id: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self.remove_pdf, session_id, pdf_id)

    def delete_session(self, session_id: str) -> int:
        ids = self._list_vector_ids(f"{session_id}:")
        if ids:
            for start in range(0, len(ids), 1000):
                self._index.delete(ids=ids[start:start+1000])  # type: ignore
        return len(ids)

    async def a_delete_session(self, session_id: str) -> int:
        return await asyncio.to_thread(self.delete_session, session_id)

    # -------------- Trim helper --------------
    def trim_session_vectors_top_k(self, session_id: str, keep_ids: List[Tuple[str, int]]):
        """Oturumdaki temp/precedent vektörlerden keep_ids dışındakileri siler."""
        keep = set(keep_ids)
        all_ids = self._list_vector_ids(f"{session_id}:")
        if not all_ids:
            return {"removed": 0}
        # Hangi vektörlerin temp/precedent olduğunu bul
        fetched = self._fetch_vectors(all_ids)
        remove_vec_ids = []
        for vid, data in fetched.items():
            meta = data.get("metadata", {})
            kind = meta.get("kind", "pdf")
            if kind not in ("temp", "precedent"):
                continue
            pdf_id = meta.get("pdf_id", "")
            raw_cid = meta.get("chunk_id")
            chunk_id = int(raw_cid) if raw_cid is not None else 0
            if (pdf_id, chunk_id) not in keep:
                remove_vec_ids.append(vid)
        if remove_vec_ids:
            for start in range(0, len(remove_vec_ids), 1000):
                self._index.delete(ids=remove_vec_ids[start:start+1000])  # type: ignore
        return {"removed": len(remove_vec_ids)}

    # -------------- Full Content Retrieval --------------
    def get_all_documents_raw(self, session_id: str, kinds: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Belirtilen oturumdaki tüm chunk kayıtlarını Pinecone'dan çeker.

        Args:
            session_id: Oturum kimliği
            kinds: Filtrelenecek tür listesi (pdf, precedent, chat, temp). None ise hepsi.
        Returns:
            Her chunk için sözlük listesi.
        """
        allowed = set(kinds) if kinds else None
        ids = self._list_vector_ids(f"{session_id}:")
        if not ids:
            return []
        fetched = self._fetch_vectors(ids)
        out: List[Dict[str, Any]] = []
        for vid, data in fetched.items():
            meta = data.get("metadata", {})
            kind = meta.get("kind", "pdf")
            if allowed and kind not in allowed:
                continue
            raw_cid = meta.get("chunk_id")
            chunk_id = int(raw_cid) if raw_cid is not None else 0
            out.append({
                "session_id": meta.get("session_id", session_id),
                "pdf_id": meta.get("pdf_id", ""),
                "chunk_id": chunk_id,
                "kind": kind,
                "role": meta.get("role"),
                "text": meta.get("text", ""),
            })
        # pdf_id + chunk_id ile sıralı
        out.sort(key=lambda x: (x["pdf_id"], x["chunk_id"]))
        return out

    def get_concatenated_documents(self, session_id: str, kinds: Optional[List[str]] = None, joiner: str = "\n\n") -> Dict[str, str]:
        """Her pdf_id (veya precedent kimliği) için chunk'ları birleştirip tam metni döndürür.

        Geriye { pdf_id: full_text } haritası döner. Chat mesajları için ayrı birleştirme yapılmaz; istenirse kinds=['chat'] çağrısıyla alınır.
        """
        raw = self.get_all_documents_raw(session_id, kinds=kinds)
        buckets: Dict[str, List[str]] = {}
        for r in raw:
            pid = r["pdf_id"]
            if pid not in buckets:
                buckets[pid] = []
            buckets[pid].append(r["text"])
        return {pid: joiner.join(parts) for pid, parts in buckets.items()}

    def get_full_precedents_for_session(self, session_id: str) -> Dict[str, str]:
        """Oturumdaki tüm precedent (emsal) dokümanlarının TAM metinlerini döner."""
        return self.get_concatenated_documents(session_id, kinds=["precedent"])

    def has_pdf_files(self, session_id: str) -> bool:
        """Session'da PDF dosyası olup olmadığını Pinecone list ile hızlıca kontrol eder."""
        ids = self._list_vector_ids(f"{session_id}:")
        if not ids:
            return False
        # İlk batch'i fetch edip kind="pdf" olan var mı kontrol et
        sample = ids[:100]
        fetched = self._fetch_vectors(sample)
        return any(
            d.get("metadata", {}).get("kind") == "pdf"
            for d in fetched.values()
        )

    def count_pdf_files(self, session_id: str) -> int:
        """Session'daki PDF chunk sayısını döner."""
        ids = self._list_vector_ids(f"{session_id}:")
        if not ids:
            return 0
        fetched = self._fetch_vectors(ids)
        return sum(1 for d in fetched.values() if d.get("metadata", {}).get("kind") == "pdf")    


_store: Optional[PineconeSessionStore] = None


def get_vector_store() -> PineconeSessionStore:
    global _store
    if _store is None:
        _store = PineconeSessionStore()
    return _store


def new_session_id() -> str:
    return str(uuid.uuid4())
# Eski isimleri dışarıda referans eden kodlara nazik alias (geri uyum)
SessionFAISSStore = PineconeSessionStore  # type: ignore
