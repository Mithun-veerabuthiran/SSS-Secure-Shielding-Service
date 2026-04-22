import requests
import json
import time

BASE_URL = "http://localhost:5000"

def run_test(name, func):
    print(f"\n[{'RUNNING':^10}] {name}")
    try:
        ts = time.time()
        result, details = func()
        te = time.time()
        elapsed = te - ts
        if result:
            print(f"[{'PASSED':^10}] {name} ({elapsed:.3f}s)")
        else:
            print(f"[{'FAILED':^10}] {name} ({elapsed:.3f}s) - {details}")
    except Exception as e:
        print(f"[{'ERROR':^10}] {name} - Exception: {e}")

def test_health():
    res = requests.get(f"{BASE_URL}/health")
    if res.status_code == 200 and res.json() == {"status": "ok"}:
        return True, ""
    return False, f"Status: {res.status_code}, Body: {res.text}"

def test_config_missing_payload():
    res = requests.post(f"{BASE_URL}/config", json={})
    if res.status_code == 400 and "No configuration provided" in res.text:
        return True, ""
    return False, f"Expected 400 No config provided. Got {res.status_code}: {res.text}"

def test_config_invalid_payload():
    res = requests.post(f"{BASE_URL}/config", json={"sites": ["Chatgpt"]})
    if res.status_code == 400 and "Invalid configuration" in res.text:
        return True, ""
    return False, f"Expected 400 Invalid config. Got {res.status_code}: {res.text}"

def test_config_valid_payload():
    payload = {
        "sites": ["Chatgpt"],
        "models": ["Presidio"],
        "methods": ["Pseudonymization"],
        "piis": ["Names", "Emails", "Phone Numbers", "Addresses", "SSN", "Aadhaar", "Account Numbers"]
    }
    res = requests.post(f"{BASE_URL}/config", json=payload)
    if res.status_code == 200 and "status" in res.json():
        return True, ""
    return False, f"Expected 200 OK. Got {res.status_code}: {res.text}"

def test_anonymize_missing_text():
    res = requests.post(f"{BASE_URL}/anonymize", json={"url": "https://chatgpt.com/c/123"})
    if res.status_code == 400 and "No text provided" in res.text:
        return True, ""
    return False, f"Expected 400 No text provided. Got {res.status_code}: {res.text}"

def test_anonymize_basic_pii():
    payload = {
        "text": "My email is test@example.com and phone is 555-123-4567. My Aadhaar is 1234 5678 9012.",
        "url": "https://chatgpt.com/c/test-basic"
    }
    res = requests.post(f"{BASE_URL}/anonymize", json=payload)
    if res.status_code != 200:
        return False, f"Status: {res.status_code}"
    
    data = res.json()
    anon_text = data.get("anonymized_text", "")
    mapping = data.get("mapping", {})
    
    # Check if original values are in the text
    if "test@example.com" in anon_text or "555-123-4567" in anon_text or "1234 5678 9012" in anon_text:
        return False, f"PII leak detected! Cleaned text: {anon_text}"
        
    return True, f"Mapping created: {len(mapping)} items"

def test_anonymize_massive_payload():
    payload = {
        "text": "Hello world " * 5000, # Large payload
        "url": "https://chatgpt.com/c/test-massive"
    }
    res = requests.post(f"{BASE_URL}/anonymize", json=payload)
    if res.status_code == 200:
        return True, ""
    return False, f"Failed on massive payload. Code {res.status_code}"

def test_anonymize_overlapping_entities():
    # RoBERTa might flag "John Doe's Company" and regex might flag something inside
    payload = {
        "text": "My son John Doe was born in New York. Contact via john.doe@newyork.com",
        "url": "https://chatgpt.com/c/test-overlap"
    }
    res = requests.post(f"{BASE_URL}/anonymize", json=payload)
    if res.status_code == 200:
        return True, f"Cleaned: {res.json().get('anonymized_text')[:50]}..."
    return False, f"Status error: {res.status_code}"

def test_deanonymize_missing_url():
    # Get mappings generically
    text_to_deanonymize = "I live in New York"
    # we need the system to have a mapping for generic if no URL passed or to gracefully fail
    res = requests.post(f"{BASE_URL}/deanonymize", json={"text": "Hello mapping test"})
    if res.status_code == 200 or res.status_code == 404:
        return True, "Handled missing url properly"
    return False, f"Unexpected code: {res.status_code}"

def test_deanonymize_invalid_url():
    res = requests.post(f"{BASE_URL}/deanonymize", json={"text": "text", "url": "https://invalid.com/123"})
    if res.status_code == 404 or res.status_code == 200: # Depending on fallback logic
        return True, ""
    return False, f"Failed invalid url test: {res.status_code}"

def test_xss_injection():
    xss_payload = "<script>alert('xss')</script> John Doe 555-123-4567"
    payload = {
        "text": xss_payload,
        "url": "https://chatgpt.com/c/test-xss"
    }
    res = requests.post(f"{BASE_URL}/anonymize", json=payload)
    if res.status_code == 200:
         return True, "Handled HTML gracefully"
    return False, f"Failed XSS test: {res.status_code}"

if __name__ == "__main__":
    print("--- SSS BACKEND QA TEST SUITE ---")
    run_test("Health Check", test_health)
    run_test("Config Missing Payload", test_config_missing_payload)
    run_test("Config Invalid Payload", test_config_invalid_payload)
    run_test("Config Valid Payload", test_config_valid_payload)
    run_test("Anonymize Missing Text", test_anonymize_missing_text)
    run_test("Anonymize Basic PII", test_anonymize_basic_pii)
    run_test("Anonymize Massive Payload", test_anonymize_massive_payload)
    run_test("Anonymize Overlapping", test_anonymize_overlapping_entities)
    run_test("Deanonymize Missing URL", test_deanonymize_missing_url)
    run_test("Deanonymize Invalid URL", test_deanonymize_invalid_url)
    run_test("HTML/XSS Injection Handling", test_xss_injection)
    print("\n--- TEST SUITE COMPLETE ---")
