[![alex-linkedin-shield]][alex-linkedin-url]

<div align="center">
  <img src="./public/images/nba-scorez-lockup.svg" style="height:200px" />
   <p align="center">
    Bienvenue! 
    <br />
    <a href="https://github.com/AlexVCS/nba-scores/issues/new">Report Bug</a>
  </p>
</div>

## Table of Contents

[About](#about) |
[Screenshots](#screenshots) |
[Playoffs](#playoffs) |
[Built With](#built-with) |
[Local Project Setup](#local-project-setup) |
[VS Code Tasks](#vs-code-tasks) |
[AI Agents](#ai-agents) |
[Clone the repo](#clone-the-repo) |
[Contact](#contact)

## About

Find the scores and stats of your favorite NBA team! Scorez, boxscores, and playoff data go back to the 1946/47 season.

## Screenshots

<table>
  <tr>
    <th>Scorez App</th>
    <th>Boxscore</th>
  </tr>
  <tr>
    <td align="center">
      <img src="./public/images/scores-app-ui.PNG" alt="NBA Scorez App" width="300">
    </td>
    <td align="center">
      <img src="./public/images/boxscore-ui.PNG" alt="Boxscore" width="300">
    </td>
  </tr>
  <tr>
    <th>Playoffz</th>
    <th>Series Detail</th>
  </tr>
  <tr>
    <td align="center">
      <img src="./public/images/playoffz-screenshot.PNG" alt="Playoffz" width="300">
    </td>
    <td align="center">
      <img
        src="./public/images/series-detail-screenshot.PNG"
        alt="Series Details"
        width="300"
      >
    </td>
  </tr>
</table>

## Playoffs

Navigate to the [Playoffs](https://nbascorez.com/playoffs) page to explore interactive bracket visualizations.

- Select any season with the year picker
- Toggle results round by round to avoid spoilers
- Click any series to see a game-by-game breakdown with scores, dates, and links to box scores
- Watch links are available for seasons from 2012/13 onward, depending on League Pass availability
- On desktop, the bracket is rendered with [React Flow](https://reactflow.dev/)

<div align='right'>

[Back to Top](#top)

</div>

## Built With

[![React.JS]][React-url][![Tailwindcss]][Tailwind-url][![TypeScript]][Typescript-url][![FastAPI]][FastAPI-url]

## Local Project Setup

Git, Node.js, Python, and PNPM (or your package manager of choice) are required to run this project locally. 

## AI Agents

AI coding agents from [OpenAI](https://openai.com) and [Anthropic](https://anthropic.com) assisted in writing code throughout this project.

### Clone the repo

Copy this and run it in your terminal:

```bash
git clone https://github.com/AlexVCS/nba-scores.git
cd nba-scores
pnpm i
```

Run the frontend by running `pnpm dev` in one terminal.

To run the backend, open a terminal and run this:

```bash
source server/venv/bin/activate
uvicorn server.main:app --reload
```

### API configuration and phone testing

During development, `VITE_API_URL_DEV` overrides the backend URL. Set it in `.env.local` when using another backend address or port:

```dotenv
VITE_API_URL_DEV=http://localhost:9000
```

When that variable is unset or empty, requests use the browser's protocol and hostname on port 8000. This works on your computer and on a phone accessing your computer's LAN IP.

For phone testing, connect both devices to the same network. Run these commands in separate terminals from the project root:

```bash
VITE_API_URL_DEV= pnpm dev --host 0.0.0.0 --port 5173 --strictPort
```

```bash
source server/venv/bin/activate
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://<your-computer-LAN-IP>:5173` on the phone. The empty command-line override enables the hostname fallback even if `.env` contains a development URL. For a custom backend, set `VITE_API_URL_DEV` to an address reachable from the phone; `localhost` on a phone refers to the phone itself. The backend's existing CORS configuration allows private-network IP origins on HTTP port 5173.

For deployment, set `VITE_API_URL_PROD` in the frontend build environment to your public backend URL, such as `https://api.nbascorez.com`, before running `pnpm build`. Production builds use this value independently of `VITE_API_URL_DEV` and the phone fallback. Use a URL without a trailing slash and ensure the backend allows your deployed frontend origin through CORS. Restart the development server after changing environment variables; rebuild the frontend after changing the production URL.

Open `/design-1` to view Gold on Hardwood, or `/original` to compare the original design with the design switcher. These routes require no token and work on the HTTP LAN address above. Deep links use the same prefix, for example `/design-1/playoffs`.

## VS Code Tasks

Run a task from **Tasks: Run Task** in the Command Palette. See [`.vscode/tasks.json`](.vscode/tasks.json) for the definitions.

| Task | What it does |
| ---- | ------------ |
| Dev Client | Runs `pnpm dev` |
| Dev Server | Runs the FastAPI server in `server/venv` |
| Dev Full Stack | Runs the client and server in parallel |

<div align='right'>

[Back to Top](#top)

</div>

## Contact

Alex Curtis-Slep - [GitHub](https://github.com/AlexVCS) / [Bluesky](https://bsky.app/profile/alexcurtisslep.bsky.social) / alexcurtisslep@gmail.com

<div align='right'>

[Back to Top](#top)

</div>

[alex-linkedin-shield]: https://img.shields.io/badge/-Alex's_LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[alex-linkedin-url]: https://www.linkedin.com/in/alexcurtisslep/
[FastAPI]: https://img.shields.io/badge/FastAPI-009485.svg?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[ReactFlow]: https://img.shields.io/badge/React_Flow-black?style=for-the-badge&logo=react
[ReactFlow-url]: https://reactflow.dev/
[Tailwindcss]: https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white
[Tailwind-url]: https://tailwindcss.com/
[Typescript]: https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white
[Typescript-url]: https://www.typescriptlang.org/
