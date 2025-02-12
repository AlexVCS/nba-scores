import express from 'express'
import { format } from "date-fns";
import cors from 'cors'
const app = express()
const port = 3000

const todaysDate = new Date();
const formattedDate = format(todaysDate, "yyyy-MM-dd")

export const whitelist = ["http://localhost:5173"]


app.use(cors({
  origin: "http://localhost:5173",
}));

// async function getScores(date: Date, formattedDate: string) {
//   const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${date ? date : formattedDate}&LeagueID=00`
//   const response = await fetch(url)
//   const formatResponse = await response.json()
//   return formatResponse.scoreboard.games
// }

app.get('/', async function getResults(req, res) {
  try {
    const { date } = req.query
    const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${date ? date : formattedDate}&LeagueID=00`
    const response = await fetch(url)
    const formatResponse = await response.json()
    const results = formatResponse.scoreboard.games
    res.send(results)
  } catch (error) {
    res.status(500).send(`Could not grab data ${error}`)
  }
})

app.get('/boxscore', async (req, res) => {
  try {
    const { date, gameId } = req.query
    let year = date ? date.toString().slice(0, 4) : formattedDate.slice(0, 4)
    console.log(req.query)
    // year && this.getResults(),

    const url = `https://data.nba.com//data/10s/v2015/json/mobile_teams/nba/${year}/scores/gamedetail/${gameId}_gamedetail.json`
  } catch (err) {
    res.status(500).send(`Could not grab boxscore ${err}`)
  }
})

app.listen(port, () => {
  console.log(`App listening on port ${port}`)
})