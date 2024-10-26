
### This script will take the emails sent by codeforces on contests and aim to add events on your calender according to the contest dates and durations.

## Usage

### Configure Google API:

1. **Go to Google Cloud Console**: [Console](https://console.cloud.google.com/).

2. **Select Project**: Ensure your project is selected.
3. **Enable APIs**: 
   - Navigate to **APIs & Services** > **Library**.
   - Enable **Gmail API** and **Google Calendar API**.
4. **Configure OAuth Consent Screen** 
   - Click **Create credentials** > **OAuth client ID**.
   - Choose **Desktop Application**
   - **Add Scopes** :
      - `https://www.googleapis.com/auth/gmail.readonly`
      - `https://www.googleapis.com/auth/calender.events.owned`
1. **Go to Credentials**: **APIs & Services** > **Credentials**.
   - Download the json file containing credentials
   - Rename it to credentials.json
   - Put it inside file location with cfdate.py

For Additional Help, refer to official documentation/youtube videos on configuring google api

### Install the following libraries:

```
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

pip install pytz

pip install tzdata

```
### Edit cfdate.py
Use your timezone in place for Asia/Dhaka
```python
LOCAL_TIMEZONE = 'Asia/Dhaka'  # Use your timezone
```
Currently the script is will only look for Div 2, Div 3 or Div 4 contests in the last 14 days. Feel free to tweak it to your needs.

### Run Script
```
python cfdate.py
```
Sign in with Google and Give user permissions
