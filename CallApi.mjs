import {promises as fs} from "fs";
import {existsSync, unlink} from "fs";
import path from "path";

export default async function getStaticProps() {
  const filePath = path.join(process.cwd(), "app/components/Scores.tsx");
  const backupExists = existsSync(`${filePath}.bak`);
  if (!backupExists) throw new Error("API is already being called")
  if (backupExists) {
    await fs.copyFile(`${filePath}.bak`, `${filePath}`);
    unlink(`${filePath}.bak`, (err) => {
      if (err) throw err;
      console.log("app/components/Scores.tsx.bak was deleted");
    });
  }
}

getStaticProps();
