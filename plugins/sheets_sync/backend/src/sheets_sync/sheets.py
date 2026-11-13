"""
Minimal Google Sheets API v4 client over google-auth's AuthorizedSession.

Endpoints (developers.google.com/workspace/sheets/api/reference/rest/v4):
- spreadsheets.values.get, values.batchUpdate, values.append
- spreadsheets.get and spreadsheets.batchUpdate (deleteDimension)
"""

import json
import re
from urllib.parse import quote

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from requests.exceptions import RequestException

from baserow.contrib.database.data_sync.exceptions import SyncError

API_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TIMEOUT_SECONDS = 60


def parse_spreadsheet_id(value: str) -> str:
    """Accepts the spreadsheet ID or the URL it's copied from."""

    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", value)
    return match.group(1) if match else value.strip()


def column_letter(index: int) -> str:
    """Zero-based column index to its A1 letters: 0 -> A, 26 -> AA."""

    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def a1_range(sheet_name: str, cells: str = "") -> str:
    # Quotes are required for names with spaces (sheets/api/guides/concepts#cell).
    # shortcut: a quote inside the name is doubled as in Sheets formulas; not in
    # the API docs, check it if a tab name contains a quote.
    quoted = "'" + sheet_name.replace("'", "''") + "'"
    return f"{quoted}!{cells}" if cells else quoted


def to_sheet_value(value) -> str:
    if value is None:
        return ""
    value = str(value)
    # Writes use USER_ENTERED so numbers and dates stay numbers and dates, which
    # would also run a leading "=" as a formula. A leading quote keeps it text.
    return "'" + value if value.startswith("=") else value


class SheetsClient:
    def __init__(self, data_sync):
        try:
            info = json.loads(data_sync.google_service_account_key)
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
        # MalformedError is a ValueError; a JSON list fails on `.keys()`.
        except (ValueError, TypeError, KeyError, AttributeError):
            raise SyncError("The service account key is not a valid Google JSON key.")
        self.session = AuthorizedSession(credentials)
        self.spreadsheet_id = parse_spreadsheet_id(data_sync.google_spreadsheet_id)
        self.sheet_name = data_sync.google_sheet_name

    def _call(self, method: str, path: str, **kwargs) -> dict:
        url = f"{API_URL}/{quote(self.spreadsheet_id, safe='')}{path}"
        try:
            response = self.session.request(
                method, url, timeout=TIMEOUT_SECONDS, **kwargs
            )
        except (RequestException, GoogleAuthError) as e:
            raise SyncError(f"Google Sheets could not be reached: {e}")
        if not response.ok:
            try:
                message = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                message = response.text[:200]
            raise SyncError(
                f"Google Sheets responded with {response.status_code}: {message}"
            )
        return response.json()

    def read_table(self) -> tuple[list[str], list[list]]:
        """The header row and the rows below it, as the cells are displayed."""

        data = self._call(
            "GET",
            f"/values/{quote(a1_range(self.sheet_name), safe='')}",
            params={"valueRenderOption": "FORMATTED_VALUE", "majorDimension": "ROWS"},
        )
        # Trailing empty rows and columns are left out of the response.
        values = data.get("values", [])
        if not values:
            raise SyncError(
                f"The sheet '{self.sheet_name}' is empty. Its first row must hold "
                "the column headers."
            )
        headers = [str(header).strip() for header in values[0]]
        return headers, values[1:]

    def update_cells(self, cells: list[tuple[int, int, str]]):
        """Writes `(row_number, column_index, value)` cells; row numbers start at 1."""

        self._call(
            "POST",
            "/values:batchUpdate",
            json={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {
                        "range": a1_range(
                            self.sheet_name, f"{column_letter(column)}{row}"
                        ),
                        "values": [[value]],
                    }
                    for row, column, value in cells
                ],
            },
        )

    def append_rows(self, rows: list[list[str]]):
        self._call(
            "POST",
            f"/values/{quote(a1_range(self.sheet_name, 'A1'), safe='')}:append",
            params={
                "valueInputOption": "USER_ENTERED",
                "insertDataOption": "INSERT_ROWS",
            },
            json={"values": rows},
        )

    def _sheet_id(self) -> int:
        data = self._call("GET", "", params={"fields": "sheets.properties"})
        for sheet in data.get("sheets", []):
            properties = sheet.get("properties", {})
            if properties.get("title") == self.sheet_name:
                return properties["sheetId"]
        raise SyncError(f"The sheet '{self.sheet_name}' does not exist.")

    def delete_rows(self, row_numbers: list[int]):
        sheet_id = self._sheet_id()
        # Bottom up, so deleting a row doesn't shift the ones still to delete.
        requests = [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        # Zero-based and end-exclusive (DimensionRange).
                        "startIndex": number - 1,
                        "endIndex": number,
                    }
                }
            }
            for number in sorted(set(row_numbers), reverse=True)
        ]
        self._call("POST", ":batchUpdate", json={"requests": requests})
