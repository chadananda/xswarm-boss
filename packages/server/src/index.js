/**
 * xSwarm Webhook Server - Cloudflare Workers
 *
 * Handles webhooks for:
 * - Twilio voice calls (POST /voice/:userId)
 * - Twilio SMS messages (POST /sms/:userId)
 * - Stripe subscription events (POST /stripe/webhook)
 */

import { handleVoiceWebhook } from './routes/voice.js';
import { handleSmsWebhook } from './routes/sms.js';
import { handleStripeWebhook } from './routes/stripe.js';
import { handleLFS } from './routes/lfs.js';
import { handleBossIntro, handleBossResponse, triggerBossCall, handleInboundCall, handleMoshiCall } from './routes/boss-call.js';
import { handleInboundEmail, sendBossEmail } from './routes/email.js';
import {
  handleGmailAuth,
  handleGmailCallback,
  handleEmailQuery,
  handleEmailBriefing,
  handleEmailSummarize,
  handleEmailCompose,
  handleEmailStatus,
  handleEmailDisconnect,
} from './routes/email-management.js';
import { handleMoshiWebSocket } from './routes/moshi-proxy.js';
import { handleGetIdentity, handleAuthValidate } from './routes/identity.js';
import { handleSignup } from './routes/auth/signup.js';
import { handleVerifyEmail } from './routes/auth/verify-email.js';
import { handleLogin } from './routes/auth/login.js';
import { handleLogout } from './routes/auth/logout.js';
import { handleForgotPassword } from './routes/auth/forgot-password.js';
import { handleResetPassword } from './routes/auth/reset-password.js';
import { handleGetMe } from './routes/auth/me.js';
import {
  handleTestEndpoint,
  handleR2List,
  handleR2Upload,
  handleR2Download,
  handleR2Delete,
} from './routes/test.js';
import {
  handleCLIMessage,
  handleSMSMessage,
  handleEmailMessage,
} from './lib/unified-message.js';
import {
  createAppointment,
  getAppointments,
  getTodaySchedule,
  getWeekSchedule,
  updateAppointment,
  deleteAppointment,
  createReminder,
  getReminders,
  updateReminder,
  scheduleNaturalLanguage,
} from './routes/calendar.js';
import {
  createProject,
  listProjects,
  getProject,
  updateProject,
  deleteProject,
  createTask,
  listTasks,
  updateTask,
  deleteTask,
  completeTask,
  syncGit,
  assignAgent,
  unassignAgent,
  getAgentWorkload,
  trackAgentCost,
  getAnalytics,
  getStalledProjects,
  getProjectStatus,
  getProjectHealth,
} from './routes/projects.js';
import { handleCreateTeam } from './routes/teams/create.js';
import { handleListTeams } from './routes/teams/list.js';
import { handleGetTeam } from './routes/teams/get.js';
import { handleUpdateTeam } from './routes/teams/update.js';
import { handleDeleteTeam } from './routes/teams/delete.js';
import { handleInviteMember } from './routes/teams/invite.js';
import { handleJoinTeam } from './routes/teams/join.js';
import { handleRemoveMember } from './routes/teams/remove-member.js';
import { handleChangeMemberRole } from './routes/teams/change-role.js';
import {
  handleEnroll,
  handleUnsubscribe,
  handleSendBatch,
  handleBatchEnroll,
  handleStats,
  handleSendGridWebhook,
  handleConvert,
} from './routes/marketing/index.js';
import { handleManualTrigger, handleScheduledEvent } from './lib/marketing-cron.js';
import {
  handleCreateSuggestion,
  handleListSuggestions,
  handleGetSuggestion,
  handleVoteSuggestion,
  handleUnvoteSuggestion,
  handleUpdateSuggestion,
  handleDeleteSuggestion,
  handleGetSuggestionStats,
} from './routes/suggestions.js';
import {
  handleCreateListing,
  handleListListings,
  handleGetListing,
  handleUpdateListing,
  handleDeleteListing,
  handleListingClick,
  handleListingReport,
  handleGetCategories,
  handleGetStats,
} from './routes/buzz/index.js';
import {
  handleGetUsage,
  handleGetBillingHistory,
  handleEstimateCosts,
  handleGetUpcomingInvoice,
} from './routes/billing-api.js';
import {
  handleProvisionPhone,
  handleReleasePhone,
  handleGetPhoneDetails,
  handleSearchPhoneNumbers,
  handlePhoneStatusCallback,
} from './routes/phone-api.js';
import {
  handleCreatePersona,
  handleListPersonas,
  handleGetActivePersona,
  handleGetPersona,
  handleUpdatePersona,
  handleDeletePersona,
  handleActivatePersona,
  handleAddExample,
  handleTrainVoice,
  handleGetTrainingStatus,
} from './routes/personas.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS headers for preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        },
      });
    }

    // Health check
    if (path === '/health' || path === '/') {
      return new Response(JSON.stringify({
        status: 'ok',
        service: 'xswarm-webhooks',
        timestamp: new Date().toISOString(),
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    try {
      // Authentication Routes
      if (path === '/auth/signup' && request.method === 'POST') {
        return await handleSignup(request, env);
      }
      if (path === '/auth/verify-email' && request.method === 'POST') {
        return await handleVerifyEmail(request, env);
      }
      if (path === '/auth/login' && request.method === 'POST') {
        return await handleLogin(request, env);
      }
      if (path === '/auth/logout' && request.method === 'POST') {
        return await handleLogout(request, env);
      }
      if (path === '/auth/forgot-password' && request.method === 'POST') {
        return await handleForgotPassword(request, env);
      }
      if (path === '/auth/reset-password' && request.method === 'POST') {
        return await handleResetPassword(request, env);
      }
      if (path === '/auth/me' && request.method === 'GET') {
        return await handleGetMe(request, env);
      }

      // Team Management Routes
      if (path === '/teams' && request.method === 'POST') {
        return await handleCreateTeam(request, env);
      }
      if (path === '/teams' && request.method === 'GET') {
        return await handleListTeams(request, env);
      }
      if (path.match(/^\/teams\/[^/]+$/) && request.method === 'GET') {
        const teamId = path.split('/')[2];
        return await handleGetTeam(request, env, teamId);
      }
      if (path.match(/^\/teams\/[^/]+$/) && request.method === 'PUT') {
        const teamId = path.split('/')[2];
        return await handleUpdateTeam(request, env, teamId);
      }
      if (path.match(/^\/teams\/[^/]+$/) && request.method === 'DELETE') {
        const teamId = path.split('/')[2];
        return await handleDeleteTeam(request, env, teamId);
      }
      if (path.match(/^\/teams\/[^/]+\/invite$/) && request.method === 'POST') {
        const teamId = path.split('/')[2];
        return await handleInviteMember(request, env, teamId);
      }
      if (path.match(/^\/teams\/join\/[^/]+$/) && request.method === 'POST') {
        const token = path.split('/')[3];
        return await handleJoinTeam(request, env, token);
      }
      if (path.match(/^\/teams\/[^/]+\/members\/[^/]+$/) && request.method === 'DELETE') {
        const teamId = path.split('/')[2];
        const userId = path.split('/')[4];
        return await handleRemoveMember(request, env, teamId, userId);
      }
      if (path.match(/^\/teams\/[^/]+\/members\/[^/]+\/role$/) && request.method === 'PUT') {
        const teamId = path.split('/')[2];
        const userId = path.split('/')[4];
        return await handleChangeMemberRole(request, env, teamId, userId);
      }

      // Identity API endpoints (for Rust client)
      if (path === '/api/identity' && request.method === 'GET') {
        return await handleGetIdentity(request, env);
      }
      if (path === '/api/auth/validate' && request.method === 'POST') {
        return await handleAuthValidate(request, env);
      }

      // MOSHI WebSocket proxy route (must be before other /voice/* routes)
      if (path === '/voice/moshi') {
        return await handleMoshiWebSocket(request, env);
      }

      // Git LFS endpoints
      if (path.startsWith('/lfs/')) {
        return await handleLFS(request, env, path);
      }

      // Test endpoints
      if (path === '/test' && request.method === 'GET') {
        return await handleTestEndpoint(request, env);
      }

      // R2 test: List files
      if (path === '/test/r2' && request.method === 'GET') {
        return await handleR2List(request, env);
      }

      // R2 test: Upload, Download, Delete
      if (path.startsWith('/test/r2/')) {
        const filename = path.split('/')[3];
        if (!filename) {
          return new Response(JSON.stringify({ error: 'Filename required' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        if (request.method === 'PUT') {
          return await handleR2Upload(request, env, filename);
        }
        if (request.method === 'GET') {
          return await handleR2Download(request, env, filename);
        }
        if (request.method === 'DELETE') {
          return await handleR2Delete(request, env, filename);
        }
      }

      // Boss call routes
      if (path === '/voice/boss-intro') {
        return await handleBossIntro(request, env);
      }
      if (path === '/voice/moshi-call') {
        return await handleMoshiCall(request, env);
      }
      if (path === '/voice/boss-response' && request.method === 'POST') {
        return await handleBossResponse(request, env);
      }
      if (path === '/api/boss/call' && request.method === 'POST') {
        return await triggerBossCall(request, env);
      }

      // Inbound call handler (when someone calls the Twilio number)
      if (path === '/voice/inbound' && request.method === 'POST') {
        return await handleInboundCall(request, env);
      }

      // Email routes
      // Inbound email handler (SendGrid Parse webhook)
      // Using unified message layer
      if (path === '/email/inbound' && request.method === 'POST') {
        const formData = await request.formData();
        return await handleEmailMessage(formData, env);
      }
      // Outbound email (Boss progress reports)
      if (path === '/api/boss/email' && request.method === 'POST') {
        return await sendBossEmail(request, env);
      }

      // Email Management API (Gmail integration)
      if (path === '/api/email/auth/gmail' && request.method === 'POST') {
        return await handleGmailAuth(request, env);
      }
      if (path === '/api/email/auth/callback' && request.method === 'GET') {
        return await handleGmailCallback(request, env);
      }
      if (path === '/api/email/query' && request.method === 'POST') {
        return await handleEmailQuery(request, env);
      }
      if (path === '/api/email/briefing' && request.method === 'GET') {
        return await handleEmailBriefing(request, env);
      }
      if (path.match(/^\/api\/email\/summarize\/[^/]+$/) && request.method === 'POST') {
        const emailId = path.split('/')[4];
        return await handleEmailSummarize(request, env, emailId);
      }
      if (path === '/api/email/compose' && request.method === 'POST') {
        return await handleEmailCompose(request, env);
      }
      if (path === '/api/email/status' && request.method === 'GET') {
        return await handleEmailStatus(request, env);
      }
      if (path === '/api/email/disconnect' && request.method === 'DELETE') {
        return await handleEmailDisconnect(request, env);
      }

      // Unified API endpoint for CLI/direct API calls
      if (path === '/api/message' && request.method === 'POST') {
        const body = await request.json();
        return await handleCLIMessage(body, env);
      }

      // Inbound SMS handler (when someone texts the Boss phone number)
      // Using unified message layer
      if (path === '/sms/inbound' && request.method === 'POST') {
        const formData = await request.formData();
        return await handleSMSMessage(formData, env);
      }

      // Twilio voice webhook: POST /voice/:userId
      if (path.startsWith('/voice/') && request.method === 'POST') {
        const userId = path.split('/')[2];
        return await handleVoiceWebhook(request, env, userId);
      }

      // Twilio SMS webhook: POST /sms/:userId
      if (path.startsWith('/sms/') && request.method === 'POST') {
        const userId = path.split('/')[2];
        return await handleSmsWebhook(request, env, userId);
      }

      // Stripe webhook: POST /stripe/webhook
      if (path === '/stripe/webhook' && request.method === 'POST') {
        return await handleStripeWebhook(request, env);
      }

      // Project Management API routes
      // Analytics and Reports
      if (path === '/api/projects/analytics' && request.method === 'GET') {
        return await getAnalytics(request, env);
      }
      if (path === '/api/projects/stalled' && request.method === 'GET') {
        return await getStalledProjects(request, env);
      }

      // Agent Management
      if (path === '/api/agents/workload' && request.method === 'GET') {
        return await getAgentWorkload(request, env);
      }
      if (path.match(/^\/api\/agents\/[^/]+\/costs$/) && request.method === 'POST') {
        const agentName = path.split('/')[3];
        return await trackAgentCost(request, env, agentName);
      }

      // Project-specific routes (must be after analytics/stalled)
      if (path.match(/^\/api\/projects\/[^/]+$/)) {
        const projectId = path.split('/')[3];
        if (request.method === 'GET') {
          return await getProject(request, env, projectId);
        }
        if (request.method === 'PUT') {
          return await updateProject(request, env, projectId);
        }
        if (request.method === 'DELETE') {
          return await deleteProject(request, env, projectId);
        }
      }

      // Project sub-routes
      if (path.match(/^\/api\/projects\/[^/]+\/status$/) && request.method === 'GET') {
        const projectId = path.split('/')[3];
        return await getProjectStatus(request, env, projectId);
      }
      if (path.match(/^\/api\/projects\/[^/]+\/health$/) && request.method === 'GET') {
        const projectId = path.split('/')[3];
        return await getProjectHealth(request, env, projectId);
      }
      if (path.match(/^\/api\/projects\/[^/]+\/sync-git$/) && request.method === 'POST') {
        const projectId = path.split('/')[3];
        return await syncGit(request, env, projectId);
      }
      if (path.match(/^\/api\/projects\/[^/]+\/assign$/)) {
        const projectId = path.split('/')[3];
        if (request.method === 'POST') {
          return await assignAgent(request, env, projectId);
        }
        if (request.method === 'DELETE') {
          return await unassignAgent(request, env, projectId);
        }
      }

      // Task routes
      if (path.match(/^\/api\/projects\/[^/]+\/tasks$/)) {
        const projectId = path.split('/')[3];
        if (request.method === 'POST') {
          return await createTask(request, env, projectId);
        }
        if (request.method === 'GET') {
          return await listTasks(request, env, projectId);
        }
      }
      if (path.match(/^\/api\/projects\/[^/]+\/tasks\/[^/]+$/)) {
        const projectId = path.split('/')[3];
        const taskId = path.split('/')[5];
        if (request.method === 'PUT') {
          return await updateTask(request, env, projectId, taskId);
        }
        if (request.method === 'DELETE') {
          return await deleteTask(request, env, projectId, taskId);
        }
      }
      if (path.match(/^\/api\/projects\/[^/]+\/tasks\/[^/]+\/complete$/) && request.method === 'POST') {
        const projectId = path.split('/')[3];
        const taskId = path.split('/')[5];
        return await completeTask(request, env, projectId, taskId);
      }

      // Project list/create (must be last to avoid conflicts)
      if (path === '/api/projects') {
        if (request.method === 'POST') {
          return await createProject(request, env);
        }
        if (request.method === 'GET') {
          return await listProjects(request, env);
        }
      }

      // Marketing Email Routes
      if (path === '/marketing/enroll' && request.method === 'POST') {
        return await handleEnroll(request, env);
      }
      if (path.match(/^\/marketing\/unsubscribe\/[^/]+$/) && request.method === 'GET') {
        const token = path.split('/')[3];
        return await handleUnsubscribe(request, env, { token });
      }
      if (path === '/marketing/send-batch' && request.method === 'POST') {
        return await handleSendBatch(request, env);
      }
      if (path === '/marketing/batch-enroll' && request.method === 'POST') {
        return await handleBatchEnroll(request, env);
      }
      if (path === '/marketing/stats' && request.method === 'GET') {
        return await handleStats(request, env);
      }
      if (path === '/marketing/webhook/sendgrid' && request.method === 'POST') {
        return await handleSendGridWebhook(request, env);
      }
      if (path === '/marketing/convert' && request.method === 'POST') {
        return await handleConvert(request, env);
      }
      if (path === '/marketing/cron-trigger' && request.method === 'POST') {
        return await handleManualTrigger(request, env);
      }

      // Suggestions API routes
      if (path === '/api/suggestions' && request.method === 'POST') {
        return await handleCreateSuggestion(request, env);
      }
      if (path === '/api/suggestions' && request.method === 'GET') {
        return await handleListSuggestions(request, env);
      }
      if (path === '/api/suggestions/stats' && request.method === 'GET') {
        return await handleGetSuggestionStats(request, env);
      }
      if (path.match(/^\/api\/suggestions\/[^/]+$/)) {
        const suggestionId = path.split('/')[3];
        if (request.method === 'GET') {
          return await handleGetSuggestion(request, env, suggestionId);
        }
        if (request.method === 'PUT') {
          return await handleUpdateSuggestion(request, env, suggestionId);
        }
        if (request.method === 'DELETE') {
          return await handleDeleteSuggestion(request, env, suggestionId);
        }
      }
      if (path.match(/^\/api\/suggestions\/[^/]+\/vote$/) && request.method === 'POST') {
        const suggestionId = path.split('/')[3];
        return await handleVoteSuggestion(request, env, suggestionId);
      }
      if (path.match(/^\/api\/suggestions\/[^/]+\/vote$/) && request.method === 'DELETE') {
        const suggestionId = path.split('/')[3];
        return await handleUnvoteSuggestion(request, env, suggestionId);
      }

      // Buzz Marketing Platform Routes
      if (path === '/buzz/listings' && request.method === 'POST') {
        return await handleCreateListing(request, env);
      }
      if (path === '/buzz/listings' && request.method === 'GET') {
        return await handleListListings(request, env);
      }
      if (path === '/buzz/categories' && request.method === 'GET') {
        return await handleGetCategories(request, env);
      }
      if (path === '/buzz/stats' && request.method === 'GET') {
        return await handleGetStats(request, env);
      }
      if (path.match(/^\/buzz\/listings\/[^/]+$/)) {
        const listingId = path.split('/')[3];
        if (request.method === 'GET') {
          return await handleGetListing(request, env, listingId);
        }
        if (request.method === 'PUT') {
          return await handleUpdateListing(request, env, listingId);
        }
        if (request.method === 'DELETE') {
          return await handleDeleteListing(request, env, listingId);
        }
      }
      if (path.match(/^\/buzz\/listings\/[^/]+\/click$/) && request.method === 'POST') {
        const listingId = path.split('/')[3];
        return await handleListingClick(request, env, listingId);
      }
      if (path.match(/^\/buzz\/listings\/[^/]+\/report$/) && request.method === 'POST') {
        const listingId = path.split('/')[3];
        return await handleListingReport(request, env, listingId);
      }

      // Calendar API routes
      // Natural language scheduling
      if (path === '/api/calendar/schedule' && request.method === 'POST') {
        return await scheduleNaturalLanguage(request, env);
      }

      // Appointments
      if (path === '/api/calendar/appointments' && request.method === 'POST') {
        return await createAppointment(request, env);
      }
      if (path === '/api/calendar/appointments' && request.method === 'GET') {
        return await getAppointments(request, env);
      }
      if (path.startsWith('/api/calendar/appointments/')) {
        const appointmentId = path.split('/')[4];
        if (request.method === 'PUT') {
          return await updateAppointment(request, env, appointmentId);
        }
        if (request.method === 'DELETE') {
          return await deleteAppointment(request, env, appointmentId);
        }
      }

      // Today's schedule
      if (path === '/api/calendar/today' && request.method === 'GET') {
        return await getTodaySchedule(request, env);
      }

      // Week's schedule
      if (path === '/api/calendar/week' && request.method === 'GET') {
        return await getWeekSchedule(request, env);
      }

      // Reminders
      if (path === '/api/calendar/reminders' && request.method === 'POST') {
        return await createReminder(request, env);
      }
      if (path === '/api/calendar/reminders' && request.method === 'GET') {
        return await getReminders(request, env);
      }
      if (path.startsWith('/api/calendar/reminders/')) {
        const reminderId = path.split('/')[4];
        if (request.method === 'PUT') {
          return await updateReminder(request, env, reminderId);
        }
      }

      // Billing API routes
      if (path === '/api/billing/usage' && request.method === 'GET') {
        return await handleGetUsage(request, env);
      }
      if (path === '/api/billing/history' && request.method === 'GET') {
        return await handleGetBillingHistory(request, env);
      }
      if (path === '/api/billing/estimate' && request.method === 'POST') {
        return await handleEstimateCosts(request, env);
      }
      if (path === '/api/billing/upcoming' && request.method === 'GET') {
        return await handleGetUpcomingInvoice(request, env);
      }

      // Phone provisioning API routes
      if (path === '/api/phone/provision' && request.method === 'POST') {
        return await handleProvisionPhone(request, env);
      }
      if (path === '/api/phone/release' && request.method === 'DELETE') {
        return await handleReleasePhone(request, env);
      }
      if (path === '/api/phone/details' && request.method === 'GET') {
        return await handleGetPhoneDetails(request, env);
      }
      if (path === '/api/phone/search' && request.method === 'GET') {
        return await handleSearchPhoneNumbers(request, env);
      }
      if (path.match(/^\/phone\/status\/[^/]+$/) && request.method === 'POST') {
        const userId = path.split('/')[3];
        return await handlePhoneStatusCallback(request, env, userId);
      }

      // Persona Management API routes
      if (path === '/api/personas' && request.method === 'POST') {
        return await handleCreatePersona(request, env);
      }
      if (path === '/api/personas' && request.method === 'GET') {
        return await handleListPersonas(request, env);
      }
      if (path === '/api/personas/active' && request.method === 'GET') {
        return await handleGetActivePersona(request, env);
      }
      if (path.match(/^\/api\/personas\/[^/]+$/)) {
        const personaId = path.split('/')[3];
        if (request.method === 'GET') {
          return await handleGetPersona(request, env, personaId);
        }
        if (request.method === 'PUT') {
          return await handleUpdatePersona(request, env, personaId);
        }
        if (request.method === 'DELETE') {
          return await handleDeletePersona(request, env, personaId);
        }
      }
      if (path.match(/^\/api\/personas\/[^/]+\/activate$/) && request.method === 'POST') {
        const personaId = path.split('/')[3];
        return await handleActivatePersona(request, env, personaId);
      }
      if (path.match(/^\/api\/personas\/[^/]+\/learn$/) && request.method === 'POST') {
        const personaId = path.split('/')[3];
        return await handleAddExample(request, env, personaId);
      }
      if (path.match(/^\/api\/personas\/[^/]+\/train-voice$/) && request.method === 'POST') {
        const personaId = path.split('/')[3];
        return await handleTrainVoice(request, env, personaId);
      }
      if (path.match(/^\/api\/personas\/[^/]+\/training-status$/) && request.method === 'GET') {
        const personaId = path.split('/')[3];
        return await handleGetTrainingStatus(request, env, personaId);
      }

      // 404 for unknown routes
      return new Response(JSON.stringify({
        error: 'Not Found',
        path,
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });

    } catch (error) {
      console.error('Error handling request:', error);

      return new Response(JSON.stringify({
        error: 'Internal Server Error',
        message: error.message,
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },

  /**
   * Scheduled event handler for Cloudflare Workers Cron Triggers
   * Runs email marketing batch sends on schedule
   */
  async scheduled(event, env, ctx) {
    try {
      console.log('[Cron] Scheduled event triggered at:', new Date().toISOString());
      const result = await handleScheduledEvent(event, env, ctx);
      console.log('[Cron] Completed:', result);
    } catch (error) {
      console.error('[Cron] Fatal error:', error);
    }
  },
};
