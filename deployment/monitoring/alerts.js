/**
 * xSwarm Boss - Alerting System
 *
 * Sends alerts for critical events:
 * - Service outages
 * - High error rates
 * - Slow response times
 * - Failed payments
 * - Database issues
 *
 * Supports multiple channels:
 * - Email (via SendGrid)
 * - SMS (via Twilio)
 * - Slack (webhook)
 *
 * Usage: Import and call alert functions when issues detected
 */

/**
 * Alert severity levels
 */
export const AlertSeverity = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
};

/**
 * Alert manager class
 */
export class AlertManager {
  constructor(env) {
    this.env = env;
    this.recentAlerts = [];
    this.alertThresholds = {
      errorRate: 5, // Percent
      responseTime: 2000, // ms
      databaseQueryTime: 5000, // ms
    };
  }

  /**
   * Send alert
   */
  async sendAlert(severity, title, message, context = {}) {
    const alert = {
      id: this.generateAlertId(),
      timestamp: new Date().toISOString(),
      severity,
      title,
      message,
      context,
      service: 'xswarm-boss',
      environment: this.env.ENVIRONMENT || 'production',
    };

    // Store alert
    this.recentAlerts.push(alert);
    this.recentAlerts = this.recentAlerts.slice(-100); // Keep last 100

    // Log alert
    console.error(JSON.stringify({
      level: 'alert',
      ...alert,
    }));

    // Send notifications based on severity
    const promises = [];

    if (severity === AlertSeverity.CRITICAL || severity === AlertSeverity.ERROR) {
      // Send email for critical/error alerts
      promises.push(this.sendEmailAlert(alert));

      // Send SMS for critical alerts
      if (severity === AlertSeverity.CRITICAL) {
        promises.push(this.sendSMSAlert(alert));
      }
    }

    // Always try Slack for all alerts
    promises.push(this.sendSlackAlert(alert));

    // Wait for all notifications (but don't fail if some fail)
    await Promise.allSettled(promises);

    return alert;
  }

  /**
   * Send email alert via SendGrid
   */
  async sendEmailAlert(alert) {
    if (!this.env.SENDGRID_API_KEY) {
      console.log('SendGrid not configured - skipping email alert');
      return;
    }

    const adminEmail = this.env.ADMIN_EMAIL || 'admin@xswarm.ai';

    try {
      const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.env.SENDGRID_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          personalizations: [{
            to: [{ email: adminEmail }],
            subject: `[${alert.severity.toUpperCase()}] ${alert.title}`,
          }],
          from: {
            email: 'alerts@xswarm.ai',
            name: 'xSwarm Alerts',
          },
          content: [{
            type: 'text/html',
            value: this.formatEmailAlert(alert),
          }],
        }),
      });

      if (!response.ok) {
        console.error('Failed to send email alert:', await response.text());
      }
    } catch (error) {
      console.error('Error sending email alert:', error);
    }
  }

  /**
   * Send SMS alert via Twilio
   */
  async sendSMSAlert(alert) {
    if (!this.env.TWILIO_AUTH_TOKEN || !this.env.TWILIO_ACCOUNT_SID) {
      console.log('Twilio not configured - skipping SMS alert');
      return;
    }

    const adminPhone = this.env.ADMIN_PHONE;
    if (!adminPhone) {
      console.log('Admin phone not configured - skipping SMS alert');
      return;
    }

    try {
      const auth = Buffer.from(
        `${this.env.TWILIO_ACCOUNT_SID}:${this.env.TWILIO_AUTH_TOKEN}`
      ).toString('base64');

      const response = await fetch(
        `https://api.twilio.com/2010-04-01/Accounts/${this.env.TWILIO_ACCOUNT_SID}/Messages.json`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Basic ${auth}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            To: adminPhone,
            From: this.env.TWILIO_PHONE_NUMBER,
            Body: this.formatSMSAlert(alert),
          }),
        }
      );

      if (!response.ok) {
        console.error('Failed to send SMS alert:', await response.text());
      }
    } catch (error) {
      console.error('Error sending SMS alert:', error);
    }
  }

  /**
   * Send Slack alert
   */
  async sendSlackAlert(alert) {
    const webhookUrl = this.env.SLACK_WEBHOOK_URL;
    if (!webhookUrl) {
      console.log('Slack webhook not configured - skipping Slack alert');
      return;
    }

    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.formatSlackAlert(alert)),
      });

      if (!response.ok) {
        console.error('Failed to send Slack alert:', await response.text());
      }
    } catch (error) {
      console.error('Error sending Slack alert:', error);
    }
  }

  /**
   * Format alert for email
   */
  formatEmailAlert(alert) {
    const color = {
      info: '#2196F3',
      warning: '#FF9800',
      error: '#F44336',
      critical: '#9C27B0',
    }[alert.severity];

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; }
          .alert-box { border-left: 4px solid ${color}; padding: 20px; margin: 20px 0; }
          .severity { color: ${color}; font-weight: bold; text-transform: uppercase; }
          .context { background: #f5f5f5; padding: 10px; margin: 10px 0; }
          pre { overflow-x: auto; }
        </style>
      </head>
      <body>
        <div class="alert-box">
          <p class="severity">${alert.severity}</p>
          <h2>${alert.title}</h2>
          <p>${alert.message}</p>
          <p><small>Service: ${alert.service} | Environment: ${alert.environment}</small></p>
          <p><small>Time: ${alert.timestamp}</small></p>

          ${Object.keys(alert.context).length > 0 ? `
            <div class="context">
              <strong>Context:</strong>
              <pre>${JSON.stringify(alert.context, null, 2)}</pre>
            </div>
          ` : ''}
        </div>
      </body>
      </html>
    `;
  }

  /**
   * Format alert for SMS (short)
   */
  formatSMSAlert(alert) {
    return `[${alert.severity.toUpperCase()}] ${alert.title}: ${alert.message.substring(0, 100)}`;
  }

  /**
   * Format alert for Slack
   */
  formatSlackAlert(alert) {
    const color = {
      info: '#2196F3',
      warning: '#FF9800',
      error: '#F44336',
      critical: '#9C27B0',
    }[alert.severity];

    const emoji = {
      info: ':information_source:',
      warning: ':warning:',
      error: ':x:',
      critical: ':rotating_light:',
    }[alert.severity];

    return {
      attachments: [{
        color,
        title: `${emoji} ${alert.title}`,
        text: alert.message,
        fields: [
          {
            title: 'Severity',
            value: alert.severity.toUpperCase(),
            short: true,
          },
          {
            title: 'Service',
            value: alert.service,
            short: true,
          },
          {
            title: 'Environment',
            value: alert.environment,
            short: true,
          },
          {
            title: 'Time',
            value: alert.timestamp,
            short: true,
          },
        ],
        footer: 'xSwarm Boss Monitoring',
        ts: Math.floor(Date.parse(alert.timestamp) / 1000),
      }],
    };
  }

  /**
   * Generate unique alert ID
   */
  generateAlertId() {
    return `alert_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  }

  /**
   * Check metrics and send alerts if thresholds exceeded
   */
  async checkMetricsAndAlert(metrics) {
    const report = metrics.getMetricsReport();

    // High error rate
    if (report.requests.errorRate > this.alertThresholds.errorRate) {
      await this.sendAlert(
        AlertSeverity.ERROR,
        'High Error Rate Detected',
        `Error rate is ${report.requests.errorRate.toFixed(2)}% (threshold: ${this.alertThresholds.errorRate}%)`,
        {
          errorRate: report.requests.errorRate,
          totalRequests: report.requests.count,
          threshold: this.alertThresholds.errorRate,
        }
      );
    }

    // Slow response times
    if (report.requests.p95ResponseTime > this.alertThresholds.responseTime) {
      await this.sendAlert(
        AlertSeverity.WARNING,
        'Slow Response Times',
        `P95 response time is ${report.requests.p95ResponseTime}ms (threshold: ${this.alertThresholds.responseTime}ms)`,
        {
          p95: report.requests.p95ResponseTime,
          p99: report.requests.p99ResponseTime,
          avg: report.requests.avgResponseTime,
          threshold: this.alertThresholds.responseTime,
        }
      );
    }

    // Slow database queries
    if (report.database.p95Duration > this.alertThresholds.databaseQueryTime) {
      await this.sendAlert(
        AlertSeverity.WARNING,
        'Slow Database Queries',
        `P95 query time is ${report.database.p95Duration}ms (threshold: ${this.alertThresholds.databaseQueryTime}ms)`,
        {
          p95: report.database.p95Duration,
          slowQueries: report.database.slowQueries,
          threshold: this.alertThresholds.databaseQueryTime,
        }
      );
    }
  }

  /**
   * Get recent alerts
   */
  getRecentAlerts(limit = 20) {
    return this.recentAlerts.slice(-limit).reverse();
  }
}

/**
 * Pre-configured alert functions
 */
export async function alertServiceOutage(alertManager, service, error) {
  return await alertManager.sendAlert(
    AlertSeverity.CRITICAL,
    `Service Outage: ${service}`,
    `The ${service} service is not responding`,
    { error: error.message, stack: error.stack }
  );
}

export async function alertDatabaseError(alertManager, error) {
  return await alertManager.sendAlert(
    AlertSeverity.CRITICAL,
    'Database Connection Error',
    'Unable to connect to database',
    { error: error.message }
  );
}

export async function alertPaymentFailed(alertManager, customerId, amount, error) {
  return await alertManager.sendAlert(
    AlertSeverity.ERROR,
    'Payment Failed',
    `Payment of $${amount} failed for customer ${customerId}`,
    { customerId, amount, error: error.message }
  );
}

export async function alertDeploymentFailed(alertManager, error) {
  return await alertManager.sendAlert(
    AlertSeverity.CRITICAL,
    'Deployment Failed',
    'Production deployment has failed',
    { error: error.message, stack: error.stack }
  );
}

export async function alertHighMemoryUsage(alertManager, usage, threshold) {
  return await alertManager.sendAlert(
    AlertSeverity.WARNING,
    'High Memory Usage',
    `Memory usage is ${usage}% (threshold: ${threshold}%)`,
    { usage, threshold }
  );
}

export async function alertAPIRateLimit(alertManager, api, remaining) {
  return await alertManager.sendAlert(
    AlertSeverity.WARNING,
    `API Rate Limit Warning: ${api}`,
    `Only ${remaining} requests remaining for ${api} API`,
    { api, remaining }
  );
}
