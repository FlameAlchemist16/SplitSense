import os
from paddleocr import PaddleOCR
from dotenv import load_dotenv
from agent.prompts import BILL_PARSER_SYSTEM_PROMPT
import anthropic
import json

load_dotenv()

# fetching environment variable for OCR, LLM model
OCR_MODEL = os.getenv("OCR_MODEL")
HAIKU_LLM_MODEL = os.getenv("LLM_MODEL")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# creating ocr instance
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    ocr_version=OCR_MODEL,
    det_limit_side_len=1216
)

# creating anthropic instance
haiku_client = anthropic.Anthropic(
    api_key= ANTHROPIC_API_KEY
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
        raise ValueError(f"Empty output for texts returned from OCR after reading the bill.")
    
    if not rec_scores:
        raise ValueError(f"Empty output for scores returned from OCR after reading the bill.")
    
    confidence_threshold = round(sum(rec_scores)/len(rec_scores),2)
    min_confidence_score = round(min(rec_scores),2)
    extract_text = ""

    for text, score in zip(rec_texts, rec_scores):
        extract_text += f"{text}({round(score,2)}) "

    final_output = {
        "text": extract_text,
        "low_confidence_detected": min_confidence_score < confidence_threshold,
        "confidence_threshold": confidence_threshold
    }

    return final_output

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
        model=HAIKU_LLM_MODEL,
        system=BILL_PARSER_SYSTEM_PROMPT,
        max_tokens=5000,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    haiku_string = haiku_response.content[0].text

    haiku_string = haiku_string.strip()

    if "```" in haiku_string:
        haiku_string = haiku_string.split("```")[1]

        if haiku_string.startswith("json"):
            haiku_string = haiku_string[4:]
        
        haiku_string = haiku_string.strip()

    try:
        haiku_dict = json.loads(haiku_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Haiku returned invalid JSON: {e}\nRaw response: {haiku_string}")
    
    return haiku_dict