import { z } from 'zod'
import { TRPCRouter, publicProcedure } from '@/app/api/trpc/init'
import type { NextRequest } from "next/server";

export type GameData = {
  games: [
    {
      gameStatus: number
      gameStatusText: string
      seriesGameNumber: string
      seriesText: string
      seriesConference: string
      homeTeam: {
        teamTricode: string
        score: number
      }
      awayTeam: {
        teamTricode: string
        score: number
      }
    }
  ]
}

const fetchOptions = {
  method: 'GET',
  headers: {
    accept: 'application/json',
  },
}

const gameScoreboardUrl =
  `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${date}&LeagueID=00`

const gameDetailsUrl = 'https://data.nba.com/'

function fetchGameList<T>(url: string): Promise<T> {
  
  return fetch(url, fetchOptions).then((response): Promise<T> => {
    // fetching the reponse body data
    return response.json()
  })
}

export const scoreRouter = TRPCRouter({
  getGameScores: publicProcedure
  
  .query(async (params: QueryParams) => {
    // const date = req.nextUrl.searchParams.get('date')
    
    const games =
      await fetchGameList<GameData>(gameScoreboardUrl)
    const gameData: GameData[]
  })
})