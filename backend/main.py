from fastapi import FastAPI, UploadFile, File
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

# ✅ PUT YOUR NGROK LINK HERE (BASE URL ONLY)
COLAB_URL = "https://94b825ea7c74.ngrok-free.app"

@app.get("/")
def health():
    return {"status": "ok", "message": "Backend running ✅"}

@app.post("/run-ocr")
async def run_ocr(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()

        r = requests.post(
            f"{COLAB_URL}/extract_pdf",
            files={"file": (file.filename, pdf_bytes, "application/pdf")},
            timeout=600
        )

        if r.status_code != 200:
            return {
                "status": "error",
                "colab_status": r.status_code,
                "colab_response": r.text
            }

        return r.json()

    except Exception as e:
        return {"status": "error", "message": str(e)}
