import { GameData, GameHistoryItemType, MessageType } from "./models";

export async function getMessages(
  gameHistory: Array<GameHistoryItemType>,
): Promise<Array<MessageType>> {
  const response = await fetch("http://0.0.0.0:5005/game-data", {
    method: "POST",
    body: JSON.stringify(gameHistory),
    headers: { "Content-Type": "application/json" },
  });
  const messages = GameData.parse(await response.json()).messages;
  return messages;
}
