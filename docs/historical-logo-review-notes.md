# Historical Logo Review Notes

Reviewer/date: Codex, 2026-06-18.

These notes record the accepted entries in `src/constants/historicalTeamLogos.ts`.
Candidates were checked against `docs/historical-logo-acceptance.md`.

## Inventory Method

The tricode inventory was generated from `nba_api.stats.endpoints.LeagueGameLog`
for regular season and playoff data from `1946-47` through `2025-26`, plus the
existing `HISTORICAL_TEAM_LOGOS` keys.

The NBA API returned 74 observed tricodes. The accepted constants below cover
the observed historical tricodes with validated static image URLs. Some observed
tricodes are intentionally excluded because they are current mixed-era tricodes,
need date-aware logo selection, or did not have an acceptable source URL.

## Common Validation Result

Each accepted URL below passed these checks on 2026-06-18:

- Returned HTTP 200.
- Returned an image content type.
- Downloaded body had non-zero size.
- Downloaded body decoded as an image with ImageMagick `identify`, or was SVG.
- Raster image intrinsic size met the 128x128 minimum, except wide historical
  marks where both dimensions still exceed current app display size.
- Backup copy was saved under ignored `.logo-backups/historical-team-logos/`.
- Active app URL is either an app-served static image path or a direct Wikimedia SVG URL.

SportsLogos.Net source assets were promoted from backup copies to
`public/images/historical-team-logos/` because the remote URLs can fail when
rendered by the app. Wikimedia SVGs were kept as active URLs for Seattle and
Vancouver because SVG is preferred and those URLs already validate cleanly.

## Accepted Logos

| Tricode | Historical team | Season range represented | Format | Intrinsic size | Source | URL | Backup |
|---|---|---:|---|---:|---|---|---|
| BAL | Baltimore Bullets | 1947-48 to 1953-54 | gif | 250x153 | SportsLogos.Net | `/images/historical-team-logos/bal-baltimore-bullets-1947-1954.gif` | `.logo-backups/historical-team-logos/bal-baltimore-bullets-1947-1954.gif` |
| BLT | Baltimore Bullets | 1963-64 to 1972-73 | gif | 350x253 | SportsLogos.Net | `/images/historical-team-logos/blt-baltimore-bullets-1963-1973.gif` | `.logo-backups/historical-team-logos/blt-baltimore-bullets-1963-1973.gif` |
| BOM | St. Louis Bombers | 1946-47 to 1949-50 | gif | 492x150 | SportsLogos.Net | `/images/historical-team-logos/bom-st-louis-bombers-1946-1950.gif` | `.logo-backups/historical-team-logos/bom-st-louis-bombers-1946-1950.gif` |
| BUF | Buffalo Braves | 1970-71 to 1977-78 | gif | 565x549 | SportsLogos.Net | `/images/historical-team-logos/buf-buffalo-braves-1970-1978.gif` | `.logo-backups/historical-team-logos/buf-buffalo-braves-1970-1978.gif` |
| CAP | Capital Bullets | 1973-74 | gif | 332x150 | SportsLogos.Net | `/images/historical-team-logos/cap-capital-bullets-1973-1974.gif` | `.logo-backups/historical-team-logos/cap-capital-bullets-1973-1974.gif` |
| CHH | Charlotte Hornets | 1988-89 to 2001-02 | gif | 424x545 | SportsLogos.Net | `/images/historical-team-logos/chh-charlotte-hornets-1988-2002.gif` | `.logo-backups/historical-team-logos/chh-charlotte-hornets-1988-2002.gif` |
| CHP | Chicago Packers | 1961-62 | gif | 253x250 | SportsLogos.Net | `/images/historical-team-logos/chp-chicago-packers-1961-1962.gif` | `.logo-backups/historical-team-logos/chp-chicago-packers-1961-1962.gif` |
| CHS | Chicago Stags | 1946-47 to 1949-50 | gif | 379x409 | SportsLogos.Net | `/images/historical-team-logos/chs-chicago-stags-1946-1950.gif` | `.logo-backups/historical-team-logos/chs-chicago-stags-1946-1950.gif` |
| CHZ | Chicago Zephyrs | 1962-63 | gif | 437x594 | SportsLogos.Net | `/images/historical-team-logos/chz-chicago-zephyrs-1962-1963.gif` | `.logo-backups/historical-team-logos/chz-chicago-zephyrs-1962-1963.gif` |
| CIN | Cincinnati Royals | 1957-58 to 1971-72 | gif | 250x281 | SportsLogos.Net | `/images/historical-team-logos/cin-cincinnati-royals-1957-1972.gif` | `.logo-backups/historical-team-logos/cin-cincinnati-royals-1957-1972.gif` |
| DN | Denver Nuggets | 1949-50 | gif | 207x249 | SportsLogos.Net | `/images/historical-team-logos/dn-denver-nuggets-1949-1950.gif` | `.logo-backups/historical-team-logos/dn-denver-nuggets-1949-1950.gif` |
| FTW | Fort Wayne Pistons | 1948-49 to 1956-57 | gif | 402x427 | SportsLogos.Net | `/images/historical-team-logos/ftw-fort-wayne-pistons-1948-1957.gif` | `.logo-backups/historical-team-logos/ftw-fort-wayne-pistons-1948-1957.gif` |
| GOS | Golden State Warriors | representative 1988-89 to 1995-96 | gif | 745x694 | SportsLogos.Net | `/images/historical-team-logos/gos-golden-state-warriors-1988-1996.gif` | `.logo-backups/historical-team-logos/gos-golden-state-warriors-1988-1996.gif` |
| HUS | Toronto Huskies | 1946-47 | gif | 168x222 | SportsLogos.Net | `/images/historical-team-logos/hus-toronto-huskies-1946-1947.gif` | `.logo-backups/historical-team-logos/hus-toronto-huskies-1946-1947.gif` |
| KCK | Kansas City Kings | representative 1975-76 to 1984-85 | gif | 277x350 | SportsLogos.Net | `/images/historical-team-logos/kck-kansas-city-kings-1972-1985.gif` | `.logo-backups/historical-team-logos/kck-kansas-city-kings-1972-1985.gif` |
| MNL | Minneapolis Lakers | 1948-49 to 1959-60 | gif | 563x589 | SportsLogos.Net | `/images/historical-team-logos/mnl-minneapolis-lakers-1948-1960.gif` | `.logo-backups/historical-team-logos/mnl-minneapolis-lakers-1948-1960.gif` |
| NJN | New Jersey Nets | representative 1997-98 to 2011-12 | gif | 687x750 | SportsLogos.Net | `/images/historical-team-logos/njn-new-jersey-nets-1977-2012.gif` | `.logo-backups/historical-team-logos/njn-new-jersey-nets-1977-2012.gif` |
| NOH | New Orleans Hornets | representative 2008-09 to 2012-13 | gif | 487x524 | SportsLogos.Net | `/images/historical-team-logos/noh-new-orleans-hornets-2002-2013.gif` | `.logo-backups/historical-team-logos/noh-new-orleans-hornets-2002-2013.gif` |
| NOJ | New Orleans Jazz | 1974-75 to 1978-79 | gif | 350x151 | SportsLogos.Net | `/images/historical-team-logos/noj-new-orleans-jazz-1974-1979.gif` | `.logo-backups/historical-team-logos/noj-new-orleans-jazz-1974-1979.gif` |
| NOK | New Orleans/Oklahoma City Hornets | 2005-06 to 2006-07 | gif | 545x530 | SportsLogos.Net | `/images/historical-team-logos/nok-new-orleans-oklahoma-city-hornets-2005-2007.gif` | `.logo-backups/historical-team-logos/nok-new-orleans-oklahoma-city-hornets-2005-2007.gif` |
| NYN | New York Nets | 1976-77 | gif | 254x250 | SportsLogos.Net | `/images/historical-team-logos/nyn-new-york-nets-1976-1977.gif` | `.logo-backups/historical-team-logos/nyn-new-york-nets-1976-1977.gif` |
| PHL | Philadelphia 76ers | representative 1977-78 to 1995-96 | gif | 700x700 | SportsLogos.Net | `/images/historical-team-logos/phl-philadelphia-76ers-1977-1996.gif` | `.logo-backups/historical-team-logos/phl-philadelphia-76ers-1977-1996.gif` |
| PHW | Philadelphia Warriors | 1946-47 to 1961-62 | gif | 231x250 | SportsLogos.Net | `/images/historical-team-logos/phw-philadelphia-warriors-1946-1962.gif` | `.logo-backups/historical-team-logos/phw-philadelphia-warriors-1946-1962.gif` |
| PRO | Providence Steamrollers | 1946-47 to 1948-49 | gif | 201x200 | SportsLogos.Net | `/images/historical-team-logos/pro-providence-steamrollers-1946-1949.gif` | `.logo-backups/historical-team-logos/pro-providence-steamrollers-1946-1949.gif` |
| ROC | Rochester Royals | 1948-49 to 1956-57 | gif | 275x279 | SportsLogos.Net | `/images/historical-team-logos/roc-rochester-royals-1948-1957.gif` | `.logo-backups/historical-team-logos/roc-rochester-royals-1948-1957.gif` |
| SAN | San Antonio Spurs | representative 1989-90 to 1995-96 | gif | 750x421 | SportsLogos.Net | `/images/historical-team-logos/san-san-antonio-spurs-1976-1996.gif` | `.logo-backups/historical-team-logos/san-san-antonio-spurs-1976-1996.gif` |
| SDC | San Diego Clippers | 1978-79 to 1983-84 | gif | 603x603 | SportsLogos.Net | `/images/historical-team-logos/sdc-san-diego-clippers-1978-1984.gif` | `.logo-backups/historical-team-logos/sdc-san-diego-clippers-1978-1984.gif` |
| SDR | San Diego Rockets | 1967-68 to 1970-71 | gif | 505x504 | SportsLogos.Net | `/images/historical-team-logos/sdr-san-diego-rockets-1967-1971.gif` | `.logo-backups/historical-team-logos/sdr-san-diego-rockets-1967-1971.gif` |
| SEA | Seattle SuperSonics | 1967-68 to 2007-08 | svg | svg | Wikimedia | `https://upload.wikimedia.org/wikipedia/en/a/a4/Seattle_SuperSonics_logo.svg` | `.logo-backups/historical-team-logos/sea-seattle-supersonics-1967-2008.svg` |
| SFW | San Francisco Warriors | representative 1969-70 to 1970-71 | gif | 218x250 | SportsLogos.Net | `/images/historical-team-logos/sfw-san-francisco-warriors-1962-1971.gif` | `.logo-backups/historical-team-logos/sfw-san-francisco-warriors-1962-1971.gif` |
| STL | St. Louis Hawks | representative 1964-65 to 1967-68 | gif | 751x712 | SportsLogos.Net | `/images/historical-team-logos/stl-st-louis-hawks-1955-1968.gif` | `.logo-backups/historical-team-logos/stl-st-louis-hawks-1955-1968.gif` |
| SYR | Syracuse Nationals | 1949-50 to 1962-63 | gif | 180x200 | SportsLogos.Net | `/images/historical-team-logos/syr-syracuse-nationals-1949-1963.gif` | `.logo-backups/historical-team-logos/syr-syracuse-nationals-1949-1963.gif` |
| TCB | Tri-Cities Blackhawks | 1949-50 to 1950-51 | gif | 241x250 | SportsLogos.Net | `/images/historical-team-logos/tcb-tri-cities-blackhawks-1949-1951.gif` | `.logo-backups/historical-team-logos/tcb-tri-cities-blackhawks-1949-1951.gif` |
| UTH | Utah Jazz | 1979-80 to 1995-96 | gif | 723x300 | SportsLogos.Net | `/images/historical-team-logos/uth-utah-jazz-1979-1996.gif` | `.logo-backups/historical-team-logos/uth-utah-jazz-1979-1996.gif` |
| VAN | Vancouver Grizzlies | 1995-96 to 2000-01 | svg | svg | Wikimedia | `https://upload.wikimedia.org/wikipedia/en/1/1e/Vancouver_Grizzlies_logo.svg` | `.logo-backups/historical-team-logos/van-vancouver-grizzlies-1995-2001.svg` |

## Exclusions And Follow-Up Notes

- `AND`, `DEF`, `INO`, `JET`, `PIT`, `SHE`, and `WAT` were observed in NBA
  API history but no acceptable direct static logo URL was validated in this
  pass.
- `CHA` and `WAS` are current tricodes that also represent historical team names
  in NBA API data. A global tricode-only mapping would break current Charlotte
  Hornets and Washington Wizards logos, so these require a date-aware logo API.
- `MIH` and `CLR` had SportsLogos.Net archive pages, but the direct full image
  URLs tested during this pass returned blocked responses and were not accepted.
- `GOS`, `KCK`, `NJN`, `NOH`, `PHL`, `SAN`, `SFW`, and `STL` span multiple logo
  eras. The current app can only map one logo per tricode, so the selected logo
  is representative and should be replaced by date-aware selection if exact
  era matching becomes required.
