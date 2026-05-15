"use client";

import dynamic from "next/dynamic";
import { JSX, useEffect, useRef } from "react";
import { headingFont, monospaceFont } from "./fonts";
import {
  ChoiceEntryForm,
  MultiChoiceEntryForm,
  PlayerNamesEntryForm,
} from "./forms";
import { GameDataType, MessageType } from "./models";

const Plot = dynamic(() => import("react-plotly.js"), {
  ssr: false,
});

export function ClientGameplayBox(props: { gameData: GameDataType }) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom / last message:
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [props.gameData.messages]);

  const plot: JSX.Element = props.gameData.latestProbabilitiesData ? (
    <Plot
      data={[
        {
          z: props.gameData.latestProbabilitiesData.matrix,
          x: props.gameData.latestProbabilitiesData.cols,
          y: props.gameData.latestProbabilitiesData.rows,
          type: "heatmap",
          zmin: 0,
          zmax: 1,
        },
      ]}
      layout={{
        xaxis: { tickangle: 90, dtick: 1 },
        yaxis: {
          autorange: "reversed",
        },
        title: {
          text: "Approximate Probabilities<br>of each rumor card being in each location",
        },
        font: {
          family: "IBM Plex Sans",
          color: "#808080",
        },
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
      }}
      style={{ width: "100%", height: "100%" }}
    />
  ) : (
    <div className={headingFont.className}>
      Approximate probabilities will display here once the game has begun.
    </div>
  );

  return (
    <>
      <div className="gameplay-messages">
        {props.gameData.messages.map((message, messageIndex) => (
          <div key={messageIndex}>{messageToComponent(message)}</div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="gameplay-probabilities">{plot}</div>
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
  if (message.type === "boolean_statements") {
    return (
      <>
        <p>Solver knowledge added:</p>
        <div className={`boolean-statements ${monospaceFont.className}`}>
          {message.booleanStatements.map((statement, index) => (
            <div key={index}>{statement}</div>
          ))}
        </div>
      </>
    );
  }
  throw new Error();
}
