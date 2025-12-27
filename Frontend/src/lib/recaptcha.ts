/**
 * reCAPTCHA Enterprise v3 helper utilities
 * 
 * Provides functions to interact with Google reCAPTCHA Enterprise API
 * for bot protection on forms and actions.
 */

/**
 * Get reCAPTCHA token for a specific action
 * 
 * @param action - Action name (e.g., 'SIGNUP', 'LOGIN', 'CONTACT')
 * @returns Promise resolving to token string, or null if unavailable/error
 */
export async function getRecaptchaToken(action: string): Promise<string | null> {
  const siteKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY;
  
  // If site key is not configured, return null (graceful degradation)
  if (!siteKey) {
    console.debug('reCAPTCHA: Site key not configured, skipping token generation');
    return null;
  }
  
  // Check if grecaptcha is available
  if (!window.grecaptcha?.enterprise) {
    console.warn('reCAPTCHA: Enterprise API not loaded, script may not be available');
    return null;
  }
  
  try {
    // Wait for reCAPTCHA to be ready
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('reCAPTCHA ready timeout'));
      }, 5000); // 5 second timeout
      
      window.grecaptcha.enterprise.ready(() => {
        clearTimeout(timeout);
        resolve();
      });
    });
    
    // Execute reCAPTCHA and get token
    const token = await window.grecaptcha.enterprise.execute(siteKey, {
      action: action,
    });
    
    return token;
  } catch (error) {
    console.error('reCAPTCHA: Error getting token:', error);
    return null;
  }
}

/**
 * Load reCAPTCHA Enterprise script dynamically
 * 
 * This function should be called once when the app initializes.
 * It loads the reCAPTCHA Enterprise script if not already loaded.
 * 
 * @returns Promise that resolves when script is loaded (or already loaded)
 */
export function loadRecaptchaScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (window.grecaptcha?.enterprise) {
      resolve();
      return;
    }
    
    const siteKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY;
    if (!siteKey) {
      console.debug('reCAPTCHA: Site key not configured, skipping script load');
      resolve(); // Resolve anyway for graceful degradation
      return;
    }
    
    // Check if script is already in DOM
    const existingScript = document.querySelector(
      `script[src*="recaptcha/enterprise.js"]`
    );
    if (existingScript) {
      // Script exists, wait for it to load
      const checkInterval = setInterval(() => {
        if (window.grecaptcha?.enterprise) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
      
      // Timeout after 5 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        if (!window.grecaptcha?.enterprise) {
          reject(new Error('reCAPTCHA script load timeout'));
        }
      }, 5000);
      return;
    }
    
    // Create and load script
    const script = document.createElement('script');
    script.src = `https://www.google.com/recaptcha/enterprise.js?render=${siteKey}`;
    script.async = true;
    script.defer = true;
    
    script.onload = () => {
      // Wait for grecaptcha to be available
      const checkInterval = setInterval(() => {
        if (window.grecaptcha?.enterprise) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
      
      // Timeout after 5 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        if (!window.grecaptcha?.enterprise) {
          reject(new Error('reCAPTCHA Enterprise API not available after script load'));
        }
      }, 5000);
    };
    
    script.onerror = () => {
      reject(new Error('Failed to load reCAPTCHA Enterprise script'));
    };
    
    document.head.appendChild(script);
  });
}

