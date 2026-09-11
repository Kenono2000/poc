"""Google Sheets job-application tracker tool.

Reads the candidate's Google Sheet that registers every company already
applied to (tab ``apps``) so the compliance auditor can deduplicate live
job results before they are surfaced to the candidate.

Authentication uses a service-account key file (``service_account.json``
by default, path overridable via the ``GOOGLE_SERVICE_ACCOUNT_FILE`` env
var).  The service account must have read access to the target spreadsheet.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import gspread
import gspread.exceptions as gspread_exc
from crewai.tools import BaseTool
from google.auth.exceptions import GoogleAuthError
from google.oauth2.service_account import Credentials

SCOPES: list[str] = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleSheetsTrackerTool(BaseTool):
    name: str = "Google Sheets Application Tracker"
    description: str = (
        "Reads the candidate's Google Sheet application tracker and returns "
        "every row of the configured worksheet as JSON. Use this to look up "
        "already-applied companies and titles so that no duplicate role is "
        "ever surfaced. Provide a spreadsheet_id and tab/worksheet name."
    )

    def _credentials(self) -> Credentials:
        cred_path = os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            str(Path(__file__).resolve().parents[2] / "service_account.json"),
        )
        return Credentials.from_service_account_file(cred_path, scopes=SCOPES)

    def _run(
        self,
        spreadsheet_id: str,
        tab: str = "apps",
    ) -> str:
        blocked = {
            "status": "BLOCKED",
        }

        try:
            client = gspread.authorize(self._credentials())
        except (GoogleAuthError, OSError) as exc:
            return json.dumps(
                {
                    **blocked,
                    "reason": (
                        "Could not authenticate with Google Sheets. "
                        "Ensure a valid service-account key is available "
                        "(GOOGLE_SERVICE_ACCOUNT_FILE env var or "
                        "service_account.json next to the project)."
                    ),
                    "error": repr(exc),
                },
                ensure_ascii=False,
            )

        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
        except gspread_exc.SpreadsheetNotFound as exc:
            return json.dumps(
                {
                    **blocked,
                    "reason": f"Spreadsheet {spreadsheet_id} was not found.",
                    "error": repr(exc),
                },
                ensure_ascii=False,
            )
        except (gspread_exc.APIError, gspread_exc.GSpreadException) as exc:
            return json.dumps(
                {
                    **blocked,
                    "reason": f"Spreadsheet {spreadsheet_id} is not accessible.",
                    "error": repr(exc),
                },
                ensure_ascii=False,
            )

        try:
            worksheet = spreadsheet.worksheet(tab)
        except gspread_exc.WorksheetNotFound:
            worksheet = spreadsheet.sheet1

        try:
            records: list[dict[str, Any]] = worksheet.get_all_records()
        except (gspread_exc.APIError, gspread_exc.GSpreadException) as exc:
            return json.dumps(
                {
                    **blocked,
                    "reason": "Worksheet records could not be read.",
                    "error": repr(exc),
                },
                ensure_ascii=False,
            )

        companies = sorted({r.get("company", "") for r in records if r.get("company")})
        titles = sorted({r.get("title", "") for r in records if r.get("title")})

        return json.dumps(
            {
                "status": "OK",
                "spreadsheet_id": spreadsheet_id,
                "tab": worksheet.title,
                "row_count": len(records),
                "applied_companies": companies,
                "applied_titles": titles,
                "raw_rows": records,
            },
            ensure_ascii=False,
            indent=2,
        )
