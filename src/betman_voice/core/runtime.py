from __future__ import annotations

import importlib.util
import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeInfo:
    platform: str
    machine: str
    cuda_available: bool
    mps_available: bool
    mlx_available: bool
    selected_device: str


def detect_runtime() -> RuntimeInfo:
    cuda_available = False
    mps_available = False
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        mps_available = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    except Exception:
        pass

    mlx_available = importlib.util.find_spec("mlx") is not None
    if cuda_available:
        device = "cuda"
    elif mps_available:
        device = "mps"
    else:
        device = "cpu"

    return RuntimeInfo(
        platform=platform.system().lower(),
        machine=platform.machine().lower(),
        cuda_available=cuda_available,
        mps_available=mps_available,
        mlx_available=mlx_available,
        selected_device=device,
    )
