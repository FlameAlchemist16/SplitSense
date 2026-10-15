import os

from dotenv import load_dotenv
from paddleocr import PaddleOCR

from agent.llm_client import LLM_MODEL, haiku_client, parse_llm_json
from agent.prompts import BILL_PARSER_SYSTEM_PROMPT

load_dotenv()

OCR_MODEL = os.getenv("OCR_MODEL")
_ocr = None


def get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        kwargs = {
            "use_angle_cls": False,
            "lang": "en",
            "det_limit_side_len": 1216,
            "det_db_box_thresh": 0.5,
            "det_db_unclip_ratio": 1.5,
            "rec_batch_num": 16,
        }
        if OCR_MODEL:
            kwargs["ocr_version"] = OCR_MODEL
        _ocr = PaddleOCR(**kwargs)
    return _ocr


def extract_text_from_image(image_path: str) -> dict:
    if image_path == "":
        raise ValueError("Image path is empty.")

    if not image_path.lower().endswith((".png", ".jpeg", ".jpg")):
        raise ValueError(
            "Invalid bill file extension. Please use (.png, .jpeg, .jpg) file formats only."
        )

    if not os.path.exists(image_path):
        raise FileNotFoundError(
            f"No bill file exists on the image path provided: {image_path}"
        )

    output = get_ocr().predict(image_path)
    rec_texts = output[0]["rec_texts"]
    rec_scores = output[0]["rec_scores"]

    if not rec_texts:
        raise ValueError("Empty output for texts returned from OCR after reading the bill.")

    if not rec_scores:
        raise ValueError("Empty output for scores returned from OCR after reading the bill.")

    confidence_threshold = round(sum(rec_scores) / len(rec_scores), 2)
    min_confidence_score = round(min(rec_scores), 2)
    extract_text = ""

    for text, score in zip(rec_texts, rec_scores):
        extract_text += f"{text}({round(score, 2)}) "

    return {
        "text": extract_text,
        "low_confidence_detected": min_confidence_score < confidence_threshold,
        "confidence_threshold": confidence_threshold,
    }


def structure_bill_with_llm(ocr_output: dict) -> dict:
    text = ocr_output.get("text")
    low_confidence_detected = ocr_output.get("low_confidence_detected")
    confidence_threshold = ocr_output.get("confidence_threshold")

    user_prompt = f"""
    The OCR ouput received is as follows:
    
    OCR TEXT:
    {text}

    LOW_CONFIDENCE_DETECTED:
    {low_confidence_detected}

    CONFIDENCE_THRESHOLD:
    {confidence_threshold}
    """
    haiku_response = haiku_client.messages.create(
        model=LLM_MODEL,
        system=BILL_PARSER_SYSTEM_PROMPT,
        max_tokens=5000,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return parse_llm_json(haiku_response.content[0].text)


def parse_bill(image_path: str) -> dict:
    return structure_bill_with_llm(extract_text_from_image(image_path))
