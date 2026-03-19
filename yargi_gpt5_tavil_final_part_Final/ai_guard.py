#!/usr/bin/env python3
"""
Production-Ready AI Request Manager with Multiple Token Support for GPT-5
Her AI modülü için farklı OpenAI API token'ları kullanır
"""

import asyncio
import inspect
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from openai import OpenAI as OpenAIClient
import threading
from collections import deque
import json
import os
from datetime import timedelta

# Default GPT-5 model
DEFAULT_GPT_MODEL = "gpt-5"

class MultiTokenAIManager:
    """Çoklu Token destekli GPT-5 AI Manager"""
    
    def __init__(self):
        """Tüm AI modülleri için ayrı OpenAI client'ları başlat"""
        self.clients = {}
        self.api_keys = {}
        
        # Her AI modülü için ayrı OpenAI API token'ları yükle
        token_mappings = {
            'main': 'OPENAI_API_KEY_MAIN',
            'search': 'OPENAI_API_KEY_SEARCH', 
            'petition': 'OPENAI_API_KEY_PETITION',
            'case_analysis': 'OPENAI_API_KEY_CASE_ANALYSIS',
            'general': 'OPENAI_API_KEY_GENERAL'
        }
        
        # Token'ları yükle ve client'ları oluştur
        loaded = []
        missing = []
        for ai_type, env_var in token_mappings.items():
            api_key = os.getenv(env_var)
            if api_key and not api_key.startswith("sk-YOUR-"):
                self.api_keys[ai_type] = api_key
                self.clients[ai_type] = OpenAIClient(api_key=api_key)
                loaded.append(ai_type)
            else:
                missing.append(env_var)

        # Fallback: eski tek token varsa general olarak kullan
        fallback_key = os.getenv('OPENAI_API_KEY')
        if fallback_key and 'general' not in self.clients:
            self.api_keys['general'] = fallback_key
            self.clients['general'] = OpenAIClient(api_key=fallback_key)
            loaded.append('general(fallback)')

        if not self.clients:
            raise ValueError("Hiçbir OpenAI API token'ı bulunamadı!")

        print(f"✅ {len(self.clients)} AI client yüklendi: {loaded}")
        if missing:
            print(f"⚠️  Eksik token değişkenleri: {missing}")
    
    def get_client(self, ai_type: str) -> Optional[OpenAIClient]:
        """Belirtilen AI tipi için OpenAI client döndür"""
        # Önce exact match ara
        if ai_type in self.clients:
            return self.clients[ai_type]

        # Fallback sırası: general -> main -> ilk mevcut client
        for fallback in ['general', 'main']:
            if fallback in self.clients:
                return self.clients[fallback]

        # Son çare: herhangi bir client
        if self.clients:
            return next(iter(self.clients.values()))

        return None
    
    async def safe_request(self, ai_type: str, api_function: Callable, *args, **kwargs):
        """Belirtilen AI tipi ile güvenli API çağrısı (sync/async destekli)"""
        client = self.get_client(ai_type)
        if not client:
            return {"error": f"{ai_type} GPT-5 client bulunamadı"}
        
        try:
            # Async callable ise doğrudan await et; değilse thread'e offload et
            if inspect.iscoroutinefunction(api_function):
                result = await api_function(*args, **kwargs)
            else:
                result = await asyncio.to_thread(api_function, *args, **kwargs)
            return {"success": True, "result": result, "ai_type": ai_type}
        except Exception as e:
            return {"error": f"{ai_type} GPT-5 hatası: {str(e)}", "ai_type": ai_type}


# Global multi-token manager instance
_multi_token_manager = None

def get_multi_token_manager() -> MultiTokenAIManager:
    """Global multi-token manager instance'ı döndür"""
    global _multi_token_manager
    if _multi_token_manager is None:
        _multi_token_manager = MultiTokenAIManager()
    return _multi_token_manager

class RequestQueue:
    """İstek kuyruğu - FIFO mantığı"""
    
    def __init__(self, max_size: int = 100):
        self.queue = deque(maxlen=max_size)
        self.processing = False
        self.lock = asyncio.Lock()
    
    async def add_request(self, request_data: Dict[str, Any]) -> str:
        """Kuyruğa istek ekle"""
        request_id = f"req_{int(time.time()*1000)}"
        request_data['request_id'] = request_id
        request_data['timestamp'] = time.time()
        request_data['status'] = 'queued'
        
        async with self.lock:
            self.queue.append(request_data)
        
        return request_id
    
    async def get_next_request(self) -> Optional[Dict[str, Any]]:
        """Sonraki isteği al"""
        async with self.lock:
            if self.queue:
                return self.queue.popleft()
        return None

class GlobalAIManager:
    """Global AI istek yöneticisi - Singleton pattern (ESKİ SİSTEM)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Fallback için eski sistem - şimdi multi-token manager kullanacağız
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            print("⚠️  Eski OPENAI_API_KEY bulunamadı, multi-token sistem kullanılacak")
        else:
            self.client = OpenAIClient(api_key=self.api_key)
        
        # Request limiting
        self.MAX_CONCURRENT = 5  # OpenAI'nin daha yüksek limiti
        self.MAX_RPM = 100  # requests per minute
        self.active_requests = 0
        self.request_history = deque(maxlen=100)
        
        # Request queue
        self.request_queue = RequestQueue()
        
        # Threading locks
        self.request_lock = asyncio.Lock()
        
        # Stats
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'queued_requests': 0,
            'rate_limited': 0
        }
        
        # Background processor başlat
        self._start_background_processor()
        
        GlobalAIManager._initialized = True
        print("✅ Global AI Manager initialized (Legacy mode - GPT-5)")

    def _start_background_processor(self):
        """Arka planda sürekli çalışan request processor"""
        async def processor():
            while True:
                try:
                    # Kuyruktaki isteği al
                    request_data = await self.request_queue.get_next_request()
                    if not request_data:
                        await asyncio.sleep(0.1)  # Kuyruk boşsa kısa bekle
                        continue
                    
                    # Rate limit kontrol
                    if not await self._check_rate_limits():
                        # Rate limit aşıldıysa geri koy
                        async with self.request_queue.lock:
                            self.request_queue.queue.appendleft(request_data)
                        await asyncio.sleep(1)
                        continue
                    
                    # İsteği işle
                    await self._process_request(request_data)
                    
                except Exception as e:
                    print(f"❌ Background processor error: {e}")
                    await asyncio.sleep(1)
        
        # Background task'i başlat
        asyncio.create_task(processor())
    
    async def _check_rate_limits(self) -> bool:
        """Rate limit kontrolü"""
        now = time.time()
        minute_ago = now - 60
        
        # Eski istekleri temizle
        while self.request_history and self.request_history[0] < minute_ago:
            self.request_history.popleft()
        
        # Limitler
        if self.active_requests >= self.MAX_CONCURRENT:
            return False
        
        if len(self.request_history) >= self.MAX_RPM:
            return False
        
        return True
    
    async def _process_request(self, request_data: Dict[str, Any]):
        """İsteği işle"""
        request_id = request_data['request_id']
        
        try:
            async with self.request_lock:
                self.active_requests += 1
                self.request_history.append(time.time())
            
            print(f"🔄 Processing request {request_id}")
            
            # API çağrısını yap
            api_func = request_data['api_function']
            args = request_data.get('args', [])
            kwargs = request_data.get('kwargs', {})
            
            result = await api_func(*args, **kwargs)
            
            # Başarılı
            request_data['result'] = result
            request_data['status'] = 'completed'
            self.stats['successful_requests'] += 1
            
            print(f"✅ Request {request_id} completed")
            
        except Exception as e:
            print(f"❌ Request {request_id} failed: {e}")
            request_data['error'] = str(e)
            request_data['status'] = 'failed'
            self.stats['failed_requests'] += 1
            
        finally:
            async with self.request_lock:
                self.active_requests = max(0, self.active_requests - 1)
            
            self.stats['total_requests'] += 1
    
    async def queue_request(self, 
                          api_function: Callable, 
                          *args, 
                          timeout: float = 30.0,
                          **kwargs) -> Dict[str, Any]:
        """İsteği kuyruğa ekle ve sonucu bekle"""
        
        request_data = {
            'api_function': api_function,
            'args': args,
            'kwargs': kwargs,
            'timeout': timeout
        }
        
        request_id = await self.request_queue.add_request(request_data)
        self.stats['queued_requests'] += 1
        
        # Sonucu bekle (polling)
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Request'in durumunu kontrol et
            if request_data.get('status') == 'completed':
                return request_data.get('result', {})
            elif request_data.get('status') == 'failed':
                return {'error': request_data.get('error', 'Unknown error')}
            
            await asyncio.sleep(0.1)  # 100ms polling
        
        return {'error': 'Request timeout'}
    
    def get_stats(self) -> Dict[str, Any]:
        """İstatistikleri döndür"""
        return {
            'active_requests': self.active_requests,
            'queue_size': len(self.request_queue.queue),
            'requests_last_minute': len(self.request_history),
            'max_concurrent': self.MAX_CONCURRENT,
            'max_rpm': self.MAX_RPM,
            **self.stats
        }

# Global instance functions
def get_ai_manager() -> GlobalAIManager:
    """Global AI Manager instance'ı döndür (Legacy)"""
    return GlobalAIManager()

# ==========================================
# YENİ MULTI-TOKEN SİSTEM API FUNCTIONS - GPT-5
# ==========================================

async def safe_openai_request(api_function: Callable, ai_type: str = "general", *args, **kwargs):
    """Güvenli OpenAI API çağrısı - Multi-token destekli"""
    manager = get_multi_token_manager()
    wrapped = await manager.safe_request(ai_type, api_function, *args, **kwargs)
    # Kullanım yerleri doğrudan model cevabını bekliyor; başarılıysa sonucu geçir, aksi halde hata döndür
    if isinstance(wrapped, dict) and wrapped.get("success"):
        return wrapped.get("result")
    return wrapped

# Her AI modülü için özel wrapper functions
def _is_transient_error(err_str: str) -> bool:
    """Geçici (yeniden denenebilir) hata mı kontrol et."""
    return any(t in err_str.lower() for t in [
        "rate limit", "429", "timeout", "server error", "503", "502", "connection"
    ])


async def safe_main_ai_request(system_prompt: str, user_message: str, model: str = DEFAULT_GPT_MODEL):
    """Main AI (Legal Advisor) için güvenli çağrı — exponential backoff ile."""
    manager = get_multi_token_manager()
    client = manager.get_client("main")
    if not client:
        return {"error": "Main GPT-5 client bulunamadı"}

    for attempt in range(3):
        try:
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return {
                "response": completion.choices[0].message.content,
                "timestamp": datetime.now().isoformat(),
                "ai_type": "main",
                "model": model
            }
        except Exception as e:
            if attempt < 2 and _is_transient_error(str(e)):
                await asyncio.sleep(2 ** attempt)
                continue
            return {"error": f"Main GPT-5 hatası: {str(e)}"}

async def safe_search_ai_request(system_prompt: str, user_message: str, model: str = DEFAULT_GPT_MODEL):
    """Search Query AI (Arama Cümlesi) için güvenli çağrı"""
    manager = get_multi_token_manager()
    client = manager.get_client("search")
    if not client:
        return {"error": "Search GPT-5 client bulunamadı"}

    # GPT-5 with simple exponential backoff (handles rate limits)
    for attempt in range(3):
        try:
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return {
                "response": completion.choices[0].message.content,
                "timestamp": datetime.now().isoformat(),
                "ai_type": "search",
                "model": model
            }
        except Exception as e:
            # Rate limit detection
            err_str = str(e).lower()
            transient = any(token in err_str for token in [
                "rate limit", "429", "timeout", "server error", "503"
            ])
            if attempt < 2 and transient:
                await asyncio.sleep(1 * (2 ** attempt))
                continue
            return {"error": f"Search GPT-5 hatası: {str(e)}"}

async def safe_petition_ai_request(system_prompt: str, user_message: str, model: str = DEFAULT_GPT_MODEL):
    """Petition AI (Dilekçe Oluşturucu) için güvenli çağrı — exponential backoff ile."""
    manager = get_multi_token_manager()
    client = manager.get_client("petition")
    if not client:
        return {"error": "Petition GPT-5 client bulunamadı"}

    for attempt in range(3):
        try:
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return {
                "response": completion.choices[0].message.content,
                "timestamp": datetime.now().isoformat(),
                "ai_type": "petition",
                "model": model
            }
        except Exception as e:
            if attempt < 2 and _is_transient_error(str(e)):
                await asyncio.sleep(2 ** attempt)
                continue
            return {"error": f"Petition GPT-5 hatası: {str(e)}"}

async def safe_case_analysis_ai_request(system_prompt: str, user_message: str, model: str = DEFAULT_GPT_MODEL):
    """Case Analysis AI (Dava Analizi) için güvenli çağrı — exponential backoff ile."""
    manager = get_multi_token_manager()
    client = manager.get_client("case_analysis")
    if not client:
        return {"error": "Case Analysis GPT-5 client bulunamadı"}

    for attempt in range(3):
        try:
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return {
                "response": completion.choices[0].message.content,
                "timestamp": datetime.now().isoformat(),
                "ai_type": "case_analysis",
                "model": model
            }
        except Exception as e:
            if attempt < 2 and _is_transient_error(str(e)):
                await asyncio.sleep(2 ** attempt)
                continue
            return {"error": f"Case Analysis GPT-5 hatası: {str(e)}"}

# Legacy function (backward compatibility)
async def safe_legal_question(question: str, system_prompt: str = None):
    """Güvenli hukuki soru API çağrısı (Legacy - general AI kullanır)"""
    manager = get_multi_token_manager()
    client = manager.get_client("general")
    if not client:
        return {"error": "General GPT-5 client bulunamadı"}
    
    try:
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model=DEFAULT_GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt or "Sen Türk Hukuku uzmanısın."},
                {"role": "user", "content": question}
            ]
        )
        
        return {
            "response": completion.choices[0].message.content,
            "timestamp": datetime.now().isoformat(),
            "model": DEFAULT_GPT_MODEL,
            "ai_type": "general"
        }
        
    except Exception as e:
        return {"error": f"API çağrı hatası: {str(e)}"}

# Debugging/Status functions
def get_token_status():
    """Yüklenen token'ların durumunu göster"""
    try:
        manager = get_multi_token_manager()
        return {
            "loaded_clients": list(manager.clients.keys()),
            "total_clients": len(manager.clients),
            "api_keys_masked": {
                ai_type: f"{key[:15]}...{key[-10:]}" if len(key) > 25 else "***"
                for ai_type, key in manager.api_keys.items()
            }
        }
    except Exception as e:
        return {"error": f"Token status hatası: {str(e)}"}

async def test_all_clients():
    """Tüm AI client'larını paralel test et (hızlı versiyon - models.list kullanır)"""
    manager = get_multi_token_manager()

    async def _test_one(ai_type):
        try:
            client = manager.get_client(ai_type)
            if not client:
                return ai_type, {"status": "❌ Client bulunamadı"}
            # models.list çok daha hızlı (~200ms vs ~2s completion)
            models_resp = await asyncio.wait_for(
                asyncio.to_thread(lambda: client.models.list()),
                timeout=5.0
            )
            # İlk modelin adını al (bağlantı kanıtı)
            first_model = next(iter(models_resp), None)
            model_name = getattr(first_model, 'id', 'unknown') if first_model else 'unknown'
            return ai_type, {"status": "✅ Başarılı", "sample_model": model_name}
        except asyncio.TimeoutError:
            return ai_type, {"status": "⏱️ Zaman aşımı (5s)"}
        except Exception as e:
            return ai_type, {"status": f"❌ Hata: {str(e)[:50]}"}

    tasks = [_test_one(ai_type) for ai_type in manager.clients.keys()]
    results_list = await asyncio.gather(*tasks)
    return dict(results_list)

# Backwards compatibility - legacy function names
safe_anthropic_request = safe_openai_request  # Compatibility alias
