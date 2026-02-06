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