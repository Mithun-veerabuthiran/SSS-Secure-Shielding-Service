import requests
import time
from faker import Faker

fake = Faker()
BASE_URL = "http://127.0.0.1:5000"
NUM_RECORDS = 100  # Number of sentences to test

def generate_ground_truth():
    """Generates test sentences along with the exact PII values embedded in them."""
    records = []
    
    for i in range(NUM_RECORDS):
        name = fake.name()
        email = fake.email()
        phone = fake.phone_number()
        city = fake.city()
        
        # We know exactly what PII is in this sentence
        sentence = f"My name is {name}, I live in {city}. You can email me at {email} or call {phone}."
        
        ground_truth_pii = [name, email, phone, city]
        
        records.append({
            "text": sentence,
            "ground_truth": ground_truth_pii
        })
        
    return records

def calculate_accuracy():
    print(f"Generating {NUM_RECORDS} test sentences with known Ground Truth PII...")
    test_data = generate_ground_truth()
    
    total_true_positives = 0
    total_false_positives = 0
    total_false_negatives = 0
    
    print("\nSending data to SSS Backend for extraction...\n")
    
    for i, item in enumerate(test_data):
        text = item["text"]
        ground_truth = item["ground_truth"]
        
        payload = {
            "text": text,
            "url": f"https://chatgpt.com/c/accuracy-test-{i}",
            "anonymization_method": "fake",
            "config": {
                "sites": ["Chatgpt"],
                "models": ["Presidio"],
                "methods": ["Pseudonymization"],
                "piis": ["Names", "Emails", "Phone Numbers", "Addresses"]
            }
        }
        
        try:
            response = requests.post(f"{BASE_URL}/anonymize", json=payload)
            if response.status_code != 200:
                print(f"Error on record {i}: HTTP {response.status_code}")
                continue
                
            data = response.json()
            mapping = data.get("mapping", {})
            
            # Extract the original values that the AI found
            ai_extracted_values = list(mapping.values())
            
            # Calculate TP, FP, FN for this sentence
            # Note: We do partial matching because RoBERTa might extract "John Doe" 
            # while Faker generated "Dr. John Doe", or punctuation might differ.
            
            matched_ground_truth = set()
            matched_extracted = set()
            
            # Check for True Positives
            for gt_val in ground_truth:
                for ex_val in ai_extracted_values:
                    # Clean up trailing punctuation for fair comparison
                    clean_gt = gt_val.strip(".,;:!'\"")
                    clean_ex = ex_val.strip(".,;:!'\"")
                    
                    if clean_ex in clean_gt or clean_gt in clean_ex:
                        matched_ground_truth.add(gt_val)
                        matched_extracted.add(ex_val)
            
            # True Positives: Ground truth items successfully found by AI
            true_positives = len(matched_ground_truth)
            
            # False Negatives: Ground truth items missed by AI
            false_negatives = len(ground_truth) - true_positives
            
            # False Positives: Items AI extracted that weren't in our ground truth
            false_positives = len(ai_extracted_values) - len(matched_extracted)
            
            total_true_positives += true_positives
            total_false_negatives += false_negatives
            total_false_positives += false_positives
            
        except Exception as e:
            print(f"Exception on record {i}: {e}")

    # Calculate final metrics
    print("==================================================")
    print("      SSS PII EXTRACTION ACCURACY REPORT")
    print("==================================================")
    
    print(f"Total Sentences Tested: {NUM_RECORDS}")
    print(f"Total PII Entities (Ground Truth): {NUM_RECORDS * 4}")
    print("---")
    print(f"True Positives (Correctly Extracted) : {total_true_positives}")
    print(f"False Negatives (Missed by AI)       : {total_false_negatives}")
    print(f"False Positives (Incorrectly Flagged): {total_false_positives}")
    print("---")
    
    # Precision: Out of all things the AI flagged, how many were actually PII?
    precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 0
    
    # Recall: Out of all actual PII, how many did the AI successfully find?
    recall = total_true_positives / (total_true_positives + total_false_negatives) if (total_true_positives + total_false_negatives) > 0 else 0
    
    # F1 Score: Harmonic mean of Precision and Recall
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"Precision : {precision * 100:.2f}%")
    print(f"Recall    : {recall * 100:.2f}%")
    print(f"F1 Score  : {f1_score * 100:.2f}%")
    print("==================================================")

if __name__ == "__main__":
    calculate_accuracy()
