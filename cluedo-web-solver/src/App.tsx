import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";
import z from "zod";
import "./App.css";

const PlainMessage = z.object({
  type: z.literal("plain_message"),
  text: z.string(),
});

const PlayerNamesEntryRequest = z.object({
  type: z.literal("player_names_entry_request"),
  text: z.string(),
});

const Banner = z.object({
  type: z.literal("banner"),
  text: z.string(),
});

const Option = z.object({
  value: z.string(),
  displayName: z.string(),
});
type OptionType = z.infer<typeof Option>;

const ChoiceEntryRequest = z.object({
  type: z.literal("choice_entry_request"),
  text: z.string(),
  options: z.array(Option),
  optional: z.nullable(z.string()),
});

const MultiChoiceEntryRequest = z.object({
  type: z.literal("multi_choice_entry_request"),
  text: z.string(),
  options: z.array(Option),
  numSelections: z.int(),
});

const Message = z.union([
  PlainMessage,
  PlayerNamesEntryRequest,
  Banner,
  ChoiceEntryRequest,
  MultiChoiceEntryRequest,
]);
type MessageType = z.infer<typeof Message>;

function App() {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Connect to Socket.IO on mount
  useEffect(() => {
    const newSocket = io("http://localhost:5005", {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    newSocket.on("message", (msg: MessageType) => {
      setMessages((prev) => [...prev, msg]);
      setLoading(false);
    });

    newSocket.on("connect", () => {
      console.log("Connected to server");
    });

    newSocket.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    setSocket(newSocket);

    return () => {
      newSocket.disconnect();
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handlePlayerNamesEntry = (playerNames: Array<string>) => {
    if (socket) {
      socket.emit("user_input", { playerNames: playerNames });
      setLoading(true);
    }
  };
  const handleChoiceEntry = (value: string | null) => {
    if (socket) {
      socket.emit("user_input", { value: value });
      setLoading(true);
    }
  };
  const handleMultiChoiceEntry = (values: Array<string>) => {
    if (socket) {
      socket.emit("user_input", { values: values });
      setLoading(true);
    }
  };

  return (
    <div className="container">
      <div className="left">
        <h1>Cluedo Web Solver</h1>
        <p>
          Beat your friends and family at the classic board game Cluedo (Clue in
          North America). Enter your gameplay to a boolean satisfiability solver
          and let it solve the crime for you faster than your opponents.
        </p>
        <p>
          Learn more about how it works{" "}
          <a
            className="link"
            href="https://keeganmjgreen.github.io/blog/readme/"
          >
            here
          </a>
          .
        </p>
      </div>
      <div className="right">
        {messages.map((message, messageIndex) => (
          <div key={messageIndex}>
            {message.type === "plain_message" && <p>{message.text}</p>}
            {message.type === "player_names_entry_request" && (
              <>
                <p>{message.text}</p>
                <PlayerNamesEntryForm onSubmit={handlePlayerNamesEntry} />
              </>
            )}
            {message.type === "banner" && <h2>{message.text}</h2>}
            {message.type === "choice_entry_request" && (
              <>
                <p>{message.text}</p>
                <ChoiceEntryForm
                  options={message.options}
                  optional={message.optional}
                  onSubmit={handleChoiceEntry}
                />
              </>
            )}
            {message.type === "multi_choice_entry_request" && (
              <>
                <p>{message.text}</p>
                <MultiChoiceEntryForm
                  options={message.options}
                  numSelections={message.numSelections}
                  onSubmit={handleMultiChoiceEntry}
                />
              </>
            )}
          </div>
        ))}
        {loading && <p>Waiting for server...</p>}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

interface PlayerNamesEntryFormProps {
  onSubmit: (value: Array<string>) => void;
}

function PlayerNamesEntryForm({ onSubmit }: PlayerNamesEntryFormProps) {
  const [playerNames, setPlayerNames] = useState([""]);
  const [admonition, setAdmonition] = useState("");
  const [disabled, setDisabled] = useState(false);

  const handleSubmit = () => {
    for (const [index, playerName] of playerNames.entries()) {
      if (playerName === "" && index !== playerNames.length - 1) {
        setAdmonition("It looks like you're missing a player's name.");
        return;
      }
    }
    if (new Set(playerNames).size < playerNames.length) {
      setAdmonition("Player names must be unique.");
      return;
    }
    const newPlayerNames = playerNames.filter(
      (_, i) => i !== playerNames.length - 1,
    );
    setPlayerNames(newPlayerNames);
    onSubmit(newPlayerNames);
    setAdmonition("");
    setDisabled(true);
  };

  var divs = [];

  for (const [index, playerName] of playerNames.entries()) {
    divs.push(
      <input
        className={
          disabled ? "player-name-input-deselected" : "player-name-input"
        }
        type="text"
        placeholder="Enter player name"
        value={playerName}
        key={index}
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
      divs.push(<div />);
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
      {!disabled && playerNames.length - 1 >= 2 && doneButton}
      {admonition}
    </div>
  );
}

interface ChoiceEntryFormProps {
  options: OptionType[];
  optional: string | null;
  onSubmit: (rumor: string | null) => void;
}

function ChoiceEntryForm({
  options,
  optional,
  onSubmit,
}: ChoiceEntryFormProps) {
  const [selected, setSelected] = useState<string | null>("");
  const [disabled, setDisabled] = useState(false);

  const handleClick = (option: string | null) => {
    setSelected(option);
    setDisabled(true);
    onSubmit(option);
  };

  const newOptions = optional
    ? [...options, { value: null, displayName: optional }]
    : options;

  return (
    <div>
      {newOptions.map((option) => {
        return (
          <button
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
        );
      })}
    </div>
  );
}

interface MultiChoiceEntryFormProps {
  options: OptionType[];
  numSelections: number;
  onSubmit: (rumor: Array<string>) => void;
}

function MultiChoiceEntryForm({
  options,
  numSelections,
  onSubmit,
}: MultiChoiceEntryFormProps) {
  const [selected, setSelected] = useState<Array<string>>([]);
  const [disabled, setDisabled] = useState(false);

  const handleClick = (option: string) => {
    if (selected.includes(option)) {
      return;
    }
    const newSelected = [...selected, option];
    setSelected(newSelected);
    if (newSelected.length >= numSelections) {
      setDisabled(true);
      onSubmit(newSelected);
    }
  };

  return (
    <div>
      {options.map((option) => {
        return (
          <button
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
        );
      })}
    </div>
  );
}

export default App;
