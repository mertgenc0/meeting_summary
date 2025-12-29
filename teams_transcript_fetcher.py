import requests
import json
import os
from datetime import datetime  # Zaman damgası için gerekli modül
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_ID = os.getenv("USER_ID")

DB_FILE = "meetings_db.json"
N8N_WEBHOOK_URL = ""


def get_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default"
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)


def get_meeting_id_from_url(token, join_url):
    url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/onlineMeetings"
    params = {"$filter": f"JoinWebUrl eq '{join_url}'"}
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        values = res.json().get("value", [])
        return values[0].get("id") if values else None
    return None


def get_transcript_content(token, meeting_id):
    headers = {"Authorization": f"Bearer {token}"}
    list_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/onlineMeetings/{meeting_id}/transcripts"

    res = requests.get(list_url, headers=headers)
    if res.status_code == 200:
        transcripts = res.json().get("value", [])
        if transcripts:
            t_id = transcripts[0]["id"]
            content_url = f"{list_url}/{t_id}/content"
            c_headers = {"Authorization": f"Bearer {token}", "Accept": "text/vtt"}
            c_res = requests.get(content_url, headers=c_headers)
            c_res.encoding = 'utf-8'
            return c_res.text if c_res.status_code == 200 else None
    return None

"""
def send_to_n8n(data):
    if N8N_WEBHOOK_URL:
        try:
            r = requests.post(N8N_WEBHOOK_URL, json=data)
            if r.status_code == 200:
                print(">>> Veri başarıyla n8n'e iletildi.")
        except Exception as e:
            print(f"!!! n8n gönderim hatası: {e}")
"""


def main():
    print("Sistem başlatıldı")
    try:
        token = get_token()
    except Exception as e:
        print(f"Kritik Hata (Token alınamadı): {e}")
        return

    db = load_db()

    events_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/events"
    headers = {"Authorization": f"Bearer {token}"}
    events_res = requests.get(events_url, headers=headers)
    events_res.encoding = 'utf-8'
    events = events_res.json().get("value", [])

    new_data_processed = False

    for event in events:
        online = event.get("onlineMeeting")
        if not online: continue

        join_url = online.get("joinUrl")
        subject = event.get("subject")

        if join_url in db and db[join_url].get("status") == "completed":
            continue

        print(f"\nKontrol ediliyor: {subject}")

        meeting_id = db.get(join_url, {}).get("meeting_id")
        if not meeting_id:
            meeting_id = get_meeting_id_from_url(token, join_url)

        if not meeting_id:
            print(f" ID bulunamadı, döküm olmayabilir.")
            continue

        transcript = get_transcript_content(token, meeting_id)

        if transcript:
            db[join_url] = {
                "subject": subject,
                "meeting_id": meeting_id,
                "start": event.get("start", {}).get("dateTime"),
                "transcript": transcript,
                "status": "completed",
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Hatalı kısım düzeltildi
            }
            new_data_processed = True
            print(f"   ✅ Döküm alındı: {subject}")

            #send_to_n8n(db[join_url])
        else:
            print(f"   ⚠️ Döküm henüz hazır değil.")
            db[join_url] = {"subject": subject, "meeting_id": meeting_id, "status": "pending"}

    if new_data_processed:
        save_db(db)
        print("\nİşlem tamamlandı. Yeni dökümler kaydedildi.")
    else:
        print("\nYeni döküm bulunamadı.")


if __name__ == "__main__":
    main()