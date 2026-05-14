import { GameData, GameDataType, GameHistoryItemType } from "./models";

export async function getGameData(
  gameHistory: Array<GameHistoryItemType>,
): Promise<GameDataType> {
  const response = await fetch("http://0.0.0.0:5005/game-data", {
    method: "POST",
    body: JSON.stringify(gameHistory),
    headers: { "Content-Type": "application/json" },
  });
  const gameData = GameData.parse(await response.json());
  return gameData;
}
