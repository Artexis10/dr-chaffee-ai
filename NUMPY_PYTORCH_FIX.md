# NumPy 2.x / PyTorch CPU Compatibility Fix

## Problem

NumPy 2.x was being installed despite pinning `numpy==1.24.3`, causing PyTorch 2.1.2 to fail with:

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.3.5 as it may crash.
module 'torch.utils._pytree' has no attribute 'register_pytree_node'
```

**Symptoms:**
- Embedding warmup fails on startup
- `/health` shows `"embeddings": "degraded"`
- BGE-small (sentence-transformers) doesn't work
- App starts but embeddings are broken

## Root Cause

**Two issues found:**

1. **Installation order** - Later packages can pull in NumPy 2.x as a transitive dependency, overriding the earlier pin
2. **`uvicorn[standard]`** - The `[standard]` extras include `uvloop` and `httptools` (compiled C extensions with NumPy dependencies)

When you run:
```dockerfile
RUN pip install numpy==1.24.3
RUN pip install uvicorn[standard]==0.24.0  # ❌ This pulls NumPy 2.x!
```

The second command upgrades NumPy to 2.x because `uvloop` or `httptools` have `numpy>=1.0` in their dependencies.

## Solution

### 1. Use Plain `uvicorn` (NOT `uvicorn[standard]`)

```dockerfile
# ❌ WRONG - pulls NumPy 2.x
RUN pip install uvicorn[standard]==0.24.0

# ✅ CORRECT - pure Python, no compiled extensions
RUN pip install uvicorn==0.24.0
```

**Trade-off:** Plain `uvicorn` is slightly slower (no `uvloop` event loop), but:
- ✅ No NumPy conflicts
- ✅ Still production-ready
- ✅ Works perfectly for CPU-only deployments
- ✅ Simpler dependency tree

### 2. Enforce Correct Installation Order

```dockerfile
# Stage 1: NumPy 1.24.3 FIRST
RUN pip install --no-cache-dir "numpy==1.24.3"

# Stage 2: PyTorch CPU-only SECOND
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Stage 3: Everything else THIRD (with explicit pins)
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    sentence-transformers==2.2.2 \
    transformers==4.36.2 \
    # ... all other deps
```

### 3. Pin ALL Transitive Dependencies

Don't just pin top-level packages - pin their dependencies too:

```dockerfile
# Top-level
sentence-transformers==2.2.2
transformers==4.36.2

# Transitive deps (prevents pip from "upgrading")
tokenizers==0.15.0
huggingface-hub==0.19.4
safetensors==0.4.1
requests==2.31.0
urllib3==2.1.0
certifi==2023.11.17
```

### 4. Verify NumPy Version at Build Time

Add a verification step to fail the build if NumPy 2.x snuck in:

```dockerfile
RUN python -c "import numpy; assert numpy.__version__.startswith('1.24'), f'NumPy {numpy.__version__} detected, expected 1.24.x'"
RUN python -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
RUN python -c "import numpy; print(f'✅ NumPy {numpy.__version__}')"
```

## Complete Dependency Matrix (Tested & Working)

### Core ML Stack
| Package | Version | Notes |
|---------|---------|-------|
| `numpy` | `1.24.3` | **MUST install first** |
| `torch` | `2.1.2+cpu` | CPU-only wheel |
| `torchvision` | `0.16.2+cpu` | CPU-only wheel |
| `torchaudio` | `2.1.2+cpu` | CPU-only wheel |

### Embeddings
| Package | Version | Notes |
|---------|---------|-------|
| `sentence-transformers` | `2.2.2` | Compatible with torch 2.1.2 |
| `transformers` | `4.36.2` | Compatible with torch 2.1.2 |
| `tokenizers` | `0.15.0` | Pinned for stability |
| `huggingface-hub` | `0.19.4` | Pinned for stability |
| `safetensors` | `0.4.1` | Pinned for stability |

### Web API
| Package | Version | Notes |
|---------|---------|-------|
| `fastapi` | `0.104.1` | Web framework |
| `uvicorn` | `0.24.0` | **Plain, NOT [standard]** |
| `click` | `8.1.7` | CLI (uvicorn dep) |
| `h11` | `0.14.0` | HTTP/1.1 (uvicorn dep) |

### HTTP Clients
| Package | Version | Notes |
|---------|---------|-------|
| `requests` | `2.31.0` | HTTP client |
| `urllib3` | `2.1.0` | Pinned |
| `certifi` | `2023.11.17` | SSL certs |
| `charset-normalizer` | `3.3.2` | Encoding |
| `idna` | `3.6` | Domain names |

### OpenAI
| Package | Version | Notes |
|---------|---------|-------|
| `openai` | `1.3.0` | OpenAI API client |
| `httpx` | `0.25.2` | Async HTTP (openai dep) |
| `httpcore` | `1.0.2` | HTTP core |
| `anyio` | `3.7.1` | Async primitives |
| `pydantic` | `2.5.2` | Data validation |
| `pydantic-core` | `2.14.5` | Pydantic core |

## Why This Works

1. **NumPy 1.24.3** is installed first and locked in place
2. **PyTorch 2.1.2** is compiled against NumPy 1.x and works perfectly with 1.24.3
3. **Plain `uvicorn`** has no compiled extensions that depend on NumPy
4. **All dependencies are pinned** to prevent pip from "upgrading" to incompatible versions
5. **Build verification** catches any NumPy 2.x leaks immediately

## Dockerfile Structure

```dockerfile
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg wget curl git postgresql-client build-essential

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

# Stage 1: NumPy 1.24.3 (MUST be first)
RUN pip install --no-cache-dir "numpy==1.24.3"

# Stage 2: PyTorch CPU-only
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Stage 3: Core dependencies
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    alembic==1.13.1 \
    sqlalchemy==2.0.23 \
    python-dotenv==1.0.0 \
    tqdm==4.66.1 \
    isodate==0.6.1 \
    psutil==5.9.6

# Stage 4: Web API (plain uvicorn, NOT [standard])
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.18 \
    aiofiles==23.2.1 \
    click==8.1.7 \
    h11==0.14.0

# Stage 5: Embeddings (all deps pinned)
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    transformers==4.36.2 \
    tokenizers==0.15.0 \
    huggingface-hub==0.19.4 \
    safetensors==0.4.1 \
    regex==2023.10.3 \
    filelock==3.13.1 \
    packaging==23.2 \
    requests==2.31.0 \
    urllib3==2.1.0 \
    certifi==2023.11.17 \
    charset-normalizer==3.3.2 \
    idna==3.6

# Stage 6: OpenAI (all deps pinned)
RUN pip install --no-cache-dir \
    openai==1.3.0 \
    anyio==3.7.1 \
    sniffio==1.3.0 \
    httpx==0.25.2 \
    httpcore==1.0.2 \
    pydantic==2.5.2 \
    pydantic-core==2.14.5 \
    typing-extensions==4.9.0 \
    distro==1.8.0

# Stage 7: VERIFY (fail build if NumPy 2.x detected)
RUN python -c "import numpy; assert numpy.__version__.startswith('1.24'), f'NumPy {numpy.__version__} detected, expected 1.24.x'"
RUN python -c "import torch; print(f'✅ PyTorch {torch.__version__}')"
RUN python -c "import numpy; print(f'✅ NumPy {numpy.__version__}')"

# Copy app code
COPY backend/ .

# Run
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## Verification

After building the Docker image:

```bash
# Check NumPy version
docker run <image> python -c "import numpy; print(numpy.__version__)"
# Expected: 1.24.3

# Check PyTorch version
docker run <image> python -c "import torch; print(torch.__version__)"
# Expected: 2.1.2+cpu

# Test sentence-transformers
docker run <image> python -c "from sentence_transformers import SentenceTransformer; print('✅ OK')"
# Expected: ✅ OK

# Test embedding generation
docker run <image> python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
emb = model.encode(['test'])
print(f'✅ Embedding shape: {emb.shape}')
"
# Expected: ✅ Embedding shape: (1, 384)
```

## Common Mistakes to Avoid

### ❌ DON'T: Use `pip install -r requirements.txt`
This will re-resolve dependencies and upgrade NumPy to 2.x.

### ❌ DON'T: Use `uvicorn[standard]`
The `[standard]` extras pull in compiled extensions with NumPy dependencies.

### ❌ DON'T: Install NumPy without pinning
`pip install numpy` will get the latest (2.x).

### ❌ DON'T: Use version ranges
`numpy>=1.24` will upgrade to 2.x. Use exact pins: `numpy==1.24.3`.

### ❌ DON'T: Skip transitive dependencies
Pin everything, not just top-level packages.

## Alternative: Upgrade to PyTorch 2.5.x + NumPy 2.x

If you want to use NumPy 2.x, you need to upgrade the entire stack:

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

**Trade-offs:**
- ✅ Latest features
- ✅ NumPy 2.x compatibility
- ❌ Larger image size
- ❌ Potential compatibility issues with older code
- ❌ Less tested in production

**Recommendation:** Stick with NumPy 1.24.3 + PyTorch 2.1.2 for production stability.

## Expected Logs (Success)

When the fix is applied, you should see:

```
INFO:     Started server process [7]
INFO:     Waiting for application startup.
2025-11-23 17:11:47 - INFO - 🚀 Warming up embedding model on startup...
2025-11-23 17:11:47 - INFO - Embedding provider: sentence-transformers
2025-11-23 17:11:47 - INFO - Model: BAAI/bge-small-en-v1.5
2025-11-23 17:11:47 - INFO - Dimensions: 384
2025-11-23 17:11:48 - INFO - Loading local embedding model: BAAI/bge-small-en-v1.5 on cpu
2025-11-23 17:11:52 - INFO - ✅ Embedding model warmed up successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Health check:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "ok",
  "service": "Ask Dr. Chaffee API",
  "timestamp": "2025-11-23T17:12:00Z",
  "checks": {
    "database": "ok",
    "embeddings": "ok"
  }
}
```

## Files Modified

1. **`Dockerfile`** - Enforced correct installation order, removed `[standard]` from uvicorn, added verification
2. **`backend/requirements-production.txt`** - Documented dependency matrix, pinned all transitive deps

## References

- PyTorch NumPy compatibility: https://github.com/pytorch/pytorch/issues/91516
- sentence-transformers compatibility: https://github.com/UKPLab/sentence-transformers/issues/1762
- NumPy 2.0 migration guide: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
- uvicorn docs: https://www.uvicorn.org/#quickstart

## Summary

**Root cause:** `uvicorn[standard]` pulled in NumPy 2.x via compiled C extensions.

**Fix:** Use plain `uvicorn` (no `[standard]`), enforce installation order, pin all dependencies.

**Result:** NumPy 1.24.3 + PyTorch 2.1.2 + sentence-transformers 2.2.2 = ✅ Working embeddings!
