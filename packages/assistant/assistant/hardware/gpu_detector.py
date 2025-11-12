"""
GPU Capability Detection and Scoring

Detects GPU hardware across platforms (NVIDIA, AMD, Apple, CPU) and calculates
a capability score with strict grading scale where 32GB VRAM = C (average).

This helps determine whether AI workloads should run locally or in the cloud.
"""

from dataclasses import dataclass
from typing import Optional
import platform


@dataclass
class GPUCapability:
    """
    GPU capability information with strict grading.

    Grading Scale (strict, 32GB VRAM = C):
    - A++: 128GB+ (ultra high-end workstation)
    - A+: 96-127GB
    - A: 80-95GB
    - A-: 64-79GB
    - B++: 56-63GB
    - B+: 48-55GB
    - B: 40-47GB
    - B-: 36-39GB
    - C: 28-35GB (includes 32GB - adequate for local inference)
    - C-: 20-27GB (marginal, some workloads may struggle)
    - D: 12-19GB (cloud recommended)
    - F: <12GB (cloud required for heavy workloads)
    """

    device_name: str
    vram_total_gb: float
    vram_used_gb: float
    vram_free_gb: float
    compute_score: float  # 0-100
    temp_c: Optional[float]
    grade: str  # A++, A+, A, A-, B++, B+, B, B-, C, C-, D, F
    util_percent: float
    device_type: str  # "nvidia", "amd", "apple", "cpu"


def _calculate_grade(vram_gb: float) -> str:
    """
    Calculate GPU grade based on VRAM with strict scale.

    32GB = C (average) - intentionally high bar for AI workloads.
    Anything below 28GB is considered inadequate for serious local inference.
    """
    if vram_gb >= 128:
        return "A++"
    elif vram_gb >= 96:
        return "A+"
    elif vram_gb >= 80:
        return "A"
    elif vram_gb >= 64:
        return "A-"
    elif vram_gb >= 56:
        return "B++"
    elif vram_gb >= 48:
        return "B+"
    elif vram_gb >= 40:
        return "B"
    elif vram_gb >= 36:
        return "B-"
    elif vram_gb >= 28:
        return "C"
    elif vram_gb >= 20:
        return "C-"
    elif vram_gb >= 12:
        return "D"
    else:
        return "F"


def _detect_nvidia_gpu() -> Optional[GPUCapability]:
    """
    Detect NVIDIA GPU using pynvml (NVIDIA Management Library).

    Returns:
        GPUCapability if NVIDIA GPU found, None otherwise
    """
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        # Device name
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode('utf-8')

        # VRAM info (in bytes, convert to GB)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_total = mem_info.total / (1024 ** 3)
        vram_used = mem_info.used / (1024 ** 3)
        vram_free = mem_info.free / (1024 ** 3)

        # Utilization
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_util = util.gpu

        # Temperature
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except:
            temp = None

        # Compute score (simplified: use VRAM as proxy)
        compute_score = min(100, (vram_total / 128) * 100)

        pynvml.nvmlShutdown()

        grade = _calculate_grade(vram_total)

        return GPUCapability(
            device_name=name,
            vram_total_gb=vram_total,
            vram_used_gb=vram_used,
            vram_free_gb=vram_free,
            compute_score=compute_score,
            temp_c=temp,
            grade=grade,
            util_percent=gpu_util,
            device_type="nvidia"
        )

    except (ImportError, Exception):
        return None


def _detect_apple_gpu() -> Optional[GPUCapability]:
    """
    Detect Apple Silicon GPU using PyTorch MPS backend.

    Apple Silicon uses unified memory, so we report available RAM.

    Returns:
        GPUCapability if Apple Silicon found, None otherwise
    """
    try:
        import torch
        import psutil

        # Check if MPS is available (Apple Silicon)
        if not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()):
            return None

        # Get system RAM (unified memory on Apple Silicon)
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        used_gb = mem.used / (1024 ** 3)
        free_gb = mem.available / (1024 ** 3)
        util_percent = mem.percent

        # Get processor name
        if platform.system() == "Darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                cpu_name = result.stdout.strip()
                # Extract chip name (e.g., "Apple M3 Max")
                if "Apple" in cpu_name:
                    device_name = cpu_name
                else:
                    device_name = "Apple Silicon"
            except:
                device_name = "Apple Silicon"
        else:
            device_name = "Apple Silicon"

        # Compute score based on available RAM
        compute_score = min(100, (total_gb / 128) * 100)

        # No temperature sensor accessible via Python on macOS
        temp = None

        grade = _calculate_grade(total_gb)

        return GPUCapability(
            device_name=device_name,
            vram_total_gb=total_gb,
            vram_used_gb=used_gb,
            vram_free_gb=free_gb,
            compute_score=compute_score,
            temp_c=temp,
            grade=grade,
            util_percent=util_percent,
            device_type="apple"
        )

    except (ImportError, Exception):
        return None


def _detect_amd_gpu() -> Optional[GPUCapability]:
    """
    Detect AMD GPU using amdsmi (AMD System Management Interface).

    Note: amdsmi support is limited and may not be available on all systems.

    Returns:
        GPUCapability if AMD GPU found, None otherwise
    """
    try:
        import amdsmi

        amdsmi.amdsmi_init()
        devices = amdsmi.amdsmi_get_processor_handles()

        if not devices:
            amdsmi.amdsmi_shut_down()
            return None

        # Use first device
        device = devices[0]

        # Device name
        try:
            name = amdsmi.amdsmi_get_gpu_asic_info(device)['market_name']
        except:
            name = "AMD GPU"

        # VRAM info
        try:
            mem_info = amdsmi.amdsmi_get_gpu_memory_total(device, amdsmi.AmdSmiMemoryType.VRAM)
            vram_total = mem_info / (1024 ** 3)

            mem_usage = amdsmi.amdsmi_get_gpu_memory_usage(device, amdsmi.AmdSmiMemoryType.VRAM)
            vram_used = mem_usage / (1024 ** 3)
            vram_free = vram_total - vram_used
        except:
            # Fallback to reasonable defaults if memory query fails
            vram_total = 16.0
            vram_used = 8.0
            vram_free = 8.0

        # Utilization
        try:
            util = amdsmi.amdsmi_get_gpu_activity(device)
            gpu_util = util['gfx_activity']
        except:
            gpu_util = 0.0

        # Temperature
        try:
            temp = amdsmi.amdsmi_get_temp_metric(device, amdsmi.AmdSmiTemperatureType.EDGE, amdsmi.AmdSmiTemperatureMetric.CURRENT)
            temp = temp / 1000.0  # Convert to Celsius
        except:
            temp = None

        amdsmi.amdsmi_shut_down()

        # Compute score
        compute_score = min(100, (vram_total / 128) * 100)

        grade = _calculate_grade(vram_total)

        return GPUCapability(
            device_name=name,
            vram_total_gb=vram_total,
            vram_used_gb=vram_used,
            vram_free_gb=vram_free,
            compute_score=compute_score,
            temp_c=temp,
            grade=grade,
            util_percent=gpu_util,
            device_type="amd"
        )

    except (ImportError, Exception):
        return None


def _detect_cpu_fallback() -> GPUCapability:
    """
    CPU fallback when no GPU is detected.

    Returns system RAM as "VRAM" with F grade (cloud required).
    """
    import psutil

    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    free_gb = mem.available / (1024 ** 3)
    util_percent = mem.percent

    # Get CPU name
    if platform.system() == "Darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=True
            )
            device_name = result.stdout.strip()
        except:
            device_name = "CPU"
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        device_name = line.split(":")[1].strip()
                        break
                else:
                    device_name = "CPU"
        except:
            device_name = "CPU"
    else:
        device_name = "CPU"

    # CPU always gets low compute score
    compute_score = 10.0

    # CPU never has temperature accessible
    temp = None

    # Grade based on RAM (will be F for most systems)
    grade = _calculate_grade(total_gb)

    return GPUCapability(
        device_name=device_name,
        vram_total_gb=total_gb,
        vram_used_gb=used_gb,
        vram_free_gb=free_gb,
        compute_score=compute_score,
        temp_c=temp,
        grade=grade,
        util_percent=util_percent,
        device_type="cpu"
    )


def detect_gpu_capability() -> GPUCapability:
    """
    Detect GPU capability across platforms.

    Detection priority:
    1. NVIDIA (CUDA) via pynvml
    2. Apple Silicon (MPS) via PyTorch + psutil
    3. AMD (ROCm) via amdsmi
    4. CPU fallback via psutil

    Returns:
        GPUCapability with device info and strict grading
    """
    # Try NVIDIA first (most common for AI workloads)
    result = _detect_nvidia_gpu()
    if result:
        return result

    # Try Apple Silicon (Mac)
    result = _detect_apple_gpu()
    if result:
        return result

    # Try AMD (less common, experimental support)
    result = _detect_amd_gpu()
    if result:
        return result

    # Fallback to CPU
    return _detect_cpu_fallback()
