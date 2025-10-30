/**
 * Authentication and Signature Verification
 *
 * Utilities for verifying Twilio webhook signatures.
 */

/**
 * Verify Twilio webhook signature (HMAC-SHA1)
 *
 * @param {string} url - Full webhook URL
 * @param {Object} params - POST parameters from webhook
 * @param {string} signature - X-Twilio-Signature header
 * @param {string} authToken - Twilio auth token
 * @returns {boolean} True if signature is valid
 */
export function verifyTwilioSignature(url, params, signature, authToken) {
  if (!signature || !authToken) {
    return false;
  }

  try {
    // Build data string (URL + sorted params)
    let data = url;

    // Sort params by key and append to data
    const sortedKeys = Object.keys(params).sort();
    for (const key of sortedKeys) {
      data += key + params[key];
    }

    // Compute HMAC-SHA1
    const expectedSignature = computeHmacSha1(data, authToken);

    // Compare signatures (constant-time comparison)
    return constantTimeEqual(signature, expectedSignature);

  } catch (error) {
    console.error('Error verifying Twilio signature:', error);
    return false;
  }
}

/**
 * Compute HMAC-SHA1 signature
 *
 * Uses Web Crypto API (available in Cloudflare Workers)
 *
 * @param {string} data - Data to sign
 * @param {string} key - Secret key
 * @returns {Promise<string>} Base64-encoded signature
 */
async function computeHmacSha1(data, key) {
  // Convert key and data to Uint8Array
  const encoder = new TextEncoder();
  const keyData = encoder.encode(key);
  const dataBytes = encoder.encode(data);

  // Import key for HMAC
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign']
  );

  // Sign data
  const signature = await crypto.subtle.sign('HMAC', cryptoKey, dataBytes);

  // Convert to base64
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

/**
 * Constant-time string comparison (prevents timing attacks)
 *
 * @param {string} a - First string
 * @param {string} b - Second string
 * @returns {boolean} True if strings are equal
 */
function constantTimeEqual(a, b) {
  if (a.length !== b.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }

  return result === 0;
}
