import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

load_dotenv()

def test_connection():
    try:
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        
        print(f"Fetch Credential: {creds_path}")
        print(f"Target Sheet ID: {sheet_id}")

        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # Establish Connection
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(creds)

        # Open and Read the spreadsheet
        sheet = client.open_by_key(sheet_id).get_worksheet(0) # First Tab
        first_row = sheet.row_values(1)
        
        print("Success")
        print(f"First Row: {first_row}")

    except Exception as e:
        print(f"Failed. Error message: {e}")

if __name__ == "__main__":
    test_connection()