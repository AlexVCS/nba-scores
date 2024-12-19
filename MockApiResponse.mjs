import {promises as fs} from "fs";
import {existsSync} from "fs"
import path from "path";

export default async function getStaticProps() {
  const filePath = path.join(process.cwd(), "app/components/Scores.tsx");
  const backupExists = existsSync(`${filePath}.bak`)
  if(backupExists) {
    throw new Error("Backup exists already")
  }
  await fs.copyFile(filePath, `${filePath}.bak`)
  let content = await fs.readFile(filePath, "utf8");

  function modifyFileContent(content) {
    content = content.replace(
      /const fetcher = \(url: string\) => fetch\(url\)\.then\(\(res\) => res\.json\(\)\);[\s\S]*?const games: Game\[\] = data\?\.response/gm,
      "// Deleted the SWR data fetching block"
    );

    content = content.replace(
      /\{isLoading && <div>Scores are loading!<\/div>\}/g,
      "{/* {isLoading && <div>Scores are loading!</div>} */}"
    );

    content = content.replace(/games(?!:)(?!\s)((?!\?date))/gm, "devModeGames");

    return content;
  }

  const modifiedContent = modifyFileContent(content);

  // Write the modified content back to the file
  await fs.writeFile(filePath, modifiedContent);

  console.log("Modified app/components/Scores.tsx successfully.");
}

// Run the function immediately
getStaticProps();
