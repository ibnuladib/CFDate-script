from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
import base64
from datetime import datetime, timedelta
import re
import pytz
from zoneinfo import ZoneInfo

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.events.owned'
]

CODEFORCES_EMAIL = "Codeforces@codeforces.com"
LOCAL_TIMEZONE = 'Asia/Dhaka'  # Use your timezone


def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_email_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode()
    elif 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode()
    return ""


def get_header_value(headers, name):
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ""


def is_valid_round_subject(subject):
    pattern = r"Codeforces Round (\d+) \(Div\. ([2-4])\)"
    return bool(re.match(pattern, subject))


def parse_contest_time(snippet):
    datetime_pattern = r"on ([A-Za-z]+), ([A-Za-z]+), (\d+), (\d{4}) (\d{2}):(\d{2}) \(UTC\)"
    datetime_match = re.search(datetime_pattern, snippet)
    if not datetime_match:
        return None, None

    duration_pattern = r"duration is (\d+) hours?(?: (\d+) minutes)?"
    duration_match = re.search(duration_pattern, snippet)

    if not duration_match:
        return None, None

    _, month, day, year, hour, minute = datetime_match.groups()
    start_time_str = f"{month} {day} {year} {hour}:{minute}"
    start_time = datetime.strptime(start_time_str, "%B %d %Y %H:%M")
    utc_time = start_time.replace(tzinfo=pytz.UTC)

    # Convert to local time
    local_time = utc_time.astimezone(ZoneInfo(LOCAL_TIMEZONE))

    # Calculate duration
    hours = int(duration_match.group(1))
    minutes = int(duration_match.group(2)) if duration_match.group(2) else 0
    duration = timedelta(hours=hours, minutes=minutes)

    return local_time, duration


def create_calendar_event(service, round_num, division, start_time, duration):
    if start_time <= datetime.now(ZoneInfo(LOCAL_TIMEZONE)):
        print("Event time is in the past. Skipping event creation.")
        return False

    end_time = start_time + duration

    time_min = start_time.isoformat()
    time_max = (start_time + timedelta(minutes=1)).isoformat()
    event_summary = f'CodeForces Div {division}'

    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            q=event_summary,
            singleEvents=True
        ).execute()

        existing_events = events_result.get('items', [])
        if existing_events:
            print("Event already exists in the calendar.")
            return False

        event = {
            'summary': event_summary,
            'description': f'Codeforces Round {round_num} (Division {division})',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': LOCAL_TIMEZONE,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': LOCAL_TIMEZONE,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f'Calendar event created: {event.get("htmlLink")}')
        return True

    except HttpError as error:
        print(f'An error occurred creating the calendar event: {error}')
        return False


def process_codeforces_emails():
    try:
        creds = get_credentials()
        gmail_service = build('gmail', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)

        fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y/%m/%d')
        query = f'from:{CODEFORCES_EMAIL} subject:"Codeforces Round" after:{fourteen_days_ago}'

        results = gmail_service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No Codeforces Round emails found in the last 14 days.")
            return

        matching_emails = []
        for message in messages:
            msg = gmail_service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = get_header_value(headers, 'subject')

            if is_valid_round_subject(subject):

                round_match = re.search(r"Round (\d+) \(Div\. ([2-4])\)", subject)
                if round_match:
                    full_content = get_email_body(msg['payload'])
                    round_num = round_match.group(1)
                    division = round_match.group(2)
                    start_time, duration = parse_contest_time(full_content)

                    if start_time and duration:
                        matching_emails.append({
                            "round_num": round_num,
                            "division": division,
                            "start_time": start_time,
                            "duration": duration
                        })

        print("Matching Codeforces Round emails:")
        for email in matching_emails:
            print(f"\nRound {email['round_num']} (Div. {email['division']})")
            print(f"Start Time (Local): {email['start_time'].strftime('%Y-%m-%d %H:%M %Z')}")
            print(f"Duration: {email['duration']}")

        print("\nCreating calendar events for future Codeforces rounds...")
        for email in matching_emails:
            if email['start_time'] > datetime.now(ZoneInfo(LOCAL_TIMEZONE)):
                if create_calendar_event(
                        calendar_service,
                        email['round_num'],
                        email['division'],
                        email['start_time'],
                        email['duration']):
                    print("Calendar event created successfully!")
                else:
                    print("Failed to create calendar event or it already exists.")
            else:
                print("Event time is in the past, skipping event creation.")

    except HttpError as error:
        print(f'An error occurred: {error}')


if __name__ == "__main__":
    process_codeforces_emails()
