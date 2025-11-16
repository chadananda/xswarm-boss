"""
AI Service Selection Based on GPU Capability

Automatically determines which AI services should run locally vs cloud based on
GPU compute score (0-100). This ensures optimal performance and cost efficiency.

Service Categories:
- Moshi (voice interface): BF16/Q8/Q4 quantization or cloud
- Thinking Engine (LLM): Local (Ollama 70B/13B/7B) or cloud (Anthropic)
- Embeddings: Always CPU (no GPU needed)
"""

from dataclasses import dataclass
from typing import Literal
from .gpu_detector import GPUCapability


# Service selection thresholds (based on compute_score 0-100)
# Note: compute_score is linear: 128GB = 100, 64GB = 50, 32GB = 25, etc.

# Moshi quality thresholds
MOSHI_BF16_MIN_SCORE = 37.5  # 48GB+ VRAM (best quality) - score 37.5
MOSHI_Q8_MIN_SCORE = 18.75   # 24GB+ VRAM (very good quality) - score 18.75
MOSHI_Q4_MIN_SCORE = 9.4     # 12GB+ VRAM (good quality) - score 9.4

# LLM (thinking engine) thresholds
# Note: These are HIGH thresholds because deep thinking requires capable models
# 7B/13B models are only suitable for simple tasks, not deep reasoning
LLM_70B_MIN_SCORE = 50      # 64GB+ VRAM (large models for deep thinking)
LLM_13B_MIN_SCORE = 40      # 50GB+ VRAM (medium models, marginal for deep thinking)
LLM_7B_MIN_SCORE = 30       # 40GB+ VRAM (small models, weak for deep thinking)
# Below these thresholds: Use cloud (Anthropic Claude) for better quality

# Embeddings always use CPU (no GPU needed)
EMBEDDING_MODE = "cpu"


@dataclass
class ServiceConfig:
    """
    Configuration for which AI services run locally vs cloud.

    This is automatically determined based on GPU capability.
    """

    # Moshi (voice interface)
    moshi_mode: Literal["local", "cloud"]
    moshi_quality: Literal["bf16", "q8", "q4", "cloud"]  # Only used when local
    moshi_vram_needed_gb: float  # Estimated VRAM for selected quality

    # Thinking Engine (LLM for deep reasoning)
    thinking_mode: Literal["local", "cloud"]
    thinking_model: str  # "ollama:70b", "ollama:13b", "ollama:7b", or "anthropic:claude"
    thinking_vram_needed_gb: float  # Estimated VRAM if local

    # Embeddings (memory & search)
    embedding_mode: Literal["cpu", "cloud"]
    embedding_model: str  # Model name (e.g., "nomic-embed-text-v1.5")

    # Overall mode
    hybrid_mode: bool  # True if some services local, some cloud
    total_vram_needed_gb: float  # Total VRAM needed for local services

    # Metadata
    gpu_score: float  # Compute score (0-100) from GPU detection
    gpu_grade: str  # Letter grade (A++ to F)
    recommendation: str  # Human-readable recommendation


def select_services(gpu: GPUCapability) -> ServiceConfig:
    """
    Automatically select which services run locally vs cloud based on GPU capability.

    Decision Logic:
    1. Moshi: Select highest quality that fits in VRAM
    2. Thinking Engine: Select largest model that fits alongside Moshi
    3. Embeddings: Always CPU (reserve GPU for Moshi/LLM)
    4. Hybrid Mode: True if any service uses cloud

    Args:
        gpu: GPU capability from detect_gpu_capability()

    Returns:
        ServiceConfig with all service selections

    Examples:
        M3 24GB (score ~19):
        - Moshi: Q8 local (12GB)
        - Thinking: Anthropic cloud
        - Hybrid: True

        96GB GPU (score ~75):
        - Moshi: BF16 local (20GB)
        - Thinking: Ollama 70B local (50GB)
        - Hybrid: False (all local)

        8GB GPU (score ~6):
        - Moshi: Cloud
        - Thinking: Anthropic cloud
        - Hybrid: False (all cloud)
    """
    score = gpu.compute_score
    total_vram = gpu.vram_total_gb

    # ===== MOSHI SELECTION =====
    # Try highest quality first, fallback to lower quality or cloud
    # Base decision on total VRAM capacity, not current free memory
    if score >= MOSHI_BF16_MIN_SCORE and total_vram >= 48:
        moshi_mode = "local"
        moshi_quality = "bf16"
        moshi_vram = 20.0
    elif score >= MOSHI_Q8_MIN_SCORE and total_vram >= 24:
        moshi_mode = "local"
        moshi_quality = "q8"
        moshi_vram = 12.0
    elif score >= MOSHI_Q4_MIN_SCORE and total_vram >= 12:
        moshi_mode = "local"
        moshi_quality = "q4"
        moshi_vram = 8.0
    else:
        moshi_mode = "cloud"
        moshi_quality = "cloud"
        moshi_vram = 0.0

    # ===== THINKING ENGINE SELECTION =====
    # Calculate remaining VRAM after Moshi
    remaining_vram = total_vram - moshi_vram

    # Try largest model that fits
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
    # Always CPU (no GPU needed)
    embedding_mode = "cpu"
    embedding_model = "nomic-embed-text-v1.5"  # 262MB, ~200 docs/sec

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
    """
    Format service configuration as string for logging.

    Useful for debugging.
    """
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
