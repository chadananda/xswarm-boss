/**
 * Natural Language Email Queries
 *
 * Processes voice-friendly natural language queries and converts them
 * to Gmail search queries
 */

import { GmailClient } from './gmail-client.js';
import { createClient } from '@libsql/client';

export class EmailQueries {
  constructor(env) {
    this.env = env;
    this.db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });
  }

  /**
   * Process natural language email query
   *
   * @param {string} userId - User ID
   * @param {string} query - Natural language query
   * @param {Object} options - Additional options
   * @returns {Object} Query results
   */
  async processQuery(userId, query, options = {}) {
    const normalizedQuery = query.toLowerCase().trim();

    // Analyze query to determine intent and extract parameters
    const analysis = this.analyzeQuery(normalizedQuery);

    // Build Gmail search query
    const gmailQuery = this.buildGmailQuery(analysis);

    // Execute search
    const gmail = new GmailClient(this.env);
    const emails = await gmail.getMessages(userId, {
      query: gmailQuery,
      maxResults: analysis.type === 'unread' ? 100 : 20
    });

    // Log query for analytics
    await this.logQuery(userId, query, analysis.type, emails.length);

    // Format response
    return this.formatQueryResponse(emails, analysis);
  }

  /**
   * Analyze natural language query
   */
  analyzeQuery(query) {
    const analysis = {
      type: 'general_search',
      sender: null,
      timeframe: null,
      keywords: [],
      hasAttachment: false,
      isUnread: false,
      isImportant: false,
      subject: null
    };

    // Extract sender
    const senderPatterns = [
      /from\s+([^\s]+@[^\s]+)/i,
      /from\s+"?([^"]+?)"?\s+(?:about|regarding|with|sent)/i,
      /emails?\s+from\s+([^\s]+)/i,
      /sent\s+by\s+([^\s]+)/i
    ];

    for (const pattern of senderPatterns) {
      const match = query.match(pattern);
      if (match) {
        analysis.sender = match[1].trim();
        analysis.type = 'from_sender';
        break;
      }
    }

    // Extract subject
    const subjectPatterns = [
      /(?:about|regarding|with subject)\s+"([^"]+)"/i,
      /subject\s+(?:is\s+)?([^\s]+(?:\s+[^\s]+){0,5})/i
    ];

    for (const pattern of subjectPatterns) {
      const match = query.match(pattern);
      if (match) {
        analysis.subject = match[1].trim();
        break;
      }
    }

    // Extract timeframe
    const timePatterns = {
      'today': { days: 0 },
      'yesterday': { days: 1 },
      'this week': { days: 7 },
      'last week': { days: 14 },
      'this month': { days: 30 },
      'last month': { days: 60 },
      'recent': { days: 3 }
    };

    for (const [pattern, timeInfo] of Object.entries(timePatterns)) {
      if (query.includes(pattern)) {
        analysis.timeframe = timeInfo;
        break;
      }
    }

    // Check for specific conditions
    if (query.match(/\bunread\b|haven'?t read|didn'?t read/i)) {
      analysis.isUnread = true;
      analysis.type = 'unread';
    }

    if (query.match(/\bimportant\b|priority|urgent|starred/i)) {
      analysis.isImportant = true;
      analysis.type = 'important';
    }

    if (query.match(/\battachment\b|file|document|pdf|image/i)) {
      analysis.hasAttachment = true;
    }

    // Extract keywords (remove common words)
    const stopWords = [
      'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
      'with', 'by', 'from', 'about', 'what', 'do', 'i', 'have', 'my',
      'emails', 'email', 'messages', 'message', 'show', 'me', 'find',
      'get', 'list', 'all', 'any', 'some', 'that', 'this'
    ];

    const words = query.split(/\s+/);
    analysis.keywords = words
      .filter(word => {
        // Remove stopwords and already extracted info
        if (stopWords.includes(word)) return false;
        if (analysis.sender && analysis.sender.includes(word)) return false;
        if (analysis.subject && analysis.subject.includes(word)) return false;
        return word.length > 2;
      })
      .slice(0, 5); // Limit to 5 keywords

    return analysis;
  }

  /**
   * Build Gmail search query from analysis
   */
  buildGmailQuery(analysis) {
    const queryParts = [];

    // Sender filter
    if (analysis.sender) {
      queryParts.push(`from:${analysis.sender}`);
    }

    // Subject filter
    if (analysis.subject) {
      queryParts.push(`subject:"${analysis.subject}"`);
    }

    // Timeframe filter
    if (analysis.timeframe) {
      const date = new Date();
      date.setDate(date.getDate() - analysis.timeframe.days);
      const dateStr = date.toISOString().split('T')[0];
      queryParts.push(`after:${dateStr}`);
    }

    // Status filters
    if (analysis.isUnread) {
      queryParts.push('is:unread');
    }

    if (analysis.isImportant) {
      queryParts.push('is:important');
    }

    if (analysis.hasAttachment) {
      queryParts.push('has:attachment');
    }

    // Keywords
    if (analysis.keywords.length > 0) {
      const keywordQuery = analysis.keywords.join(' ');
      queryParts.push(keywordQuery);
    }

    return queryParts.join(' ');
  }

  /**
   * Format query response
   */
  formatQueryResponse(emails, analysis) {
    if (emails.length === 0) {
      return {
        type: 'no_results',
        message: this.getNoResultsMessage(analysis),
        emails: [],
        count: 0
      };
    }

    const message = this.generateResponseMessage(emails, analysis);

    return {
      type: 'email_results',
      message,
      emails: emails.slice(0, 10), // Limit to 10 for voice response
      count: emails.length,
      summary: this.generateEmailsSummary(emails, analysis)
    };
  }

  /**
   * Generate response message
   */
  generateResponseMessage(emails, analysis) {
    const count = emails.length;

    switch (analysis.type) {
      case 'from_sender':
        return `I found ${count} email${count > 1 ? 's' : ''} from ${analysis.sender}`;
      case 'unread':
        return `You have ${count} unread email${count > 1 ? 's' : ''}`;
      case 'important':
        return `I found ${count} important email${count > 1 ? 's' : ''}`;
      default:
        return `I found ${count} email${count > 1 ? 's' : ''} matching your search`;
    }
  }

  /**
   * Generate emails summary
   */
  generateEmailsSummary(emails, analysis) {
    const summary = {
      totalEmails: emails.length,
      unreadCount: emails.filter(e => !e.isRead).length,
      importantCount: emails.filter(e => e.isImportant).length,
      withAttachments: emails.filter(e => e.hasAttachments).length,
      senders: [...new Set(emails.map(e => e.from))].slice(0, 5),
      recentEmails: emails
        .sort((a, b) => b.date - a.date)
        .slice(0, 3)
        .map(e => ({
          subject: e.subject,
          from: e.from,
          snippet: e.snippet,
          date: e.date
        }))
    };

    return summary;
  }

  /**
   * Get "no results" message
   */
  getNoResultsMessage(analysis) {
    switch (analysis.type) {
      case 'from_sender':
        return `No emails found from ${analysis.sender}`;
      case 'unread':
        return 'You have no unread emails';
      case 'important':
        return 'No important emails found';
      default:
        if (analysis.keywords.length > 0) {
          return `No emails found matching "${analysis.keywords.join(' ')}"`;
        }
        return 'No emails found matching your search';
    }
  }

  /**
   * Log query for analytics
   */
  async logQuery(userId, query, queryType, resultCount) {
    try {
      await this.db.execute({
        sql: `
          INSERT INTO email_query_history (user_id, query, query_type, result_count)
          VALUES (?, ?, ?, ?)
        `,
        args: [userId, query, queryType, resultCount]
      });
    } catch (error) {
      console.error('Failed to log query:', error);
      // Don't throw - logging failure shouldn't break the query
    }
  }

  /**
   * Get common queries for user (for suggestions)
   */
  async getCommonQueries(userId, limit = 5) {
    try {
      const result = await this.db.execute({
        sql: `
          SELECT query, query_type, COUNT(*) as count
          FROM email_query_history
          WHERE user_id = ?
          GROUP BY query, query_type
          ORDER BY count DESC
          LIMIT ?
        `,
        args: [userId, limit]
      });

      return result.rows;
    } catch (error) {
      console.error('Failed to get common queries:', error);
      return [];
    }
  }
}
