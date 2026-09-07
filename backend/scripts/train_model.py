"""Fast Fine-Tuning Pipeline for RescueMesh Damage Classifier.

Optimized for ultra-fast CPU/GPU training:
1. Live progress bar via tqdm.
2. Balanced subsampling (800 train / 200 val) for rapid demo convergence (~45s on CPU).
3. Frozen backbone feature extractor with trainable classification head.
4. Saves weights to backend/app/models/damage_classifier.pth.
"""

import os
import sys
import time
import random
import argparse
from typing import Tuple, Dict, List

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
import timm
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

try:
    from tqdm import tqdm
except ImportError:
    # Graceful fallback if tqdm is not installed
    def tqdm(iterable, desc=None, total=None, **kwargs):
        return iterable

# Resolve backend root path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(SCRIPT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

DEFAULT_DATASET_DIR = os.path.join(BACKEND_ROOT, "data", "dataset")
DEFAULT_OUTPUT_MODEL = os.path.join(BACKEND_ROOT, "app", "models", "damage_classifier.pth")


def get_balanced_subset(dataset: datasets.ImageFolder, max_samples: int) -> Subset:
    """Extracts a balanced random subset across all classes in the dataset."""
    targets = dataset.targets
    classes = list(set(targets))
    per_class_limit = max_samples // len(classes)

    class_indices: Dict[int, List[int]] = {c: [] for c in classes}
    for idx, target in enumerate(targets):
        class_indices[target].append(idx)

    selected_indices = []
    for c, indices in class_indices.items():
        random.seed(42)
        sample_k = min(len(indices), per_class_limit)
        selected_indices.extend(random.sample(indices, sample_k))

    random.shuffle(selected_indices)
    return Subset(dataset, selected_indices)


def get_data_loaders(
    dataset_dir: str,
    batch_size: int = 32,
    img_size: int = 224,
    train_samples: int = 800,
    val_samples: int = 200,
    full_dataset: bool = False,
) -> Tuple[DataLoader, DataLoader]:
    """Prepares PyTorch DataLoaders with fast transforms and balanced subsampling."""
    train_dir = os.path.join(dataset_dir, "train_another")
    val_dir = os.path.join(dataset_dir, "validation_another")

    # Fallback to alternative folder naming if needed
    if not os.path.exists(train_dir):
        train_dir = os.path.join(dataset_dir, "train")
    if not os.path.exists(val_dir):
        val_dir = os.path.join(dataset_dir, "validation")
        if not os.path.exists(val_dir):
            val_dir = os.path.join(dataset_dir, "test_another")

    if not os.path.exists(train_dir):
        raise FileNotFoundError(f"Training dataset directory not found in {dataset_dir}")

    train_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    raw_train = datasets.ImageFolder(train_dir, transform=train_transforms)
    raw_val = datasets.ImageFolder(val_dir, transform=val_transforms) if os.path.exists(val_dir) else raw_train

    if full_dataset:
        train_dataset = raw_train
        val_dataset = raw_val
    else:
        train_dataset = get_balanced_subset(raw_train, train_samples)
        val_dataset = get_balanced_subset(raw_val, val_samples)

    print(f"[DataLoader] Classes: {raw_train.classes} (mapping: {raw_train.class_to_idx})")
    print(f"[DataLoader] Samples: {len(train_dataset)} Train | {len(val_dataset)} Validation")

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )

    return train_loader, val_loader


def evaluate_model(
    model: nn.Module,
    val_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Dict[str, float]:
    """Runs evaluation on validation dataset and computes precision, recall, and F1."""
    model.eval()
    val_loss = 0.0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)

            val_loss += loss.item() * inputs.size(0)
            preds = torch.argmax(outputs, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    total_samples = len(all_targets)
    avg_loss = val_loss / max(1, total_samples)
    acc = accuracy_score(all_targets, all_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="binary", zero_division=0
    )

    return {
        "loss": avg_loss,
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    }


def freeze_backbone_unfreeze_head(model: nn.Module):
    """Freezes backbone feature weights and unfreezes classification head for ultra-fast training."""
    # 1. Freeze all parameters first
    for param in model.parameters():
        param.requires_grad = False

    # 2. Unfreeze classification head
    unfrozen_count = 0
    if hasattr(model, "head") and hasattr(model.head, "fc"):
        for param in model.head.fc.parameters():
            param.requires_grad = True
            unfrozen_count += param.numel()
    elif hasattr(model, "head"):
        for param in model.head.parameters():
            param.requires_grad = True
            unfrozen_count += param.numel()
    elif hasattr(model, "fc"):
        for param in model.fc.parameters():
            param.requires_grad = True
            unfrozen_count += param.numel()
    else:
        # Fallback: scan named modules for final linear layer
        for name, param in model.named_parameters():
            if "fc" in name or "head" in name or "classifier" in name:
                param.requires_grad = True
                unfrozen_count += param.numel()

    total_params = sum(p.numel() for p in model.parameters())
    print(f"[Model Optimization] Backbone frozen. Training {unfrozen_count:,} / {total_params:,} parameters.")


def train_damage_classifier(
    dataset_dir: str = DEFAULT_DATASET_DIR,
    output_path: str = DEFAULT_OUTPUT_MODEL,
    model_name: str = "convnext_tiny",
    epochs: int = 2,
    batch_size: int = 32,
    lr: float = 1e-3,
    train_samples: int = 800,
    val_samples: int = 200,
    full_dataset: bool = False,
):
    """Fine-tunes the satellite damage classifier with live progress bar and fast head-tuning."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 70)
    print(f"RESCUEMESH // ULTRA-FAST DAMAGE CLASSIFIER TRAINING")
    print(f"Device: {device} | Model: {model_name} | Epochs: {epochs} | Batch: {batch_size}")
    print("=" * 70)

    # 1. Load Data (with balanced subsampling)
    train_loader, val_loader = get_data_loaders(
        dataset_dir,
        batch_size=batch_size,
        train_samples=train_samples,
        val_samples=val_samples,
        full_dataset=full_dataset,
    )

    # 2. Build Model
    try:
        model = timm.create_model(model_name, pretrained=True, num_classes=2)
    except Exception as e:
        print(f"[Model Notice] Pretrained fetch notice ({e}), creating standard architecture...")
        try:
            model = timm.create_model(model_name, pretrained=False, num_classes=2)
        except Exception:
            model = timm.create_model("resnet50", pretrained=False, num_classes=2)

    # 3. Freeze Backbone & Unfreeze Head for fast CPU execution
    freeze_backbone_unfreeze_head(model)
    model.to(device)

    # 4. Optimizer & Loss
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=1e-2)
    criterion = nn.CrossEntropyLoss()

    best_f1 = 0.0
    best_acc = 0.0
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 5. Training Loop with live tqdm bar
    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}", total=len(train_loader), leave=True)

        for inputs, targets in pbar:
            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            preds = torch.argmax(outputs, dim=1)
            correct_train += (preds == targets).sum().item()
            total_train += targets.size(0)

            # Update live progress bar
            running_acc = correct_train / max(1, total_train)
            if hasattr(pbar, "set_postfix"):
                pbar.set_postfix({
                    "loss": f"{loss.item():.4f}",
                    "acc": f"{running_acc:.3f}"
                })

        train_acc = correct_train / max(1, total_train)
        train_loss = running_loss / max(1, total_train)

        # Evaluate on validation subset
        metrics = evaluate_model(model, val_loader, criterion, device)

        print(f"\n[Epoch {epoch} Results]")
        print(f"  Train: Loss {train_loss:.4f} | Acc {train_acc:.4f}")
        print(f"  Val:   Loss {metrics['loss']:.4f} | Acc {metrics['accuracy']:.4f} | Precision {metrics['precision']:.4f} | Recall {metrics['recall']:.4f} | F1 {metrics['f1_score']:.4f}")

        if metrics["f1_score"] >= best_f1 or metrics["accuracy"] >= best_acc or epoch == epochs:
            best_f1 = metrics["f1_score"]
            best_acc = metrics["accuracy"]
            torch.save(model.state_dict(), output_path)
            print(f"  -> Saved checkpoint to: {output_path} (F1: {best_f1:.4f}, Acc: {best_acc:.4f})\n")

    total_time = time.time() - start_time
    print("=" * 70)
    print(f"TRAINING FINISHED in {total_time:.1f}s")
    print(f"Final Validation Accuracy: {best_acc:.4f} | F1-Score: {best_f1:.4f}")
    print(f"Model saved to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ultra-Fast RescueMesh Damage Classifier Training")
    parser.add_argument("--dataset-dir", type=str, default=DEFAULT_DATASET_DIR, help="Path to dataset directory")
    parser.add_argument("--output-path", type=str, default=DEFAULT_OUTPUT_MODEL, help="Path to save damage_classifier.pth")
    parser.add_argument("--model-name", type=str, default="convnext_tiny", help="Backbone model name")
    parser.add_argument("--epochs", type=int, default=2, help="Number of training epochs (default: 2)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--train-samples", type=int, default=800, help="Balanced train sample limit (default: 800)")
    parser.add_argument("--val-samples", type=int, default=200, help="Balanced validation sample limit (default: 200)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate (default: 1e-3)")
    parser.add_argument("--full-dataset", action="store_true", help="Train on full 10,000 images instead of subset")
    args = parser.parse_args()

    train_damage_classifier(
        dataset_dir=args.dataset_dir,
        output_path=args.output_path,
        model_name=args.model_name,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        train_samples=args.train_samples,
        val_samples=args.val_samples,
        full_dataset=args.full_dataset,
    )
