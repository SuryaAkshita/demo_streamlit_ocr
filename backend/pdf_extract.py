# backend/pdf_extract.py

import gc
import re
import time
from datetime import datetime
from queue import Queue
from threading import Thread
import os
import torch
from PIL import Image
from pdf2image import convert_from_bytes
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from tqdm import tqdm

from backend.inference import DEVICE, DTYPE, ai_analysis
from backend.prompts import EXTRACTION_PROMPT, METADATA_PROMPT
from backend.utils import normalize_extracted_data, save_json, pretty_console


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

POPPLER_PATH = os.getenv("POPPLER_PATH")
def build_transform(input_size):
    return T.Compose([
        T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])


def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_diff = float("inf")
    best = (1, 1)
    for r in target_ratios:
        diff = abs(aspect_ratio - (r[0] / r[1]))
        if diff < best_diff:
            best_diff = diff
            best = r
    return best


# ✅ OPTIMIZED: Pre-calculate for max_num up to 12 (balanced quality/speed)
TARGET_RATIOS_6 = sorted(
    {(i, j) for n in range(1, 7)
     for i in range(1, n + 1) for j in range(1, n + 1)
     if 1 <= i * j <= 6},
    key=lambda x: x[0] * x[1]
)

TARGET_RATIOS_12 = sorted(
    {(i, j) for n in range(1, 13)
     for i in range(1, n + 1) for j in range(1, n + 1)
     if 1 <= i * j <= 12},
    key=lambda x: x[0] * x[1]
)


def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=True):
    """✅ OPTIMIZED: Default max_num=12 for better quality"""
    ow, oh = image.size
    aspect_ratio = ow / oh

    # Use pre-calculated ratios for common values
    if max_num == 6:
        target_ratios = TARGET_RATIOS_6
    elif max_num == 12:
        target_ratios = TARGET_RATIOS_12
    else:
        target_ratios = sorted(
            {(i, j) for n in range(min_num, max_num + 1)
             for i in range(1, n + 1) for j in range(1, n + 1)
             if 1 <= i * j <= max_num},
            key=lambda x: x[0] * x[1]
        )

    best = find_closest_aspect_ratio(aspect_ratio, target_ratios, ow, oh, image_size)
    tw, th = image_size * best[0], image_size * best[1]
    blocks = best[0] * best[1]

    resized = image.resize((tw, th))
    crops = []
    for i in range(blocks):
        box = (
            (i % (tw // image_size)) * image_size,
            (i // (tw // image_size)) * image_size,
            ((i % (tw // image_size)) + 1) * image_size,
            ((i // (tw // image_size)) + 1) * image_size
        )
        crops.append(resized.crop(box))

    if use_thumbnail and len(crops) != 1:
        crops.append(image.resize((image_size, image_size)))

    return crops


def load_image(image, input_size=448, max_num=12, use_thumbnail=True):
    """✅ OPTIMIZED: Default max_num=12 for balanced quality/speed"""
    if not isinstance(image, Image.Image):
        image = Image.open(image).convert("RGB")
    else:
        if image.mode != "RGB":
            image = image.convert("RGB")

    transform = build_transform(input_size)
    chunks = dynamic_preprocess(image, image_size=input_size, max_num=max_num, use_thumbnail=use_thumbnail)
    px = torch.stack([transform(c) for c in chunks])
    return px


def process_single_page(image_pil, prompt, max_num=12):
    """✅ OPTIMIZED: Default max_num=12 with fallback to 6 if OOM"""
    try:
        pv = load_image(image_pil, input_size=448, max_num=max_num, use_thumbnail=True)
        pv = pv.to(dtype=DTYPE, device=DEVICE)
        parsed, raw = ai_analysis(pv, prompt)
        parsed = normalize_extracted_data(parsed)
        return {"status": "success", "data": parsed}

    except RuntimeError as e:
        if "CUDA" in str(e) or "out of memory" in str(e).lower():
            torch.cuda.empty_cache()
            gc.collect()
            # Fallback to fewer tiles
            pv = load_image(image_pil, input_size=448, max_num=6, use_thumbnail=True)
            pv = pv.to(dtype=DTYPE, device=DEVICE)
            parsed, raw = ai_analysis(pv, prompt)
            parsed = normalize_extracted_data(parsed)
            return {"status": "success_fallback", "data": parsed}

        return {"status": "error", "data": {"section": "ERROR", "error_message": str(e)}}

    except Exception as e:
        return {"status": "error", "data": {"section": "ERROR", "error_message": str(e)}}


def extract_pdf_multi(
    pdf_file,
    pdf_filename="unknown",
    start_page=1,
    end_page=None,  # ✅ NEW: Use end_page instead of max_pages
    prompt=EXTRACTION_PROMPT,
    batch_size=1
):
    """
    ✅ OPTIMIZED: Now supports flexible page ranges

    Args:
        pdf_file: PDF file object with getvalue() method
        pdf_filename: Name of the PDF file
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (1-indexed, None = all pages)
        prompt: Extraction prompt
        batch_size: Always 1 for sequential processing

    Examples:
        extract_pdf_multi(pdf, start_page=1, end_page=5)  # Pages 1-5
        extract_pdf_multi(pdf, start_page=3, end_page=7)  # Pages 3-7
        extract_pdf_multi(pdf, start_page=1, end_page=None)  # All pages
    """
    t0 = time.time()

    # Calculate page range for conversion
    first_p = start_page
    last_p = end_page

    # ✅ OPTIMIZED: DPI=250 (balanced quality/speed, faster than 300)
    images = convert_from_bytes(
        pdf_file.getvalue(),
        dpi=250,  # Increased from 200 for better OCR
        first_page=first_p,
        last_page=last_p,
        thread_count=4,
        fmt="png",
        grayscale=False,
        size=None,
        poppler_path=POPPLER_PATH
    )

    total = len(images)
    pages = images

    print(f"📄 PDF converted: {total} pages (Range: {first_p} to {last_p or 'end'})")

    # Process metadata from first page
    print("📋 Extracting metadata...")
    metadata_start = time.time()
    first_page_img = images[0]
    metadata_res = process_single_page(first_page_img, METADATA_PROMPT, max_num=12)
    metadata = metadata_res["data"]
    metadata_time = time.time() - metadata_start
    print(f"✅ Metadata extracted in {metadata_time:.2f}s")

    doc_type = metadata.get("document_type") or "unknown"
    envelope_id = metadata.get("envelope_id")
    total_pages_in_doc = metadata.get("total_pages_in_doc")

    if total_pages_in_doc and isinstance(total_pages_in_doc, str):
        try:
            # Extract number from "Page 1 of 10" format
            match = re.search(r"(\d+)$", total_pages_in_doc)
            if match:
                total_pages_in_doc = int(match.group(1))
            else:
                total_pages_in_doc = int(total_pages_in_doc)
        except Exception:
            total_pages_in_doc = total

    page_results = []

    print(f"🚀 Processing {len(pages)} pages...")

    # ✅ OPTIMIZED: Pipelined preprocessing with Queue
    preprocessed_queue = Queue(maxsize=2)

    def preprocessor_worker():
        for page_idx, img in enumerate(pages, start=start_page):
            try:
                # Preprocess with max_num=12 for quality
                pv = load_image(img, input_size=448, max_num=12, use_thumbnail=True)
                pv = pv.to(dtype=DTYPE, device=DEVICE, non_blocking=True)
                preprocessed_queue.put((page_idx, pv))
            except Exception as e:
                print(f"⚠ Preprocessor error page {page_idx}: {e}")
                preprocessed_queue.put((page_idx, None))

    # Start preprocessor thread
    prepro_thread = Thread(target=preprocessor_worker, daemon=True)
    prepro_thread.start()

    # Process pages sequentially for GPU efficiency
    with tqdm(total=len(pages), desc="Extracting", unit="pg") as pbar:
        for _ in range(len(pages)):
            page_start = time.time()
            inference_time = 0.0

            page_idx, pv = preprocessed_queue.get()

            if pv is None:
                page_data = {
                    "page": page_idx,
                    "section": "ERROR",
                    "error_message": "Preprocessing failed"
                }
            else:
                try:
                    inference_start = time.time()
                    parsed, raw = ai_analysis(pv, prompt)
                    inference_time = time.time() - inference_start

                    if parsed is None:
                        page_data = {
                            "page": page_idx,
                            "section": "ERROR",
                            "error_message": f"Invalid JSON. Raw: {raw[:200] if raw else 'None'}"
                        }
                    else:
                        parsed = normalize_extracted_data(parsed)

                        page_data = {
                            "page": page_idx,
                            "section": parsed.get("section", "UNKNOWN SECTION")
                        }
                        for key, value in parsed.items():
                            if key != "section" and value:
                                page_data[key] = value

                except Exception as e:
                    print(f"❌ Error page {page_idx}: {e}")
                    page_data = {
                        "page": page_idx,
                        "section": "ERROR",
                        "error_message": str(e)
                    }

            page_results.append(page_data)

            page_time = time.time() - page_start
            pbar.set_postfix({"inf": f"{inference_time:.1f}s", "tot": f"{page_time:.1f}s"})
            pbar.update(1)

    page_results.sort(key=lambda x: x["page"])

    final = {
        "document": {
            "file_name": pdf_filename,
            "document_type": doc_type,
            "extracted_at": datetime.now().isoformat(),
            "total_pages_from_document": total_pages_in_doc or total,
            "pages_processed": len(page_results),
            "page_range": f"{start_page}-{end_page or 'end'}"
        },
        "pages": page_results
    }

    if envelope_id:
        final["document"]["envelope_id"] = envelope_id

    processing_time = round(time.time() - t0, 2)
    print("\n✅ EXTRACTION COMPLETE")
    print(f"📊 Processed {len(page_results)} pages in {processing_time}s")
    print(f"⏱ Average: {round(processing_time/len(page_results), 2)}s/page")

    save_json("structured_output.json", final)
    print("💾 Saved: structured_output.json")

    pretty_console(final, max_chars=2000)
    return final