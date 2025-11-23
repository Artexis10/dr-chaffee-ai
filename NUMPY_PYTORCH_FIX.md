# NumPy 2.x / PyTorch Compatibility Fix

## Problem

NumPy 2.x was being installed despite pinning `numpy<2.0.0`, causing PyTorch 2.1.2 to fail with:

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.3.5 as it may crash.
module 'torch.utils._pytree' has no attribute 'register_pytree_node'
```

## Root Cause

**Installation order matters!** When you install packages in the wrong order, later packages can pull in NumPy 2.x as a dependency, overriding your pin.

### ❌ Wrong Order (causes NumPy 2.x to be installed):
```dockerfile
RUN pip install numpy  # Generic, gets latest (2.x)
RUN pip install torch==2.1.2  # Works with NumPy 1.x
RUN pip install sentence-transformers  # May pull NumPy 2.x
```

### ✅ Correct Order (prevents NumPy 2.x):
```dockerfile
RUN pip install "numpy==1.24.3"  # Pin FIRST
RUN pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
RUN pip install sentence-transformers==2.2.2  # Pin to compatible version
```

## Solution

### 1. **Install NumPy 1.24.3 FIRST** (before PyTorch)
```dockerfile
RUN pip install --no-cache-dir "numpy==1.24.3"
```

### 2. **Install PyTorch CPU-only SECOND** (after NumPy)
```dockerfile
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu
```

### 3. **Install everything else THIRD** (with pinned versions)
```dockerfile
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    transformers==4.36.2 \
    tokenizers==0.15.0 \
    huggingface-hub==0.19.4 \
    safetensors==0.4.1
```

## Dependency Matrix (Tested & Working)

| Package | Version | Notes |
|---------|---------|-------|
| `numpy` | `1.24.3` | **MUST install first** |
| `torch` | `2.1.2+cpu` | CPU-only wheel |
| `torchvision` | `0.16.2+cpu` | CPU-only wheel |
| `torchaudio` | `2.1.2+cpu` | CPU-only wheel |
| `sentence-transformers` | `2.2.2` | Compatible with torch 2.1.2 |
| `transformers` | `4.36.2` | Compatible with torch 2.1.2 |
| `tokenizers` | `0.15.0` | Pinned for stability |
| `huggingface-hub` | `0.19.4` | Pinned for stability |
| `safetensors` | `0.4.1` | Pinned for stability |

## Why This Works

1. **NumPy 1.24.3** is installed first and locked in place
2. **PyTorch 2.1.2** is compiled against NumPy 1.x and works perfectly with 1.24.3
3. **sentence-transformers 2.2.2** is compatible with both NumPy 1.24.3 and PyTorch 2.1.2
4. **All dependencies are pinned** to prevent pip from "upgrading" to incompatible versions

## Verification

After building the Docker image, verify NumPy version:

```bash
docker run <image> python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
# Expected: NumPy: 1.24.3

docker run <image> python -c "import torch; print(f'PyTorch: {torch.__version__}')"
# Expected: PyTorch: 2.1.2+cpu

docker run <image> python -c "from sentence_transformers import SentenceTransformer; print('✅ OK')"
# Expected: ✅ OK
```

## Alternative: Use PyTorch 2.5.x + NumPy 2.x

If you want to use NumPy 2.x, you need to upgrade PyTorch:

```dockerfile
RUN pip install --no-cache-dir "numpy>=2.0.0"
RUN pip install --no-cache-dir \
    torch==2.5.1 \
    torchvision==0.20.1 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    sentence-transformers>=3.0.0 \
    transformers>=4.45.0
```

**However**, PyTorch 2.5.x CPU wheels are larger and may have compatibility issues with older code.

## Recommendation

**Stick with NumPy 1.24.3 + PyTorch 2.1.2** for production stability.

## Files Modified

- `Dockerfile` - Enforces correct installation order
- `backend/requirements-production.txt` - Documents dependency matrix

## References

- PyTorch NumPy compatibility: https://github.com/pytorch/pytorch/issues/91516
- sentence-transformers compatibility: https://github.com/UKPLab/sentence-transformers/issues/1762
- NumPy 2.0 migration guide: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
