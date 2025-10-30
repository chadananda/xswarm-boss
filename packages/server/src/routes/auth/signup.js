/**
 * User Signup Route
 *
 * POST /auth/signup
 * Creates new user account and sends email verification
 */

import { getUserByEmail, createUser, setVerificationToken } from '../../lib/users.js';
import { hashPassword, validatePasswordStrength } from '../../lib/password.js';
import { generateEmailVerificationToken } from '../../lib/jwt.js';
import { getVerificationEmailTemplate } from '../../lib/email-templates.js';
import { sendEmail } from '../../lib/send-email.js';

/**
 * Handle user signup
 *
 * @param {Request} request - Fetch API request
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} JSON response
 */
export async function handleSignup(request, env) {
  try {
    // Parse request body
    const body = await request.json();
    const { email, password, firstName, lastName, plan } = body;

    // Validate required fields
    if (!email || !password || !firstName || !lastName || !plan) {
      return new Response(
        JSON.stringify({
          error: 'Missing required fields: email, password, firstName, lastName, plan',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return new Response(
        JSON.stringify({
          error: 'Invalid email format',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate password strength
    const passwordValidation = validatePasswordStrength(password);
    if (!passwordValidation.valid) {
      return new Response(
        JSON.stringify({
          error: 'Password does not meet requirements',
          details: passwordValidation.errors,
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate plan
    const validPlans = ['free', 'personal', 'professional', 'enterprise'];
    if (!validPlans.includes(plan)) {
      return new Response(
        JSON.stringify({
          error: 'Invalid plan',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Check if user already exists
    const existingUser = await getUserByEmail(email, env);
    if (existingUser) {
      return new Response(
        JSON.stringify({
          error: 'Email already registered',
        }),
        {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Hash password
    const passwordHash = await hashPassword(password);

    // Generate email verification token
    const verificationToken = generateEmailVerificationToken();

    // Create user record
    const newUser = await createUser(
      {
        id: crypto.randomUUID(),
        username: email.split('@')[0], // Use email prefix as username
        name: `${firstName} ${lastName}`,
        email: email,
        user_phone: null,
        xswarm_email: null, // Will be assigned after subscription
        xswarm_phone: null,
        subscription_tier: plan,
        persona: 'boss',
        wake_word: null,
        stripe_customer_id: null,
        stripe_subscription_id: null,
      },
      env
    );

    // Set password hash (separate from createUser since it doesn't handle password)
    await updatePasswordHash(newUser.id, passwordHash, env);

    // Set verification token
    await setVerificationToken(
      newUser.id,
      verificationToken.token,
      verificationToken.expires,
      env
    );

    // Send verification email
    const baseUrl = env.BASE_URL || 'https://xswarm.ai';
    const verificationLink = `${baseUrl}/verify-email?token=${verificationToken.token}`;

    const emailTemplate = getVerificationEmailTemplate(verificationLink, firstName);

    await sendEmail(
      {
        to: email,
        from: env.FROM_EMAIL || 'noreply@xswarm.ai',
        subject: emailTemplate.subject,
        text: emailTemplate.text,
        html: emailTemplate.html,
      },
      env
    );

    console.log(`User signup successful: ${email}`);

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Account created! Please check your email to verify your account.',
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('Signup error:', error);
    return new Response(
      JSON.stringify({
        error: 'Failed to create account',
        details: error.message,
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// Import updatePasswordHash for setting password after user creation
import { updatePasswordHash } from '../../lib/users.js';
