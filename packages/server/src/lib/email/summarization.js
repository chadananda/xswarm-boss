/**
 * Email Summarization with AI
 *
 * Uses OpenAI to generate intelligent email summaries,
 * extract action items, and score importance
 */

export class EmailSummarization {
  constructor(env) {
    this.env = env;
    this.apiKey = env.OPENAI_API_KEY;
  }

  /**
   * Summarize email with AI
   *
   * @param {Object} email - Email object
   * @returns {Object} Summary data
   */
  async summarizeEmail(email) {
    if (!this.apiKey) {
      return this.fallbackSummarization(email);
    }

    try {
      const prompt = this.buildSummarizationPrompt(email);

      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'gpt-3.5-turbo',
          messages: [
            {
              role: 'system',
              content: 'You are an AI assistant that creates concise, actionable email summaries. Focus on key points, action items, and important context.'
            },
            {
              role: 'user',
              content: prompt
            }
          ],
          max_tokens: 200,
          temperature: 0.3
        })
      });

      if (!response.ok) {
        console.error('OpenAI API error:', await response.text());
        return this.fallbackSummarization(email);
      }

      const data = await response.json();
      const summary = data.choices[0].message.content;

      const importance = this.calculateImportance(email);
      const actionItems = this.extractActionItems(email.bodyText || email.snippet);
      const keyPoints = this.extractKeyPoints(email.bodyText || email.snippet);
      const sentiment = this.analyzeSentiment(email.bodyText || email.snippet);
      const readingTime = this.estimateReadingTime(email.bodyText || email.snippet);

      return {
        summary,
        importance,
        actionItems,
        keyPoints,
        sentiment,
        readingTime
      };
    } catch (error) {
      console.error('Error in AI summarization:', error);
      return this.fallbackSummarization(email);
    }
  }

  /**
   * Build summarization prompt
   */
  buildSummarizationPrompt(email) {
    const bodyPreview = (email.bodyText || email.snippet).substring(0, 1000);
    const hasMore = (email.bodyText || email.snippet).length > 1000;

    return `Summarize this email in 2-3 sentences. Focus on the main purpose, any requests or action items, and key information.

From: ${email.from}
Subject: ${email.subject}
Body: ${bodyPreview}${hasMore ? '...' : ''}

Summary:`;
  }

  /**
   * Calculate email importance score (0-1)
   */
  calculateImportance(email) {
    let score = 0.5; // Base importance

    // Check if marked as important
    if (email.isImportant) {
      score += 0.3;
    }

    // Subject keywords
    const importantKeywords = [
      'urgent', 'asap', 'deadline', 'important', 'critical',
      'meeting', 'interview', 'proposal', 'contract', 'invoice',
      'action required', 'respond', 'immediate'
    ];

    const subjectLower = (email.subject || '').toLowerCase();
    importantKeywords.forEach(keyword => {
      if (subjectLower.includes(keyword)) {
        score += 0.1;
      }
    });

    // Email length (longer emails often more important)
    const bodyLength = (email.bodyText || email.snippet || '').length;
    if (bodyLength > 1000) {
      score += 0.1;
    }

    // Has attachments
    if (email.hasAttachments) {
      score += 0.1;
    }

    // Direct emails (not CC'd) are more important
    const cc = email.cc || '';
    if (cc.length > 0) {
      score -= 0.1;
    }

    // Not read yet (might be important)
    if (!email.isRead) {
      score += 0.05;
    }

    return Math.min(Math.max(score, 0), 1); // Clamp between 0 and 1
  }

  /**
   * Extract action items from email body
   */
  extractActionItems(body) {
    if (!body) return [];

    const actionPatterns = [
      /please\s+(.{5,100}?)[.!?]/gi,
      /can\s+you\s+(.{5,100}?)[.!?]/gi,
      /need\s+you\s+to\s+(.{5,100}?)[.!?]/gi,
      /would\s+you\s+(.{5,100}?)[.!?]/gi,
      /let\s+me\s+know\s+(.{5,100}?)[.!?]/gi,
      /action\s+required:?\s*(.{5,100}?)[.!?]/gi
    ];

    const actionItems = [];

    actionPatterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(body)) !== null) {
        const item = match[1].trim();
        if (item.length > 5 && item.length < 100) {
          actionItems.push(item);
        }
      }
    });

    // Remove duplicates
    return [...new Set(actionItems)].slice(0, 5); // Max 5 action items
  }

  /**
   * Extract key points from email
   */
  extractKeyPoints(body) {
    if (!body) return [];

    // Split into sentences
    const sentences = body
      .split(/[.!?]+/)
      .map(s => s.trim())
      .filter(s => s.length > 20 && s.length < 200);

    // Score sentences based on keyword importance
    const scoredSentences = sentences.map(sentence => ({
      text: sentence,
      score: this.calculateSentenceImportance(sentence)
    }));

    // Sort by score and take top 3
    return scoredSentences
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(s => s.text);
  }

  /**
   * Calculate sentence importance
   */
  calculateSentenceImportance(sentence) {
    const importantWords = [
      'deadline', 'meeting', 'important', 'urgent', 'required',
      'budget', 'cost', 'price', 'schedule', 'timeline',
      'decision', 'approve', 'confirm', 'complete', 'deliver',
      'project', 'report', 'update', 'status'
    ];

    const words = sentence.toLowerCase().split(/\s+/);
    const importantWordCount = words.filter(word =>
      importantWords.some(iw => word.includes(iw))
    ).length;

    return importantWordCount / words.length;
  }

  /**
   * Analyze email sentiment
   */
  analyzeSentiment(body) {
    if (!body) return 'neutral';

    const positiveWords = [
      'thanks', 'thank you', 'great', 'excellent', 'perfect', 'amazing',
      'wonderful', 'appreciate', 'love', 'happy', 'pleased'
    ];

    const negativeWords = [
      'problem', 'issue', 'concern', 'worried', 'disappointed', 'urgent',
      'failed', 'error', 'wrong', 'bad', 'poor', 'unacceptable'
    ];

    const bodyLower = body.toLowerCase();
    const words = bodyLower.split(/\s+/);

    const positiveCount = words.filter(word =>
      positiveWords.some(pw => word.includes(pw))
    ).length;

    const negativeCount = words.filter(word =>
      negativeWords.some(nw => word.includes(nw))
    ).length;

    if (positiveCount > negativeCount + 1) return 'positive';
    if (negativeCount > positiveCount + 1) return 'negative';
    return 'neutral';
  }

  /**
   * Estimate reading time in minutes
   */
  estimateReadingTime(body) {
    if (!body) return 1;

    const wordsPerMinute = 200;
    const wordCount = body.split(/\s+/).length;
    const minutes = Math.ceil(wordCount / wordsPerMinute);

    return Math.max(minutes, 1); // At least 1 minute
  }

  /**
   * Fallback summarization (no AI)
   */
  fallbackSummarization(email) {
    return {
      summary: email.snippet || 'No summary available',
      importance: this.calculateImportance(email),
      actionItems: this.extractActionItems(email.bodyText || email.snippet),
      keyPoints: this.extractKeyPoints(email.bodyText || email.snippet),
      sentiment: this.analyzeSentiment(email.bodyText || email.snippet),
      readingTime: this.estimateReadingTime(email.bodyText || email.snippet)
    };
  }

  /**
   * Batch summarize multiple emails
   */
  async summarizeMultiple(emails) {
    const summaries = [];

    // Summarize in parallel (max 5 at a time to avoid rate limits)
    const batchSize = 5;
    for (let i = 0; i < emails.length; i += batchSize) {
      const batch = emails.slice(i, i + batchSize);
      const batchSummaries = await Promise.all(
        batch.map(email => this.summarizeEmail(email))
      );
      summaries.push(...batchSummaries);
    }

    return summaries;
  }
}
