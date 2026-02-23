import os
import json
import httpx
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP Server
mcp = FastMCP("Sleepon", dependencies=["httpx", "python-dotenv"])

# ---------------------------------------------------------------------------
# Sleepon API Client  –  centralises login, token caching, headers & HTTP I/O
# ---------------------------------------------------------------------------

# Default headers required by the Sleepon backend on every request
SLEEPON_DEFAULT_HEADERS = {
    "Accept-Language": "en",
    "System-Name": "iOS",
    "Machine": "iPhone8,1",
    "System-Version": "14.4.1",
    "App-Version": "1.01",
}


class SleeponClient:
    """Singleton-style wrapper around the Sleepon REST API.

    * Logs in **once** (lazily, on the first API call) and caches the token.
    * Reuses a single ``httpx.AsyncClient`` for the lifetime of the server
      process so TCP connections are kept alive.
    * Attaches the required client-identification headers to **every** request.
    """

    def __init__(self):
        self.base_url: str = os.getenv(
            "SLEEPON_API_BASE_URL", "https://sleep3-dev.sleepon.us/v1/api"
        )
        self._username: str = os.getenv("SLEEPON_USERNAME", "")
        self._password: str = os.getenv("SLEEPON_PASSWORD", "")
        self._token: Optional[str] = None
        self._http: Optional[httpx.AsyncClient] = None

    # -- HTTP client management ------------------------------------------------

    @property
    def http(self) -> httpx.AsyncClient:
        """Return (and lazily create) the shared ``httpx.AsyncClient``."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=30.0,
                headers=SLEEPON_DEFAULT_HEADERS,  # attached to every request
            )
        return self._http

    # -- Authentication --------------------------------------------------------

    async def login(self, force: bool = False) -> str:
        """Authenticate and cache the access token.

        If the token has already been acquired and *force* is ``False``, the
        cached token is returned immediately – no network call is made.
        """
        if self._token and not force:
            return self._token

        if not self._username or not self._password:
            raise ValueError(
                "SLEEPON_USERNAME or SLEEPON_PASSWORD not set in environment variables."
            )

        url = f"{self.base_url}/user/login"
        params = {"username": self._username, "password": self._password}

        try:
            response = await self.http.get(url, params=params)
        except httpx.HTTPError as exc:
            raise ValueError(f"HTTP error during login: {exc}") from exc

        data = self._parse_response(response)

        token_info = data.get("details", {}).get("token", {})
        token = str(token_info.get("access_token", ""))
        if not token or token == "None":
            raise ValueError("Could not find access_token in the login response.")

        self._token = token
        return self._token

    # -- Generic API request ---------------------------------------------------

    async def request(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Any:
        """Make an authenticated request to the Sleepon API.

        Automatically logs in (once) if no token is available yet.
        """
        token = await self.login()
        url = f"{self.base_url}{endpoint}"

        for attempt in range(2):  # retry once on 401
            headers = {"Authorization": f"Bearer {token}"}

            try:
                if method.upper() == "GET":
                    response = await self.http.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await self.http.post(url, headers=headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
            except httpx.HTTPError as exc:
                return {"error": f"HTTP API request failed: {type(exc).__name__}: {exc}"}

            try:
                data = response.json()
            except Exception:
                response.raise_for_status()
                return {"error": "Received invalid non-JSON response from server"}

            # Auto-refresh token on 401 Unauthorized, then retry
            if response.status_code == 401 or data.get("code") == 16:
                if attempt == 0:
                    token = await self.login(force=True)
                    continue
                return {"error": "Unauthorized after token refresh – please check credentials."}

            if data.get("code") != 0:
                return {
                    "error": (
                        f"API Error {data.get('code')}: "
                        f"{data.get('message', '')} - {data.get('cause', '')}"
                    )
                }

            return data

        return {"error": "Request failed after retry."}

    # -- Helpers ---------------------------------------------------------------

    @staticmethod
    def _parse_response(response: httpx.Response) -> dict:
        """Parse a JSON response, handling Sleepon's HTTP-500-for-business-errors quirk."""
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            raise ValueError("Received invalid non-JSON response from server")

        if data.get("code") != 0:
            raise ValueError(
                f"API error: {data.get('message', 'Unknown')} – {data.get('cause', '')}"
            )
        return data


# Global singleton – one client for the whole MCP server session
client = SleeponClient()

# Fields to strip from API responses – meaningless for LLM analysis
_NOISE_FIELDS = {
    "day_id", "user_id", "id", "label_id",
    "is_sync20", "is_deleted",
    "created_at", "updated_at",
}


def _strip_fields(obj, extra_fields: set = None):
    """Recursively remove noisy / internal fields from dicts and lists."""
    fields = _NOISE_FIELDS | (extra_fields or set())
    if isinstance(obj, dict):
        return {k: _strip_fields(v, extra_fields) for k, v in obj.items() if k not in fields}
    if isinstance(obj, list):
        return [_strip_fields(item, extra_fields) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def login_and_check_status() -> str:
    """
    Force a login / re-login and check if authentication is successful.
    Use this to verify credentials are correct and the API is reachable.
    """
    try:
        token = await client.login(force=True)
        return f"Successfully logged in! Access token acquired: {token[:10]}... (truncated for security)"
    except Exception as exc:
        return f"Failed to login: {exc}"


@mcp.tool()
async def get_user_profile() -> str:
    """
    Get the basic user profile information of the currently logged-in user.
    """
    try:
        data = await client.request("/user")

        if "error" in data:
            return data["error"]

        details = data.get("details", {})

        return (
            f"User Profile Information:\n"
            f"- User ID: {details.get('user_id')}\n"
            f"- Email: {details.get('email')}\n"
            f"- Name: {details.get('nickname') or details.get('first_name')}\n"
            f"- Devices: {details.get('user_device_info', {}).get('device_name', 'None')}\n"
            f"- Last Sync: {details.get('user_detail', {}).get('last_data_sync_time', 'Unknown')}\n"
        )
    except Exception as exc:
        return f"Error fetching user profile: {exc}"


@mcp.tool()
async def get_daily_sleep_summary(date: str) -> str:
    """
    Get **complete** daily sleep summary data (via the /data/:date/detail API).

    Args:
        date: The date to query in YYYY-MM-DD format (e.g. "2024-03-14")
    """
    try:
        data = await client.request(f"/data/{date}/detail")

        if "error" in data:
            return f"Error fetching sleep data: {data['error']}"

        details = data.get("details", {})
        if not details or not details.get("data_total_day"):
            return f"No detailed sleep data found for date: {date}"

        cleaned = _strip_fields(details)

        return (
            f"Complete Sleep Summary Details for {date}:\n"
            f"```json\n"
            f"{json.dumps(cleaned, indent=2, ensure_ascii=False)}\n"
            f"```"
        )
    except Exception as exc:
        return f"Error fetching sleep summary details: {exc}"


@mcp.tool()
async def get_detailed_sleep_segments(date: str) -> str:
    """
    Get detailed sleep segment summaries (stages, heart rate, blood oxygen, HRV,
    movement, ODI) for a specific day (via the /data/:date/raw API).

    The noisy per-second / per-minute data arrays are stripped out – only the
    aggregated *segment* summaries are returned, which work much better for LLM
    analysis.

    Args:
        date: The date to query in YYYY-MM-DD format (e.g. "2024-03-14")
    """
    try:
        data = await client.request(f"/data/{date}/raw")

        if "error" in data:
            return f"Error fetching sleep segments: {data['error']}"

        details = data.get("details", {})
        if not details:
            return f"No detailed segment data found for date: {date}"

        # The API returns details as a dict: {"raw": [...], "hand": [...]}
        # Inside "raw" is a LIST of records. Each record has "data" (huge per-minute
        # arrays) and "segment" (summaries). We strip "data" from every record.
        raw_list = details.get("raw", [])
        if isinstance(raw_list, list):
            for record in raw_list:
                if isinstance(record, dict):
                    record.pop("data", None)

        cleaned = _strip_fields(details)

        return (
            f"Sleep Segments Details for {date}:\n"
            f"```json\n"
            f"{json.dumps(cleaned, indent=2, ensure_ascii=False)}\n"
            f"```"
        )
    except Exception as exc:
        return f"Error fetching sleep segments: {exc}"


@mcp.tool()
async def get_sleep_calendar(start: str, end: str) -> str:
    """
    Get the sleep calendar for a date range — shows which days the device was
    worn (with sleep scores) and which days have log records.

    Args:
        start: Start date in YYYY-MM-DD format (e.g. "2023-01-01")
        end:   End date in YYYY-MM-DD format (e.g. "2024-10-30")
    """
    try:
        data = await client.request(
            "/data/calendar", params={"start": start, "end": end}
        )

        if "error" in data:
            return f"Error fetching sleep calendar: {data['error']}"

        details = data.get("details", {})
        if not details:
            return f"No calendar data found for {start} ~ {end}"

        return (
            f"Sleep Calendar ({start} ~ {end}):\n"
            f"```json\n"
            f"{json.dumps(details, indent=2, ensure_ascii=False)}\n"
            f"```"
        )
    except Exception as exc:
        return f"Error fetching sleep calendar: {exc}"


@mcp.tool()
async def get_sleep_trend(start: str, end: str) -> str:
    """
    Get sleep data trends over a date range — includes daily sleep scores,
    total sleep time, average blood oxygen, heart rate, HRV, ODI counts,
    as well as the period-wide averages.

    Args:
        start: Start date in YYYY-MM-DD format (e.g. "2024-01-12")
        end:   End date in YYYY-MM-DD format (e.g. "2024-03-15")
    """
    try:
        data = await client.request(
            "/data/trend", params={"start": start, "end": end}
        )

        if "error" in data:
            return f"Error fetching sleep trend: {data['error']}"

        details = data.get("details", {})
        if not details:
            return f"No trend data found for {start} ~ {end}"

        return (
            f"Sleep Trend ({start} ~ {end}):\n"
            f"```json\n"
            f"{json.dumps(details, indent=2, ensure_ascii=False)}\n"
            f"```"
        )
    except Exception as exc:
        return f"Error fetching sleep trend: {exc}"


@mcp.tool()
async def get_sleep_labels(date: str) -> str:
    """
    Get user-added sleep labels and notes (tags like "drank coffee",
    "exercised", subjective feelings, ideas) for a specific date.

    Args:
        date: The date to query in YYYY-MM-DD format (e.g. "2024-03-14")
    """
    try:
        data = await client.request("/label/user", params={"date": date})

        if "error" in data:
            return f"Error fetching sleep labels: {data['error']}"

        details = data.get("details", [])
        if not details:
            return f"No labels or notes found for date: {date}"

        cleaned = _strip_fields(details)

        return (
            f"Sleep Labels & Notes for {date}:\n"
            f"```json\n"
            f"{json.dumps(cleaned, indent=2, ensure_ascii=False)}\n"
            f"```"
        )
    except Exception as exc:
        return f"Error fetching sleep labels: {exc}"


@mcp.tool()
async def get_latest_data_time() -> str:
    """
    Get the timestamp of the most recent sleep data sync.
    Useful to know up to which date the user has available data.
    """
    try:
        data = await client.request(
            "/data/endTime", params={"data_source": "Sleepon3.0"}
        )

        if "error" in data:
            return f"Error fetching latest data time: {data['error']}"

        details = data.get("details", {})
        time_str = details.get("time", "Unknown")

        return f"Latest data sync time: {time_str}"
    except Exception as exc:
        return f"Error fetching latest data time: {exc}"


# ---------------------------------------------------------------------------
# MCP Prompts  –  predefined prompt templates for common sleep analysis tasks
# ---------------------------------------------------------------------------

@mcp.prompt()
def analyze_sleep(date: str) -> str:
    """Perform a comprehensive sleep quality analysis for a specific date."""
    return (
        f"Please perform a thorough sleep quality analysis for {date}.\n\n"
        "Follow these steps:\n"
        "1. Call get_daily_sleep_summary to get the day's sleep summary data\n"
        "2. Call get_detailed_sleep_segments to get detailed segment data\n"
        "3. Call get_sleep_labels to check if the user added any tags or notes\n\n"
        "Then analyze the data across these dimensions:\n"
        "- **Overall Sleep Quality**: sleep score, sleep efficiency\n"
        "- **Sleep Architecture**: duration and proportion of each stage "
        "(N1/N2/N3/REM/Wake) – are they healthy?\n"
        "- **Physiological Indicators**: heart rate, blood oxygen, HRV – "
        "any abnormalities?\n"
        "- **Respiratory Health**: ODI analysis, sleep apnea risk assessment\n"
        "- **Movement Analysis**: movement intensity and count\n"
        "- **User Label Correlation**: if labels exist (e.g. alcohol, exercise), "
        "analyze their potential impact on sleep\n\n"
        "Conclude with a summary and actionable recommendations."
    )


@mcp.prompt()
def compare_sleep(date1: str, date2: str) -> str:
    """Compare sleep quality between two dates and highlight differences."""
    return (
        f"Please compare sleep data between {date1} and {date2}.\n\n"
        "Follow these steps:\n"
        f"1. Call get_daily_sleep_summary for both {date1} and {date2}\n"
        f"2. Call get_detailed_sleep_segments for both dates\n"
        f"3. Call get_sleep_labels for both dates to check for user tags\n\n"
        "Then produce a comparison report including:\n"
        "- A comparison table of key metrics (score, total sleep time, "
        "efficiency, heart rate, blood oxygen, HRV)\n"
        "- Sleep architecture differences (stage proportion changes)\n"
        "- Which day had better sleep quality, and why\n"
        "- If labels exist, analyze how lifestyle factors may have affected sleep\n"
        "- Improvement recommendations\n\n"
        "Present data in table format where appropriate."
    )


@mcp.prompt()
def sleep_report(start: str, end: str) -> str:
    """Generate a comprehensive sleep report for a date range."""
    return (
        f"Please generate a sleep health report for the period {start} to {end}.\n\n"
        "Follow these steps to gather data:\n"
        f"1. Call get_sleep_trend for {start} to {end}\n"
        f"2. Call get_sleep_calendar for this period\n"
        "3. Pick the highest-scoring and lowest-scoring days from the trend, "
        "and call get_daily_sleep_summary on each for a deep dive\n\n"
        "The report should include these sections:\n"
        "## 📊 Overall Summary\n"
        "Number of days worn, average sleep score, average sleep duration\n\n"
        "## 📈 Trend Analysis\n"
        "Trends and fluctuations in key metrics (score, duration, heart rate, "
        "blood oxygen, HRV)\n\n"
        "## 🏆 Best vs Worst\n"
        "Detailed comparison of the best and worst sleep days\n\n"
        "## ⚠️ Health Alerts\n"
        "Blood oxygen anomalies, heart rate irregularities, low HRV, "
        "or other concerns\n\n"
        "## 💡 Improvement Recommendations\n"
        "Personalized sleep improvement suggestions based on the data"
    )


@mcp.prompt()
def sleep_improvement_tips() -> str:
    """Get personalized sleep improvement tips based on recent data."""
    return (
        "Please provide personalized sleep improvement tips based on the "
        "user's recent sleep data.\n\n"
        "Follow these steps:\n"
        "1. Call get_latest_data_time to find the most recent data date\n"
        "2. Use that date as the end date, go back 7 days for the start date, "
        "and call get_sleep_trend for the past week\n"
        "3. Call get_daily_sleep_summary for the most recent day\n"
        "4. Call get_sleep_labels for the most recent day to check for "
        "lifestyle tags\n\n"
        "Then analyze and provide advice on:\n"
        "- If sleep efficiency is below 85%, suggest ways to improve sleep onset\n"
        "- If deep sleep (N3) proportion is low, suggest methods to increase it\n"
        "- If heart rate is elevated or HRV is low, suggest stress management\n"
        "- If blood oxygen is abnormal (<94% or high ODI), flag respiratory concerns\n"
        "- If total sleep time is under 7 hours, suggest schedule adjustments\n"
        "- If user labels exist, suggest lifestyle adjustments accordingly\n\n"
        "Provide 5-8 specific, actionable recommendations."
    )


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
def main():
    """CLI entry point."""
    mcp.run()

if __name__ == "__main__":
    main()
