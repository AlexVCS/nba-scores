export const HISTORICAL_TEAM_LOGOS: Record<string, string> = {
  WAT: '/images/historical-team-logos/wat-waterloo-hawks-1949-1950.png',
  SHE: '/images/historical-team-logos/she-sheboygan-red-skins-1949-1950.png',
  AND: '/images/historical-team-logos/and-anderson-packers-1949-1950.webp',
  PIT: '/images/historical-team-logos/pit-pittsburgh-ironmen-1946-1947.png',
  DEF: '/images/historical-team-logos/def-detroit-falcons-1946-1947.png',
  CLR: '/images/historical-team-logos/clr-cleveland-rebels-1946-1947.png',
  MIH: '/images/historical-team-logos/mih-milwaukee-hawks-1952-1954.png',
  INO: '/images/historical-team-logos/ino-indianapolis-olympians-1949-1953.png',
  BAL: '/images/historical-team-logos/bal-baltimore-bullets-1947-1954.gif', // Baltimore Bullets, 1947-48 to 1953-54
  BLT: '/images/historical-team-logos/blt-baltimore-bullets-1963-1973.gif', // Baltimore Bullets, 1963-64 to 1972-73
  BOM: '/images/historical-team-logos/bom-st-louis-bombers-1946-1950.gif', // St. Louis Bombers, 1946-47 to 1949-50
  BUF: '/images/historical-team-logos/buf-buffalo-braves-1970-1978.gif', // Buffalo Braves, 1970-71 to 1977-78
  CAP: '/images/historical-team-logos/cap-capital-bullets-1973-1974.gif', // Capital Bullets, 1973-74
  CHH: '/images/historical-team-logos/chh-charlotte-hornets-1988-2002.gif', // Charlotte Hornets, 1988-89 to 2001-02
  CHP: '/images/historical-team-logos/chp-chicago-packers-1961-1962.gif', // Chicago Packers, 1961-62
  CHS: '/images/historical-team-logos/chs-chicago-stags-1946-1950.gif', // Chicago Stags, 1946-47 to 1949-50
  CHZ: '/images/historical-team-logos/chz-chicago-zephyrs-1962-1963.gif', // Chicago Zephyrs, 1962-63
  CIN: '/images/historical-team-logos/cin-cincinnati-royals-1957-1972.gif', // Cincinnati Royals, 1957-58 to 1971-72
  DN: '/images/historical-team-logos/dn-denver-nuggets-1949-1950.gif', // Denver Nuggets, 1949-50
  FTW: '/images/historical-team-logos/ftw-fort-wayne-pistons-1948-1957.gif', // Fort Wayne Pistons, 1948-49 to 1956-57
  GOS: '/images/historical-team-logos/gos-golden-state-warriors-1988-1996.gif', // Golden State Warriors, representative 1988-89 to 1995-96
  HUS: '/images/historical-team-logos/hus-toronto-huskies-1946-1947.gif', // Toronto Huskies, 1946-47
  KCK: '/images/historical-team-logos/kck-kansas-city-kings-1972-1985.gif', // Kansas City Kings, representative 1975-76 to 1984-85
  MNL: '/images/historical-team-logos/mnl-minneapolis-lakers-1948-1960.gif', // Minneapolis Lakers, 1948-49 to 1959-60
  NJN: '/images/historical-team-logos/njn-new-jersey-nets-1977-2012.gif', // New Jersey Nets, representative 1997-98 to 2011-12
  NOH: '/images/historical-team-logos/noh-new-orleans-hornets-2002-2013.gif', // New Orleans Hornets, representative 2008-09 to 2012-13
  NOJ: '/images/historical-team-logos/noj-new-orleans-jazz-1974-1979.gif', // New Orleans Jazz, 1974-75 to 1978-79
  NOK: '/images/historical-team-logos/nok-new-orleans-oklahoma-city-hornets-2005-2007.gif', // New Orleans/Oklahoma City Hornets, 2005-06 to 2006-07
  NYN: '/images/historical-team-logos/nyn-new-york-nets-1976-1977.gif', // New York Nets, 1976-77
  PHL: '/images/historical-team-logos/phl-philadelphia-76ers-1977-1996.gif', // Philadelphia 76ers, representative 1977-78 to 1995-96
  PHW: '/images/historical-team-logos/phw-philadelphia-warriors-1946-1962.gif', // Philadelphia Warriors, 1946-47 to 1961-62
  PRO: '/images/historical-team-logos/pro-providence-steamrollers-1946-1949.gif', // Providence Steamrollers, 1946-47 to 1948-49
  ROC: '/images/historical-team-logos/roc-rochester-royals-1948-1957.gif', // Rochester Royals, 1948-49 to 1956-57
  SAN: '/images/historical-team-logos/san-san-antonio-spurs-1976-1996.gif', // San Antonio Spurs, representative 1989-90 to 1995-96
  SDC: '/images/historical-team-logos/sdc-san-diego-clippers-1978-1984.gif', // San Diego Clippers, 1978-79 to 1983-84
  SDR: '/images/historical-team-logos/sdr-san-diego-rockets-1967-1971.gif', // San Diego Rockets, 1967-68 to 1970-71
  SEA: '/images/historical-team-logos/sea-seattle-supersonics-1967-2008.svg', // Seattle SuperSonics, 1967-68 to 2007-08
  SFW: '/images/historical-team-logos/sfw-san-francisco-warriors-1962-1971.gif', // San Francisco Warriors, representative 1969-70 to 1970-71
  STL: '/images/historical-team-logos/stl-st-louis-hawks-1955-1968.gif', // St. Louis Hawks, representative 1964-65 to 1967-68
  SYR: '/images/historical-team-logos/syr-syracuse-nationals-1949-1963.gif', // Syracuse Nationals, 1949-50 to 1962-63
  TCB: '/images/historical-team-logos/tcb-tri-cities-blackhawks-1949-1951.gif', // Tri-Cities Blackhawks, 1949-50 to 1950-51
  UTH: '/images/historical-team-logos/uth-utah-jazz-1979-1996.gif', // Utah Jazz, 1979-80 to 1995-96
  VAN: '/images/historical-team-logos/van-vancouver-grizzlies-1995-2001.svg', // Vancouver Grizzlies, 1995-96 to 2000-01
};

// The Capitols and Wizards share WAS, but have distinct NBA team IDs.
export const HISTORICAL_TEAM_LOGOS_BY_ID: Record<number, string> = {
  1610610036: '/images/historical-team-logos/was-washington-capitols-1946-1951.png',
};

// Boxscore data sometimes uses DTF where game logs use DEF.
export const HISTORICAL_TEAM_LOGO_ALIASES: Record<string, string> = { DTF: 'DEF' };
