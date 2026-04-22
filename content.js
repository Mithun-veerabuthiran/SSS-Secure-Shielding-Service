// content.js - Chrome Extension Content Script for ProseMirror integration with deanonymization

// Global variable to store mappings
let deanonymizationMappings = {};

// Get mappings from the background script
function fetchMappings() {
  chrome.runtime.sendMessage({ action: 'getMappings' }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('Error fetching mappings:', chrome.runtime.lastError.message);
      return;
    }
    
    if (response.error) {
      console.error('Error fetching mappings:', response.error);
      return;
    }
    
    if (response.mappings) {
      console.log('Deanonymization mappings loaded successfully:', Object.keys(response.mappings).length, 'URLs');
      deanonymizationMappings = response.mappings;
      
      // Process any existing content with new mappings
      processResponses();
    }
  });
}

// Listen for mapping updates from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'updateMappings') {
    console.log('Received updated mappings:', Object.keys(message.mappings).length, 'URLs');
    deanonymizationMappings = message.mappings;
    
    // Process content with new mappings
    processResponses();
  }
});

// Create and place the button
function createProcessButton() {
  // First check if button already exists to avoid duplicates
  if (document.getElementById('prosemirror-api-button')) {
    return;
  }
  
  // Find the text input area using modern ChatGPT selectors
  console.log("Looking for ChatGPT input area...");
  let inputArea = document.getElementById('prompt-textarea') || 
                  document.querySelector('div.ProseMirror') || 
                  document.querySelector('textarea[data-id="root"]');
                  
  if (!inputArea) {
    return; // Wait until the input area is available
  }
  
  // Find a stable container to inject the button into
  // Usually the wrapper around the text area
  const container = inputArea.closest('div.flex.items-end') || 
                    inputArea.closest('form') ||
                    inputArea.parentNode;
  
  // Create the button
  const apiButton = document.createElement('button');
  apiButton.id = 'prosemirror-api-button';
  apiButton.type = 'button'; // Prevent form submission
  apiButton.style.display = 'flex';
  apiButton.style.alignItems = 'center';
  apiButton.style.justifyContent = 'center';
  apiButton.style.backgroundColor = 'transparent'; // native look
  apiButton.style.border = 'none';
  apiButton.style.borderRadius = '50%'; // ChatGPT uses rounded buttons for tools
  apiButton.style.cursor = 'pointer';
  apiButton.style.width = '32px';
  apiButton.style.height = '32px';
  apiButton.style.margin = '0 2px';
  apiButton.style.color = 'inherit';
  
  // Create an <img> element for the icon
  const incognitoIcon = document.createElement('img');
  incognitoIcon.src = 'https://cdn-icons-png.flaticon.com/512/6463/6463397.png'; // Replace with your downloaded icon path
  incognitoIcon.alt = 'Incognito Mode';
  incognitoIcon.style.width = '20px';
  incognitoIcon.style.height = '20px';
  // Optional: add a filter to make the icon blend in more with native monochrome ChatGPT icons
  // incognitoIcon.style.filter = 'grayscale(100%) contrast(200%)';
  
  // Append the icon to the button
  apiButton.appendChild(incognitoIcon);
  
  // Hover effect to act like a native ChatGPT button
  apiButton.onmouseover = () => apiButton.style.backgroundColor = 'rgba(180, 180, 180, 0.2)';
  apiButton.onmouseout = () => apiButton.style.backgroundColor = 'transparent';

  // INSERTION LOGIC - Target left toolbar inside the composer
  // Find the attachment button, which is usually on the left next to 'Tools'
  const attachButton = document.querySelector('button[aria-label="Attach files"]') || 
                       document.querySelector('button[aria-label="Attach"]') ||
                       document.querySelector('button[aria-label="File upload"]');
                       
  const composer = document.querySelector('[data-testid="composer"]');
  
  if (attachButton && attachButton.parentNode) {
      // Insert right after the attach/+ button in the left tools container
      attachButton.parentNode.insertBefore(apiButton, attachButton.nextSibling);
      console.log("Incognito Button Successfully Injected next to Attach button!");
  } else if (composer) {
      // Fallback: If composer is found but no attach button, inject it inside the left container manually
      // Usually there's a flex container for the left buttons. We can place it before the textarea.
      const promptTextarea = document.getElementById('prompt-textarea');
      if (promptTextarea && promptTextarea.parentElement) {
          promptTextarea.parentElement.insertBefore(apiButton, promptTextarea);
      } else {
          composer.insertBefore(apiButton, composer.firstChild);
      }
      console.log("Incognito Button Successfully Injected into Composer!");
  } else if (inputArea && inputArea.parentNode) {
      // Complete fallback
      inputArea.parentNode.insertBefore(apiButton, inputArea.nextSibling);
      console.log("Incognito Button Injected into DOM (Fallback)!");
  }
  
  // Add click event listener
apiButton.addEventListener('click', async () => {
  try {
    // Extract text from the identified input Area
    // Different containers hold text differently (value vs textContent)
    let text = "";
    if (inputArea.tagName.toLowerCase() === 'textarea') {
      text = inputArea.value;
    } else {
      text = inputArea.textContent;
    }
    
    // Show loading state
    const originalHtml = apiButton.innerHTML; // Save original HTML with icon
    apiButton.innerHTML = '<span style="font-size: 12px;">Processing...</span>';
    apiButton.disabled = true;
    
    // Get current URL
    const currentUrl = window.location.href;
    
    // Send message to background script
    chrome.runtime.sendMessage(
      {
        action: 'processText',
        text: text,
        url: currentUrl
      },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error('Runtime Error:', chrome.runtime.lastError.message);
          if (apiButton) {
              apiButton.innerHTML = '<span style="font-size: 10px;">Error!</span>';
              apiButton.style.backgroundColor = '#ff4444';
              setTimeout(() => {
                if (apiButton) {
                    apiButton.innerHTML = originalHtml; // Restore original icon
                    apiButton.style.backgroundColor = '#ffffff';
                    apiButton.disabled = false;
                }
              }, 3000);
          }
          return;
        }
        
        if (!response || response.error) {
          console.error('Response Error:', response ? response.error : 'No response received');
          if (apiButton) {
              apiButton.innerHTML = '<span style="font-size: 10px;">Error!</span>';
              apiButton.style.backgroundColor = '#ff4444';
              setTimeout(() => {
                if (apiButton) {
                    apiButton.innerHTML = originalHtml; // Restore original icon
                    apiButton.style.backgroundColor = '#ffffff';
                    apiButton.disabled = false;
                }
              }, 3000);
          }
          return;
        }
        
        // Update the input area safely
        const processedText = response.processedText || '';
        
        // Focus the editor first
        inputArea.focus();
        
        // If it's a standard textarea (Modern ChatGPT)
        if (inputArea.tagName.toLowerCase() === 'textarea') {
            inputArea.value = processedText;
            
            // Trigger input events so React registers the change
            inputArea.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
            inputArea.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
            
            // Adjust height if it's an auto-resizing textarea
            inputArea.style.height = 'auto';
            inputArea.style.height = (inputArea.scrollHeight) + 'px';
        } else {
            // Legacy ProseMirror logic
            // Select all text in the editor
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(inputArea);
            selection.removeAllRanges();
            selection.addRange(range);
            
            let success = false;
            try {
              document.execCommand('delete', false, null);
              success = document.execCommand('insertText', false, processedText);
            } catch (e) {
              console.warn('execCommand failed:', e);
            }
            
            if (!success) {
               // Fallback 1: InputEvent
               inputArea.textContent = processedText;
               const inputEvent = new Event('input', { bubbles: true, cancelable: true });
               inputArea.dispatchEvent(inputEvent);
            }
        }
        
        // Reset button state
        apiButton.innerHTML = originalHtml; // Restore original icon
        apiButton.disabled = false;
        
        // Fetch updated mappings
        fetchMappings();
      }
    );
  } catch (error) {
    console.error('Error processing text:', error);
    
    // Safely attempt to restore button state if it still exists
    if (apiButton) {
        apiButton.innerHTML = '<span style="font-size: 10px;">Error!</span>';
        apiButton.style.backgroundColor = '#ff4444';
        setTimeout(() => {
          if (apiButton) {
              // Create an <img> element for the icon if original text not available
              const resetIcon = document.createElement('img');
              resetIcon.src = 'https://cdn-icons-png.flaticon.com/512/6463/6463397.png';
              resetIcon.alt = 'Incognito Mode';
              apiButton.innerHTML = '';
              apiButton.appendChild(resetIcon);
              apiButton.style.backgroundColor = '#ffffff';
              apiButton.disabled = false;
          }
        }, 3000);
    }
  }
});
}

// Function to find the best URL match for deanonymization
function findBestUrlMatch(currentUrl) {
  // If there's an exact match, use it
  if (deanonymizationMappings[currentUrl]) {
    return currentUrl;
  }
  
  // Extract the conversation ID from the URL if it's a ChatGPT URL
  const match = currentUrl.match(/chatgpt\.com\/c\/([a-zA-Z0-9-]+)/);
  if (match) {
    const conversationId = match[1];
    
    // Look for any URL containing this conversation ID
    for (const url in deanonymizationMappings) {
      if (url.includes(conversationId)) {
        return url;
      }
    }
  }
  
  // If no match found, return null
  return null;
}

// Function to deanonymize text based on mappings
function deanonymizeText(text, url) {
  if (!text || typeof text !== 'string') return text;
  
  // Find the best URL match
  const bestMatchUrl = findBestUrlMatch(url);
  if (!bestMatchUrl) {
    console.log(`No mappings found for URL: ${url}`);
    return text;
  }
  
  const urlMappings = deanonymizationMappings[bestMatchUrl];
  if (!urlMappings || !Array.isArray(urlMappings)) {
    console.log(`Invalid mappings for URL: ${bestMatchUrl}`);
    return text;
  }
  
  console.log(`Applying mappings for URL: ${bestMatchUrl}`);
  let deanonymizedText = text;
  
  // Apply all mapping groups for this URL
  urlMappings.forEach((mappingGroup, index) => {
    if (!mappingGroup.mapping) {
      console.warn(`Mapping group ${index} has no mapping property`);
      return;
    }
    
    const mapping = mappingGroup.mapping;
    
    // Replace each anonymized string with its original value
    for (const [anonymized, original] of Object.entries(mapping)) {
      // Use smart boundaries to prevent partial word replacements (Scunthorpe problem)
      // We look for word boundaries OR start/end of string OR non-word characters
      try {
        const escapedAnonymized = anonymized.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // Match either the start of the string or a non-word character, 
        // followed by our exact anonymized string, 
        // followed by a non-word character or the end of the string
        const regex = new RegExp(`(^|\\W)(${escapedAnonymized})($|\\W)`, 'g');
        const beforeCount = (deanonymizedText.match(regex) || []).length;
        
        // The first capture group ($1) is the preceding character/boundary, 
        // the original string replaces the matched text ($2), 
        // the third capture group ($3) is the succeeding character/boundary
        deanonymizedText = deanonymizedText.replace(regex, `$1${original}$3`);
        
        const escapedOriginal = original.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const afterCount = (deanonymizedText.match(new RegExp(`(^|\\W)(${escapedOriginal})($|\\W)`, 'g')) || []).length;
        
        if (beforeCount > 0) {
          console.log(`Replaced "${anonymized}" with "${original}" (${beforeCount} -> ${afterCount})`);
        }
      } catch (e) {
        console.error(`Error creating regex for "${anonymized}":`, e);
      }
    }
  });
  
  return deanonymizedText;
}

// Process responses that need deanonymization
function processResponses() {
  const currentUrl = window.location.href;
  
  // Process sent messages
  const sentElements = document.getElementsByClassName("whitespace-pre-wrap");
  for (let i = 0; i < sentElements.length; i++) {
    const element = sentElements[i];
    
    // Skip if already processed
    if (element.dataset.deanonymized === 'true') {
      continue;
    }
    
    const originalText = element.textContent;
    const deanonymizedText = deanonymizeText(originalText, currentUrl);
    
    // Update text if it changed
    if (deanonymizedText !== originalText) {
      element.textContent = deanonymizedText;
      console.log('Sent message deanonymized');
    }
    
    // Mark as processed
    element.dataset.deanonymized = 'true';
  }
  
  // Also try to find messages with different class names
  const alternativeSentSelectors = [
    '.whitespace-pre-wrap', 
    '.message-content',
    '[data-message-author-role="user"] p',
    '[data-testid="conversation-turn-user"] p'
  ];
  
  alternativeSentSelectors.forEach(selector => {
    try {
      const elements = document.querySelectorAll(selector);
      for (let i = 0; i < elements.length; i++) {
        const element = elements[i];
        
        // Skip if already processed
        if (element.dataset.deanonymized === 'true') {
          continue;
        }
        
        const originalText = element.textContent;
        const deanonymizedText = deanonymizeText(originalText, currentUrl);
        
        // Update text if it changed
        if (deanonymizedText !== originalText) {
          element.textContent = deanonymizedText;
          console.log(`Sent message deanonymized using selector: ${selector}`);
        }
        
        // Mark as processed
        element.dataset.deanonymized = 'true';
      }
    } catch (err) {
      console.warn(`Error processing selector ${selector}:`, err);
    }
  });
  
  // Process received messages
  const receivedElements = document.getElementsByClassName("prose");
  for (let i = 0; i < receivedElements.length; i++) {
    const element = receivedElements[i];
    
    // Skip if already processed
    if (element.dataset.deanonymized === 'true') {
      continue;
    }
    
    const originalText = element.textContent;
    const deanonymizedText = deanonymizeText(originalText, currentUrl);
    
    // Update text if it changed
    if (deanonymizedText !== originalText) {
      // Use innerHTML to preserve formatting
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      let node;
      
      while (node = walker.nextNode()) {
        const nodeText = node.nodeValue;
        const nodeDeanonymized = deanonymizeText(nodeText, currentUrl);
        if (nodeText !== nodeDeanonymized) {
          node.nodeValue = nodeDeanonymized;
        }
      }
      
      console.log('Received message deanonymized');
    }
    
    // Mark as processed
    element.dataset.deanonymized = 'true';
  }
  
  // Also try to find responses with different class names
  const alternativeReceivedSelectors = [
    '.prose', 
    '.markdown-content',
    '[data-message-author-role="assistant"] p',
    '[data-testid="conversation-turn-assistant"] p'
  ];
  
  alternativeReceivedSelectors.forEach(selector => {
    try {
      const elements = document.querySelectorAll(selector);
      for (let i = 0; i < elements.length; i++) {
        const element = elements[i];
        
        // Skip if already processed
        if (element.dataset.deanonymized === 'true') {
          continue;
        }
        
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        let hasChanges = false;
        let node;
        
        while (node = walker.nextNode()) {
          const nodeText = node.nodeValue;
          const nodeDeanonymized = deanonymizeText(nodeText, currentUrl);
          if (nodeText !== nodeDeanonymized) {
            node.nodeValue = nodeDeanonymized;
            hasChanges = true;
          }
        }
        
        if (hasChanges) {
          console.log(`Received message deanonymized using selector: ${selector}`);
        }
        
        // Mark as processed
        element.dataset.deanonymized = 'true';
      }
    } catch (err) {
      console.warn(`Error processing selector ${selector}:`, err);
    }
  });
}

// Global flag for extension state
let isExtensionEnabled = true;

// Listen for messages from popup or background about state changes
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'local' && changes.extensionEnabled) {
    isExtensionEnabled = changes.extensionEnabled.newValue;
    console.log(`Extension state changed to: ${isExtensionEnabled}`);
    if (isExtensionEnabled) {
      ensureButtonExists();
      processResponses();
    } else {
      // Remove button if disabled
      const btn = document.getElementById('prosemirror-api-button');
      if (btn) btn.remove();
    }
  }
});

// Function to check and ensure the button exists
function ensureButtonExists() {
  if (!isExtensionEnabled) return;
  if (!document.getElementById('prosemirror-api-button')) {
    createProcessButton();
  }
}

// Function to reset deanonymization flags
function resetDeanonymizationFlags() {
  if (!isExtensionEnabled) return;
  // This allows text to be reprocessed with new mappings
  document.querySelectorAll('[data-deanonymized="true"]').forEach(element => {
    element.dataset.deanonymized = 'false';
  });
}

// Initial setup
async function initialize() {
  // Check initial state
  chrome.storage.local.get(['extensionEnabled'], async (result) => {
    isExtensionEnabled = result.extensionEnabled !== false; // Default true
    
    // Load the mappings first
    await fetchMappings();
    
    // Then set up the rest of the extension
    if (isExtensionEnabled) {
      createProcessButton();
      processResponses();
      
      // Set up interval to ensure button always exists and to process new responses (every 2 seconds)
      setInterval(() => {
        if (isExtensionEnabled) {
          ensureButtonExists();
          processResponses();
        }
      }, 2000);
      
      // Set up interval to periodically fetch new mappings (every 3 seconds)
      setInterval(() => {
        if (isExtensionEnabled) {
          fetchMappings();
        }
      }, 3000);
    }
    
    // Set up MutationObserver to detect DOM changes
    const observer = new MutationObserver((mutations) => {
      if (!isExtensionEnabled) return;
      
      let needToCreateButton = false;
      let needToProcessResponses = false;
      
      for (const mutation of mutations) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          // Check added nodes
          for (let i = 0; i < mutation.addedNodes.length; i++) {
            const node = mutation.addedNodes[i];
            if (node.nodeType !== Node.ELEMENT_NODE) continue;
            
            // Check if input area was added
            if (node.id === 'prompt-textarea' || 
                (node.classList && node.classList.contains('ProseMirror')) || 
                (node.querySelector && node.querySelector('.ProseMirror')) ||
                (node.querySelector && node.querySelector('#prompt-textarea'))) {
              needToCreateButton = true;
            }
            
            // Check if response was added
            if ((node.classList && (node.classList.contains('whitespace-pre-wrap') || node.classList.contains('prose'))) || 
                (node.querySelector && (node.querySelector('.whitespace-pre-wrap') || node.querySelector('.prose')))) {
              needToProcessResponses = true;
            }
          }
        }
      }
      
      // Update as needed
      if (needToCreateButton) {
        ensureButtonExists();
      }
      
      if (needToProcessResponses) {
        processResponses();
      }
    });
    
    // Start observing
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}

// Start the initialization process
initialize();
