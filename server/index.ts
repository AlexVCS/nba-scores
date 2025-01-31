import express from 'express'
import { format } from "date-fns";
import cors from 'cors'
const app = express()
const port = 3000

const todaysDate = new Date();
const formattedDate = format(todaysDate, "yyyy-MM-dd")
// console.log(formattedDate)
// const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${formattedDate}&LeagueID=00`


export const whitelist = ["http://localhost:5173"]


app.use(cors({
  origin:"http://localhost:5173",
}));

app.get('/', async (req, res) => {
  try {
    const response = await fetch(url)
    // console.log(await response.json())
    const formatResponse = await response.json()
    const results = formatResponse.scoreboard.games
    // console.log(results)
    res.send(results)
  } catch (error) {
    res.status(500).send(`Could not grab data ${error}`)
  }

})

app.listen(port, () => {
  console.log(`App listening on port ${port}`)
})