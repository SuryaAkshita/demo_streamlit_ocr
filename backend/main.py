from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  PUT YOUR NGROK LINK HERE (BASE URL ONLY)
COLAB_URL = "https://25372d7175d3.ngrok-free.app"

@app.get("/")
def health():
    return {"status": "ok", "message": "Backend running smoothly."}

@app.post("/run-ocr")
async def run_ocr(
    file: UploadFile = File(...),
    start_page: int = Query(1, ge=1, description="Starting page number (default: 1)"),
    end_page: int = Query(None, ge=1, description="Ending page number (None = all pages)")
):
    """
    ✅ UPDATED: Now supports page range parameters
    
    Examples:
        POST /run-ocr (all pages)
        POST /run-ocr?start_page=1&end_page=5 (pages 1-5)
        POST /run-ocr?start_page=3&end_page=7 (pages 3-7)
    """
    try:
        pdf_bytes = await file.read()

        # ✅ NEW: Pass page range parameters to Colab
        params = {
            "start_page": start_page,
        }
        if end_page is not None:
            params["end_page"] = end_page

        r = requests.post(
            f"{COLAB_URL}/extract_pdf",
            files={"file": (file.filename, pdf_bytes, "application/pdf")},
            params=params,  # ✅ NEW: Send page range params
            timeout=600
        )

        if r.status_code != 200:
            return {
                "status": "error",
                "colab_status": r.status_code,
                "colab_response": r.text
            }

        return r.json()

    except requests.exceptions.Timeout:
        return {
            "status": "error", 
            "message": "Request timed out. PDF may be too large or Colab is slow."
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Cannot connect to Colab. Check if ngrok URL is correct and Colab is running."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ✅ OPTIONAL: Add endpoint to test Colab connection
@app.get("/test-colab")
def test_colab():
    """Test if Colab backend is reachable"""
    try:
        r = requests.get(f"{COLAB_URL}/", timeout=10)
        return {
            "status": "connected",
            "colab_response": r.json(),
            "colab_url": COLAB_URL
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "colab_url": COLAB_URL
        }