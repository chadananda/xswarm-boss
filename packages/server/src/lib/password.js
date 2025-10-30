/**
 * Password Hashing and Validation
 *
 * Uses PBKDF2 with SHA-256 (Web Crypto API) for Cloudflare Workers compatibility
 * Format: pbkdf2:iterations:salt:hash
 */

const ITERATIONS = 100000; // OWASP recommended minimum
const KEY_LENGTH = 32; // 256 bits
const SALT_LENGTH = 16; // 128 bits

/**
 * Hash a password using PBKDF2
 *
 * @param {string} password - Plain text password
 * @returns {Promise<string>} Hashed password in format: pbkdf2:iterations:salt:hash
 */
export async function hashPassword(password) {
  if (!password || password.length < 8) {
    throw new Error('Password must be at least 8 characters');
  }

  // Generate random salt
  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));

  // Convert password to bytes
  const encoder = new TextEncoder();
  const passwordBytes = encoder.encode(password);

  // Import password as key material
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    passwordBytes,
    'PBKDF2',
    false,
    ['deriveBits']
  );

  // Derive key using PBKDF2
  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: ITERATIONS,
      hash: 'SHA-256',
    },
    keyMaterial,
    KEY_LENGTH * 8
  );

  // Convert to base64 for storage
  const hashBytes = new Uint8Array(derivedBits);
  const saltBase64 = btoa(String.fromCharCode(...salt));
  const hashBase64 = btoa(String.fromCharCode(...hashBytes));

  return `pbkdf2:${ITERATIONS}:${saltBase64}:${hashBase64}`;
}

/**
 * Verify a password against a hash
 *
 * @param {string} password - Plain text password to verify
 * @param {string} hash - Stored hash in format: pbkdf2:iterations:salt:hash
 * @returns {Promise<boolean>} True if password matches
 */
export async function verifyPassword(password, hash) {
  if (!password || !hash) {
    return false;
  }

  try {
    // Parse the stored hash
    const parts = hash.split(':');
    if (parts.length !== 4 || parts[0] !== 'pbkdf2') {
      throw new Error('Invalid hash format');
    }

    const iterations = parseInt(parts[1], 10);
    const saltBase64 = parts[2];
    const storedHashBase64 = parts[3];

    // Decode salt and hash
    const salt = Uint8Array.from(atob(saltBase64), c => c.charCodeAt(0));
    const storedHash = Uint8Array.from(atob(storedHashBase64), c => c.charCodeAt(0));

    // Hash the provided password with the same salt and iterations
    const encoder = new TextEncoder();
    const passwordBytes = encoder.encode(password);

    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      passwordBytes,
      'PBKDF2',
      false,
      ['deriveBits']
    );

    const derivedBits = await crypto.subtle.deriveBits(
      {
        name: 'PBKDF2',
        salt: salt,
        iterations: iterations,
        hash: 'SHA-256',
      },
      keyMaterial,
      KEY_LENGTH * 8
    );

    const computedHash = new Uint8Array(derivedBits);

    // Constant-time comparison
    return constantTimeEqual(computedHash, storedHash);

  } catch (error) {
    console.error('Password verification error:', error);
    return false;
  }
}

/**
 * Validate password strength
 *
 * Requirements:
 * - At least 8 characters
 * - At least one uppercase letter
 * - At least one lowercase letter
 * - At least one number
 *
 * @param {string} password - Password to validate
 * @returns {Object} { valid: boolean, errors: string[] }
 */
export function validatePasswordStrength(password) {
  const errors = [];

  if (!password) {
    return { valid: false, errors: ['Password is required'] };
  }

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters');
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Constant-time comparison to prevent timing attacks
 *
 * @param {Uint8Array} a - First array
 * @param {Uint8Array} b - Second array
 * @returns {boolean} True if arrays are equal
 */
function constantTimeEqual(a, b) {
  if (a.length !== b.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a[i] ^ b[i];
  }

  return result === 0;
}
