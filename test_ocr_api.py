import requests

def test_ocr():
    print("Testing OCR.space API...")
    try:
        # Create a dummy image with text just to test the endpoint
        from PIL import Image, ImageDraw, ImageFont
        import io
        img = Image.new('RGB', (200, 100), color = (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10,10), "Aadhaar: 1234 5678 9012", fill=(0,0,0))
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        
        payload = {
            'isOverlayRequired': False,
            'apikey': 'helloworld',
            'language': 'eng',
        }
        res = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': ('image.jpg', img_bytes, 'image/jpeg')},
            data=payload,
            timeout=10
        )
        print("Status code:", res.status_code)
        print("Response:", res.json())
    except Exception as e:
        print("Error:", e)

test_ocr()
