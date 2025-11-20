"""
Hardware Detection and Service Selection Module.
Consolidates GPU detection and AI service selection logic.
"""

from dataclasses import dataclass
from typing import Optional, Literal
import platform

# ==============================================================================
# GPU DETECTION
# ==============================================================================

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


def _calculate_compute_score(vram_gb: float) -> float:
    """
    Calculate numeric compute score (0-100) based on VRAM.

    Linear scale where 128GB = 100, 0GB = 0.
    This score is used for automatic service selection.
    """
    return min(100.0, (vram_gb / 128.0) * 100.0)


def _detect_nvidia_gpu() -> Optional[GPUCapability]:
    """Detect NVIDIA GPU using pynvml."""
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

        pynvml.nvmlShutdown()

        # Calculate grade and compute score
        grade = _calculate_grade(vram_total)
        compute_score = _calculate_compute_score(vram_total)

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
    """Detect Apple Silicon GPU using PyTorch MPS backend."""
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

        # No temperature sensor accessible via Python on macOS
        temp = None

        # Calculate grade and compute score
        grade = _calculate_grade(total_gb)
        compute_score = _calculate_compute_score(total_gb)

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
    """Detect AMD GPU using amdsmi."""
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

        # Calculate grade and compute score
        grade = _calculate_grade(vram_total)
        compute_score = _calculate_compute_score(vram_total)

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
    """CPU fallback when no GPU is detected."""
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

    # CPU never has temperature accessible
    temp = None

    # Grade based on RAM (will be F for most systems)
    grade = _calculate_grade(total_gb)
    # CPU gets compute score based on RAM, but capped lower since no GPU
    compute_score = min(10.0, _calculate_compute_score(total_gb))

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


# ==============================================================================
# SERVICE SELECTION
# ==============================================================================

# Service selection thresholds (based on compute_score 0-100)
MOSHI_BF16_MIN_SCORE = 37.5  # 48GB+ VRAM (best quality)
MOSHI_Q8_MIN_SCORE = 18.75   # 24GB+ VRAM (very good quality)
MOSHI_Q4_MIN_SCORE = 9.4     # 12GB+ VRAM (good quality)

LLM_70B_MIN_SCORE = 50      # 64GB+ VRAM
LLM_13B_MIN_SCORE = 40      # 50GB+ VRAM
LLM_7B_MIN_SCORE = 30       # 40GB+ VRAM

EMBEDDING_MODE = "cpu"


@dataclass
class ServiceConfig:
    """Configuration for which AI services run locally vs cloud."""

    # Moshi (voice interface)
    moshi_mode: Literal["local", "cloud"]
    moshi_quality: Literal["bf16", "q8", "q4", "cloud"]
    moshi_vram_needed_gb: float

    # Thinking Engine (LLM for deep reasoning)
    thinking_mode: Literal["local", "cloud"]
    thinking_model: str
    thinking_vram_needed_gb: float

    # Embeddings (memory & search)
    embedding_mode: Literal["cpu", "cloud"]
    embedding_model: str

    # Overall mode
    hybrid_mode: bool
    total_vram_needed_gb: float

    # Metadata
    gpu_score: float
    gpu_grade: str
    recommendation: str


def select_services(gpu: GPUCapability) -> ServiceConfig:
    """Automatically select which services run locally vs cloud based on GPU capability."""
    score = gpu.compute_score
    total_vram = gpu.vram_total_gb

    # ===== MOSHI SELECTION =====
    if score >= MOSHI_Q4_MIN_SCORE and total_vram >= 12:
        moshi_mode = "local"
        moshi_quality = "q4"
        moshi_vram = 8.0
    else:
        moshi_mode = "cloud"
        moshi_quality = "cloud"
        moshi_vram = 0.0

    # ===== THINKING ENGINE SELECTION =====
    remaining_vram = total_vram - moshi_vram

    if score >= LLM_70B_MIN_SCORE and remaining_vram >= 50:
        thinking_mode = "local"
        thinking_model = "ollama:llama3.1:70b"
        thinking_vram = 50.0
    elif score >= LLM_13B_MIN_SCORE and remaining_vram >= 10:
        thinking_mode = "local"
        thinking_model = "ollama:llama3.1:13b"
        thinking_vram = 10.0
    elif score >= LLM_7B_MIN_SCORE and remaining_vram >= 5:
        thinking_mode = "local"
        thinking_model = "ollama:llama3.1:7b"
        thinking_vram = 5.0
    else:
        thinking_mode = "cloud"
        thinking_model = "anthropic:claude-sonnet-4-5"
        thinking_vram = 0.0

    # ===== EMBEDDINGS =====
    embedding_mode = "cpu"
    embedding_model = "nomic-embed-text-v1.5"

    # ===== TOTALS & METADATA =====
    total_vram = moshi_vram + thinking_vram
    hybrid_mode = (moshi_mode == "local" and thinking_mode == "cloud") or \
                  (moshi_mode == "cloud" and thinking_mode == "local")

    # Generate recommendation
    if moshi_mode == "local" and thinking_mode == "local":
        recommendation = f"Excellent! Run all AI locally ({moshi_quality.upper()} voice + {thinking_model.split(':')[1]} thinking)"
    elif hybrid_mode:
        if moshi_mode == "local":
            recommendation = f"Good! Run voice locally ({moshi_quality.upper()}) with cloud thinking"
        else:
            recommendation = f"Run thinking locally ({thinking_model.split(':')[1]}) with cloud voice"
    else:
        recommendation = "Cloud recommended for all AI services (insufficient GPU)"

    return ServiceConfig(
        moshi_mode=moshi_mode,
        moshi_quality=moshi_quality,
        moshi_vram_needed_gb=moshi_vram,
        thinking_mode=thinking_mode,
        thinking_model=thinking_model,
        thinking_vram_needed_gb=thinking_vram,
        embedding_mode=embedding_mode,
        embedding_model=embedding_model,
        hybrid_mode=hybrid_mode,
        total_vram_needed_gb=total_vram,
        gpu_score=score,
        gpu_grade=gpu.grade,
        recommendation=recommendation,
    )


def format_service_config(config: ServiceConfig) -> str:
    """Format service configuration as string for logging."""
    lines = []
    lines.append("=" * 60)
    lines.append("AI Service Configuration")
    lines.append("=" * 60)
    lines.append(f"GPU Score: {config.gpu_score:.1f}/100 (Grade: {config.gpu_grade})")
    lines.append(f"Mode: {'Hybrid' if config.hybrid_mode else 'All Local' if config.moshi_mode == 'local' else 'All Cloud'}")
    lines.append("")
    lines.append(f"🎤 Voice (Moshi): {config.moshi_mode.upper()}")
    if config.moshi_mode == "local":
        lines.append(f"   Quality: {config.moshi_quality.upper()} ({config.moshi_vram_needed_gb:.0f}GB VRAM)")
    lines.append("")
    lines.append(f"🧠 Thinking Engine: {config.thinking_mode.upper()}")
    lines.append(f"   Model: {config.thinking_model}")
    if config.thinking_mode == "local":
        lines.append(f"   VRAM: {config.thinking_vram_needed_gb:.0f}GB")
    lines.append("")
    lines.append(f"🔍 Embeddings: {config.embedding_mode.upper()}")
    lines.append(f"   Model: {config.embedding_model}")
    lines.append("")
    if config.total_vram_needed_gb > 0:
        lines.append(f"Total VRAM: {config.total_vram_needed_gb:.0f}GB")
    lines.append("")
    lines.append(f"💡 {config.recommendation}")
    lines.append("=" * 60)
    return "\n".join(lines)
