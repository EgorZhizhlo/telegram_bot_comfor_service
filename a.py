from google.oauth2.service_account import Credentials
import gspread
import os

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_file('auth_info.json', scopes=scopes)
client = gspread.authorize(creds)

# получим список всех таблиц
all_spreadsheets = client.openall()
for ss in all_spreadsheets:
    print(f"{ss.title} — id: {ss.id}")
