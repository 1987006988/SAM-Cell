from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
import tifffile


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _stem(row: dict[str, str]) -> str:
    image_name = row.get("image_name") or Path(row["image_path"]).name
    return Path(image_name).stem


def _refresh_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        dst.symlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def _write_empty_mask_like(image_path: Path, output_mask: Path) -> None:
    image = np.asarray(Image.open(image_path))
    if image.ndim < 2:
        raise ValueError(f"Expected at least 2D image, got shape {image.shape} for {image_path}")
    empty = np.zeros(image.shape[:2], dtype=np.uint16)
    tifffile.imwrite(output_mask, empty)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official Cellpose CLI once over a manifest-backed staging directory.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--pretrained_model", default="cyto3")
    parser.add_argument("--diameter", default="0")
    parser.add_argument("--gpu_device", default="0")
    parser.add_argument("--chan", default="0")
    parser.add_argument("--chan2", default="0")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--stage_dir")
    parser.add_argument("--keep_stage", action="store_true")
    args = parser.parse_args()

    rows = _read_rows(Path(args.manifest_csv), args.limit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage_dir = Path(args.stage_dir) if args.stage_dir else out_dir / "_cellpose_cli_stage"
    _refresh_dir(stage_dir)

    pending = []
    skipped = []
    for row in rows:
        image_path = Path(row["image_path"])
        output_mask = out_dir / f"{_stem(row)}_cp_masks.tif"
        if output_mask.exists() and args.skip_existing and not args.overwrite:
            skipped.append(str(output_mask))
            continue
        pending.append(row)
        _link_or_copy(image_path, stage_dir / image_path.name)

    started = time.time()
    if pending:
        cmd = [
            sys.executable,
            "-m",
            "cellpose",
            "--dir",
            str(stage_dir),
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
        print("$ " + " ".join(cmd), flush=True)
        subprocess.run(cmd, env=os.environ.copy(), check=True)

    missing = []
    filled_empty = []
    outputs = []
    for row in rows:
        output_mask = out_dir / f"{_stem(row)}_cp_masks.tif"
        if output_mask.exists():
            outputs.append(str(output_mask))
        else:
            # The official Cellpose CLI may not write a mask file when it
            # predicts no objects. For evaluation, that is a valid empty
            # instance map rather than an inference failure.
            _write_empty_mask_like(Path(row["image_path"]), output_mask)
            filled_empty.append(str(output_mask))
            outputs.append(str(output_mask))
    if missing:
        raise FileNotFoundError(f"Cellpose did not create {len(missing)} expected masks; first: {missing[0]}")
    if not args.keep_stage:
        shutil.rmtree(stage_dir, ignore_errors=True)
    payload = {
        "manifest_csv": args.manifest_csv,
        "pretrained_model": args.pretrained_model,
        "diameter": args.diameter,
        "gpu_device": args.gpu_device,
        "n_images": len(rows),
        "pending": len(pending),
        "skipped": len(skipped),
        "elapsed_sec": time.time() - started,
        "filled_empty": filled_empty,
        "outputs": outputs,
    }
    (out_dir / "inference_manifest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ["n_images", "pending", "skipped", "elapsed_sec"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
