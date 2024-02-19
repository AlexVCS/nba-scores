// import {Suspense} from "react";
// import {headers} from "next/headers";

// async function User() {
//   const authorization = headers().get("authorization");
//   const res = await fetch("https://api-nba-v1.p.rapidapi.com/games?h2h=1-2", {
//     headers: "X-RapidAPI-Key": process.env.X_RapidAPI_Key ?? "",
//       "X-RapidAPI-Host": process.env.X_RapidAPI_Host ?? "", // Forward the authorization header
//   });
//   const user = await res.json();

//   return <h1>{user.name}</h1>;
// }

// export default function Page() {
//   return (
//     <Suspense fallback={null}>
//       <User />
//     </Suspense>
//   );
// }
