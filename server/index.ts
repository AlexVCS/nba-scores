import { Hono } from 'hono';
import { format } from "date-fns";
import { cors } from 'hono/cors'
const app = new Hono()



app.use('/*',
  cors({
    origin: ['http://localhost:5173', 'https://nba-scorez.onrender.com'],
  })
)

app.get('/', async function getResults(c) {
  try {
    const todaysDate = new Date();
    const formattedDate = format(todaysDate, "yyyy-MM-dd")
    const date = c.req.query('date')
    const url = `https://proxy.boxscores.site/?apiUrl=stats.nba.com/stats/scoreboardv3&GameDate=${!date ? formattedDate : date}&LeagueID=00`
    const response = await fetch(url)
    const formatResponse = await response.json()
    const results = formatResponse.scoreboard.games
    return c.json({games: results})
  } catch (error) {
    c.status(500)
    return c.body(`Could not grab data ${error}`)
  }
})

app.get('/games/:gameId/boxscore', async function getBoxscore(c) {
  try {
    const gameId = c.req.param('gameId');
    const response = await fetch(`https://cdn.nba.com/static/json/liveData/boxscore/boxscore_${gameId}.json`);
    const boxscoreData = await response.json();
    return c.json(boxscoreData.game);
  } catch (error) {
    console.error(`Could not grab boxscore ${error}`);
    c.status(500)
    return c.body(`Could not grab boxscore ${error}`);
  }
})

export default app