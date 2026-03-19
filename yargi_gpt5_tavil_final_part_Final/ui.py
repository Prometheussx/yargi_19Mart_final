import io
import json
import time
import os
import threading
from typing import List, Dict, Any

import requests
import streamlit as st


# Config: Streamlit secrets yoksa env veya localhost'a düş
API_BASE = "http://127.0.0.1:8000"
try:
	API_BASE = st.secrets["API_BASE"]
except Exception:
	API_BASE = os.environ.get("API_BASE", API_BASE)


def new_session_id() -> str:
	try:
		r = requests.get(f"{API_BASE}/session/new", timeout=15)
		r.raise_for_status()
		return r.json().get("session_id")
	except Exception as e:
		st.error(f"Session oluşturulamadı: {e}")
		return ""


def ensure_session() -> str:
	if "session_id" not in st.session_state or not st.session_state["session_id"]:
		st.session_state["session_id"] = new_session_id()
	return st.session_state["session_id"]


def api_headers(session_id: str) -> Dict[str, str]:
	return {"session_id": session_id}


def upload_files(session_id: str, files: List[Any]):
	for f in files:
		try:
			files_payload = {"file": (f.name, f.getvalue(), f.type or "application/octet-stream")}
			r = requests.post(f"{API_BASE}/upload-file", headers=api_headers(session_id), files=files_payload, timeout=120)
			data = r.json()
			if not data.get("success"):
				st.warning(f"{f.name}: yüklenemedi: {data}")
			else:
				st.toast(f"Yüklendi: {f.name}")
		except Exception as e:
			st.error(f"{f.name}: yükleme hatası: {e}")


def remove_file(session_id: str, filename: str):
	try:
		r = requests.post(
			f"{API_BASE}/remove-file",
			headers={**api_headers(session_id), "Content-Type": "application/json"},
			data=json.dumps({"filename": filename}),
			timeout=30,
		)
		return r.json()
	except Exception as e:
		st.error(f"Dosya kaldırılamadı: {e}")
		return {"error": str(e)}


def send_chat(session_id: str, text: str, *, is_petition: bool, detail: str, scan_precedents: bool = True, party_info: str | None = None, situation_info: str | None = None):
	fd = {
		"message": text,
		"is_petition": str(bool(is_petition)).lower(),
		"chat_detail": detail,
	}
	# Emsal tarama tercihini gönder (sadece detay modda anlamlı, concise ise backend zaten yoksayacak)
	fd["scan_precedents"] = str(bool(scan_precedents)).lower()
	if party_info:
		fd["party_info"] = party_info
	if situation_info:
		fd["situation_info"] = situation_info
	try:
		r = requests.post(f"{API_BASE}/chat", headers=api_headers(session_id), data=fd, timeout=600)
		return r.json()
	except Exception as e:
		return {"success": False, "error": str(e)}


# Case preview kaldırıldı


def get_chat_precedent_set(session_id: str, precedent_set_id: str):
	try:
		r = requests.get(f"{API_BASE}/chat-precedents/{session_id}/{precedent_set_id}")
		return r.json()
	except Exception as e:
		return {"error": str(e)}


# Case analysis raw kaldırıldı


def enhance_prompt(session_id: str, text: str):
	try:
		r = requests.post(f"{API_BASE}/enhance-prompt", headers=api_headers(session_id), data={"prompt": text}, timeout=60)
		return r.json()
	except Exception as e:
		return {"error": str(e)}


def render_messages(messages: List[Dict[str, Any]]):
	for m in messages:
		role = m.get("role") or m.get("type") or "assistant"
		content = m.get("content") or m.get("response") or ""
		if role == "user":
			with st.chat_message("user"):
				st.write(content)
		else:
			with st.chat_message("assistant"):
				st.markdown(content)


def render_precedents_block(precedents: List[Dict[str, Any]], search_query: str | None = None):
	st.subheader("Emsal Kararlar")
	if search_query:
		st.caption(f"Arama: {search_query}")
	if not precedents:
		st.info("Emsal bulunamadı")
		return
	for p in precedents[:50]:
		title = p.get("title") or f"{p.get('birim','')} - {p.get('tarih','')}"
		code = p.get("id") or p.get("document_id")
		full = p.get("full_content") or p.get("content") or p.get("markdown_content") or ""
		with st.expander(f"[{code}] {title}"):
			st.text(full)


def main():
	st.set_page_config(page_title="Yargı AI UI", page_icon="⚖️", layout="wide")
	st.title("⚖️ Yargı AI")

	session_id = ensure_session()
	st.sidebar.success(f"Session: {session_id[:8]}")

	# Modes
	st.sidebar.subheader("Modlar")
	is_petition = st.checkbox("Dilekçe", value=False)

	detail = st.sidebar.selectbox("Yanıt stili", options=["concise", "detailed"], index=0)

	# Emsal tarama seçeneği: sadece detaylı modda anlamlıdır
	scan_precedents = True
	if detail == "detailed":
		scan_precedents = st.sidebar.checkbox("Emsal Tara", value=True, help="Detaylı modda emsal kararlar taransın ve yanıta eklensin")
	else:
		st.sidebar.checkbox("Emsal Tara", value=False, help="Kısa modda emsal taranmaz", disabled=True)

	st.sidebar.caption("Detaylı modda emsal ve web kaynakları eklenir.")

	# Prompt araçları (yalnızca güzelleştir, gönderim yok)
	st.sidebar.subheader("Prompt Araçları")
	with st.sidebar.expander("Taslak Üzerinde Çalış", expanded=False):
		_draft_val = st.session_state.get("prompt_draft", "")
		prompt_draft = st.text_area("Taslak", value=_draft_val, height=120, placeholder="Buraya taslak yazıp güzelleştirebilir ve gönderebilirsiniz")
		# Widget key kullanmadan state senkronizasyonu
		st.session_state["prompt_draft"] = prompt_draft
		if st.button("✨ Güzelleştir", use_container_width=True):
			if not prompt_draft or not prompt_draft.strip():
				st.warning("Önce taslak yazın")
			else:
				res = enhance_prompt(session_id, prompt_draft)
				if res.get("success") and res.get("enhanced"):
					st.session_state["prompt_draft"] = res["enhanced"].strip()
					st.success("Güzelleştirildi")
					try:
						st.rerun()
					except Exception:
						try:
							st.experimental_rerun()
						except Exception:
							pass
				else:
					st.error(res.get("error") or "Prompt güzelleştirilemedi")
    
	st.sidebar.subheader("Opsiyonel Notlar")
	party_info = st.sidebar.text_input("Taraf bilgisi (opsiyonel)", placeholder="Örn: Davacı vekiliyim…")
	situation_info = st.sidebar.text_area("Durum/olay özeti (opsiyonel)", height=80)

	st.sidebar.divider()
	if st.sidebar.button("Yeni Session", type="primary"):
		st.session_state["session_id"] = new_session_id()
		st.rerun()

	st.sidebar.divider()
	uploaded = st.sidebar.file_uploader("Dosyalar (PDF/TXT/DOC/DOCX)", type=["pdf", "txt", "doc", "docx"], accept_multiple_files=True)
	if uploaded:
		upload_files(session_id, uploaded)

	# Emsal önizleme kaldırıldı

	# Chat area
	if "messages" not in st.session_state:
		st.session_state["messages"] = [
			{"role": "assistant", "content": "Merhaba! Dosya yükleyin ve mesaj yazın. Dilekçe modunu seçebilir, detaylı modda emsal ve web kaynaklarıyla destekli yanıt alabilirsiniz."}
		]

	for m in st.session_state["messages"]:
		with st.chat_message(m.get("role", "assistant")):
			st.markdown(m.get("content", ""))

	user_text = st.chat_input("Mesajınızı yazın…")
	if user_text:
		st.session_state["last_user_text"] = user_text
		st.session_state["messages"].append({"role": "user", "content": user_text})
		with st.chat_message("user"):
			st.write(user_text)

		# Emsal önizleme kaldırıldı

		with st.chat_message("assistant"):
			# Sayaçlı bekleme: istek arka planda; her 0.2 sn'de sayaç güncellenir
			status_ph = st.empty()
			resp_holder: Dict[str, Any] = {}
			done = threading.Event()

			def _fetch():
				resp_holder["resp"] = send_chat(
					session_id,
					user_text,
					is_petition=is_petition,
					detail=detail,
					scan_precedents=(scan_precedents if detail == "detailed" else False),
					party_info=party_info.strip() if party_info else None,
					situation_info=situation_info.strip() if situation_info else None,
				)
				done.set()

			th = threading.Thread(target=_fetch, daemon=True)
			th.start()

			start_ts = time.time()
			while not done.is_set():
				elapsed = int(time.time() - start_ts)
				status_ph.markdown(f"⏳ Yanıt hazırlanıyor… {elapsed} sn")
				time.sleep(0.2)

			status_ph.empty()
			resp = resp_holder.get("resp", {"success": False, "error": "Yanıt alınamadı"})

			if resp.get("success"):
				content = resp["response"].get("content") or resp["response"].get("response") or ""
				st.markdown(content)
				st.session_state["messages"].append({"role": "assistant", "content": content})

				# Load detailed precedents if chat provides precedent_set_id
				if resp["response"].get("precedent_set_id"):
					pset = get_chat_precedent_set(session_id, resp["response"]["precedent_set_id"])
					if pset.get("precedents"):
						st.session_state["precedents_preview"] = {"precedents": pset.get("precedents")}
			else:
				err = resp.get("response", {}).get("content") or resp.get("error") or "Bilinmeyen hata"
				st.error(err)
				st.session_state["messages"].append({"role": "assistant", "content": f"❌ {err}"})

	# Right column: precedents
	with st.sidebar:
		st.divider()
		st.subheader("Emsaller")
		pre = st.session_state.get("precedents_preview")
		if pre and pre.get("precedents"):
			for p in pre.get("precedents")[:20]:
				title = p.get("title") or f"{p.get('birim','')} - {p.get('tarih','')}"
				code = p.get("id") or p.get("document_id")
				with st.expander(f"[{code}] {title}"):
					full = p.get("full_content") or p.get("content") or p.get("markdown_content") or ""
					st.text(full)
		else:
			st.caption("Emsal görünmüyor. Detaylı modda soru sorarak emsal görebilirsiniz.")


if __name__ == "__main__":
	main()

