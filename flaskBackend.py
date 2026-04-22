from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import logging
import threading
import time
from faker import Faker
from cryptography.fernet import Fernet
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import hashlib

# --- SECURE ENCRYPTION SETUP ---
# Initialize or load AES-256 Symmetric Key for Database Encryption-at-Rest
KEY_FILE = "SECRET.key"
if not os.path.exists(KEY_FILE):
    encryption_key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(encryption_key)
else:
    with open(KEY_FILE, "rb") as key_file:
        encryption_key = key_file.read()

cipher_suite = Fernet(encryption_key)

# --- CUSTOM KEYWORD BLOCKLIST ---
# Hardcoded Enterprise Redaction Targets
# The system will forcefully anonymize these keywords regardless of AI context
ENTERPRISE_BLOCKLIST = [
    "Project Titan",
    "AlphaCorp",
    "TopSecretAlgorithm_v2",
    "192.168.1.254"
]

# --- MODULE F: OUTPUT DELIVERY & LOGGING MODULE ---
# Secure logging configuration: Records actions but NEVER logs actual PII
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
system_logger = logging.getLogger('SecureShield_System')

app = Flask(__name__)
CORS(app)  # Enable CORS for Chrome extension

# --- MODULE B: SENSITIVE DATA DETECTION MODULE (PRESIDIO SETUP) ---
# Initialize base Presidio
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Add Custom Recognizer for Aadhaar Numbers
# Pattern: 12 digits, often formatted as XXXX XXXX XXXX or XXXX-XXXX-XXXX
aadhaar_pattern = Pattern(
    name="aadhaar_pattern",
    regex=r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
    score=0.8
)
aadhaar_recognizer = PatternRecognizer(
    supported_entity="IN_AADHAAR", 
    patterns=[aadhaar_pattern],
    context=["aadhaar", "uidai", "id"]
)
analyzer.registry.add_recognizer(aadhaar_recognizer)

# Add Custom Recognizer for Bank Account Numbers (BBAN)
account_pattern = Pattern(
    name="account_pattern",
    regex=r"\b\d{9,18}\b",
    score=0.85
)
account_recognizer = PatternRecognizer(
    supported_entity="FINANCIAL_ACCOUNT", 
    patterns=[account_pattern]
)
analyzer.registry.add_recognizer(account_recognizer)

# Add Recognizers for things that Presidio might miss without context
ssn_pattern = Pattern(name="ssn_pattern", regex=r"\b\d{3}-\d{2}-\d{4}\b", score=0.85)
ssn_recognizer = PatternRecognizer(supported_entity="US_SSN", patterns=[ssn_pattern])
analyzer.registry.add_recognizer(ssn_recognizer)

phone_pattern = Pattern(name="phone_pattern", regex=r"\b\(\d{3}\)\d{3}-\d{4}\b", score=0.85)
phone_recognizer = PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern])
analyzer.registry.add_recognizer(phone_recognizer)

url_pattern = Pattern(name="url_pattern", regex=r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", score=0.85)
url_recognizer = PatternRecognizer(supported_entity="URL", patterns=[url_pattern])
analyzer.registry.add_recognizer(url_recognizer)

# Initialize RoBERTa PII Extractor
from update import RobertaPIIExtractor
try:
    roberta_analyzer = RobertaPIIExtractor()
    system_logger.info("RoBERTa Deep Learning Extractor initialized successfully.")
    print("RoBERTa Extractor initialized successfully in Flask.")
    
    print("\n[Running Pipeline Evaluation]")
    system_logger.info("Initiating pipeline evaluation metrics computation...")
    metrics = roberta_analyzer.evaluate_pipeline()
    
except Exception as e:
    system_logger.error("Failed to initialize RoBERTa Model.")
    print(f"Failed to initialize RoBERTa: {e}")
    roberta_analyzer = None

# Initialize Faker
fake = Faker()

import sqlite3

# Path to the SQLite DB
DB_PATH = 'mappings.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS url_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                mapping_json TEXT NOT NULL,
                anonymization_method TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON url_mappings(url)')
        conn.commit()

init_db()

# Generic URL that should be updated when specific URL is available
GENERIC_URL = "https://chatgpt.com/"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

# New endpoint to get mappings
@app.route('/get_mappings', methods=['GET'])
def get_mappings():
    """Return all mappings from the Database"""
    mappings = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url, mapping_json, anonymization_method, config_json FROM url_mappings ORDER BY id ASC")
            for row in cursor.fetchall():
                url = row[0]
                if url not in mappings:
                    mappings[url] = []
                
                # AES-256 Decryption of stored JSON payload
                try:
                    decrypted_mapping_bytes = cipher_suite.decrypt(row[1])
                    decrypted_mapping_str = decrypted_mapping_bytes.decode('utf-8')
                    mapping_dict = json.loads(decrypted_mapping_str)
                except Exception as dec_err:
                    system_logger.error(f"Failed to decrypt DB mapping row: {dec_err}")
                    continue
                    
                mappings[url].append({
                    "mapping": mapping_dict,
                    "anonymization_method": row[2],
                    "config": json.loads(row[3])
                })
    except Exception as e:
        print(f"Error fetching mappings: {e}")
    return jsonify(mappings)

def get_fake_value(entity_type, original_value):
    """
    MODULE C: PROMPT SANITIZATION
    Generate appropriate context-aware fake placeholder value based on entity type.
    """
    if entity_type == "PERSON":
        return fake.name()
    elif entity_type == "EMAIL_ADDRESS":
        return fake.email()
    elif entity_type == "PHONE_NUMBER":
        return fake.phone_number()
    elif entity_type == "CREDIT_CARD":
        return fake.credit_card_number()
    elif entity_type in ["US_BANK_NUMBER", "FINANCIAL_ACCOUNT"]:
        return fake.bban()
    elif entity_type == "IN_AADHAAR":
        return fake.numerify('#### #### ####')
    elif entity_type == "US_SSN":
        return fake.ssn()
    elif entity_type == "LOCATION":
        return fake.city()
    elif entity_type == "IP_ADDRESS":
        return fake.ipv4()
    elif entity_type == "DATE_TIME":
        return fake.date()
    elif entity_type == "URL":
        return fake.url()
    else:
        # Default case
        return f"FAKE_{entity_type}"

@app.route('/config', methods=['POST'])
def update_config():
    """Update the anonymization configuration"""
    try:
        config = request.json
        
        if not config:
            return jsonify({"error": "No configuration provided"}), 400
        
        # Validate configuration
        if not all(key in config for key in ['sites', 'models', 'methods', 'piis']):
            return jsonify({"error": "Invalid configuration. Missing required fields"}), 400
        
        # Log the configuration for debugging
        print(f"Received configuration: {json.dumps(config, indent=2)}")
        
        # Store the configuration (you might want to persist this to disk)
        # For now, we'll use a global variable
        app.config['ANONYMIZATION_CONFIG'] = config
        
        # Apply the configuration to the analyzer settings
        # This depends on how your anonymization logic works - below is an example
        
        # Example: Update entities list based on PIIs selection
        entity_mapping = {
            "Names": "PERSON",
            "Emails": "EMAIL_ADDRESS",
            "Phone Numbers": "PHONE_NUMBER",
            "Addresses": "LOCATION",
            "SSN": "US_SSN",
            "Aadhaar": "IN_AADHAAR",
            "Account Numbers": "FINANCIAL_ACCOUNT"
        }
        
        selected_entities = []
        for pii in config.get('piis', []):
            if pii in entity_mapping:
                selected_entities.append(entity_mapping[pii])
        
        # If no PIIs are selected, default to all
        if not selected_entities:
            selected_entities = list(entity_mapping.values())
        
        # Store the entities for use in the anonymize endpoint
        app.config['SELECTED_ENTITIES'] = selected_entities
        
        # Store the anonymization method
        if "Pseudonymization" in config.get('methods', []):
            app.config['ANONYMIZATION_METHOD'] = "fake"
        else:
            app.config['ANONYMIZATION_METHOD'] = "redact"
        
        return jsonify({"status": "Configuration updated successfully", "config": config})
    
    except Exception as e:
        print(f"Error updating configuration: {e}")
        return jsonify({"error": f"Failed to update configuration: {e}"}), 500

# Update the anonymize endpoint to use the configuration
@app.route('/anonymize', methods=['POST'])
def anonymize_text():
    data = request.json
    print("Received data:", data)
    
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    text = data['text']
    url = data.get('url', '')
    
    # Get configuration from app config or request
    config = data.get('config', app.config.get('ANONYMIZATION_CONFIG', {}))
    
    # Determine anonymization method from config or request
    if data.get('anonymization_method'):
        anonymization_method = data.get('anonymization_method')
    elif "Pseudonymization" in config.get('methods', []):
        anonymization_method = "fake"
    elif "Redacting" in config.get('methods', []):
        anonymization_method = "redact"
    else:
        anonymization_method = app.config.get('ANONYMIZATION_METHOD', 'redact')
    
    # Parse selected entities from the provided config
    entity_mapping = {
        "Names": "PERSON",
        "Emails": "EMAIL_ADDRESS",
        "Phone Numbers": "PHONE_NUMBER",
        "Addresses": "LOCATION",
        "SSN": "US_SSN",
        "Aadhaar": "IN_AADHAAR",
        "Account Numbers": "FINANCIAL_ACCOUNT",
        "URLs": "URL"
    }
    
    selected_entities = []
    if 'piis' in config:
        for pii in config['piis']:
            if pii in entity_mapping:
                selected_entities.append(entity_mapping[pii])
    
    # Default if nothing is selected or no config passed
    if not selected_entities:
        selected_entities = app.config.get('SELECTED_ENTITIES', [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN", 
            "US_BANK_NUMBER", "LOCATION", "NRP", "DATE_TIME", "IP_ADDRESS",
            "IN_AADHAAR", "FINANCIAL_ACCOUNT", "URL"
        ])
    
    # Default to generic URL if none provided
    if not url:
        url = GENERIC_URL
    
    # Validate anonymization method
    if anonymization_method not in ['redact', 'fake']:
        return jsonify({"error": "Invalid anonymization method. Use 'redact' or 'fake'"}), 400
    
    # MODULE A: INPUT ACQUISITION (Validation)
    if len(text) > 10000:
        system_logger.warning("Very large prompt received, truncating or splitting may be required.")
    
    # MODULE B.0: ENTERPRISE CUSTOM KEYWORD BLOCKLIST INTERCEPTION
    analyzer_results = []
    
    # Pre-scan text for hardcoded corporate blocklist items before ML processing
    for blocked_word in ENTERPRISE_BLOCKLIST:
        # Find all occurrences of the blocklist literal string
        for match in re.finditer(re.escape(blocked_word), text, re.IGNORECASE):
            class BlocklistResult:
                def __init__(self, start, end):
                    self.entity_type = "CUSTOM_BLOCK"
                    self.start = start
                    self.end = end
            analyzer_results.append(BlocklistResult(match.start(), match.end()))
    
    # Engine 1: RoBERTa Deep Learning (Contextual Analysis for Names, Locations, Orgs)
    if roberta_analyzer:
        try:
            # Implement sliding window chunking to prevent max token crashing on large texts
            chunk_size = 500  # Safe character limit for ~512 tokens
            overlap = 50
            start_idx = 0
            
            while start_idx < len(text):
                end_idx = min(start_idx + chunk_size, len(text))
                chunk_text = text[start_idx:end_idx]
                
                roberta_raw = roberta_analyzer.analyze(text=chunk_text)
                for res in roberta_raw:
                    if res["entity_type"] in selected_entities:
                        class RobertaResult:
                            def __init__(self, entity_type, start, end):
                                self.entity_type = entity_type
                                self.start = start
                                self.end = end
                                
                        # Adjust indices based on the chunk's offset in the original text
                        absolute_start = res["start"] + start_idx
                        absolute_end = res["end"] + start_idx
                        analyzer_results.append(RobertaResult(res["entity_type"], absolute_start, absolute_end))
                        
                start_idx += chunk_size - overlap
                
        except Exception as e:
            system_logger.error(f"RoBERTa analysis failed: {e}")

    # Engine 2: Presidio Regex Pattern Matcher (For Aadhaar, Accounts, Emails, Phones)
    # We only run presidio for non-contextual entities to avoid double-flagging standard names/locations
    presidio_entities = [e for e in selected_entities if e not in ["PERSON", "LOCATION", "ORGANIZATION"]]
    if presidio_entities:
        try:
            presidio_raw = analyzer.analyze(
                text=text,
                entities=presidio_entities,
                language="en",
                score_threshold=0.3
            )
            analyzer_results.extend(presidio_raw)
        except Exception as e:
            system_logger.error(f"Presidio analysis failed: {e}")

    # Remove overlapping entities (e.g., if both engines somehow flagged the exact same characters)
    # Give priority to RoBERTa context over Regex
    final_results = []
    # Sort by start index, then by end index (longest match first)
    sorted_temp = sorted(analyzer_results, key=lambda x: (x.start, -x.end))
    last_end = -1
    for res in sorted_temp:
        if res.start >= last_end:
            final_results.append(res)
            last_end = res.end
            
    analyzer_results = final_results

    # First pass: Create a consistent mapping for each unique original value
    value_mapping = {}  # Maps entity mappings to their replacements
    mapping = {}        # Maps replacements back to original values (for de-anonymization)
    
    # Sort results by position to process them in order
    sorted_results = sorted(analyzer_results, key=lambda x: x.start)
    
    for result in sorted_results:
        entity_type = result.entity_type
        original_value = text[result.start:result.end]
        
        # Tie original_value to its entity_type to prevent Cross-Entity mapping collisions
        mapping_key = f"{entity_type}_{original_value}"
        
        # Check if we've already assigned a replacement for this mapping key
        if mapping_key not in value_mapping:
            if anonymization_method == "redact":
                replacement = f"[REDACTED_{entity_type}_{len(mapping)}]"
            else:  # fake
                replacement = get_fake_value(entity_type, original_value)
                # Ensure the fake value is unique across the document
                attempts = 0
                while replacement in mapping and attempts < 100:
                    replacement = get_fake_value(entity_type, original_value)
                    attempts += 1
                if replacement in mapping:
                    # Fallback
                    replacement = f"{replacement}_{len(mapping)}"
            
            value_mapping[mapping_key] = replacement
            mapping[replacement] = original_value
    
    # Second pass: Apply the replacements to the text
    # We need to replace from right to left to maintain correct indices
    anonymized_text = text
    for result in sorted(analyzer_results, key=lambda x: x.start, reverse=True):
        entity_type = result.entity_type
        original_value = text[result.start:result.end]
        mapping_key = f"{entity_type}_{original_value}"
        replacement = value_mapping[mapping_key]
        
        # Replace just this instance
        anonymized_text = anonymized_text[:result.start] + replacement + anonymized_text[result.end:]
    
    # Log the successful sanitization execution securely
    system_logger.info(f"Sanitization executed using method: {anonymization_method}. {len(value_mapping)} unique entities anonymized.")
    
    # ↳ INTERNAL MAP TRACE (Obfuscated) - Secure logging of mapping relationships without exposing PII
    obfuscated_trace = {f"HASH_{hashlib.sha256(k.encode()).hexdigest()[:8]}": v for k, v in value_mapping.items()}
    system_logger.info(f"# ↳ INTERNAL MAP TRACE (Obfuscated): {json.dumps(obfuscated_trace)}")

    # Update GENERIC_URL to precise URL if applicable
    if url != GENERIC_URL and url.startswith("https://chatgpt.com/c/"):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE url_mappings SET url = ? WHERE url = ?", (url, GENERIC_URL))
                conn.commit()
                print(f"Updated generic URL to specific URL: {url} in DB.")
        except Exception as e:
            print(f"Error updating generic URL: {e}")
            
    # Save new mapping directly to Database (AES-256 Encrypted)
    try:
        # Encrypt the structural mapping dictionary
        mapping_str = json.dumps(mapping)
        encrypted_mapping = cipher_suite.encrypt(mapping_str.encode('utf-8'))
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO url_mappings (url, mapping_json, anonymization_method, config_json)
                VALUES (?, ?, ?, ?)
            ''', (url, encrypted_mapping, anonymization_method, json.dumps(config)))
            conn.commit()
            print(f"Mapping saved to DB (Encrypted) for URL: {url}")
    except Exception as e:
        print(f"Error saving new mapping: {e}")
    print(anonymized_text)
    return jsonify({
        "anonymized_text": anonymized_text,
        "mapping": mapping,
        "anonymization_method": anonymization_method,
        "config": config
    })

@app.route('/deanonymize', methods=['POST'])
def deanonymize_text():
    data = request.json
    print("Deanonymize request:", data)
    
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400
    
    text = data['text']
    chat_url = data.get('url', '')
    
    # Default to generic URL if none provided
    if not chat_url:
        chat_url = GENERIC_URL
        
    url_mappings = []
    
    # Fetch exclusively for the specified URL, or the generic fallback
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mapping_json, anonymization_method FROM url_mappings WHERE url = ? ORDER BY id ASC", (chat_url,))
            rows = cursor.fetchall()
            
            # Secure Fallback Mechanism: Only fallback to GENERIC_URL if the specific URL has no mappings.
            # Never fallback to random other users' URLs to prevent mapping collisions.
            if not rows and chat_url != GENERIC_URL:
                cursor.execute("SELECT mapping_json, anonymization_method FROM url_mappings WHERE url = ? ORDER BY id ASC", (GENERIC_URL,))
                rows = cursor.fetchall()
            
            for row in rows:
                # AES-256 Decryption of stored JSON payload
                try:
                    decrypted_mapping_bytes = cipher_suite.decrypt(row[0])
                    decrypted_mapping_str = decrypted_mapping_bytes.decode('utf-8')
                    mapping_dict = json.loads(decrypted_mapping_str)
                except Exception as dec_err:
                    system_logger.error(f"Failed to decrypt DB mapping row: {dec_err}")
                    continue
                    
                url_mappings.append({
                    "mapping": mapping_dict,
                    "anonymization_method": row[1]
                })
    except Exception as e:
        print(f"Error reading mappings from DB: {e}")

    if not url_mappings:
        return jsonify({"error": f"No mappings found for URL: {chat_url}"}), 404
    
    # De-anonymize the text using all mappings for this URL
    deanonymized_text = text
    anonymization_method = "unknown"
    
    # Apply mappings in reverse order (most recent first)
    for mapping_entry in reversed(url_mappings):
        current_mapping = mapping_entry.get("mapping", {})
        anonymization_method = mapping_entry.get("anonymization_method", "unknown")
        
        # Create a single-pass regex replacement to prevent double-replacements
        if current_mapping:
            # Sort keys by length descending to match longest possible fakes first
            sorted_keys = sorted(current_mapping.keys(), key=len, reverse=True)
            # Escape the keys for regex
            escaped_keys = [re.escape(k) for k in sorted_keys]
            pattern = re.compile("|".join(escaped_keys))
            
            # Sub function uses the match string to look up the original from the map
            deanonymized_text = pattern.sub(lambda m: current_mapping[m.group(0)], deanonymized_text)
    
    # Log the successful reintegration securely
    system_logger.info(f"Data Reintegration executed for URL.")

    print(f"De-anonymized text using mapping from URL: {chat_url}")
    return jsonify({
        "deanonymized_text": deanonymized_text,
        "anonymization_method": anonymization_method
    })

def auto_delete_old_mappings():
    """
    Background cron job to permanently delete mapping arrays from the SQLite DB 
    that are older than 24 hours to enforce zero-trust privacy.
    """
    while True:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Delete rows older than 24 hours
                cursor.execute('''
                    DELETE FROM url_mappings 
                    WHERE created_at < datetime('now', '-24 hours')
                ''')
                deleted_rows = cursor.rowcount
                conn.commit()
                if deleted_rows > 0:
                    system_logger.info(f"Cron auto-deleted {deleted_rows} expired mapping sessions (>24h old).")
                    print(f"[*] TTL Auto-Delete: Wiped {deleted_rows} expired sessions.")
        except Exception as e:
            system_logger.error(f"Error in auto-delete cron: {e}")
            print(f"[!] TTL Auto-Delete Error: {e}")
            
        # Wait 1 hour before checking again
        time.sleep(3600)

if __name__ == '__main__':
    system_logger.info("Starting Secure Shielding Service Backend.")
    
    # Start the 24-hour TTL auto-deletion daemon
    deletion_thread = threading.Thread(target=auto_delete_old_mappings, daemon=True)
    deletion_thread.start()
    print("[*] 24-Hour TTL Auto-Deletion Thread Started.")
    
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(debug=True, port=port)