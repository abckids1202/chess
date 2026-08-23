"""Train the first supervised HumanPolicyNet."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import yaml

from ml.common.board_encoder import BOARD_ENCODER_VERSION
from ml.common.move_encoder import MOVE_VOCAB_VERSION


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def train(config_path: str | Path) -> Path:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, random_split

    from ml.bot.policy_dataset import PolicyParquetDataset
    from ml.bot.policy_model import HumanPolicyNet

    config = load_config(config_path)
    torch.manual_seed(config.get("seed", 42))
    device = torch.device("cuda" if torch.cuda.is_available() and config["training"].get("device", "auto") != "cpu" else "cpu")
    dataset = PolicyParquetDataset(
        config["data"]["train_dir"],
        rating_mean=config["data"].get("rating_mean", 1500.0),
        rating_std=config["data"].get("rating_std", 400.0),
    )
    val_size = max(1, int(len(dataset) * config["data"].get("validation_fraction", 0.05)))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_ds, batch_size=config["training"]["batch_size"], shuffle=True, num_workers=config["training"].get("num_workers", 0))
    val_loader = DataLoader(val_ds, batch_size=config["training"]["batch_size"], shuffle=False, num_workers=config["training"].get("num_workers", 0))

    model = HumanPolicyNet(**config["model"]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["training"]["learning_rate"], weight_decay=config["training"].get("weight_decay", 0.0))
    loss_fn = nn.CrossEntropyLoss()

    run_id = "policy_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(config["checkpoint"]["output_dir"]) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    Path(run_dir / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    metrics_path = run_dir / "metrics.csv"
    best_val = float("inf")

    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["epoch", "train_loss", "val_loss", "top1", "top3", "top5"])
        writer.writeheader()
        for epoch in range(1, config["training"]["epochs"] + 1):
            model.train()
            train_loss = _run_epoch(model, train_loader, loss_fn, device, optimizer)
            model.eval()
            val_loss, topk = _evaluate(model, val_loader, loss_fn, device)
            row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, **topk}
            writer.writerow(row)
            handle.flush()
            checkpoint = {"model_state_dict": model.state_dict(), "epoch": epoch, "config": config}
            torch.save(checkpoint, run_dir / "last.pt")
            if val_loss < best_val:
                best_val = val_loss
                torch.save(checkpoint, run_dir / "best.pt")
            print(row)

    metadata = {
        "model_type": "human_policy",
        "model_version": "0.1.0",
        "board_encoder_version": BOARD_ENCODER_VERSION,
        "move_vocab_version": MOVE_VOCAB_VERSION,
        "training_samples": train_size,
        "rating_mean": config["data"].get("rating_mean", 1500.0),
        "rating_std": config["data"].get("rating_std", 400.0),
        "architecture": config["model"],
    }
    (run_dir / "best.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return run_dir


def _run_epoch(model, loader, loss_fn, device, optimizer):
    import torch

    total_loss = 0.0
    total = 0
    for boards, ratings, targets in loader:
        boards = boards.to(device).float()
        ratings = ratings.to(device).float()
        targets = targets.to(device).long()
        optimizer.zero_grad(set_to_none=True)
        loss = loss_fn(model(boards, ratings), targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total_loss += loss.item() * boards.size(0)
        total += boards.size(0)
    return total_loss / max(total, 1)


def _evaluate(model, loader, loss_fn, device):
    import torch

    total_loss = 0.0
    total = 0
    correct = {1: 0, 3: 0, 5: 0}
    with torch.no_grad():
        for boards, ratings, targets in loader:
            boards = boards.to(device).float()
            ratings = ratings.to(device).float()
            targets = targets.to(device).long()
            logits = model(boards, ratings)
            loss = loss_fn(logits, targets)
            total_loss += loss.item() * boards.size(0)
            total += boards.size(0)
            for k in correct:
                top = logits.topk(k, dim=1).indices
                correct[k] += top.eq(targets.view(-1, 1)).any(dim=1).sum().item()
    return total_loss / max(total, 1), {f"top{k}": correct[k] / max(total, 1) for k in correct}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="ml/config/policy_config.yaml")
    args = parser.parse_args()
    run_dir = train(args.config)
    print(f"saved run to {run_dir}")


if __name__ == "__main__":
    main()
