/**
 * Git LFS Server for Cloudflare Workers + R2
 *
 * Implements Git LFS Batch API v1
 * Specification: https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md
 *
 * Storage: Cloudflare R2 with prefix "lfs/objects/"
 * Authentication: Bearer token (LFS_AUTH_TOKEN environment variable)
 */

const LFS_PREFIX = 'lfs/objects';
const URL_EXPIRATION = 3600; // 1 hour for presigned URLs

/**
 * Authenticate request using Bearer token
 */
function authenticate(request, env, requireWrite) {
	const authHeader = request.headers.get('Authorization');

	if (!authHeader || !authHeader.startsWith('Bearer ')) {
		return false;
	}

	const token = authHeader.substring(7); // Remove "Bearer "

	if (requireWrite) {
		// Write operations require write token
		return token === env.LFS_AUTH_TOKEN_WRITE;
	} else {
		// Read operations accept either token
		return token === env.LFS_AUTH_TOKEN_READ || token === env.LFS_AUTH_TOKEN_WRITE;
	}
}

/**
 * Get R2 object key for LFS object
 */
function getObjectKey(oid) {
	// Store as: lfs/objects/ab/cd/abcdef123...
	// This matches Git LFS convention and helps with listing
	return `${LFS_PREFIX}/${oid.substring(0, 2)}/${oid.substring(2, 4)}/${oid}`;
}

/**
 * Check if object exists in R2
 */
async function objectExists(bucket, oid) {
	const key = getObjectKey(oid);
	const object = await bucket.head(key);
	return object !== null;
}

/**
 * Generate presigned URL for R2 object access
 * Note: Cloudflare R2 doesn't support presigned URLs directly in Workers
 * So we use our own endpoints with temporary authentication
 */
function generatePresignedUrl(baseUrl, oid, operation, token) {
	const url = new URL(`/lfs/objects/${oid}`, baseUrl);
	// Use JWT or time-limited token in real implementation
	// For now, require Bearer token on each request
	return url.toString();
}

/**
 * Handle Git LFS Batch API request
 * POST /objects/batch
 */
export async function handleLFSBatch(request, env) {
	// Only accept POST requests
	if (request.method !== 'POST') {
		return new Response('Method not allowed', { status: 405 });
	}

	// Authenticate request
	const isWrite = (await request.clone().json()).operation === 'upload';
	if (!authenticate(request, env, isWrite)) {
		return new Response(JSON.stringify({
			message: 'Authentication required',
			documentation_url: 'https://github.com/chadananda/xswarm-boss',
		}), {
			status: 401,
			headers: {
				'Content-Type': 'application/vnd.git-lfs+json',
				'WWW-Authenticate': 'Bearer realm="Git LFS"',
			},
		});
	}

	// Parse request
	let batchRequest;
	try {
		batchRequest = await request.json();
	} catch (error) {
		return new Response(JSON.stringify({
			message: 'Invalid JSON request',
		}), {
			status: 400,
			headers: { 'Content-Type': 'application/vnd.git-lfs+json' },
		});
	}

	// Validate request
	if (!batchRequest.operation || !batchRequest.objects) {
		return new Response(JSON.stringify({
			message: 'Missing required fields: operation, objects',
		}), {
			status: 400,
			headers: { 'Content-Type': 'application/vnd.git-lfs+json' },
		});
	}

	// Only support basic transfer
	const transferMethod = (batchRequest.transfers && batchRequest.transfers[0]) || 'basic';
	if (transferMethod !== 'basic') {
		return new Response(JSON.stringify({
			message: `Transfer method "${transferMethod}" not supported. Only "basic" is supported.`,
		}), {
			status: 400,
			headers: { 'Content-Type': 'application/vnd.git-lfs+json' },
		});
	}

	// Process each object
	const baseUrl = new URL(request.url).origin;
	const authToken = request.headers.get('Authorization')?.substring(7) || '';

	const objects = await Promise.all(
		batchRequest.objects.map(async (obj) => {
			const exists = await objectExists(env.R2_BUCKET, obj.oid);
			const objectResponse = {
				oid: obj.oid,
				size: obj.size,
				authenticated: true,
			};

			if (batchRequest.operation === 'upload') {
				// Upload: provide upload URL if object doesn't exist
				if (!exists) {
					objectResponse.actions = {
						upload: {
							href: `${baseUrl}/lfs/objects/${obj.oid}`,
							header: {
								'Authorization': `Bearer ${authToken}`,
							},
							expires_in: URL_EXPIRATION,
						},
					};
				}
				// If exists, no actions needed (client won't upload)
			} else if (batchRequest.operation === 'download') {
				// Download: provide download URL if object exists
				if (exists) {
					objectResponse.actions = {
						download: {
							href: `${baseUrl}/lfs/objects/${obj.oid}`,
							header: {
								'Authorization': `Bearer ${authToken}`,
							},
							expires_in: URL_EXPIRATION,
						},
					};
				} else {
					// Object not found
					objectResponse.error = {
						code: 404,
						message: `Object ${obj.oid} not found`,
					};
				}
			}

			return objectResponse;
		})
	);

	// Build response
	const response = {
		transfer: 'basic',
		objects,
		hash_algo: batchRequest.hash_algo || 'sha256',
	};

	return new Response(JSON.stringify(response), {
		status: 200,
		headers: {
			'Content-Type': 'application/vnd.git-lfs+json',
		},
	});
}

/**
 * Handle LFS object upload
 * PUT /objects/{oid}
 */
export async function handleLFSUpload(request, env, oid) {
	// Only accept PUT requests
	if (request.method !== 'PUT') {
		return new Response('Method not allowed', { status: 405 });
	}

	// Authenticate (write permission required)
	if (!authenticate(request, env, true)) {
		return new Response('Unauthorized', { status: 401 });
	}

	// Validate OID format (SHA256 hex)
	if (!/^[a-f0-9]{64}$/.test(oid)) {
		return new Response('Invalid OID format', { status: 400 });
	}

	// Upload to R2
	try {
		const key = getObjectKey(oid);
		const body = request.body;

		if (!body) {
			return new Response('Missing request body', { status: 400 });
		}

		await env.R2_BUCKET.put(key, body, {
			httpMetadata: {
				contentType: 'application/octet-stream',
			},
			customMetadata: {
				'lfs-oid': oid,
				'uploaded-at': new Date().toISOString(),
			},
		});

		return new Response(null, { status: 200 });
	} catch (error) {
		console.error('LFS upload error:', error);
		return new Response('Internal server error', { status: 500 });
	}
}

/**
 * Handle LFS object download
 * GET /objects/{oid}
 */
export async function handleLFSDownload(request, env, oid) {
	// Only accept GET requests
	if (request.method !== 'GET') {
		return new Response('Method not allowed', { status: 405 });
	}

	// Authenticate (read permission required)
	if (!authenticate(request, env, false)) {
		return new Response('Unauthorized', { status: 401 });
	}

	// Validate OID format
	if (!/^[a-f0-9]{64}$/.test(oid)) {
		return new Response('Invalid OID format', { status: 400 });
	}

	// Download from R2
	try {
		const key = getObjectKey(oid);
		const object = await env.R2_BUCKET.get(key);

		if (!object) {
			return new Response('Object not found', { status: 404 });
		}

		return new Response(object.body, {
			status: 200,
			headers: {
				'Content-Type': 'application/octet-stream',
				'Content-Length': object.size.toString(),
				'Cache-Control': 'public, max-age=31536000, immutable', // Objects are content-addressed
			},
		});
	} catch (error) {
		console.error('LFS download error:', error);
		return new Response('Internal server error', { status: 500 });
	}
}

/**
 * Handle LFS object verification (optional)
 * POST /verify
 */
export async function handleLFSVerify(request, env) {
	// Authentication
	if (!authenticate(request, env, false)) {
		return new Response('Unauthorized', { status: 401 });
	}

	// Parse request
	let verifyRequest;
	try {
		verifyRequest = await request.json();
	} catch (error) {
		return new Response('Invalid JSON', { status: 400 });
	}

	// Check if object exists
	const exists = await objectExists(env.R2_BUCKET, verifyRequest.oid);

	if (exists) {
		return new Response(null, { status: 200 });
	} else {
		return new Response(JSON.stringify({
			message: `Object ${verifyRequest.oid} not found`,
		}), {
			status: 404,
			headers: { 'Content-Type': 'application/vnd.git-lfs+json' },
		});
	}
}

/**
 * Handle LFS locks API (stub implementation - locking not enforced)
 * POST /locks/verify
 */
export async function handleLFSLocksVerify(request, env) {
	// Authenticate
	if (!authenticate(request, env, false)) {
		return new Response('Unauthorized', { status: 401 });
	}

	// Return empty locks list (we don't implement locking)
	return new Response(JSON.stringify({
		ours: [],
		theirs: [],
		next_cursor: '',
	}), {
		status: 200,
		headers: { 'Content-Type': 'application/vnd.git-lfs+json' },
	});
}

/**
 * Main LFS router
 */
export async function handleLFS(request, env, pathname) {
	// Route LFS requests
	if (pathname === '/lfs/objects/batch') {
		return handleLFSBatch(request, env);
	}

	if (pathname === '/lfs/verify') {
		return handleLFSVerify(request, env);
	}

	// Lock API (stub - no actual locking enforced)
	if (pathname === '/lfs/locks/verify') {
		return handleLFSLocksVerify(request, env);
	}

	// Match /lfs/objects/{oid} for upload/download
	const objectMatch = pathname.match(/^\/lfs\/objects\/([a-f0-9]{64})$/);
	if (objectMatch) {
		const oid = objectMatch[1];

		if (request.method === 'PUT') {
			return handleLFSUpload(request, env, oid);
		} else if (request.method === 'GET') {
			return handleLFSDownload(request, env, oid);
		}
	}

	return new Response('Not found', { status: 404 });
}
