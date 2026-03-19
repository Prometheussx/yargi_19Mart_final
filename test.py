"""
Yargı AI - Chat History Test
Aynı session_id ile iki istek atıp geçmiş (history) kontrolü yapar.
"""

import requests
import uuid
import json

BASE_URL = "http://164.92.236.99:8000"
SESSION_ID = str(uuid.uuid4())

print(f"Session ID: {SESSION_ID}\n")
print("=" * 60)

# --- 1. İstek: Hukuki bir soru sor ---
print("📤 1. İSTEK: Hukuki soru soruluyor...\n")

resp1 = requests.post(
    f"{BASE_URL}/chat",
    data={
        "message": "İş sözleşmesi feshedilen bir işçinin kıdem tazminatı hakkı ne zaman doğar ve hangi şartlarda ödenir?",
        "is_petition": False,
        "chat_detail": "concise",
        "scan_precedents": False,
    },
    headers={"session_id": SESSION_ID},
    timeout=120,
)

print(f"Status: {resp1.status_code}")
data1 = resp1.json()
print(f"Success: {data1.get('success')}")
print(f"Session ID (dönen): {data1.get('session_id')}")
print(f"\n--- AI Yanıtı ---")
print(data1.get("response", {}).get("content", "")[:500])
print(f"\n--- Chat History (mesaj sayısı): {len(data1.get('chat_history', []))} ---")
for msg in data1.get("chat_history", []):
    role = msg.get("role", "?")
    content = msg.get("content", "")[:80]
    print(f"  [{role}] {content}...")

print("\n" + "=" * 60)

# --- 2. İstek: Aynı session ile "daha basit anlat" de ---
print("📤 2. İSTEK: 'Bunu daha basit bir şekilde anlat' deniyor...\n")

resp2 = requests.post(
    f"{BASE_URL}/chat",
    data={
        "message": "Bunu daha basit ve kısa bir şekilde anlat, herkesin anlayacağı dilde özetle.",
        "is_petition": False,
        "chat_detail": "concise",
        "scan_precedents": False,
    },
    headers={"session_id": SESSION_ID},
    timeout=120,
)

print(f"Status: {resp2.status_code}")
data2 = resp2.json()
print(f"Success: {data2.get('success')}")
print(f"\n--- AI Yanıtı ---")
print(data2.get("response", {}).get("content", "")[:500])
print(f"\n--- Chat History (mesaj sayısı): {len(data2.get('chat_history', []))} ---")
for msg in data2.get("chat_history", []):
    role = msg.get("role", "?")
    content = msg.get("content", "")[:80]
    print(f"  [{role}] {content}...")

# --- Sonuç Değerlendirmesi ---
print("\n" + "=" * 60)
history_count = len(data2.get("chat_history", []))
print(f"\n🔍 SONUÇ DEĞERLENDİRMESİ:")
print(f"   Chat history mesaj sayısı: {history_count}")
if history_count >= 4:
    print("   ✅ BAŞARILI - Geçmiş korunuyor! (en az 4 mesaj: user+ai+user+ai)")
elif history_count >= 2:
    print("   ⚠️  KISMI - Geçmiş var ama eksik olabilir")
else:
    print("   ❌ BAŞARISIZ - Geçmiş korunmuyor!")

# 2. yanıtın içeriğinde önceki konuya referans var mı kontrol et
resp2_content = data2.get("response", {}).get("content", "").lower()
keywords = ["kıdem", "tazminat", "işçi", "fesih", "iş sözleşme"]
found = [k for k in keywords if k in resp2_content]
if found:
    print(f"   ✅ 2. yanıt önceki konuya referans içeriyor: {found}")
else:
    print("   ⚠️  2. yanıtta önceki konuya açık referans bulunamadı")
