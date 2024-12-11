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
https://api-sports.io/documentation/nba/v2

Design: https://www.figma.com/file/AQL6ywEUiKkconAcaX5upM/NBA-Website-(Community)?node-id=0:1&mode=dev

### Local Setup

To run this locally on your machine, copy the contents of `.env.example`.

Then create your own `.env.local` file, add in what you copied, and signup for the [API](https://rapidapi.com/api-sports/api/api-nba/).

Add your API keys by finding and copying them in the Rapid API docs.

### Mimic an API Response

If you'd like to see what the scores UI looks like without signing up for the API, or test the view in dev mode, here's how:

In `app/components/Scores.tsx`, comment out the last line of the useEffect function where fetchData is called:

```ts
  useEffect(() => {
    async function fetchData() {
  // useEffect redacted for brevity
  // fetchData();
  }, [dateSelected]);
```

Then scroll down or use the find function to get to where you find `gameData?.map`. Change `gameData` to `devModeData`, like so:

```ts
 {devModeData?.map((game) => {
        return // inner map function logic)
})}
```

After you make these changes and run the app with `npm run dev`, you'll be using `exampleResponse.json` as your data instead of making a call to the API.

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
