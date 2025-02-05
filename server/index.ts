import express from 'express'
import { format } from "date-fns";
import cors from 'cors'
const app = express()
const port = 3000

const todaysDate = new Date();
const formattedDate = format(todaysDate, "yyyy-MM-dd")
// console.log(formattedDate)
// const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

// Parameters, Returns, Examples, Pseudo code

// selectedDate from frontend
// want to pass that to backend from a query parameter



export const whitelist = ["http://localhost:5173"]


app.use(cors({
  origin:"http://localhost:5173",
}));

app.get('/', async (req, res) => {
  try {
    // const { date } = req.query;
    console.log(req.params)
    // const dateParam = req.params as string;
    // console.log(dateParam)
    const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${formattedDate}&LeagueID=00`
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