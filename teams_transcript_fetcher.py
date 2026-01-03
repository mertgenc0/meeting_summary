import requests
import json
import os
import sys
import re
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Microsoft graph API bilgileri
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_ID = os.getenv("USER_ID")

# Postgresql Bilgileri
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def check_if_exists(join_url):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM meetings WHERE join_url = %s", (join_url,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def clean_vtt(vtt_text):
    if not vtt_text: return ""
    lines = vtt_text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        speaker_match = re.search(r'<v (.*?)>(.*?)</v>', line)
        if speaker_match:
            cleaned_lines.append(f"{speaker_match.group(1)}: {speaker_match.group(2)}")
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def get_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials", "scope": "https://graph.microsoft.com/.default"
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


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
            c_res = requests.get(content_url, headers={"Authorization": f"Bearer {token}", "Accept": "text/vtt"})#Accept şart
            c_res.encoding = 'utf-8'
            return c_res.text if c_res.status_code == 200 else None
    return None


def main():
    try:
        token = get_token()

        # SADECE SON 24 SAAT (n8n her gün çalıştığı için)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        events_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/events"
        params = {
            "$filter": f"start/dateTime ge '{yesterday}'",# Sistem her gün otoamatik çalışıtırlacak şekilde tasaralnmıştır belli bir zaman sonra scriptin çalışma zamanı ve kontrolü uzamamsı için şart.
            "$select": "subject,onlineMeeting,start,end"
        }

        events_res = requests.get(events_url, headers={"Authorization": f"Bearer {token}"}, params=params)
        events = events_res.json().get("value", [])

        new_meetings_to_output = []

        for event in events:
            online = event.get("onlineMeeting")
            if not online: continue

            join_url = online.get("joinUrl")

            if check_if_exists(join_url):# Eğer kayıt gece ssatleri gibi sebelerden çakışma yaşanabilir ve eğer aynı joinurl varsa bunu yeni kayıt diye alamsın.
                continue

            meeting_id = get_meeting_id_from_url(token, join_url)
            if meeting_id:
                raw_transcript = get_transcript_content(token, meeting_id)
                if raw_transcript:
                    clean_transcript = clean_vtt(raw_transcript)

                    meeting_data = {
                        "subject": event.get("subject"),
                        "meeting_id": meeting_id,
                        "join_url": join_url,
                        "start_time": event.get("start", {}).get("dateTime"),
                        "end_time": event.get("end", {}).get("dateTime"),
                        "transcript": clean_transcript,
                        "status": "completed"
                    }
                    # Sadece yeni olanları listeye ekle
                    new_meetings_to_output.append(meeting_data)
        print(json.dumps(new_meetings_to_output, ensure_ascii=False))

    except Exception as e:
        sys.stderr.write(f"Hata: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()