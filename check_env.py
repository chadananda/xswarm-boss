
try:
    import mlx.core
    print("MLX Available")
except ImportError as e:
    print(f"MLX Not Available: {e}")

try:
    import moshi_mlx
    print("Moshi MLX Available")
except ImportError as e:
    print(f"Moshi MLX Not Available: {e}")
