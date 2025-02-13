const getBoxScores = async (gameId: string, year: string) => {
  try {
    const url = `http://localhost:3000/boxscore?gameId=${gameId}&year=${year}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.json();
    console.log(response.json());
  } catch (error) {
    console.error(`Error fetching boxscore: ${error}`);
    throw error; // Re-throw the error to be caught by useQuery
  }
};

const Boxscore = ({boxscore}: any) => {
  return <div>{
    boxscore?.map((game) => {
      return (
        <div key={game.gameId}>game.homeTeam.score</div>
      )
    })
  }</div>;
};

export default Boxscore;
