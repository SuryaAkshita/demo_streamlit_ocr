# backend/inference.py

# ============================================
# 🔥 CRITICAL: SET ENV BEFORE ANY IMPORTS
# ============================================
import os

# os.environ["TRANSFORMERS_NO_META"] = "1"  # Disable if causing issues
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"
os.environ["INTERNVL_USE_FLASH_ATTN"] = "0"

import gc
import torch
from transformers import AutoTokenizer, AutoModel, BitsAndBytesConfig
from backend.prompts import METADATA_PROMPT, EXTRACTION_PROMPT
from backend.utils import try_parse_json_strict


MODEL_PATH = "OpenGVLab/InternVL2_5-4B-MPO"

# ✅ OPTIMIZED: Increased from 768 to 900 for better field coverage
generation_config = dict(
    max_new_tokens=900,
    do_sample=False,
    temperature=0.0  # deterministic output
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8) else torch.float16

# Enable performance optimizations
torch.backends.cudnn.benchmark = True
if hasattr(torch, "set_float32_matmul_precision"):
    torch.set_float32_matmul_precision("medium")

# Enable TF32 for extra speed on compatible GPUs
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class ModelNotLoadedError(RuntimeError):
    pass


class InferenceContext:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer


_CTX = None


def load_context() -> InferenceContext:
    """
    Loads tokenizer + model exactly like your code.
    Called once, then cached.
    """
    global _CTX

    disable = os.getenv("DISABLE_MODEL_LOAD", "0") == "1"
    if disable:
        raise ModelNotLoadedError("Model loading disabled (DISABLE_MODEL_LOAD=1).")

    if _CTX is not None:
        return _CTX

    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

    print("Loading model...")

    try:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=DTYPE,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )

        model = AutoModel.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            torch_dtype=DTYPE,
            quantization_config=quantization_config,
            use_flash_attn=False,
            device_map="auto"  # Crucial for bitsandbytes
        ).eval()

        print("✅ Model loaded with 4-bit quantization")

    except Exception as e:
        print(f"⚠️ 4-bit loading failed: {e}")
        print("Trying fallback: loading in bfloat16/float16...")

        model = AutoModel.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
            torch_dtype=DTYPE,
            use_flash_attn=False
        ).to(DEVICE).eval()

        print("✅ Model loaded in bfloat16/float16 (no quantization)")

    print(f"✅ Using device: {DEVICE}")
    print(f"✅ Model is on: {next(model.parameters()).device}")
    if torch.cuda.is_available():
        print(f"✅ GPU name: {torch.cuda.get_device_name(0)}")
        print(f"✅ GPU memory allocated: {torch.cuda.memory_allocated(0)/1024**3:.2f} GB")

    _CTX = InferenceContext(model=model, tokenizer=tokenizer)
    return _CTX


def get_context() -> InferenceContext:
    """
    Safe accessor.
    """
    return load_context()


def internvl_chat(image_pixels, prompt: str) -> str:
    """
    Your exact internvl_chat logic, except model/tokenizer come from cached context.
    """
    ctx = get_context()
    model = ctx.model
    tokenizer = ctx.tokenizer

    try:
        with torch.no_grad():
            out, hist = model.chat(
                tokenizer,
                image_pixels,
                prompt,
                generation_config,
                history=None,
                return_history=True
            )
        return out
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Inference failed on page: {e}")
        raise e


def ai_analysis(image_pixels, prompt: str):
    """
    Your exact ai_analysis logic.
    """
    resp = internvl_chat(image_pixels, prompt)
    if not resp:
        return None, None
    parsed, is_json = try_parse_json_strict(resp)
    if is_json:
        return parsed, None
    return None, resp


def clear_gpu():
    """
    Helper to clear GPU memory if needed.
    """
    global _CTX
    _CTX = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()