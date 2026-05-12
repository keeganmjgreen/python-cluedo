"use client";

import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import {
  ReadonlyURLSearchParams,
  useRouter,
  useSearchParams,
} from "next/navigation";
import { JSX, useState } from "react";
import { GAME_HISTORY_PARAM } from "./consts";
import {
  ChoiceEntryResponse,
  GameHistoryItemType,
  MultiChoiceEntryResponse,
  PlayerNamesEntryResponse,
  type OptionType,
} from "./models";

export function PlayerNamesEntryForm(props: {
  initialPlayerNames: Array<string> | undefined;
}) {
  const [playerNames, setPlayerNames] = useState(
    props.initialPlayerNames || [""],
  );
  const [admonition, setAdmonition] = useState("");
  const [disabled, setDisabled] = useState(
    props.initialPlayerNames !== undefined,
  );
  const searchParams = useSearchParams();
  const router = useRouter();

  const handleSubmit = () => {
    const trimmedPlayerNames = playerNames.map((playerName) =>
      playerName.trim(),
    );
    for (const [index, playerName] of trimmedPlayerNames.entries()) {
      if (playerName === "" && index !== trimmedPlayerNames.length - 1) {
        setAdmonition("It looks like you're missing a player's name.");
        return;
      }
    }
    if (new Set(trimmedPlayerNames).size < trimmedPlayerNames.length) {
      setAdmonition("Player names must be unique.");
      return;
    }
    const newPlayerNames = trimmedPlayerNames.filter(
      (_, i) => i !== trimmedPlayerNames.length - 1,
    );
    setPlayerNames(newPlayerNames);
    updateGameHistory(
      searchParams,
      router,
      PlayerNamesEntryResponse.parse({ playerNames: newPlayerNames }),
    );
    setAdmonition("");
    setDisabled(true);
  };

  var divs: JSX.Element[] = [];

  for (const [index, playerName] of playerNames.entries()) {
    divs.push(
      <input
        key={`${index}-input`}
        className={
          disabled ? "player-name-input-deselected" : "player-name-input"
        }
        type="text"
        placeholder="Enter player name"
        value={playerName}
        onChange={(e) => {
          var newPlayerNames = playerNames.map((n, i) =>
            i === index ? e.target.value : n,
          );
          if (index === playerNames.length - 1) {
            newPlayerNames = [...newPlayerNames, ""];
          }
          setPlayerNames(newPlayerNames);
          setAdmonition("");
        }}
        disabled={disabled}
      />,
    );
    if (!disabled && index !== playerNames.length - 1) {
      const removeButton = (
        <button
          key={`${index}-remove-button`}
          className="player-name-remove-button"
          onClick={() => {
            setPlayerNames(playerNames.filter((_, i) => i !== index));
          }}
          disabled={disabled}
        >
          ❌
        </button>
      );
      divs.push(removeButton);
    } else {
      divs.push(<div key={index} />);
    }
  }

  const doneButton = (
    <button className="text-button" onClick={handleSubmit} disabled={disabled}>
      Start Game
    </button>
  );

  return (
    <div>
      <div className="players-entry-table">{divs}</div>
      <p>{admonition}</p>
      {!disabled && playerNames.length - 1 >= 2 && doneButton}
    </div>
  );
}

export function ChoiceEntryForm(props: {
  options: OptionType[];
  optional: string | null;
  initialChoice: string | null | undefined;
}) {
  const [selected, setSelected] = useState<string | null | undefined>(
    props.initialChoice,
  );
  const [disabled, setDisabled] = useState(props.initialChoice !== undefined);
  const searchParams = useSearchParams();
  const router = useRouter();

  const handleClick = (option: string | null) => {
    setSelected(option);
    setDisabled(true);
    updateGameHistory(
      searchParams,
      router,
      ChoiceEntryResponse.parse({ value: option }),
    );
  };

  const newOptions = props.optional
    ? [...props.options, { value: null, displayName: props.optional }]
    : props.options;

  return (
    <div>
      {Array.from(newOptions.entries()).map(([index, option]) => (
        <button
          key={`${index}-button`}
          className={
            option.value === selected
              ? "text-button-selected"
              : disabled
                ? "text-button-deselected"
                : "text-button"
          }
          onClick={() => handleClick(option.value)}
          disabled={disabled}
        >
          {option.displayName}
        </button>
      ))}
    </div>
  );
}

export function MultiChoiceEntryForm(props: {
  options: OptionType[];
  numSelections: number;
  initialChoices: Array<string> | undefined;
}) {
  const [selected, setSelected] = useState<Array<string>>(
    props.initialChoices || [],
  );
  const [disabled, setDisabled] = useState(props.initialChoices !== undefined);
  const searchParams = useSearchParams();
  const router = useRouter();

  const handleClick = (option: string) => {
    if (selected.includes(option)) {
      return;
    }
    const newSelected = [...selected, option];
    setSelected(newSelected);
    if (newSelected.length >= props.numSelections) {
      setDisabled(true);
      updateGameHistory(
        searchParams,
        router,
        MultiChoiceEntryResponse.parse({ values: newSelected }),
      );
    }
  };

  return (
    <div>
      {Array.from(props.options.entries()).map(([index, option]) => (
        <button
          key={index}
          className={
            selected.includes(option.value)
              ? "text-button-selected"
              : disabled
                ? "text-button-deselected"
                : "text-button"
          }
          onClick={() => handleClick(option.value)}
          disabled={disabled}
        >
          {option.displayName}
        </button>
      ))}
    </div>
  );
}

function updateGameHistory(
  searchParams: ReadonlyURLSearchParams,
  router: AppRouterInstance,
  newGameHistoryItem: GameHistoryItemType,
) {
  const params = new URLSearchParams(searchParams.toString());
  const gameHistory = params.get(GAME_HISTORY_PARAM);
  params.set(
    GAME_HISTORY_PARAM,
    JSON.stringify([
      ...(gameHistory ? JSON.parse(gameHistory) : []),
      newGameHistoryItem,
    ]),
  );
  router.push(`?${params.toString()}`);
}
