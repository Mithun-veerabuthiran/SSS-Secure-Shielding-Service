import requests
import time
import json
from faker import Faker

fake = Faker()

# Configuration
BASE_URL = "http://127.0.0.1:5000"
NUM_RECORDS = 1000

def generate_test_data(num_records):
    print(f"Generating {num_records} records of test data...")
    records = []
    for _ in range(num_records):
        # Create a sentence with some PII
        name = fake.name()
        email = fake.email()
        phone = fake.phone_number()
        
        sentence = f"User {name} can be contacted at {email} or by phone at {phone}."
        records.append(sentence)
    
    # Join into one large text block
    full_text = "\n".join(records)
    print(f"Generated text length: {len(full_text)} characters")
    return full_text, records

def run_test():
    full_text, original_records = generate_test_data(NUM_RECORDS)
    
    import uuid
    test_session_id = str(uuid.uuid4())
    test_url = f"https://chatgpt.com/c/test-1000-records-{test_session_id}"
    
    # Test 1: Anonymization
    print("\n--- Testing Anonymization ---")
    anonymize_payload = {
        "text": full_text,
        "url": test_url,
        "anonymization_method": "fake"
    }
    
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/anonymize", json=anonymize_payload)
        response.raise_for_status()
        anonymized_data = response.json()
        anonymize_time = time.time() - start_time
        
        print(f"Anonymization successful!")
        print(f"Time taken: {anonymize_time:.2f} seconds")
        print(f"Anonymized text preview: {anonymized_data.get('anonymized_text', '')[:200]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"Anonymization failed: {e}")
        return

    # Test 2: De-anonymization
    print("\n--- Testing De-anonymization ---")
    deanonymize_payload = {
        "text": anonymized_data.get("anonymized_text", ""),
        "url": test_url
    }
    
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/deanonymize", json=deanonymize_payload)
        response.raise_for_status()
        deanonymized_data = response.json()
        deanonymize_time = time.time() - start_time
        
        deanonymized_text = deanonymized_data.get("deanonymized_text", "")
        
        print(f"De-anonymization successful!")
        print(f"Time taken: {deanonymize_time:.2f} seconds")
        print(f"De-anonymized text preview: {deanonymized_text[:200]}...")
        
        # Verify correctness
        print("\n--- Verification ---")
        if deanonymized_text == full_text:
            print("SUCCESS: De-anonymized text perfectly matches the original text!")
        else:
            print("WARNING: De-anonymized text does NOT match the original text.")
            print(f"Original length: {len(full_text)}")
            print(f"Restored length: {len(deanonymized_text)}")
            
            # Simple diff
            min_len = min(len(full_text), len(deanonymized_text))
            for i in range(min_len):
                if full_text[i] != deanonymized_text[i]:
                    print(f"First difference at index {i}:")
                    print(f"Original: '{full_text[max(0, i-20):i+20]}'")
                    print(f"Restored: '{deanonymized_text[max(0, i-20):i+20]}'")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"De-anonymization failed: {e}")

if __name__ == "__main__":
    # Ensure backend is running before testing
    try:
        health_check = requests.get(f"{BASE_URL}/health")
        if health_check.status_code == 200:
            run_test()
        else:
            print("Backend health check failed. Is the Flask server fully started?")
    except requests.exceptions.ConnectionError:
        print("Could not connect to backend. Please ensure flaskBackend.py is running on port 5000.")
