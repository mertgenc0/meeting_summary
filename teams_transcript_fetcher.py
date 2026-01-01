import requests
import json
import os
import sys
import re  # Metin temizleme için eklendi
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_ID = os.getenv("USER_ID")

DB_FILE = "meetings_db.json"


def clean_vtt(vtt_text):
    """
    VTT formatındaki dökümü temizler:
    - WEBVTT başlığını siler.
    - Zaman damgalarını (00:00:00.000 --> ...) siler.
    - <v İsim> etiketlerini 'İsim: ' formatına çevirir.
    """
    if not vtt_text:
        return ""

    lines = vtt_text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        # WEBVTT başlığını, boş satırları ve zaman damgalarını atla
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue

        # Konuşmacı etiketini temizle: <v Mert Genc>Merhaba</v> -> Mert Genc: Merhaba
        speaker_match = re.search(r'<v (.*?)>(.*?)</v>', line)
        if speaker_match:
            speaker_name = speaker_match.group(1)
            content = speaker_match.group(2)
            cleaned_lines.append(f"{speaker_name}: {content}")
        else:
            # Etiket yoksa ama metin varsa direkt ekle
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


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
        except:
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
            c_res = requests.get(content_url, headers={"Authorization": f"Bearer {token}", "Accept": "text/vtt"})
            c_res.encoding = 'utf-8'
            return c_res.text if c_res.status_code == 200 else None
    return None


def main():
    try:
        token = get_token()
        db = load_db()
        events_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/events"
        events = requests.get(events_url, headers={"Authorization": f"Bearer {token}"}).json().get("value", [])

        new_meetings = []

        for event in events:
            online = event.get("onlineMeeting")
            if not online: continue

            join_url = online.get("joinUrl")
            if join_url in db and db[join_url].get("status") == "completed":
                continue

            meeting_id = get_meeting_id_from_url(token, join_url)
            if meeting_id:
                raw_transcript = get_transcript_content(token, meeting_id)
                if raw_transcript:

                    clean_transcript = clean_vtt(raw_transcript)#

                    meeting_data = {
                        "subject": event.get("subject"),
                        "meeting_id": meeting_id,
                        "join_url": join_url,
                        "start": event.get("start", {}).get("dateTime"),
                        "end": event.get("end", {}).get("dateTime"),
                        "transcript": clean_transcript,  # Temizlenmiş veri
                        "status": "completed",
                        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    db[join_url] = meeting_data
                    new_meetings.append(meeting_data)

        if new_meetings:
            save_db(db)
            print(json.dumps(new_meetings, ensure_ascii=False))
        else:
            print(json.dumps([]))

    except Exception as e:
        sys.stderr.write(f"Hata Oluştu: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()