export const HISTORICAL_TEAM_LOGOS: Record<string, string> = {
  // Wikimedia (verified 200, correct historical branding)
  SEA: 'https://upload.wikimedia.org/wikipedia/en/a/a4/Seattle_SuperSonics_logo.svg', // Seattle SuperSonics → OKC Thunder 2008-09
  NJN: 'https://upload.wikimedia.org/wikipedia/commons/8/8f/Nets97-12Wordmark.gif',   // New Jersey Nets → Brooklyn Nets 2012-13
  VAN: 'https://upload.wikimedia.org/wikipedia/en/1/1e/Vancouver_Grizzlies_logo.svg', // Vancouver Grizzlies → Memphis 2001-02

  // ESPN CDN (200 - serves a historical New Orleans logo)
  NOH: 'https://a.espncdn.com/i/teamlogos/nba/500/no.png',

  // ESPN CDN (404 → onError → placeholder, still better than showing the wrong current-franchise logo)
  NOK: 'https://a.espncdn.com/i/teamlogos/nba/500/nok.png', // New Orleans/OKC Hornets 2005-08
  CHH: 'https://a.espncdn.com/i/teamlogos/nba/500/chh.png', // Charlotte Hornets (original) 1988-2002
  KCK: 'https://a.espncdn.com/i/teamlogos/nba/500/kck.png', // Kansas City Kings → Sacramento 1985-86
  SDC: 'https://a.espncdn.com/i/teamlogos/nba/500/sdc.png', // San Diego Clippers → LA 1984-85
};
