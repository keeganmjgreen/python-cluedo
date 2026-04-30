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

const ChoiceEntryRequest = z.object({
  type: z.literal("choice_entry_request"),
  text: z.string(),
  options: z.array(z.string()),
  optional: z.boolean(),
});

const Message = z.union([
  PlainMessage,
  PlayerNamesEntryRequest,
  ChoiceEntryRequest,
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

  return (
    <div className="container">
      <div className="left">
        <h1>Cluedo Web Solver</h1>
      </div>
      <div className="right">
        {messages.map((message, messageIndex) => (
          <div key={messageIndex}>
            <p>{message.text}</p>
            {message.type === "player_names_entry_request" && (
              <PlayerNamesEntryForm onSubmit={handlePlayerNamesEntry} />
            )}
            {message.type === "choice_entry_request" && (
              <ChoiceEntryForm
                options={message.options}
                optional={message.optional}
                onSubmit={handleChoiceEntry}
              />
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
  const [disabled, setDisabled] = useState(false);
  const [playerNames, setPlayerNames] = useState([""]);
  const [admonition, setAdmonition] = useState("");

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
    setDisabled(true);
    setAdmonition("");
    const newPlayerNames = playerNames.filter(
      (_, i) => i !== playerNames.length - 1,
    );
    setPlayerNames(newPlayerNames);
    onSubmit(newPlayerNames);
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
  options: string[];
  optional: boolean;
  onSubmit: (rumor: string | null) => void;
}

function ChoiceEntryForm({
  options,
  optional,
  onSubmit,
}: ChoiceEntryFormProps) {
  const [disabled, setDisabled] = useState(false);
  const [selected, setSelected] = useState<string | null>("");

  const handleSubmit = (option: string | null) => {
    setDisabled(true);
    setSelected(option);
    onSubmit(option);
  };

  const newOptions = optional ? [...options, null] : options;

  return (
    <div>
      {newOptions.map((option) => {
        return (
          <button
            className={
              disabled
                ? option === selected
                  ? "text-button-selected"
                  : "text-button-deselected"
                : "text-button"
            }
            onClick={() => handleSubmit(option)}
            disabled={disabled}
          >
            {option ?? "No Player"}
          </button>
        );
      })}
    </div>
  );
}

export default App;
