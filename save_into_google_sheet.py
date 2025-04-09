import os
import gspread
from google.oauth2.service_account import Credentials


scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


async def insert_info_into_sheet(data):
    try:
        creds = Credentials.from_service_account_file(
            'auth_info.json', scopes=scopes)
        client = gspread.authorize(creds)
        INFO_SPREADSHEET_KEY = os.getenv("INFO_SPREADSHEET_KEY")
        spreadsheet = client.open_by_key(INFO_SPREADSHEET_KEY)
        sheet = spreadsheet.sheet1
        sheet.append_row(data, value_input_option='USER_ENTERED')
        return True
    except Exception:
        return False
