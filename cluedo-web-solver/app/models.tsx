import z from "zod";

const PlainMessage = z.object({
  type: z.literal("plain_message"),
  text: z.string(),
});

export const PlayerNamesEntryResponse = z.object({
  playerNames: z.array(z.string()),
});

const PlayerNamesEntryRequest = z.object({
  type: z.literal("player_names_entry_request"),
  text: z.string(),
  response: z.nullable(PlayerNamesEntryResponse),
});

const Banner = z.object({
  type: z.literal("banner"),
  text: z.string(),
});

const Option = z.object({
  value: z.string(),
  displayName: z.string(),
});
export type OptionType = z.infer<typeof Option>;

export const ChoiceEntryResponse = z.object({
  value: z.nullable(z.string()),
});

const ChoiceEntryRequest = z.object({
  type: z.literal("choice_entry_request"),
  text: z.string(),
  options: z.array(Option),
  optional: z.nullable(z.string()),
  response: z.nullable(ChoiceEntryResponse),
});

export const MultiChoiceEntryResponse = z.object({
  values: z.array(z.string()),
});

const MultiChoiceEntryRequest = z.object({
  type: z.literal("multi_choice_entry_request"),
  text: z.string(),
  options: z.array(Option),
  numSelections: z.int(),
  response: z.nullable(MultiChoiceEntryResponse),
});

const Message = z.union([
  PlainMessage,
  PlayerNamesEntryRequest,
  Banner,
  ChoiceEntryRequest,
  MultiChoiceEntryRequest,
]);
export type MessageType = z.infer<typeof Message>;
export const GameData = z.object({ messages: z.array(Message) });

export const GameHistoryItem = z.union([
  PlayerNamesEntryResponse,
  ChoiceEntryResponse,
  MultiChoiceEntryResponse,
]);
export type GameHistoryItemType = z.infer<typeof GameHistoryItem>;
