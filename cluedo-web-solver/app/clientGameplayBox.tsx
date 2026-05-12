"use client";

import { JSX, useEffect, useRef } from "react";
import { headingFont } from "./fonts";
import {
  ChoiceEntryForm,
  MultiChoiceEntryForm,
  PlayerNamesEntryForm,
} from "./forms";
import { MessageType } from "./models";

export function ClientGameplayBox(props: { messages: Array<MessageType> }) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom / last message:
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [props.messages]);

  return (
    <>
      {props.messages.map((message, messageIndex) => (
        <div key={messageIndex}>{messageToComponent(message)}</div>
      ))}
      <div ref={messagesEndRef} />
    </>
  );
}

function messageToComponent(message: MessageType): JSX.Element {
  if (message.type === "plain_message") {
    return <p>{message.text}</p>;
  }
  if (message.type === "player_names_entry_request") {
    return (
      <>
        <p>{message.text}</p>
        <PlayerNamesEntryForm
          initialPlayerNames={message.response?.playerNames}
        />
      </>
    );
  }
  if (message.type === "banner") {
    return <h2 className={headingFont.className}>{message.text}</h2>;
  }
  if (message.type === "choice_entry_request") {
    return (
      <>
        <p>{message.text}</p>
        <ChoiceEntryForm
          options={message.options}
          optional={message.optional}
          initialChoice={message.response?.value}
        />
      </>
    );
  }
  if (message.type === "multi_choice_entry_request") {
    return (
      <>
        <p>{message.text}</p>
        <MultiChoiceEntryForm
          options={message.options}
          numSelections={message.numSelections}
          initialChoices={message.response?.values}
        />
      </>
    );
  }
  throw new Error();
}
