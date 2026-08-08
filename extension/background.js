// background.js - Handles API requests from the content script

// Global variable to store mappings
let mappingsCache = null;
let lastFetchTime = 0;
const CACHE_TTL = 3000; // 30 seconds in milliseconds

// Function to fetch mappings from the backend
async function fetchMappings() {
  try {
    const currentTime = Date.now();
    
    // Use cached mappings if they exist and aren't too old
    if (mappingsCache && (currentTime - lastFetchTime < CACHE_TTL)) {
      return mappingsCache;
    }
    
    const response = await fetch('http://localhost:5000/get_mappings');
    if (!response.ok) {
      throw new Error(`Failed to fetch mappings: ${response.status} ${response.statusText}`);
    }
    
    mappingsCache = await response.json();
    lastFetchTime = currentTime;
    
    return mappingsCache;
  } catch (error) {
    console.error('Error fetching mappings:', error);
    throw error;
  }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'processText') {
    // Get current config from storage
    chrome.storage.local.get(['sites', 'models', 'methods', 'piis'], (result) => {
      const config = {
        sites: result.sites || ["Chatgpt"],
        models: result.models || ["Presidio"],
        methods: result.methods || ["Pseudonymization"],
        piis: result.piis || ["Names", "Emails", "Phone Numbers", "Addresses", "SSN"]
      };
      
      const anonymization_method = config.methods.includes("Pseudonymization") ? "fake" : "redact";

      fetch('http://localhost:5000/anonymize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          text: request.text, 
          url: request.url, 
          anonymization_method: anonymization_method,
          config: config
        }),
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`API responded with status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        sendResponse({ processedText: data.anonymized_text || data.text });
        
        // After successful anonymization, fetch the latest mappings and notify content script
        fetchMappings().then(mappings => {
          chrome.tabs.sendMessage(sender.tab.id, {
            action: 'updateMappings',
            mappings: mappings
          });
        });
      })
      .catch(error => {
        console.error('Error in background script:', error);
        sendResponse({ error: error.message });
      });
    });
    
    // Return true to indicate that the response will be sent asynchronously
    return true;
  } else if (request.action === 'getMappings') {
    fetchMappings()
      .then(mappings => {
        sendResponse({ mappings });
      })
      .catch(error => {
        console.error('Error fetching mappings for content script:', error);
        sendResponse({ error: error.message });
      });
    
    // Return true to indicate that the response will be sent asynchronously
    return true;
  }
  
  // Handle keep-alive pings to prevent Service Worker timeout
  if (request.action === 'ping') {
      sendResponse({ status: 'alive' });
      return true;
  }
});

// When extension is installed or updated
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed or updated. Fetching initial mappings...');
  fetchMappings().catch(err => console.error('Initial mappings fetch failed:', err));
  
  // Set default config if empty
  chrome.storage.local.get(['extensionEnabled'], (result) => {
      if (result.extensionEnabled === undefined) {
          chrome.storage.local.set({ extensionEnabled: true });
      }
  });
});

// Implement keep-alive interval to prevent Status code 3 (Service Worker dying)
setInterval(() => {
    chrome.storage.local.get('extensionEnabled', () => {
        // Just reading a tiny bit of storage keeps the worker alive during long AI tasks
    });
}, 20000);