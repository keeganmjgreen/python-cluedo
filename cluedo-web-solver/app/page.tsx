import z from "zod";
import { getGameData } from "./api";
import { ClientGameplayBox } from "./clientGameplayBox";
import { GAME_HISTORY_PARAM } from "./consts";
import { bodyFont, headingFont } from "./fonts";
import { GameHistoryItem } from "./models";

export default async function Home(props: {
  searchParams: Promise<{ [GAME_HISTORY_PARAM]: string }>;
}) {
  return (
    <div className={`container ${bodyFont.className}`}>
      <div className="info-box">
        <h1 className={headingFont.className}>Cluedo Solver</h1>
        <p>
          Beat your friends and family at the classic board game Cluedo (Clue in
          North America). Enter your gameplay to a boolean satisfiability solver
          and let it solve the crime for you faster than your opponents. Learn
          more about how it works{" "}
          <a href="https://keeganmjgreen.github.io/blog/readme/">here</a>.
        </p>
        <p>
          Game data is stored in the URL &ndash; no cookies required. To save
          your game, simply bookmark the site. Use your browser's back/forward
          buttons to undo/redo game history.
        </p>
        <p>
          Board games not nerdy enough for you? Try the{" "}
          <a href="https://github.com/keeganmjgreen/python-cluedo/#cluedo-assistant">
            Cluedo Solver CLI
          </a>
          :
        </p>
        <img
          src="/assistant_cli_screenshot.png"
          style={{ maxWidth: "300px", margin: "0 auto", display: "block" }}
        ></img>
        <p>
          Cluedo Solver is a tool not affiliated with Cluedo, Clue, Hasbro or
          any other trademark holders.
        </p>
      </div>
      <div className="gameplay-box">
        <GameplayBox searchParams={props.searchParams} />
      </div>
    </div>
  );
}

async function GameplayBox(props: {
  searchParams: Promise<{ [GAME_HISTORY_PARAM]: string }>;
}) {
  const sp = await props.searchParams;
  const gameHistory = sp[GAME_HISTORY_PARAM]
    ? JSON.parse(sp[GAME_HISTORY_PARAM])
    : [];
  const gameData = await getGameData(
    z.array(GameHistoryItem).parse(gameHistory),
  );
  return <ClientGameplayBox gameData={gameData} />;
}
