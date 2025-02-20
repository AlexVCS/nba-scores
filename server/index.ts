import express, { Request, Response } from 'express';
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

app.get('/', async function getResults(req, res) {
  try {
    const { date } = req.query
    const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${date ? date : formattedDate}&LeagueID=00`
    const response = await fetch(url)
    const formatResponse = await response.json()
    const results = formatResponse.scoreboard.games
    res.send({games: results})
  } catch (error) {
    res.status(500).send(`Could not grab data ${error}`)
  }
})

app.get('/boxscore', async function getBoxscore(req, res) {
  try {
    const { gameId } = req.query;
    console.log('this is the gameId', gameId)
    // console.log('this is the year', year)
    // const url = `https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/${year}/scores/gamedetail/${gameId}_gamedetail.json`;
    const response = await fetch(`https://cdn.nba.com/static/json/liveData/boxscore/boxscore_${gameId}.json`);
    // console.log(await response.json())
    const boxscoreData = await response.json();
    console.log(boxscoreData)
    res.send(boxscoreData.game);
  } catch (error) {
    console.error(`Could not grab boxscore ${error}`);
    res.status(500).send(`Could not grab boxscore ${error}`);
  }
})

app.listen(port, () => {
  console.log(`App listening on port ${port}`)
})