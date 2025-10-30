/**
 * HTTP Test Utilities
 * Helper functions for making HTTP requests in tests
 */

/**
 * Make an HTTP request
 * @param {string} url - The URL to request
 * @param {object} options - Request options
 * @returns {Promise<Response>}
 */
export async function request(url, options = {}) {
  const {
    method = 'GET',
    headers = {},
    body = null,
    query = null,
    auth = null,
  } = options;

  // Build URL with query params
  let fullUrl = url;
  if (query) {
    const params = new URLSearchParams(query);
    fullUrl = `${url}?${params.toString()}`;
  }

  // Build headers
  const finalHeaders = { ...headers };

  // Add auth header if provided
  if (auth) {
    if (typeof auth === 'string') {
      finalHeaders['Authorization'] = `Bearer ${auth}`;
    } else if (auth.token) {
      finalHeaders['Authorization'] = `Bearer ${auth.token}`;
    } else if (auth.user && auth.password) {
      const credentials = Buffer.from(`${auth.user}:${auth.password}`).toString('base64');
      finalHeaders['Authorization'] = `Basic ${credentials}`;
    }
  }

  // Add content-type for JSON bodies
  if (body && typeof body === 'object') {
    finalHeaders['Content-Type'] = 'application/json';
  }

  // Make request
  const response = await fetch(fullUrl, {
    method,
    headers: finalHeaders,
    body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
  });

  // Parse response based on content-type
  const contentType = response.headers.get('content-type') || '';
  let data;

  if (contentType.includes('application/json')) {
    data = await response.json();
  } else if (contentType.includes('text/')) {
    data = await response.text();
  } else {
    data = await response.arrayBuffer();
  }

  // Return enhanced response object
  return {
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    data,
    ok: response.ok,
  };
}

/**
 * GET request helper
 */
export async function get(url, options = {}) {
  return request(url, { ...options, method: 'GET' });
}

/**
 * POST request helper
 */
export async function post(url, body, options = {}) {
  return request(url, { ...options, method: 'POST', body });
}

/**
 * PUT request helper
 */
export async function put(url, body, options = {}) {
  return request(url, { ...options, method: 'PUT', body });
}

/**
 * PATCH request helper
 */
export async function patch(url, body, options = {}) {
  return request(url, { ...options, method: 'PATCH', body });
}

/**
 * DELETE request helper
 */
export async function del(url, options = {}) {
  return request(url, { ...options, method: 'DELETE' });
}

/**
 * Create an auth helper for a specific token
 */
export function createAuthClient(token) {
  return {
    get: (url, options = {}) => get(url, { ...options, auth: token }),
    post: (url, body, options = {}) => post(url, body, { ...options, auth: token }),
    put: (url, body, options = {}) => put(url, body, { ...options, auth: token }),
    patch: (url, body, options = {}) => patch(url, body, { ...options, auth: token }),
    del: (url, options = {}) => del(url, { ...options, auth: token }),
  };
}

/**
 * Login and get auth token
 */
export async function login(baseUrl, credentials) {
  const response = await post(`${baseUrl}/api/auth/login`, credentials);

  if (!response.ok) {
    throw new Error(`Login failed: ${response.data?.error || response.statusText}`);
  }

  return {
    token: response.data.token,
    user: response.data.user,
    client: createAuthClient(response.data.token),
  };
}

/**
 * Signup and get auth token
 */
export async function signup(baseUrl, userData) {
  const response = await post(`${baseUrl}/api/auth/signup`, userData);

  if (!response.ok) {
    throw new Error(`Signup failed: ${response.data?.error || response.statusText}`);
  }

  return {
    token: response.data.token,
    user: response.data.user,
    client: createAuthClient(response.data.token),
  };
}

/**
 * Wait for a condition to be true
 */
export async function waitFor(condition, options = {}) {
  const {
    timeout = 5000,
    interval = 100,
    timeoutMessage = 'Condition not met within timeout',
  } = options;

  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error(timeoutMessage);
}

/**
 * Retry a function with exponential backoff
 */
export async function retry(fn, options = {}) {
  const {
    maxAttempts = 3,
    initialDelay = 100,
    maxDelay = 5000,
    backoffFactor = 2,
  } = options;

  let attempt = 0;
  let delay = initialDelay;

  while (attempt < maxAttempts) {
    try {
      return await fn();
    } catch (error) {
      attempt++;

      if (attempt >= maxAttempts) {
        throw error;
      }

      await new Promise(resolve => setTimeout(resolve, delay));
      delay = Math.min(delay * backoffFactor, maxDelay);
    }
  }
}

export default {
  request,
  get,
  post,
  put,
  patch,
  del,
  createAuthClient,
  login,
  signup,
  waitFor,
  retry,
};
