/**
 * Test Routes - API Testing and R2 Operations
 *
 * GET  /test - Basic health check with environment info
 * GET  /test/r2 - List files in R2 bucket
 * PUT  /test/r2/:filename - Upload file to R2
 * GET  /test/r2/:filename - Download file from R2
 * DELETE /test/r2/:filename - Delete file from R2
 */

/**
 * Basic test endpoint
 */
export async function handleTestEndpoint(request, env) {
  return new Response(JSON.stringify({
    status: 'ok',
    message: 'Test endpoint is working',
    environment: env.ENVIRONMENT || 'unknown',
    timestamp: new Date().toISOString(),
    bindings: {
      storage: env.R2_BUCKET ? 'connected' : 'not configured',
    },
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * List all files in R2 bucket
 */
export async function handleR2List(request, env) {
  if (!env.R2_BUCKET) {
    return new Response(JSON.stringify({
      error: 'R2 storage not configured',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    // List objects with pagination support
    const url = new URL(request.url);
    const prefix = url.searchParams.get('prefix') || 'test/';
    const limit = parseInt(url.searchParams.get('limit') || '100');

    const listed = await env.R2_BUCKET.list({ prefix, limit });

    const objects = listed.objects.map(obj => ({
      key: obj.key,
      size: obj.size,
      uploaded: obj.uploaded,
    }));

    return new Response(JSON.stringify({
      prefix,
      count: objects.length,
      truncated: listed.truncated,
      objects,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Failed to list R2 objects',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Upload file to R2
 */
export async function handleR2Upload(request, env, filename) {
  if (!env.R2_BUCKET) {
    return new Response(JSON.stringify({
      error: 'R2 storage not configured',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const key = `test/${filename}`;
    const contentType = request.headers.get('content-type') || 'application/octet-stream';

    // Get request body
    const body = await request.arrayBuffer();

    // Upload to R2
    await env.R2_BUCKET.put(key, body, {
      httpMetadata: {
        contentType,
      },
    });

    return new Response(JSON.stringify({
      success: true,
      message: 'File uploaded successfully',
      key,
      size: body.byteLength,
      contentType,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Failed to upload file',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Download file from R2
 */
export async function handleR2Download(request, env, filename) {
  if (!env.R2_BUCKET) {
    return new Response(JSON.stringify({
      error: 'R2 storage not configured',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const key = `test/${filename}`;
    const object = await env.R2_BUCKET.get(key);

    if (!object) {
      return new Response(JSON.stringify({
        error: 'File not found',
        key,
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(object.body, {
      headers: {
        'Content-Type': object.httpMetadata?.contentType || 'application/octet-stream',
        'Content-Length': object.size,
        'ETag': object.httpEtag,
      },
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Failed to download file',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Delete file from R2
 */
export async function handleR2Delete(request, env, filename) {
  if (!env.R2_BUCKET) {
    return new Response(JSON.stringify({
      error: 'R2 storage not configured',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const key = `test/${filename}`;

    // Check if file exists first
    const object = await env.R2_BUCKET.head(key);
    if (!object) {
      return new Response(JSON.stringify({
        error: 'File not found',
        key,
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Delete the file
    await env.R2_BUCKET.delete(key);

    return new Response(JSON.stringify({
      success: true,
      message: 'File deleted successfully',
      key,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Failed to delete file',
      message: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
