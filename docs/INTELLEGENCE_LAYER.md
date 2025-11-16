# Smart Intelligence Integration for a Personal Assistant Application

## Product Requirements Document (PRD)

***

### Overview

This PRD defines the architecture, features, and implementation strategy for **Smart Intelligence Integration** in a Python-based TUI Personal Assistant application. The system will dynamically select and configure the optimal intelligence engine—local LLM or API—based on hardware detection, maximizing tool-calling, summarization, and instruction-following. The experience will be fully packaged: no manual Ollama setup required, seamless operation across Windows, Linux, and Apple M-series Macs. Remote API switching, model downloading, and context memory management are handled automatically.

***

## Intelligence Levels

| Level | Hardware/Strategy                                             | Main Model/Quantization              | Engine                   | Quality |
|-------|--------------------------------------------------------------|--------------------------------------|--------------------------|---------|
| 0     | <8GB VRAM (Minimal), API smart-routing                       | Claude Sonnet 4 (main), Gemini Flash | Remote Server (API)      | ~97%    |
| 1     | 12-16GB VRAM, Entry GPU                                      | Qwen2.5-7B Q5_K_M                    | llama.cpp/Ollama         | ~89%    |
| 2     | 20-24GB VRAM, Prosumer GPU                                   | Qwen2.5-14B Q6_K                     | llama.cpp/Ollama         | ~93%    |
| 3     | 28-32GB VRAM, Workstation                                    | Qwen3-30B-A3B Q4_K_M                 | llama.cpp/Ollama         | ~96%    |
| 4     | 40-48GB VRAM, Professional                                   | Qwen2.5-72B IQ4_XS                   | llama.cpp/Ollama         | ~98%    |
| 5     | 60-80GB VRAM, High-End Data-center                           | Qwen2.5-72B Q6_K or Q8_0             | llama.cpp/Ollama         | ~99%    |
| 6     | Any GPU 12GB+, Hybrid (local + API fallback)                 | Best local fit + API fallback        | Hybrid Router            | ~97%    |

***

## Key Capabilities

- **Level Assignment**: At first run, the application auto-assesses VRAM, GPU type, CPU speed, and concurrency. It then assigns the optimal intelligence level.
- **Automatic Model Management**: The required GGUF model and quantization are selected, downloaded, and launched automatically.
- **Local Engine Integration**: The app includes or auto-installs llama.cpp binaries or a minimal local Ollama, fully managed by the application context.
- **API Routing**: All remote inference goes through your own server, which smart-switches between API sources (Claude Sonnet 4, Gemini Flash) to optimize cost and quality.
- **Context Memory**: The app interacts with a dedicated local memory manager for all context/state, keeping API usage stateless and secure.
- **Zero manual configuration**: From user perspective, everything "just works", with no need to launch Ollama or configure it manually.

***

## Integration & Workflow

### 1. Hardware/Environment Detection

- Upon install/first run:
    - Detect total VRAM via cross-platform checks:
      - Windows: WMI queries (`pywin32`)
      - Linux: `nvidia-smi`, `lshw`, PCI sysfs
      - Mac (M-series): `system_profiler`, Metal queries
    - Assess available CPU cores/threads
    - Benchmark simple matrix multiplication for throughput estimate (optional)
    - Determine if GPU drivers/support present (fall back to API as needed)
    - Set concurrency (session) limits based on measured VRAM and CPU perf

#### Sample Python Detection Code

```python
import platform, subprocess
def detect_vram():
    system = platform.system()
    if system == "Windows":
        # Use WMI via PowerShell
        output = subprocess.check_output(
            ["powershell", "(Get-WmiObject Win32_VideoController).AdapterRAM"], text=True)
        return int(output.split()[0]) / (1024**3)
    elif system == "Linux":
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], text=True)
            return int(output.split()[0]) / 1024
        except:
            return 0
    elif system == "Darwin":
        # MacOS: Try Metal
        output = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True)
        # Parse out VRAM
        for line in output.splitlines():
            if "VRAM" in line:
                return int(line.split()[-2])
        return 0
    return 0
```

### 2. Level Selection Logic

- Map detected VRAM and CPU to the closest supported Level (0-6)
- Offer override (advanced mode) for expert users
- Expose current level and rationale in status panel

### 3. Model Download & Launch

- Model selection table in code (see above PRD)
- Download GGUF model from reliable source (e.g. Hugging Face, Alibaba, custom server)
- Validate quantization (Q5_K_M, Q6_K, IQ4_XS, Q8_0) for hardware
- Unpack and mount model for llama.cpp/Ollama instance
- Use subprocess control to launch engine (no user action), bind to local socket

#### Sample Model Selection

```python
def select_model(vram):
    if vram < 8: return "api"
    elif vram < 16: return "qwen2.5-7b-q5_k_m"
    elif vram < 24: return "qwen2.5-14b-q6_k"
    elif vram < 32: return "qwen3-30b-a3b-q4_k_m"
    elif vram < 48: return "qwen2.5-72b-iq4_xs"
    elif vram < 80: return "qwen2.5-72b-q6_k"
    else: return "api"
```

### 4. Ollama/llama.cpp Integration

- Bundle llama.cpp or Ollama binaries for Win/Lin/Mac; provide install scripts if not present
- Use engine subprocess with pre-configured flags:
    - Flash Attention enabled (`--flash-attn`)
    - KV cache configured (`--kv-cache q8_0`)
    - Context setting matched to level
- Do not expose user config file; all options managed by app

### 5. API Routing & Orchestration

- Direct all remote requests to centralized server API
- Server implements intelligent routing for balance of cost, instruction quality, and tool function support
    - API selects between Claude Sonnet 4 (tool-heavy) and Gemini Flash (speed, context)
    - All API billing and authentication handled server-side, not exposed to user

### 6. Context Memory Management

- Use isolated context/memory manager on local system
- LLM engine interacts with this manager via local interface (gRPC, pipes, etc.)
- API-level sessions remain stateless; data privacy is maintained for all local context

***

## Platform & Packaging Requirements

- Distribute Python TUI application as a standalone binary with bundled dependencies
- Use PyInstaller, Briefcase, or similar to bundle with llama.cpp/Ollama, preventing the need for system-level configuration
- Provide fallback to API level if hardware unsupported or model launch fails
- Confirm platform support for Win10+, modern Linux distros, macOS 13+ (Intel & M-series)

***

## Implementation Notes

- All engine launch, model download, and options set by the application; no user input needed
- Models adaptively downloaded and mounted on user's hardware
- API routing and fallback performed intelligently
- All local model output managed for context and summarization
- Upgrades/optimization strategies (Flash Attention, KV cache) always maximal per hardware tier

***

## Summary Table for Developer Integration

| Step             | Implementation                                    |
|------------------|--------------------------------------------------|
| Hardware Detect  | Cross-platform script as above                    |
| Level Select     | Map VRAM/speed to 0-6, expose in UI               |
| Model Download   | On-demand, based on selection/config              |
| Engine Launch    | Subprocess; config by level                       |
| API Integrate    | Route through central API/remote server           |
| Memory Manager   | Local backend (separate module/gRPC)              |
| Pack/Bundling    | PyInstaller/Briefcase w/ binaries, Win+Lin+Mac    |

***

## End of PRD