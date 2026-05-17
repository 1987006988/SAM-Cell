from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.cli import build_argparser, run


if __name__ == "__main__":
    parser = build_argparser()
    args = parser.parse_args(
        [
            "--config",
            "configs/sam_cell_default.yaml",
            "--image",
            "/mnt/d/cell data/CellCosmos_Benchmark/images/cellpose_000.png",
            "--out_dir",
            "outputs/debug_one",
            "--save_debug",
        ]
    )
    run(args)

