/**
 * xSwarm Boss - Metrics Collection System
 *
 * Tracks performance and business metrics:
 * - Request rates and response times
 * - Error rates and types
 * - API usage by endpoint
 * - Database query performance
 * - Business KPIs (signups, subscriptions, revenue)
 *
 * Usage: Import and integrate into your request handlers
 */

/**
 * Metrics collector class
 */
export class MetricsCollector {
  constructor(env) {
    this.env = env;
    this.metrics = {
      requests: [],
      errors: [],
      database: [],
      business: [],
    };
    this.startTime = Date.now();
  }

  /**
   * Track HTTP request
   */
  trackRequest(method, path, statusCode, responseTime, userId = null) {
    const metric = {
      timestamp: Date.now(),
      type: 'http_request',
      method,
      path: this.sanitizePath(path),
      statusCode,
      responseTime,
      userId,
      success: statusCode >= 200 && statusCode < 400,
    };

    this.metrics.requests.push(metric);
    this.logMetric(metric);
  }

  /**
   * Track error
   */
  trackError(error, context = {}) {
    const metric = {
      timestamp: Date.now(),
      type: 'error',
      message: error.message,
      stack: error.stack,
      name: error.name,
      ...context,
    };

    this.metrics.errors.push(metric);
    this.logMetric(metric);
  }

  /**
   * Track database query
   */
  trackDatabaseQuery(query, duration, rowCount = 0) {
    const metric = {
      timestamp: Date.now(),
      type: 'database_query',
      query: this.sanitizeQuery(query),
      duration,
      rowCount,
    };

    this.metrics.database.push(metric);

    // Log slow queries
    if (duration > 1000) {
      this.logMetric({ ...metric, slow: true });
    }
  }

  /**
   * Track business event
   */
  trackBusinessEvent(event, data = {}) {
    const metric = {
      timestamp: Date.now(),
      type: 'business_event',
      event,
      ...data,
    };

    this.metrics.business.push(metric);
    this.logMetric(metric);
  }

  /**
   * Sanitize URL path (remove IDs and sensitive data)
   */
  sanitizePath(path) {
    return path
      .replace(/\/[\w-]{20,}/g, '/:id') // Replace long IDs
      .replace(/\/\d+/g, '/:num') // Replace numeric IDs
      .replace(/email=[^&]+/g, 'email=***') // Remove emails
      .replace(/token=[^&]+/g, 'token=***'); // Remove tokens
  }

  /**
   * Sanitize SQL query (remove sensitive data)
   */
  sanitizeQuery(query) {
    if (typeof query !== 'string') {
      query = String(query);
    }

    return query
      .substring(0, 200) // Limit length
      .replace(/'[^']*@[^']*'/g, "'***@***'") // Remove emails
      .replace(/'[A-Za-z0-9]{20,}'/g, "'***'"); // Remove long strings (likely tokens)
  }

  /**
   * Log metric to console (structured logging)
   */
  logMetric(metric) {
    console.log(JSON.stringify({
      level: metric.type === 'error' ? 'error' : 'info',
      ...metric,
    }));
  }

  /**
   * Get request metrics summary
   */
  getRequestMetrics() {
    const requests = this.metrics.requests;

    if (requests.length === 0) {
      return {
        count: 0,
        avgResponseTime: 0,
        successRate: 0,
      };
    }

    const responseTimes = requests.map(r => r.responseTime);
    const successCount = requests.filter(r => r.success).length;

    return {
      count: requests.length,
      avgResponseTime: this.average(responseTimes),
      minResponseTime: Math.min(...responseTimes),
      maxResponseTime: Math.max(...responseTimes),
      p50ResponseTime: this.percentile(responseTimes, 0.5),
      p95ResponseTime: this.percentile(responseTimes, 0.95),
      p99ResponseTime: this.percentile(responseTimes, 0.99),
      successRate: (successCount / requests.length) * 100,
      errorRate: ((requests.length - successCount) / requests.length) * 100,
      byStatus: this.groupBy(requests, 'statusCode'),
      byPath: this.groupBy(requests, 'path'),
    };
  }

  /**
   * Get error metrics summary
   */
  getErrorMetrics() {
    const errors = this.metrics.errors;

    return {
      count: errors.length,
      byType: this.groupBy(errors, 'name'),
      byMessage: this.groupBy(errors, 'message'),
      recent: errors.slice(-10), // Last 10 errors
    };
  }

  /**
   * Get database metrics summary
   */
  getDatabaseMetrics() {
    const queries = this.metrics.database;

    if (queries.length === 0) {
      return {
        count: 0,
        avgDuration: 0,
      };
    }

    const durations = queries.map(q => q.duration);
    const slowQueries = queries.filter(q => q.duration > 1000);

    return {
      count: queries.length,
      avgDuration: this.average(durations),
      minDuration: Math.min(...durations),
      maxDuration: Math.max(...durations),
      p50Duration: this.percentile(durations, 0.5),
      p95Duration: this.percentile(durations, 0.95),
      slowQueries: slowQueries.length,
      totalRows: queries.reduce((sum, q) => sum + q.rowCount, 0),
    };
  }

  /**
   * Get business metrics summary
   */
  getBusinessMetrics() {
    const events = this.metrics.business;

    return {
      count: events.length,
      byEvent: this.groupBy(events, 'event'),
      events: events,
    };
  }

  /**
   * Get complete metrics report
   */
  getMetricsReport() {
    return {
      timestamp: new Date().toISOString(),
      uptime: Date.now() - this.startTime,
      requests: this.getRequestMetrics(),
      errors: this.getErrorMetrics(),
      database: this.getDatabaseMetrics(),
      business: this.getBusinessMetrics(),
    };
  }

  /**
   * Calculate average
   */
  average(numbers) {
    if (numbers.length === 0) return 0;
    return numbers.reduce((a, b) => a + b, 0) / numbers.length;
  }

  /**
   * Calculate percentile
   */
  percentile(numbers, p) {
    if (numbers.length === 0) return 0;
    const sorted = [...numbers].sort((a, b) => a - b);
    const index = Math.ceil(sorted.length * p) - 1;
    return sorted[index];
  }

  /**
   * Group by key
   */
  groupBy(items, key) {
    const grouped = {};
    for (const item of items) {
      const value = item[key];
      grouped[value] = (grouped[value] || 0) + 1;
    }
    return grouped;
  }
}

/**
 * Middleware to track request metrics
 */
export function metricsMiddleware(metrics) {
  return async (request, next) => {
    const startTime = Date.now();
    const url = new URL(request.url);

    try {
      const response = await next(request);
      const responseTime = Date.now() - startTime;

      metrics.trackRequest(
        request.method,
        url.pathname,
        response.status,
        responseTime,
        request.userId // If available from auth middleware
      );

      return response;
    } catch (error) {
      const responseTime = Date.now() - startTime;

      metrics.trackRequest(
        request.method,
        url.pathname,
        500,
        responseTime,
        request.userId
      );

      metrics.trackError(error, {
        method: request.method,
        path: url.pathname,
      });

      throw error;
    }
  };
}

/**
 * Handle metrics endpoint
 */
export async function handleMetricsEndpoint(request, env, metrics) {
  // Only allow access from internal IPs or with admin auth
  // TODO: Add authentication

  const report = metrics.getMetricsReport();

  return new Response(JSON.stringify(report, null, 2), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    },
  });
}

/**
 * Export metrics in Prometheus format (optional)
 */
export function exportPrometheusMetrics(metrics) {
  const report = metrics.getMetricsReport();
  const lines = [];

  // Request metrics
  lines.push('# HELP http_requests_total Total number of HTTP requests');
  lines.push('# TYPE http_requests_total counter');
  lines.push(`http_requests_total ${report.requests.count}`);

  lines.push('# HELP http_request_duration_seconds HTTP request duration');
  lines.push('# TYPE http_request_duration_seconds summary');
  lines.push(`http_request_duration_seconds{quantile="0.5"} ${report.requests.p50ResponseTime / 1000}`);
  lines.push(`http_request_duration_seconds{quantile="0.95"} ${report.requests.p95ResponseTime / 1000}`);
  lines.push(`http_request_duration_seconds{quantile="0.99"} ${report.requests.p99ResponseTime / 1000}`);

  lines.push('# HELP http_request_error_rate HTTP request error rate');
  lines.push('# TYPE http_request_error_rate gauge');
  lines.push(`http_request_error_rate ${report.requests.errorRate / 100}`);

  // Database metrics
  lines.push('# HELP database_queries_total Total number of database queries');
  lines.push('# TYPE database_queries_total counter');
  lines.push(`database_queries_total ${report.database.count}`);

  lines.push('# HELP database_query_duration_seconds Database query duration');
  lines.push('# TYPE database_query_duration_seconds summary');
  lines.push(`database_query_duration_seconds{quantile="0.5"} ${report.database.p50Duration / 1000}`);
  lines.push(`database_query_duration_seconds{quantile="0.95"} ${report.database.p95Duration / 1000}`);

  // Error metrics
  lines.push('# HELP errors_total Total number of errors');
  lines.push('# TYPE errors_total counter');
  lines.push(`errors_total ${report.errors.count}`);

  return lines.join('\n');
}
