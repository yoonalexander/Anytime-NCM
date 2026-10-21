"""Record an allowlisted environment and pinned local artifact checksums."""

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing to record a successful preflight.")
    probe = torch.ones((64, 64), device="cuda")
    product = probe @ probe
    torch.cuda.synchronize()
    assert torch.equal(product, torch.full_like(product, 64))
    output_dir = ROOT / "results/setup"
    output_dir.mkdir(parents=True, exist_ok=True)
    properties = torch.cuda.get_device_properties(0)
    sources = json.loads((ROOT / "configs/setup_sources.json").read_text())
    nvidia_smi = "/usr/lib/wsl/lib/nvidia-smi"
    environment = {
        "python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "os_release": platform.freedesktop_os_release(),
        "torch": str(torch.__version__), "cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(), "cuda_available": True,
        "gpu": properties.name, "gpu_total_bytes": properties.total_memory,
        "compute_capability": list(torch.cuda.get_device_capability()),
        "cuda_matrix_multiplication_probe": "passed",
        "nvidia_smi": subprocess.check_output(
            [nvidia_smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], text=True
        ).strip(),
        "inference_precision": "upstream default float32; no autocast override",
        "torch_compile": False,
        "environment_variables": {key: os.environ.get(key) for key in (
            "CUDA_VISIBLE_DEVICES", "TOKENIZERS_PARALLELISM", "OMP_NUM_THREADS",
            "MKL_NUM_THREADS", "PYTORCH_CUDA_ALLOC_CONF", "CUBLAS_WORKSPACE_CONFIG",
            "CUDA_MODULE_LOADING", "HF_HUB_DISABLE_TELEMETRY",
        )},
        "sources": sources,
    }
    artifacts = []
    for directory in (ROOT / "artifacts/sudoku/hard", ROOT / "data/sudoku/hard"):
        for path in sorted(directory.iterdir()):
            if path.is_file():
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                artifacts.append({"path": path.relative_to(ROOT).as_posix(),
                                  "bytes": path.stat().st_size,
                                  "sha256": digest})
    required = {"artifacts/sudoku/hard/tokenizer.pt", "artifacts/sudoku/hard/generator.pt",
                "data/sudoku/hard/puzzles.pickle", "data/sudoku/hard/solutions.pickle"}
    assert required <= {entry["path"] for entry in artifacts}
    for name, record in (("environment.json", environment), ("artifacts.json", artifacts)):
        (output_dir / name).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"torch": environment["torch"], "cuda": environment["cuda_runtime"],
                      "gpu": environment["gpu"], "probe": "passed", "hashed_files": len(artifacts)}))


if __name__ == "__main__":
    main()
