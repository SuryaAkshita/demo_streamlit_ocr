# backend/main.py

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import requests
from backend.inference import load_context, clear_gpu, ModelNotLoadedError
from backend.pdf_extract import extract_pdf_multi


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Loads the model ONCE at startup (AWS GPU), unless DISABLE_MODEL_LOAD=1.
    FastAPI lifespan runs startup/shutdown logic exactly once for the application lifetime. [1](https://dev.to/ikoh_sylva/aws-security-groups-for-ec2-instances-a-comprehensive-guide-4fp9)
    """
    disable = os.getenv("DISABLE_MODEL_LOAD", "0") == "1"

    if disable:
        app.state.model_loaded = False
        yield
        return

    # ✅ Force model load at startup (not first request)
    try:
        load_context()
        app.state.model_loaded = True
        print("✅ Model loaded at startup (lifespan).")
    except Exception as e:
        app.state.model_loaded = False
        print(f"❌ Model failed to load at startup: {e}")
        # You can choose to raise here to fail fast:
        # raise

    yield

    # Shutdown cleanup
    try:
        clear_gpu()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)

# CORS (your original settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok", "message": "Backend running ✅"}


@app.get("/health")
def detailed_health(request: Request):
    """
    Returns whether model is loaded. Useful for AWS readiness checks.
    """
    return {
        "status": "ok",
        "model_loaded": bool(getattr(request.app.state, "model_loaded", False)),
        "disable_model_load": os.getenv("DISABLE_MODEL_LOAD", "0") == "1"
    }


@app.post("/run-ocr")
async def run_ocr(
    file: UploadFile = File(...),
    start_page: int = Query(1, ge=1, description="Starting page number (default: 1)"),
    end_page: int = Query(None, ge=1, description="Ending page number (None = all pages)")
):
    """
    Runs InternVL OCR extraction.
    If REMOTE_OCR_URL is set and DISABLE_MODEL_LOAD=1, proxies to remote GPU instance.
    """
    # 1. Check if we should proxy to AWS
    remote_url = os.getenv("REMOTE_OCR_URL")
    disable_local = os.getenv("DISABLE_MODEL_LOAD", "0") == "1"

    if disable_local and remote_url:
        print(f"📡 Proxying OCR request to remote AWS GPU: {remote_url}")
        try:
            # Prepare data and files for remote request
            pdf_bytes = await file.read()
            remote_params = {"start_page": start_page, "end_page": end_page}
            remote_files = {"file": (file.filename, pdf_bytes, file.content_type)}

            # Forward the request (note: timeout increased for OCR)
            response = requests.post(
                f"{remote_url.rstrip('/')}/run-ocr",
                params=remote_params,
                files=remote_files,
                timeout=600
            )

            # Return the remote response
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"status": "error", "message": f"Proxy failed: {str(e)}", "hint": "Check if AWS instance is running and accessible."}
            )

    # 2. Local/Standard processing
    try:
        pdf_bytes = await file.read()

        # Wrap bytes like your previous DummyUpload (keeps extract_pdf_multi unchanged)
        class DummyUpload:
            def __init__(self, b: bytes, name: str = "file.pdf"):
                self._bytes = b
                self.name = name

            def getvalue(self):
                return self._bytes

        pdf_file = DummyUpload(pdf_bytes, name=file.filename)

        # ✅ Call your actual extraction pipeline
        result = extract_pdf_multi(
            pdf_file,
            pdf_filename=file.filename,
            start_page=start_page,
            end_page=end_page
        )

        return JSONResponse(content=result)

    except ModelNotLoadedError as e:
        # Happens on office laptop when DISABLE_MODEL_LOAD=1
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e),
                "hint": "On AWS GPU set DISABLE_MODEL_LOAD=0 (or unset it)."
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )