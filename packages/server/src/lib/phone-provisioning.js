/**
 * Phone Number Provisioning
 *
 * Handles Twilio phone number provisioning and release for subscribers.
 * Integrates with subscription lifecycle events.
 */

import { updateUserPhone } from './users.js';

/**
 * Search for available Twilio phone numbers
 *
 * @param {string} areaCode - Optional area code (e.g., '415')
 * @param {string} country - Country code (default 'US')
 * @param {Object} env - Environment variables
 * @returns {Array} Available phone numbers
 */
export async function searchAvailablePhoneNumbers(areaCode = null, country = 'US', env) {
  try {
    const accountSid = env.TWILIO_ACCOUNT_SID;
    const authToken = env.TWILIO_AUTH_TOKEN;

    const searchParams = new URLSearchParams({
      VoiceEnabled: 'true',
      SmsEnabled: 'true',
    });

    if (areaCode) {
      searchParams.append('AreaCode', areaCode);
    }

    const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/AvailablePhoneNumbers/${country}/Local.json?${searchParams}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Twilio API error: ${error}`);
    }

    const data = await response.json();

    return data.available_phone_numbers.map(number => ({
      phone_number: number.phone_number,
      friendly_name: number.friendly_name,
      locality: number.locality,
      region: number.region,
      postal_code: number.postal_code,
      capabilities: {
        voice: number.capabilities.voice,
        sms: number.capabilities.SMS,
        mms: number.capabilities.MMS,
      },
    }));
  } catch (error) {
    console.error('Error searching phone numbers:', error);
    throw error;
  }
}

/**
 * Provision a phone number for a user
 *
 * @param {string} userId - User ID
 * @param {string} phoneNumber - Phone number to provision (E.164 format)
 * @param {Object} env - Environment variables
 * @returns {Object} Provisioned phone details
 */
export async function provisionPhoneNumber(userId, phoneNumber = null, env) {
  try {
    const accountSid = env.TWILIO_ACCOUNT_SID;
    const authToken = env.TWILIO_AUTH_TOKEN;
    const baseUrl = env.BASE_URL;

    // If no phone number specified, search for one
    if (!phoneNumber) {
      console.log(`Searching for available phone numbers...`);
      const availableNumbers = await searchAvailablePhoneNumbers(null, 'US', env);

      if (availableNumbers.length === 0) {
        throw new Error('No available phone numbers found');
      }

      phoneNumber = availableNumbers[0].phone_number;
      console.log(`Selected phone number: ${phoneNumber}`);
    }

    // Purchase the phone number
    const purchaseUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers.json`;

    const formData = new URLSearchParams({
      PhoneNumber: phoneNumber,
      VoiceUrl: `${baseUrl}/voice/inbound`,
      VoiceMethod: 'POST',
      SmsUrl: `${baseUrl}/sms/inbound`,
      SmsMethod: 'POST',
      StatusCallback: `${baseUrl}/phone/status/${userId}`,
      StatusCallbackMethod: 'POST',
      FriendlyName: `xSwarm - User ${userId}`,
    });

    const response = await fetch(purchaseUrl, {
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to purchase phone number: ${error}`);
    }

    const data = await response.json();

    // Update user record with new phone number
    await updateUserPhone(userId, data.phone_number, env);

    console.log(`Provisioned phone number ${data.phone_number} for user ${userId}`);

    return {
      phone_number: data.phone_number,
      sid: data.sid,
      friendly_name: data.friendly_name,
      voice_url: data.voice_url,
      sms_url: data.sms_url,
      capabilities: {
        voice: data.capabilities.voice,
        sms: data.capabilities.sms,
        mms: data.capabilities.mms,
      },
    };
  } catch (error) {
    console.error('Error provisioning phone number:', error);
    throw error;
  }
}

/**
 * Release a phone number
 *
 * @param {string} userId - User ID
 * @param {string} phoneNumber - Phone number to release (E.164 format)
 * @param {Object} env - Environment variables
 * @returns {boolean} True if released successfully
 */
export async function releasePhoneNumber(userId, phoneNumber, env) {
  try {
    const accountSid = env.TWILIO_ACCOUNT_SID;
    const authToken = env.TWILIO_AUTH_TOKEN;

    // First, find the phone number SID
    const listUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers.json?PhoneNumber=${encodeURIComponent(phoneNumber)}`;

    const listResponse = await fetch(listUrl, {
      method: 'GET',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
      },
    });

    if (!listResponse.ok) {
      const error = await listResponse.text();
      throw new Error(`Failed to find phone number: ${error}`);
    }

    const listData = await listResponse.json();

    if (listData.incoming_phone_numbers.length === 0) {
      console.log(`Phone number ${phoneNumber} not found, may already be released`);
      // Clear from user record anyway
      await updateUserPhone(userId, null, env);
      return true;
    }

    const phoneSid = listData.incoming_phone_numbers[0].sid;

    // Release the phone number
    const deleteUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers/${phoneSid}.json`;

    const deleteResponse = await fetch(deleteUrl, {
      method: 'DELETE',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
      },
    });

    if (!deleteResponse.ok && deleteResponse.status !== 404) {
      const error = await deleteResponse.text();
      throw new Error(`Failed to release phone number: ${error}`);
    }

    // Clear from user record
    await updateUserPhone(userId, null, env);

    console.log(`Released phone number ${phoneNumber} for user ${userId}`);

    return true;
  } catch (error) {
    console.error('Error releasing phone number:', error);
    throw error;
  }
}

/**
 * Get phone number details from Twilio
 *
 * @param {string} phoneNumber - Phone number (E.164 format)
 * @param {Object} env - Environment variables
 * @returns {Object} Phone number details
 */
export async function getPhoneNumberDetails(phoneNumber, env) {
  try {
    const accountSid = env.TWILIO_ACCOUNT_SID;
    const authToken = env.TWILIO_AUTH_TOKEN;

    const listUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers.json?PhoneNumber=${encodeURIComponent(phoneNumber)}`;

    const response = await fetch(listUrl, {
      method: 'GET',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to get phone number details: ${error}`);
    }

    const data = await response.json();

    if (data.incoming_phone_numbers.length === 0) {
      return null;
    }

    const number = data.incoming_phone_numbers[0];

    return {
      phone_number: number.phone_number,
      sid: number.sid,
      friendly_name: number.friendly_name,
      voice_url: number.voice_url,
      sms_url: number.sms_url,
      status_callback: number.status_callback,
      capabilities: {
        voice: number.capabilities.voice,
        sms: number.capabilities.sms,
        mms: number.capabilities.mms,
      },
      date_created: number.date_created,
      date_updated: number.date_updated,
    };
  } catch (error) {
    console.error('Error getting phone number details:', error);
    throw error;
  }
}

/**
 * Update phone number webhook URLs
 *
 * @param {string} phoneNumber - Phone number (E.164 format)
 * @param {Object} webhooks - Webhook URLs { voice_url, sms_url }
 * @param {Object} env - Environment variables
 * @returns {Object} Updated phone number details
 */
export async function updatePhoneWebhooks(phoneNumber, webhooks, env) {
  try {
    const accountSid = env.TWILIO_ACCOUNT_SID;
    const authToken = env.TWILIO_AUTH_TOKEN;

    // First, find the phone number SID
    const listUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers.json?PhoneNumber=${encodeURIComponent(phoneNumber)}`;

    const listResponse = await fetch(listUrl, {
      method: 'GET',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
      },
    });

    if (!listResponse.ok) {
      const error = await listResponse.text();
      throw new Error(`Failed to find phone number: ${error}`);
    }

    const listData = await listResponse.json();

    if (listData.incoming_phone_numbers.length === 0) {
      throw new Error(`Phone number ${phoneNumber} not found`);
    }

    const phoneSid = listData.incoming_phone_numbers[0].sid;

    // Update the phone number
    const updateUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers/${phoneSid}.json`;

    const formData = new URLSearchParams();

    if (webhooks.voice_url) {
      formData.append('VoiceUrl', webhooks.voice_url);
      formData.append('VoiceMethod', 'POST');
    }

    if (webhooks.sms_url) {
      formData.append('SmsUrl', webhooks.sms_url);
      formData.append('SmsMethod', 'POST');
    }

    const updateResponse = await fetch(updateUrl, {
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    if (!updateResponse.ok) {
      const error = await updateResponse.text();
      throw new Error(`Failed to update phone number webhooks: ${error}`);
    }

    const data = await updateResponse.json();

    console.log(`Updated webhooks for phone number ${phoneNumber}`);

    return {
      phone_number: data.phone_number,
      voice_url: data.voice_url,
      sms_url: data.sms_url,
    };
  } catch (error) {
    console.error('Error updating phone webhooks:', error);
    throw error;
  }
}

/**
 * List all provisioned phone numbers for the account
 *
 * @param {Object} env - Environment variables
 * @returns {Array} List of phone numbers
 */
export async function listProvisionedPhoneNumbers(env) {
  try {
    const accountSid = env.TWILIO_ACCOUNT_SID;
    const authToken = env.TWILIO_AUTH_TOKEN;

    const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers.json`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to list phone numbers: ${error}`);
    }

    const data = await response.json();

    return data.incoming_phone_numbers.map(number => ({
      phone_number: number.phone_number,
      sid: number.sid,
      friendly_name: number.friendly_name,
      capabilities: {
        voice: number.capabilities.voice,
        sms: number.capabilities.sms,
        mms: number.capabilities.mms,
      },
    }));
  } catch (error) {
    console.error('Error listing phone numbers:', error);
    throw error;
  }
}
