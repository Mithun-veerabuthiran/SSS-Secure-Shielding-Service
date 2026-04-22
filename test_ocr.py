import torch
import easyocr
import time

try:
    print("Testing EasyOCR initialization...")
    start = time.time()
    # Initialize the OCR reader (enables GPU if available)
    reader = easyocr.Reader(['en'])
    print(f"Model loaded in {time.time() - start:.2f} seconds.")
    
    # We will test an image containing text to confirm it reads accurately
    print("Please provide an image named 'test_id.png' in this directory to test text extraction.")
except Exception as e:
    print(f"Error initializing EasyOCR: {e}")
