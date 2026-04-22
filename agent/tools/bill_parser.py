from paddleocr import PaddleOCR
from dotenv import load_dotenv
import os

load_dotenv()

# fetching environment variable for OCR model
OCR_MODEL = os.getenv("OCR_MODEL")

# creating ocr instance
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    ocr_version=OCR_MODEL,
    det_limit_side_len=1216
)

def extract_text_from_image(image_path: str) -> dict:
    if image_path == "":
        raise ValueError(f"Image path is empty.")
    
    if not image_path.lower().endswith((".png",".jpeg","jpg")):
        raise ValueError(f"Invalide bill file extension. Please use (.png, .jpeg, .jpg) file formats only.")
    
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No bill file exists on the image path provided: {image_path}")
    
    output = ocr.predict(image_path)

    rec_texts = output[0]["rec_texts"]
    rec_scores = output[0]["rec_scores"]

    if not rec_texts:
        raise ValueError(f"Empty output returned from OCR after reading the bill.")
    
    min_confidence_score = round(min(rec_scores),2)
    extract_text = ""

    for items in rec_texts:
        extract_text += items + "\n"

    final_output = {
        "text": extract_text,
        "low_confidence_detected": True if min_confidence_score < 0.6 else False,
        "min_confidence": min_confidence_score
    }

    return final_output