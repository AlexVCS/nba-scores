from datetime import date, datetime
from zoneinfo import ZoneInfo

# NBA game dates are published in US Eastern time.
NBA_TIMEZONE = ZoneInfo("America/New_York")


def nba_now() -> datetime:
    return datetime.now(NBA_TIMEZONE)


def nba_today() -> date:
    return nba_now().date()


def get_nba_season(year: int, month: int) -> str:
    """
    Derive the NBA season string for a given calendar year/month.
    NBA regular season roughly runs Oct -> Apr.
    - Oct-Dec of year Y  → season "Y-YY+1"   (e.g., Oct 2025 → "2025-26")
    - Jan-Sep of year Y  → season "Y-1-YY"   (e.g., Feb 2026 → "2025-26")
    """
    if month >= 10:
        start_year = year
    else:
        start_year = year - 1
    end_suffix = str(start_year + 1)[-2:]
    return f"{start_year}-{end_suffix}"


def current_nba_season() -> str:
    today = nba_today()
    return get_nba_season(today.year, today.month)
