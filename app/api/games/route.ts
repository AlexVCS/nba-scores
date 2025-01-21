import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const apiCache = new Map<string, Record<string, string>>()


export async function GET(req: NextRequest) {
  const date = req.nextUrl.searchParams.get('date')
  const timezone = req.nextUrl.searchParams.get('timezone')
  const league = req.nextUrl.searchParams.get('league')
  const season = req.nextUrl.searchParams.get('season')
  
  const cachedKey = `${date}|${timezone}|${league}|${season}`
  if(apiCache.has(cachedKey)) {
    const data = apiCache.get(cachedKey)
    return NextResponse.json(data)
  }

  // export const API_URL = {
  //   base: 'https://proxy.boxscores.site/?apiUrl=stats.nba.com',
  //   details: 'https://data.nba.com/',
  // }


  const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${date}&LeagueID=00`
  
  // `https://api-basketball.p.rapidapi.com/games?date=${date}&timezone=${timezone}&league=${league}&season=${season}`;
  const options = {
    method: "GET",
    // headers: {
    //   "X-RapidAPI-Key": process.env.XRapidAPIKey || "",
    //   "X-RapidAPI-Host": process.env.XRapidAPIHost || "",
    // },
  };
  const res = await fetch(url, options);
  const jsonRes = await res.json();
  apiCache.set(cachedKey, jsonRes)

  return NextResponse.json(jsonRes)
}