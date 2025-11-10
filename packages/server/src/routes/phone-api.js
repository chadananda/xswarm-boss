/**
 * Phone Provisioning API Endpoints
 *
 * Allows users to provision and manage their phone numbers.
 */

import {
  provisionPhoneNumber,
  releasePhoneNumber,
  getPhoneNumberDetails,
  searchAvailablePhoneNumbers,
} from '../lib/phone-provisioning.js';

/**
 * POST /api/phone/provision - Provision a phone number
 */
export async function handleProvisionPhone(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if user has a paid subscription
    if (user.subscription_tier === 'ai_buddy') {
      return new Response(JSON.stringify({
        error: 'Phone provisioning requires a paid subscription',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if user already has a phone
    if (user.xswarm_phone) {
      return new Response(JSON.stringify({
        error: 'Phone number already provisioned',
        phone_number: user.xswarm_phone,
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json().catch(() => ({}));
    const { phone_number, area_code } = body;

    // If area code provided, search for numbers first
    let selectedNumber = phone_number;

    if (area_code && !selectedNumber) {
      const availableNumbers = await searchAvailablePhoneNumbers(area_code, 'US', env);
      if (availableNumbers.length === 0) {
        return new Response(JSON.stringify({
          error: 'No phone numbers available in that area code',
        }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      selectedNumber = availableNumbers[0].phone_number;
    }

    // Provision the phone number
    const phoneDetails = await provisionPhoneNumber(user.id, selectedNumber, env);

    return new Response(JSON.stringify({
      message: 'Phone number provisioned successfully',
      phone_number: phoneDetails.phone_number,
      capabilities: phoneDetails.capabilities,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error provisioning phone:', error);
    return new Response(JSON.stringify({
      error: 'Failed to provision phone number',
      details: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * DELETE /api/phone/release - Release phone number
 */
export async function handleReleasePhone(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (!user.xswarm_phone) {
      return new Response(JSON.stringify({
        error: 'No phone number to release',
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    await releasePhoneNumber(user.id, user.xswarm_phone, env);

    return new Response(JSON.stringify({
      message: 'Phone number released successfully',
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error releasing phone:', error);
    return new Response(JSON.stringify({
      error: 'Failed to release phone number',
      details: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/phone/details - Get phone number details
 */
export async function handleGetPhoneDetails(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (!user.xswarm_phone) {
      return new Response(JSON.stringify({
        error: 'No phone number provisioned',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const details = await getPhoneNumberDetails(user.xswarm_phone, env);

    if (!details) {
      return new Response(JSON.stringify({
        error: 'Phone number not found',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify(details), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error getting phone details:', error);
    return new Response(JSON.stringify({
      error: 'Failed to get phone details',
      details: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/phone/search - Search available phone numbers
 */
export async function handleSearchPhoneNumbers(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if user has a paid subscription
    if (user.subscription_tier === 'ai_buddy') {
      return new Response(JSON.stringify({
        error: 'Phone search requires a paid subscription',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const url = new URL(request.url);
    const areaCode = url.searchParams.get('area_code');
    const country = url.searchParams.get('country') || 'US';

    const numbers = await searchAvailablePhoneNumbers(areaCode, country, env);

    return new Response(JSON.stringify({
      count: numbers.length,
      numbers: numbers.slice(0, 10), // Return max 10 numbers
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error searching phone numbers:', error);
    return new Response(JSON.stringify({
      error: 'Failed to search phone numbers',
      details: error.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * POST /phone/status/:userId - Handle phone provisioning status callback
 */
export async function handlePhoneStatusCallback(request, env, userId) {
  try {
    const formData = await request.formData();
    const status = formData.get('StatusCallbackEvent');
    const phoneNumber = formData.get('PhoneNumber');

    console.log(`Phone status callback for user ${userId}: ${status} (${phoneNumber})`);

    // Log the status for debugging/monitoring
    // In production, you might want to send notifications or update database

    return new Response('OK', { status: 200 });
  } catch (error) {
    console.error('Error handling phone status callback:', error);
    return new Response('Error', { status: 500 });
  }
}
