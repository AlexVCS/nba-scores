[![alex-linkedin-shield]][alex-linkedin-url]

<div align="center">
  <h3 align="center">NBA Scores</h3>

   <p align="center">
    Bienvenue! 
    <br />
    <a href="https://github.com/AlexVCS/nba-scores/issues/new">Report Bug</a>
  </p>
</div>

## About NBA Scores

Find the scores of your favorite NBA team!

### Built With

[![NextJS]][Next-url][![Tailwindcss]][Tailwind-url][![TypeScript]][Typescript-url]

<!-- [![NPM]][NPM-url] -->

NBA scores API:
https://api-sports.io/documentation/basketball/v1

Design: https://www.figma.com/file/AQL6ywEUiKkconAcaX5upM/NBA-Website-(Community)?node-id=0:1&mode=dev

### Local Setup

To run this locally on your machine, install the dependencies with your package manager of choice. I'm using NPM, which means I run `npm i`.

To use the API to grab data for the app, copy the contents of `.env.example`.

Then create your own `.env.local` file, add in what you copied, and signup for the [API](https://rapidapi.com/api-sports/api/api-nba/).

Add your API keys by finding and copying them in the Rapid API docs.

Run the app by running `npm run dev` in your terminal. Then open the app at 

### Mock an API Response

If you'd like to see what the scores UI looks like without signing up for the API, or test the view in dev mode, run this in your terminal:

`npm run mock-api`

This runs a file at the root called `MockApiResponse.mjs` that edits `app/components/Scores.tsx` to no longer call the API and use `exampleResponse.json` as your data.

To undo these changes, make sure you have `app/components/Scores.tsx` open before you run `npm run mock-api`. Then in `app/components/Scores.tsx` you can undo the changes the script makes.

## Contact

Alex Curtis-Slep - [GitHub](https://github.com/AlexVCS) / [Bluesky](https://bsky.app/profile/alexcurtisslep.bsky.social) / alexcurtisslep@gmail.com

[alex-linkedin-shield]: https://img.shields.io/badge/-Alex's_LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[alex-linkedin-url]: https://www.linkedin.com/in/alexcurtisslep/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Tailwindcss]: https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white
[Tailwind-url]: https://tailwindcss.com/
[NextJS]: https://img.shields.io/badge/Next-black?style=for-the-badge&logo=next.js&logoColor=white
[Next-url]: https://nextjs.org/
[Typescript]: https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white
[Typescript-url]: https://www.typescriptlang.org/
