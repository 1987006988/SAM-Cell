from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cellpose inference over a CellCosmos manifest.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--pretrained_model", required=True)
    parser.add_argument("--diameter", default="0")
    parser.add_argument("--gpu_device", default="0")
    parser.add_argument("--chan", default="0")
    parser.add_argument("--chan2", default="0")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    rows = _read_rows(Path(args.manifest_csv))
    if args.limit:
        rows = rows[: args.limit]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    completed = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        output_mask = out_dir / f"{image_path.stem}_cp_masks.tif"
        if output_mask.exists() and not args.overwrite:
            print(f"[{idx}/{len(rows)}] cached {output_mask.name}", flush=True)
            completed.append(str(output_mask))
            continue
        print(f"[{idx}/{len(rows)}] cellpose {image_path.name}", flush=True)
        cmd = [
            sys.executable,
            "-m",
            "cellpose",
            "--image_path",
            str(image_path),
            "--pretrained_model",
            str(args.pretrained_model),
            "--chan",
            str(args.chan),
            "--chan2",
            str(args.chan2),
            "--diameter",
            str(args.diameter),
            "--gpu_device",
            str(args.gpu_device),
            "--use_gpu",
            "--save_tif",
            "--no_npy",
            "--savedir",
            str(out_dir),
        ]
        subprocess.run(cmd, env=env, check=True)
        if not output_mask.exists():
            raise FileNotFoundError(f"Cellpose did not create expected mask: {output_mask}")
        completed.append(str(output_mask))
    (out_dir / "inference_manifest.json").write_text(
        json.dumps(
            {
                "manifest_csv": args.manifest_csv,
                "pretrained_model": args.pretrained_model,
                "diameter": args.diameter,
                "gpu_device": args.gpu_device,
                "n_images": len(rows),
                "outputs": completed,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
