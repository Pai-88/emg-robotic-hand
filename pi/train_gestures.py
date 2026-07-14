"""
Train the EMG gesture classifier from a recorded gestures.npz.

Important design choices (vs. the original emg_pipeline.py):

  * Temporal split per gesture, not random. Because windows overlap
    (hop < window_size), a random split would put nearly-identical
    consecutive windows into both train and test → leaked accuracy.
    We split each gesture's raw signal temporally, then re-window inside
    each segment.

  * Normaliser fitted on the training set only.

  * Class-weighted loss in case some gestures end up under-represented.

  * Early stopping on validation accuracy + cosine LR schedule.

    python train_gestures.py --data gestures.npz --epochs 80
"""
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import classification_report, confusion_matrix

from emg_common import (
    EMGGestureNet, Normaliser,
    WINDOW_SIZE, WINDOW_HOP,
    filter_offline, window_signal,
)


def temporal_split(raw, fractions=(0.7, 0.15, 0.15)):
    T = len(raw)
    n_tr = int(fractions[0] * T)
    n_va = int(fractions[1] * T)
    return raw[:n_tr], raw[n_tr:n_tr + n_va], raw[n_tr + n_va:]


def build_splits(npz, fractions=(0.7, 0.15, 0.15)):
    gestures = list(npz['gestures'])
    Xs = {'train': [], 'val': [], 'test': []}
    ys = {'train': [], 'val': [], 'test': []}
    for label_idx, gesture in enumerate(gestures):
        raw = npz[f'raw_{gesture}']
        tr, va, te = temporal_split(raw, fractions)
        for name, seg in zip(('train', 'val', 'test'), (tr, va, te)):
            if len(seg) < WINDOW_SIZE:
                continue
            filtered = filter_offline(seg)
            windows = window_signal(filtered, WINDOW_SIZE, WINDOW_HOP)
            Xs[name].append(windows)
            ys[name].append(np.full(len(windows), label_idx, dtype=np.int64))

    out = {}
    for name in Xs:
        out[name] = (np.concatenate(Xs[name]), np.concatenate(ys[name]))
    return out, gestures


def evaluate(model, loader, device):
    model.eval()
    preds, ys = [], []
    with torch.no_grad():
        for X, y in loader:
            X = X.to(device)
            preds.extend(model(X).argmax(1).cpu().numpy())
            ys.extend(y.numpy())
    return np.array(preds), np.array(ys)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='gestures.npz')
    parser.add_argument('--output-model', default='emg_model.pth')
    parser.add_argument('--output-norm',  default='emg_norm.npz')
    parser.add_argument('--epochs', type=int, default=80)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--patience', type=int, default=15)
    args = parser.parse_args()

    print("=" * 60)
    print("  EMG Gesture Trainer")
    print("=" * 60)

    npz = np.load(args.data, allow_pickle=True)
    splits, gestures = build_splits(npz)

    # Normaliser — fit on train only
    norm = Normaliser()
    norm.fit(splits['train'][0])

    loaders = {}
    for name in ('train', 'val', 'test'):
        X, y = splits[name]
        X = norm.transform(X)
        loaders[name] = DataLoader(
            TensorDataset(torch.from_numpy(X), torch.from_numpy(y)),
            batch_size=args.batch_size,
            shuffle=(name == 'train'),
        )
        print(f"  {name:5s}: {len(X):5d} windows | "
              f"class counts: {np.bincount(y, minlength=len(gestures)).tolist()}")

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = EMGGestureNet(num_classes=len(gestures)).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n  Model: EMGGestureNet — {n_params:,} parameters | device: {device}\n")

    # Class-weighted loss so rare gestures aren't ignored
    train_y = splits['train'][1]
    counts = np.bincount(train_y, minlength=len(gestures))
    weights = torch.tensor(
        len(train_y) / (len(gestures) * np.maximum(counts, 1)),
        dtype=torch.float32, device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_acc, best_state, patience = 0.0, None, 0
    for epoch in range(args.epochs):
        model.train()
        running = 0.0
        for X, y in loaders['train']:
            X, y = X.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(X), y)
            loss.backward()
            optimizer.step()
            running += loss.item() * X.size(0)
        train_loss = running / len(loaders['train'].dataset)
        scheduler.step()

        val_preds, val_y = evaluate(model, loaders['val'], device)
        val_acc = (val_preds == val_y).mean() if len(val_y) else 0.0

        if val_acc > best_acc:
            best_acc = val_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  epoch {epoch + 1:3d}/{args.epochs}  "
                  f"train_loss={train_loss:.3f}  "
                  f"val_acc={val_acc:.3f}  best={best_acc:.3f}")
        if patience >= args.patience:
            print(f"  early stop @ epoch {epoch + 1}  (best val_acc={best_acc:.3f})")
            break

    model.load_state_dict(best_state)

    print("\n=== TEST SET ===")
    test_preds, test_y = evaluate(model, loaders['test'], device)
    print(classification_report(
        test_y, test_preds, target_names=gestures, zero_division=0))
    print("Confusion matrix (rows = true, cols = predicted):")
    print(confusion_matrix(test_y, test_preds))

    torch.save({
        'model_state': model.state_dict(),
        'gestures': gestures,
        'window_size': WINDOW_SIZE,
        'window_hop': WINDOW_HOP,
    }, args.output_model)
    norm.save(args.output_norm)
    print(f"\n  Saved model    → {args.output_model}")
    print(f"  Saved normaliser → {args.output_norm}")


if __name__ == '__main__':
    main()
