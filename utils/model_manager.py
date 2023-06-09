import json
import re
from pathlib import Path

import torch as T
from torch import nn
from typing_extensions import Self

BASE_DIR = Path(__file__).parents[1]


MODULE_REGEX = re.compile("module.")


class ModelManager:
    def __init__(
        self: Self,
        model_name: str,
        max_num_checkpoints: int = 3,
        checkpoint_dir: str = "checkpoints",
        model_dir: str = "trained_models",
    ) -> None:
        self.model_name = model_name
        self.max_num_checkpoints = max_num_checkpoints
        self.checkpoint_dir = BASE_DIR / checkpoint_dir / model_name
        self.model_dir = BASE_DIR / model_dir / model_name

        self.checkpoint_dir.mkdir(exist_ok=True)
        self.model_dir.mkdir(exist_ok=True)

    def checkpoint_exists(self: Self) -> bool:
        return len(list(self.checkpoint_dir.glob("*.pt"))) != 0

    def model_exists(self: Self) -> bool:
        return (
            Path(self.model_dir / "model.pt").exists()
            and Path(self.model_dir / "info.json").exists()
        )

    def load_model_info(self: Self) -> dict:
        if not self.model_exists():
            return None

        with open(self.model_dir / "info.json", "rt") as f:
            info = json.load(f)
        return info

    def load_model(self: Self) -> dict:
        if not self.model_exists():
            return

        _state_dict = T.load(self.model_dir / "model.pt")

        # state dict format gets changed when using DDP, fix here
        state_dict = {}
        for key, value in _state_dict.items():
            state_dict[re.sub(MODULE_REGEX, "", key)] = value

        return state_dict

    def load_checkpoint(self: Self) -> dict:
        if not self.checkpoint_exists():
            return None

        checkpoints = list(self.checkpoint_dir.glob("*.pt"))

        most_recent_checkpoint = max(checkpoints, key=lambda x: x.stem.split("-")[-1])

        return T.load(most_recent_checkpoint, map_location="cpu")

    def save_checkpoint(self: Self, checkpoint_dict: dict) -> None:
        checkpoints = sorted(self.checkpoint_dir.glob("*.pt"))
        checkpoint_num = len(checkpoints) + 1

        while checkpoint_num > self.max_num_checkpoints:
            checkpoints.pop(0).unlink()
            checkpoint_num -= 1

        for idx, checkpoint in enumerate(checkpoints):
            new_name = f"checkpoint-{idx + 1}.pt"
            if checkpoint.name != new_name:
                checkpoint.rename(self.checkpoint_dir / new_name)

        T.save(
            checkpoint_dict,
            self.checkpoint_dir / f"checkpoint-{checkpoint_num}.pt",
        )

    def save_model(self: Self, network: nn.Module, model_kwargs: dict) -> None:
        T.save(network.state_dict(), f"{self.model_dir}/model.pt")
        with open(self.model_dir / "info.json", "wt+") as f:
            json.dump(model_kwargs, f)

    def clean(self: Self) -> None:
        for checkpoint in self.checkpoint_dir.glob("*"):
            checkpoint.unlink()

        for model in self.model_dir.glob("*"):
            model.unlink()
