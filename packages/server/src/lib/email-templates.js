/**
 * Email Templates for Authentication
 *
 * Provides HTML and text templates for:
 * - Email verification
 * - Password reset
 * - Welcome email
 */

/**
 * Get email verification template
 *
 * @param {string} verificationLink - Full URL for email verification
 * @param {string} userName - User's first name
 * @returns {Object} { subject, text, html }
 */
export function getVerificationEmailTemplate(verificationLink, userName = 'there') {
  const subject = 'Verify your xSwarm account';

  const text = `Hi ${userName},

Thanks for signing up for xSwarm AI Assistant!

Please verify your email address by clicking the link below:

${verificationLink}

This link will expire in 24 hours.

If you didn't create an account with xSwarm, you can safely ignore this email.

Best regards,
The xSwarm Team

---
xSwarm AI Assistant - Voice-First AI for Developers
https://xswarm.ai`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #00d9ff; border-radius: 8px;">
          <!-- Header -->
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #00d9ff;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">xSwarm AI Assistant</h1>
              <p style="margin: 10px 0 0 0; color: #a0a0a0; font-size: 14px;">Voice-First AI for Developers</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 40px 30px;">
              <h2 style="margin: 0 0 20px 0; color: #00d9ff; font-size: 20px;">Verify Your Email</h2>

              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Hi ${userName},
              </p>

              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Thanks for signing up for xSwarm AI Assistant! Please verify your email address to activate your account.
              </p>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 30px 0;">
                    <a href="${verificationLink}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00d9ff, #0099bb); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Verify Email Address</a>
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 10px 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                Or copy and paste this link into your browser:
              </p>

              <p style="margin: 0 0 20px 0; padding: 15px; background-color: #050810; border: 1px solid #1a2332; border-radius: 4px; word-break: break-all; font-size: 12px; color: #00d9ff;">
                ${verificationLink}
              </p>

              <p style="margin: 0 0 10px 0; line-height: 1.6; color: #e0e0e0;">
                <strong style="color: #ffcc00;">⏱️ This link expires in 24 hours.</strong>
              </p>

              <p style="margin: 20px 0 0 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                If you didn't create an account with xSwarm, you can safely ignore this email.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px;">
                Best regards,<br>
                The xSwarm Team
              </p>
              <p style="margin: 10px 0 0 0; color: #00d9ff; font-size: 12px;">
                <a href="https://xswarm.ai" style="color: #00d9ff; text-decoration: none;">xswarm.ai</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get password reset email template
 *
 * @param {string} resetLink - Full URL for password reset
 * @param {string} userName - User's first name
 * @returns {Object} { subject, text, html }
 */
export function getPasswordResetEmailTemplate(resetLink, userName = 'there') {
  const subject = 'Reset your xSwarm password';

  const text = `Hi ${userName},

We received a request to reset your xSwarm account password.

Click the link below to reset your password:

${resetLink}

This link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.

Best regards,
The xSwarm Team

---
xSwarm AI Assistant - Voice-First AI for Developers
https://xswarm.ai`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #ff4444; border-radius: 8px;">
          <!-- Header -->
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #ff4444;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">xSwarm AI Assistant</h1>
              <p style="margin: 10px 0 0 0; color: #a0a0a0; font-size: 14px;">Voice-First AI for Developers</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 40px 30px;">
              <h2 style="margin: 0 0 20px 0; color: #ff4444; font-size: 20px;">🔒 Reset Your Password</h2>

              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Hi ${userName},
              </p>

              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                We received a request to reset your xSwarm account password. Click the button below to set a new password.
              </p>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 30px 0;">
                    <a href="${resetLink}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #ff4444, #cc0000); color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Reset Password</a>
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 10px 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                Or copy and paste this link into your browser:
              </p>

              <p style="margin: 0 0 20px 0; padding: 15px; background-color: #050810; border: 1px solid #1a2332; border-radius: 4px; word-break: break-all; font-size: 12px; color: #00d9ff;">
                ${resetLink}
              </p>

              <p style="margin: 0 0 10px 0; line-height: 1.6; color: #e0e0e0;">
                <strong style="color: #ffcc00;">⏱️ This link expires in 1 hour.</strong>
              </p>

              <p style="margin: 20px 0 0 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px;">
                Best regards,<br>
                The xSwarm Team
              </p>
              <p style="margin: 10px 0 0 0; color: #00d9ff; font-size: 12px;">
                <a href="https://xswarm.ai" style="color: #00d9ff; text-decoration: none;">xswarm.ai</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get welcome email template (sent after verification)
 *
 * @param {string} userName - User's first name
 * @param {string} userTier - User's subscription tier
 * @returns {Object} { subject, text, html }
 */
export function getWelcomeEmailTemplate(userName = 'there', userTier = 'free') {
  const subject = 'Welcome to xSwarm AI Assistant!';

  const features = {
    free: ['Local AI assistant', 'Command-line interface', 'Basic project management'],
    personal: ['SMS communication', 'Voice calls', 'Email support', 'All free features'],
    professional: ['Full xSwarm coding tools', 'Advanced AI features', 'Priority support', 'All personal features'],
    enterprise: ['Phone support', 'Custom integrations', 'Dedicated account manager', 'All professional features'],
  };

  const tierFeatures = features[userTier] || features.free;
  const featureList = tierFeatures.map(f => `- ${f}`).join('\n');
  const featureListHtml = tierFeatures.map(f => `<li style="margin: 5px 0; color: #e0e0e0;">${f}</li>`).join('');

  const text = `Hi ${userName},

Welcome to xSwarm AI Assistant! 🚀

Your account has been verified and you're all set to go!

Your ${userTier} plan includes:

${featureList}

Getting started:

1. Download the xSwarm CLI: npm install -g @xswarm/cli
2. Log in with your account: xswarm login
3. Start your first project: xswarm new my-project
4. Ask your AI assistant for help: xswarm ask "How do I...?"

Need help? Check out our documentation at https://docs.xswarm.ai or reply to this email.

Happy coding!

Best regards,
The xSwarm Team

---
xSwarm AI Assistant - Voice-First AI for Developers
https://xswarm.ai`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #00ff88; border-radius: 8px;">
          <!-- Header -->
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #00ff88;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">🚀 Welcome to xSwarm!</h1>
              <p style="margin: 10px 0 0 0; color: #a0a0a0; font-size: 14px;">Voice-First AI for Developers</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 40px 30px;">
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0; font-size: 18px;">
                Hi ${userName},
              </p>

              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Welcome to xSwarm AI Assistant! Your account has been verified and you're all set to go! 🎉
              </p>

              <h3 style="margin: 30px 0 15px 0; color: #00ff88; font-size: 18px;">Your ${userTier.charAt(0).toUpperCase() + userTier.slice(1)} Plan Includes:</h3>

              <ul style="margin: 0 0 30px 20px; padding: 0; list-style-type: none;">
                ${featureListHtml}
              </ul>

              <h3 style="margin: 30px 0 15px 0; color: #00d9ff; font-size: 18px;">Getting Started</h3>

              <ol style="margin: 0 0 30px 20px; padding: 0; line-height: 2; color: #e0e0e0;">
                <li>Download the xSwarm CLI: <code style="background-color: #050810; padding: 4px 8px; border-radius: 4px; color: #00d9ff;">npm install -g @xswarm/cli</code></li>
                <li>Log in with your account: <code style="background-color: #050810; padding: 4px 8px; border-radius: 4px; color: #00d9ff;">xswarm login</code></li>
                <li>Start your first project: <code style="background-color: #050810; padding: 4px 8px; border-radius: 4px; color: #00d9ff;">xswarm new my-project</code></li>
                <li>Ask your AI assistant for help: <code style="background-color: #050810; padding: 4px 8px; border-radius: 4px; color: #00d9ff;">xswarm ask "How do I...?"</code></li>
              </ol>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 20px 0;">
                    <a href="https://docs.xswarm.ai" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00d9ff, #0099bb); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">View Documentation</a>
                  </td>
                </tr>
              </table>

              <p style="margin: 20px 0 0 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                Need help? Check out our <a href="https://docs.xswarm.ai" style="color: #00d9ff; text-decoration: none;">documentation</a> or reply to this email.
              </p>

              <p style="margin: 20px 0 0 0; line-height: 1.6; color: #e0e0e0;">
                Happy coding! 💻
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px;">
                Best regards,<br>
                The xSwarm Team
              </p>
              <p style="margin: 10px 0 0 0; color: #00d9ff; font-size: 12px;">
                <a href="https://xswarm.ai" style="color: #00d9ff; text-decoration: none;">xswarm.ai</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get team invitation email template
 *
 * @param {string} teamName - Team name
 * @param {string} inviterName - Name of person who invited
 * @param {string} invitationLink - Full URL for accepting invitation
 * @param {string} role - Role being offered (admin, member, viewer)
 * @returns {Object} { subject, text, html }
 */
export function getTeamInvitationEmailTemplate(teamName, inviterName, invitationLink, role = 'member') {
  const subject = `You've been invited to join ${teamName} on xSwarm`;

  const roleDescriptions = {
    admin: 'team administrator with the ability to manage members and settings',
    member: 'team member with full access to team features',
    viewer: 'team viewer with read-only access',
  };

  const roleDescription = roleDescriptions[role] || roleDescriptions.member;

  const text = `Hi there,

${inviterName} has invited you to join the team "${teamName}" on xSwarm AI Assistant!

You've been invited as a ${role}, giving you ${roleDescription}.

Click the link below to accept the invitation:

${invitationLink}

This invitation will expire in 7 days.

If you don't have an xSwarm account yet, you'll be able to create one when you accept the invitation.

Best regards,
The xSwarm Team

---
xSwarm AI Assistant - Voice-First AI for Developers
https://xswarm.ai`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #00ff88; border-radius: 8px;">
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #00ff88;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">xSwarm AI Assistant</h1>
              <p style="margin: 10px 0 0 0; color: #a0a0a0; font-size: 14px;">Team Collaboration</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <h2 style="margin: 0 0 20px 0; color: #00ff88; font-size: 20px;">You're Invited to Join a Team!</h2>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                <strong style="color: #00d9ff;">${inviterName}</strong> has invited you to join the team <strong style="color: #00d9ff;">"${teamName}"</strong> on xSwarm AI Assistant!
              </p>
              <div style="margin: 20px 0; padding: 20px; background-color: #050810; border-left: 4px solid #00ff88; border-radius: 4px;">
                <p style="margin: 0; color: #e0e0e0; font-size: 14px;">
                  <strong style="color: #00ff88;">Your Role:</strong> ${role.charAt(0).toUpperCase() + role.slice(1)}
                </p>
                <p style="margin: 10px 0 0 0; color: #a0a0a0; font-size: 13px;">${roleDescription}</p>
              </div>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 30px 0;">
                    <a href="${invitationLink}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00ff88, #00bb66); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Accept Invitation</a>
                  </td>
                </tr>
              </table>
              <p style="margin: 0 0 10px 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">Or copy and paste this link into your browser:</p>
              <p style="margin: 0 0 20px 0; padding: 15px; background-color: #050810; border: 1px solid #1a2332; border-radius: 4px; word-break: break-all; font-size: 12px; color: #00d9ff;">${invitationLink}</p>
              <p style="margin: 0 0 10px 0; line-height: 1.6; color: #e0e0e0;"><strong style="color: #ffcc00;">⏱️ This invitation expires in 7 days.</strong></p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px;">Best regards,<br>The xSwarm Team</p>
              <p style="margin: 10px 0 0 0; color: #00d9ff; font-size: 12px;"><a href="https://xswarm.ai" style="color: #00d9ff; text-decoration: none;">xswarm.ai</a></p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get team welcome email template (sent after joining team)
 */
export function getTeamWelcomeEmailTemplate(teamName, userName = 'there', role = 'member') {
  const subject = `Welcome to ${teamName}!`;

  const text = `Hi ${userName},

Welcome to the team "${teamName}" on xSwarm AI Assistant!

You've joined as a ${role} and now have access to all team features and resources.

Log in to your xSwarm account to get started: https://xswarm.ai/login

Best regards,
The xSwarm Team`;

  const html = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr><td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #00ff88; border-radius: 8px;">
          <tr><td style="padding: 30px; text-align: center; border-bottom: 2px solid #00ff88;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">Welcome to the Team!</h1>
            </td></tr>
          <tr><td style="padding: 40px 30px;">
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">Hi ${userName},</p>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">Welcome to <strong style="color: #00ff88;">"${teamName}"</strong> on xSwarm AI Assistant!</p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td align="center" style="padding: 20px 0;">
                    <a href="https://xswarm.ai/login" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00d9ff, #0099bb); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Go to Dashboard</a>
                  </td></tr>
              </table>
            </td></tr>
          <tr><td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0; color: #a0a0a0; font-size: 12px;">Best regards,<br>The xSwarm Team</p>
            </td></tr>
        </table>
      </td></tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get team removal email template
 */
export function getTeamRemovedEmailTemplate(teamName, userName = 'there') {
  const subject = `You've been removed from ${teamName}`;

  const text = `Hi ${userName},

You've been removed from the team "${teamName}" on xSwarm AI Assistant.

You no longer have access to this team's resources and features.

Best regards,
The xSwarm Team`;

  const html = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr><td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #ff4444; border-radius: 8px;">
          <tr><td style="padding: 30px; text-align: center; border-bottom: 2px solid #ff4444;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">Team Membership Removed</h1>
            </td></tr>
          <tr><td style="padding: 40px 30px;">
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">Hi ${userName},</p>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">You've been removed from the team <strong style="color: #ff4444;">"${teamName}"</strong> on xSwarm AI Assistant.</p>
            </td></tr>
          <tr><td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0; color: #a0a0a0; font-size: 12px;">Best regards,<br>The xSwarm Team</p>
            </td></tr>
        </table>
      </td></tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get suggestion submission confirmation template
 *
 * @param {string} suggestionId - Suggestion ID
 * @param {string} title - Suggestion title
 * @param {string} userName - User's name (or 'Anonymous')
 * @returns {Object} { subject, text, html }
 */
export function getSuggestionConfirmationTemplate(suggestionId, title, userName = 'there') {
  const subject = 'Thanks for your suggestion!';
  const suggestionUrl = `https://xswarm.ai/suggestions/${suggestionId}`;

  const text = `Hi ${userName},

Thank you for submitting your suggestion: "${title}"

We've received your feedback and our team will review it shortly. You can track the status of your suggestion at:

${suggestionUrl}

Your input helps us build a better product for everyone!

Best regards,
The xSwarm Team

---
xSwarm AI Assistant - Voice-First AI for Developers
https://xswarm.ai`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #00ff88; border-radius: 8px;">
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #00ff88;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">xSwarm AI Assistant</h1>
              <p style="margin: 10px 0 0 0; color: #a0a0a0; font-size: 14px;">Thank You!</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <h2 style="margin: 0 0 20px 0; color: #00ff88; font-size: 20px;">We received your suggestion!</h2>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">Hi ${userName},</p>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Thank you for submitting your suggestion:
              </p>
              <div style="margin: 20px 0; padding: 20px; background-color: #050810; border-left: 4px solid #00ff88; border-radius: 4px;">
                <p style="margin: 0; color: #00d9ff; font-size: 16px; font-weight: bold;">"${title}"</p>
              </div>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Our team will review your feedback shortly. You can track the status of your suggestion anytime.
              </p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 20px 0;">
                    <a href="${suggestionUrl}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00ff88, #00bb66); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Track Your Suggestion</a>
                  </td>
                </tr>
              </table>
              <p style="margin: 20px 0 0 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                Your input helps us build a better product for everyone!
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px;">
                Best regards,<br>The xSwarm Team
              </p>
              <p style="margin: 10px 0 0 0; color: #00d9ff; font-size: 12px;">
                <a href="https://xswarm.ai" style="color: #00d9ff; text-decoration: none;">xswarm.ai</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get admin notification for new suggestion
 *
 * @param {Object} suggestion - Suggestion data
 * @returns {Object} { subject, text, html }
 */
export function getAdminSuggestionNotificationTemplate(suggestion) {
  const subject = `New ${suggestion.category.replace('_', ' ')}: ${suggestion.title}`;
  const adminUrl = `https://xswarm.ai/admin/suggestions/${suggestion.id}`;
  const submitter = suggestion.user_id ? suggestion.user_name : `Anonymous (${suggestion.email})`;

  const text = `New suggestion submitted:

Title: ${suggestion.title}
Category: ${suggestion.category}
Submitted by: ${submitter}

Description:
${suggestion.description}

Priority: ${suggestion.priority}
Status: ${suggestion.status}

Review and manage this suggestion:
${adminUrl}

---
xSwarm Admin Notification`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #ffcc00; border-radius: 8px;">
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #ffcc00;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">New Suggestion</h1>
              <p style="margin: 10px 0 0 0; color: #ffcc00; font-size: 14px;">Admin Notification</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <div style="margin: 0 0 20px 0; padding: 15px; background-color: #050810; border-left: 4px solid #00d9ff; border-radius: 4px;">
                <p style="margin: 0 0 10px 0; color: #00d9ff; font-size: 18px; font-weight: bold;">${suggestion.title}</p>
                <p style="margin: 0; color: #a0a0a0; font-size: 14px;">
                  <strong>Category:</strong> ${suggestion.category.replace('_', ' ')} |
                  <strong>Priority:</strong> ${suggestion.priority} |
                  <strong>Status:</strong> ${suggestion.status}
                </p>
              </div>
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 14px;">
                <strong>Submitted by:</strong> ${submitter}
              </p>
              <div style="margin: 20px 0; padding: 20px; background-color: #050810; border-radius: 4px;">
                <p style="margin: 0; color: #e0e0e0; line-height: 1.6;">${suggestion.description}</p>
              </div>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 20px 0;">
                    <a href="${adminUrl}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00d9ff, #0099bb); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Review & Manage</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get suggestion status update notification
 *
 * @param {Object} suggestion - Suggestion data
 * @param {string} newStatus - New status
 * @param {string} userName - User's name
 * @returns {Object} { subject, text, html }
 */
export function getSuggestionStatusUpdateTemplate(suggestion, newStatus, userName = 'there') {
  const subject = `Your suggestion has been ${newStatus.replace('_', ' ')}`;
  const suggestionUrl = `https://xswarm.ai/suggestions/${suggestion.id}`;

  const statusColors = {
    reviewed: '#00d9ff',
    in_progress: '#ffcc00',
    completed: '#00ff88',
    rejected: '#ff4444'
  };
  const statusColor = statusColors[newStatus] || '#00d9ff';

  const text = `Hi ${userName},

Your suggestion "${suggestion.title}" has been updated!

New Status: ${newStatus.replace('_', ' ').toUpperCase()}

${suggestion.admin_notes ? `Notes from our team:\n${suggestion.admin_notes}\n\n` : ''}View your suggestion:
${suggestionUrl}

Thank you for helping us improve xSwarm!

Best regards,
The xSwarm Team

---
xSwarm AI Assistant - Voice-First AI for Developers
https://xswarm.ai`;

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid ${statusColor}; border-radius: 8px;">
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid ${statusColor};">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">Suggestion Update</h1>
              <p style="margin: 10px 0 0 0; color: ${statusColor}; font-size: 16px; font-weight: bold;">
                ${newStatus.replace('_', ' ').toUpperCase()}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">Hi ${userName},</p>
              <p style="margin: 0 0 20px 0; line-height: 1.6; color: #e0e0e0;">
                Your suggestion has been updated:
              </p>
              <div style="margin: 20px 0; padding: 20px; background-color: #050810; border-left: 4px solid ${statusColor}; border-radius: 4px;">
                <p style="margin: 0 0 10px 0; color: #00d9ff; font-size: 16px; font-weight: bold;">"${suggestion.title}"</p>
                <p style="margin: 0; color: ${statusColor}; font-size: 14px;">
                  Status: ${newStatus.replace('_', ' ').toUpperCase()}
                </p>
              </div>
              ${suggestion.admin_notes ? `
              <div style="margin: 20px 0; padding: 20px; background-color: #050810; border-radius: 4px;">
                <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px; font-weight: bold;">Notes from our team:</p>
                <p style="margin: 0; color: #e0e0e0; line-height: 1.6;">${suggestion.admin_notes}</p>
              </div>
              ` : ''}
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 20px 0;">
                    <a href="${suggestionUrl}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, ${statusColor}, ${statusColor}dd); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">View Your Suggestion</a>
                  </td>
                </tr>
              </table>
              <p style="margin: 20px 0 0 0; line-height: 1.6; color: #a0a0a0; font-size: 14px;">
                Thank you for helping us improve xSwarm!
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 30px; border-top: 2px solid #1a2332; text-align: center;">
              <p style="margin: 0 0 10px 0; color: #a0a0a0; font-size: 12px;">
                Best regards,<br>The xSwarm Team
              </p>
              <p style="margin: 10px 0 0 0; color: #00d9ff; font-size: 12px;">
                <a href="https://xswarm.ai" style="color: #00d9ff; text-decoration: none;">xswarm.ai</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}

/**
 * Get weekly suggestion digest for admin
 *
 * @param {Array} topSuggestions - Top suggestions this week
 * @param {Object} stats - Weekly statistics
 * @returns {Object} { subject, text, html }
 */
export function getWeeklySuggestionDigestTemplate(topSuggestions, stats) {
  const subject = `Weekly Suggestion Digest - ${stats.new_count} new suggestions`;
  const adminUrl = 'https://xswarm.ai/admin/suggestions';

  const suggestionsList = topSuggestions.map(s =>
    `- ${s.title} (${s.upvotes} votes) - ${s.category}`
  ).join('\n');

  const text = `Weekly Suggestion Digest

This Week's Activity:
- New suggestions: ${stats.new_count}
- Total votes: ${stats.total_votes}
- Suggestions needing review: ${stats.needs_review}

Top Suggestions This Week:
${suggestionsList}

Review all suggestions:
${adminUrl}

---
xSwarm Admin Notification`;

  const suggestionsHtml = topSuggestions.map(s => `
    <div style="margin: 10px 0; padding: 15px; background-color: #050810; border-left: 4px solid #00d9ff; border-radius: 4px;">
      <p style="margin: 0 0 5px 0; color: #00d9ff; font-size: 14px; font-weight: bold;">${s.title}</p>
      <p style="margin: 0; color: #a0a0a0; font-size: 12px;">
        ${s.upvotes} votes | ${s.category.replace('_', ' ')} | ${s.status}
      </p>
    </div>
  `).join('');

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #0a0e27; color: #e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e27;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0f1419; border: 2px solid #9d4edd; border-radius: 8px;">
          <tr>
            <td style="padding: 30px; text-align: center; border-bottom: 2px solid #9d4edd;">
              <h1 style="margin: 0; color: #00d9ff; font-size: 24px;">Weekly Suggestion Digest</h1>
              <p style="margin: 10px 0 0 0; color: #9d4edd; font-size: 14px;">Admin Report</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 30px;">
              <h3 style="margin: 0 0 20px 0; color: #00ff88; font-size: 18px;">This Week's Activity</h3>
              <div style="display: flex; margin: 0 0 30px 0;">
                <div style="flex: 1; text-align: center; padding: 15px; background-color: #050810; margin-right: 10px; border-radius: 4px;">
                  <p style="margin: 0; color: #00d9ff; font-size: 24px; font-weight: bold;">${stats.new_count}</p>
                  <p style="margin: 5px 0 0 0; color: #a0a0a0; font-size: 12px;">New Suggestions</p>
                </div>
                <div style="flex: 1; text-align: center; padding: 15px; background-color: #050810; margin-right: 10px; border-radius: 4px;">
                  <p style="margin: 0; color: #00ff88; font-size: 24px; font-weight: bold;">${stats.total_votes}</p>
                  <p style="margin: 5px 0 0 0; color: #a0a0a0; font-size: 12px;">Total Votes</p>
                </div>
                <div style="flex: 1; text-align: center; padding: 15px; background-color: #050810; border-radius: 4px;">
                  <p style="margin: 0; color: #ffcc00; font-size: 24px; font-weight: bold;">${stats.needs_review}</p>
                  <p style="margin: 5px 0 0 0; color: #a0a0a0; font-size: 12px;">Need Review</p>
                </div>
              </div>
              <h3 style="margin: 30px 0 15px 0; color: #00d9ff; font-size: 18px;">Top Suggestions</h3>
              ${suggestionsHtml}
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding: 30px 0 10px 0;">
                    <a href="${adminUrl}" style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #00d9ff, #0099bb); color: #050810; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Review All Suggestions</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, text, html };
}
