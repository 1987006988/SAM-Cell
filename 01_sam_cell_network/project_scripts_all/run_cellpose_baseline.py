from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _mask_path(out_dir: Path, image_path: Path) -> Path:
    return out_dir / f"{image_path.stem}_cp_masks.tif"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cached Cellpose baseline for a devset CSV")
    parser.add_argument("--devset_csv", default="outputs/dev_eval/devset_25.csv")
    parser.add_argument("--out_dir", default="outputs/cellpose_baseline")
    parser.add_argument("--conda_env", default="segment-anything-251")
    parser.add_argument("--pretrained_model", default="cyto")
    parser.add_argument("--diameter", default="0")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    rows = _read_rows(Path(args.devset_csv), args.limit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        output_mask = _mask_path(out_dir, image_path)
        if output_mask.exists() and not args.overwrite:
            print(f"[{idx}/{len(rows)}] cached {output_mask.name}")
            continue
        print(f"[{idx}/{len(rows)}] cellpose {image_path.name}")
        cmd = [
            "conda",
            "run",
            "-n",
            args.conda_env,
            "python",
            "-m",
            "cellpose",
            "--image_path",
            str(image_path),
            "--pretrained_model",
            args.pretrained_model,
            "--chan",
            "0",
            "--chan2",
            "0",
            "--diameter",
            str(args.diameter),
            "--use_gpu",
            "--save_tif",
            "--no_npy",
            "--savedir",
            str(out_dir),
        ]
        subprocess.run(cmd, check=True)
        if not output_mask.exists():
            raise FileNotFoundError(f"Cellpose did not create expected mask: {output_mask}")


if __name__ == "__main__":
    main()

