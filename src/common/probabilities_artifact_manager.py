import os
from pathlib import Path
from typing import Union

import pandas as pd

from src.common.agent_utils import agent_index_type

CSV_PATH = Path("tmp", "probabilities_data.csv")


class ProbabilitiesArtifactManager:
    fields = [
        "game_id",
        "agent_type",
        "agent_index",
        "turn_index",
        "player_index",
        "rumor_card",
        "approx_probability",
    ]

    def __init__(self, csv_path: Path = CSV_PATH, start_over: bool = False):
        self.csv_path = csv_path
        if self.csv_path is not None:
            if not start_over:
                df = self.read_csv()
            if start_over or (df is None):
                self.df = pd.DataFrame(columns=self.fields)
                self.write_csv()
            else:
                self.df = df

    def refresh(self) -> pd.DataFrame:
        if self.csv_path is not None:
            df = self.read_csv()
            if df is not None:
                self.df = df

    def read_csv(self) -> Union[pd.DataFrame, None]:
        try:
            return pd.read_csv(self.csv_path)
        except FileNotFoundError:
            return None

    def write_csv(self) -> None:
        for folder in self.csv_path.parts[:-1]:
            try:
                os.mkdir(folder)
            except FileExistsError:
                pass
        self.df.to_csv(self.csv_path, index=False)

    def get_probabilities_ser(
        self,
        game_id: int,
        agent_type: str,
        agent_index: agent_index_type,
        turn_index: int,
    ) -> pd.Series:
        probabilities_ser = (
            self.df.set_index(["game_id", "agent_type", "agent_index", "turn_index"])
            .sort_index()
            .loc[game_id, agent_type, agent_index, turn_index]
            .set_index(["player_index", "rumor_card"])["approx_probability"]
        )
        return probabilities_ser

    def append_probabilities_ser(
        self,
        game_id: int,
        agent_type: str,
        agent_index: agent_index_type,
        turn_index: int,
        probabilities_ser: pd.Series,
    ) -> None:
        append_df = probabilities_ser.reset_index()
        append_df[["game_id", "agent_type", "agent_index", "turn_index"]] = (
            game_id,
            agent_type,
            agent_index,
            turn_index,
        )
        append_df = append_df[self.fields]

        self.refresh()
        self.df = pd.concat([self.df, append_df])
        if self.csv_path is not None:
            self.write_csv()
