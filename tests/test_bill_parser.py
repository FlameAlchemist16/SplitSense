import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.tools.bill_parser import extract_text_from_image, structure_bill_with_llm

image_path = "D:/splitsense/agent/tools/bill_1.png"  # use one of your test bills

ocr_output = extract_text_from_image(image_path)
print("=== OCR OUTPUT ===")
print(ocr_output)

structured = structure_bill_with_llm(ocr_output)
print("\n=== STRUCTURED OUTPUT ===")
print(structured)