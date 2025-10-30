/**
 * Marketing Email Templates
 *
 * Professional, branded email templates for tier upselling campaigns.
 * Uses xSwarm terminal aesthetic with clear CTAs and compelling copy.
 */

/**
 * Get email template by ID
 *
 * @param {string} templateId - Template identifier
 * @param {Object} data - Template data (user info, campaign info, etc)
 * @returns {Object} { html, text } - Email content
 */
export function getEmailTemplate(templateId, data) {
  const templates = {
    // =========================================================================
    // FREE → AI SECRETARY TEMPLATES
    // =========================================================================

    template_free_to_secretary_welcome: () => ({
      html: renderTemplate('Welcome to xSwarm', `
        <h1>Your AI Secretary is Ready</h1>
        <p>Hi ${data.name || 'there'},</p>
        <p>Welcome to xSwarm! You've taken the first step into AI-powered productivity.</p>
        <p>Right now, you're on our <strong>Free tier</strong>. But imagine if you had a voice AI secretary that:</p>
        <ul>
          <li>Answers calls professionally 24/7</li>
          <li>Schedules meetings automatically</li>
          <li>Takes messages and sends you transcripts</li>
          <li>Never misses an important call again</li>
        </ul>
        <p>That's what <strong>AI Secretary</strong> can do for you.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
        <p><small>Try it free for 14 days. Cancel anytime.</small></p>
      `, data),
      text: `Welcome to xSwarm!

Hi ${data.name || 'there'},

You've taken the first step into AI-powered productivity.

Right now, you're on our Free tier. But imagine if you had a voice AI secretary that:
- Answers calls professionally 24/7
- Schedules meetings automatically
- Takes messages and sends you transcripts
- Never misses an important call again

That's what AI Secretary can do for you.

Start your free trial: ${data.cta_url}

Try it free for 14 days. Cancel anytime.`
    }),

    template_free_to_secretary_features: () => ({
      html: renderTemplate('Transform Your Workday with AI', `
        <h1>See What AI Secretary Can Do</h1>
        <p>Hi ${data.name},</p>
        <p>Your time is valuable. Stop wasting it on:</p>
        <div class="feature-grid">
          <div class="feature">
            <h3>📞 Call Screening</h3>
            <p>AI handles spam and routes important calls to you</p>
          </div>
          <div class="feature">
            <h3>📅 Smart Scheduling</h3>
            <p>Book meetings without the back-and-forth</p>
          </div>
          <div class="feature">
            <h3>📝 Message Taking</h3>
            <p>Get transcripts of every call instantly</p>
          </div>
          <div class="feature">
            <h3>🎯 Priority Routing</h3>
            <p>VIPs always get through, spam never does</p>
          </div>
        </div>
        <p><strong>AI Secretary users save an average of 10 hours per week.</strong></p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `See What AI Secretary Can Do

Hi ${data.name},

Your time is valuable. AI Secretary handles:

📞 Call Screening - AI handles spam and routes important calls
📅 Smart Scheduling - Book meetings without back-and-forth
📝 Message Taking - Get transcripts of every call instantly
🎯 Priority Routing - VIPs always get through, spam never does

AI Secretary users save an average of 10 hours per week.

Explore features: ${data.cta_url}`
    }),

    template_free_to_secretary_testimonial: () => ({
      html: renderTemplate('Real Results from Real Users', `
        <h1>How Sarah Saved 10 Hours per Week</h1>
        <blockquote>
          "I was drowning in phone calls. xSwarm AI Secretary changed everything.
          It handles all my screening, scheduling, and message-taking. I get my time back
          and my clients love the professional experience."
          <footer>— Sarah Chen, Marketing Consultant</footer>
        </blockquote>
        <div class="stats">
          <div class="stat">
            <div class="stat-number">10 hrs</div>
            <div class="stat-label">Saved per week</div>
          </div>
          <div class="stat">
            <div class="stat-number">100%</div>
            <div class="stat-label">Calls answered</div>
          </div>
          <div class="stat">
            <div class="stat-number">$2.4K</div>
            <div class="stat-label">Extra revenue/month</div>
          </div>
        </div>
        <p>Join thousands of professionals who trust xSwarm AI Secretary.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `How Sarah Saved 10 Hours per Week

"I was drowning in phone calls. xSwarm AI Secretary changed everything.
It handles all my screening, scheduling, and message-taking. I get my time back
and my clients love the professional experience."
— Sarah Chen, Marketing Consultant

Results:
- 10 hours saved per week
- 100% of calls answered
- $2,400 extra revenue per month

Join thousands of professionals who trust xSwarm AI Secretary.

Read more success stories: ${data.cta_url}`
    }),

    template_free_to_secretary_spotlight: () => ({
      html: renderTemplate('Your AI Secretary Never Sleeps', `
        <h1>24/7 Call Handling You Can Trust</h1>
        <p>Hi ${data.name},</p>
        <p>It's 3am. A potential client calls. What happens?</p>
        <p><strong>With AI Secretary:</strong> Your AI answers professionally, qualifies the lead,
        schedules a callback, and sends you a transcript. You wake up to a new opportunity.</p>
        <p><strong>Without it:</strong> Voicemail. They call your competitor instead.</p>
        <p>AI Secretary represents you perfectly, 24/7/365:</p>
        <ul>
          <li>Natural conversation (not robotic)</li>
          <li>Learns your preferences and schedule</li>
          <li>Handles complex scheduling scenarios</li>
          <li>Transfers urgent calls to you</li>
        </ul>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `Your AI Secretary Never Sleeps

Hi ${data.name},

It's 3am. A potential client calls. What happens?

With AI Secretary: Your AI answers professionally, qualifies the lead,
schedules a callback, and sends you a transcript. You wake up to a new opportunity.

Without it: Voicemail. They call your competitor instead.

AI Secretary represents you perfectly, 24/7/365:
- Natural conversation (not robotic)
- Learns your preferences and schedule
- Handles complex scheduling scenarios
- Transfers urgent calls to you

See it in action: ${data.cta_url}`
    }),

    template_free_to_secretary_offer: () => ({
      html: renderTemplate('Special Offer: 50% Off AI Secretary', `
        <h1>50% Off AI Secretary - This Week Only</h1>
        <p>Hi ${data.name},</p>
        <div class="offer-box">
          <div class="old-price">$49/month</div>
          <div class="new-price">$24.50/month</div>
          <div class="offer-badge">FIRST50 - 50% OFF FIRST 3 MONTHS</div>
        </div>
        <p><strong>Get professional voice AI at startup prices.</strong></p>
        <p>This is our best offer ever for new AI Secretary subscribers:</p>
        <ul>
          <li>✓ Unlimited incoming calls</li>
          <li>✓ Smart call routing and screening</li>
          <li>✓ Automatic scheduling and calendar sync</li>
          <li>✓ SMS and email transcripts</li>
          <li>✓ Custom voice and personality</li>
        </ul>
        <p><strong>Offer expires in 7 days.</strong></p>
        ${renderCTA(data.cta_url, 'Claim Your 50% Discount')}
        <p><small>Use code FIRST50 at checkout. Offer valid for new subscribers only.</small></p>
      `, data),
      text: `50% Off AI Secretary - This Week Only

Hi ${data.name},

Special Offer: $24.50/month (was $49/month)
Code: FIRST50 - 50% off first 3 months

Get professional voice AI at startup prices:
✓ Unlimited incoming calls
✓ Smart call routing and screening
✓ Automatic scheduling and calendar sync
✓ SMS and email transcripts
✓ Custom voice and personality

Offer expires in 7 days.

Claim your discount: ${data.cta_url}

Use code FIRST50 at checkout.`
    }),

    template_free_to_secretary_final: () => ({
      html: renderTemplate('Last Chance: Upgrade to AI Secretary', `
        <h1>Don't Miss Out on AI-Powered Productivity</h1>
        <p>Hi ${data.name},</p>
        <p>This is my last email about AI Secretary, so I'll keep it simple:</p>
        <p><strong>Without AI Secretary:</strong></p>
        <ul>
          <li>Missed calls = missed opportunities</li>
          <li>Playing phone tag wastes your time</li>
          <li>Voicemail is where leads go to die</li>
        </ul>
        <p><strong>With AI Secretary:</strong></p>
        <ul>
          <li>Every call answered professionally</li>
          <li>Meetings scheduled automatically</li>
          <li>You focus on what matters</li>
        </ul>
        <p>Thousands of professionals trust xSwarm. Ready to join them?</p>
        ${renderCTA(data.cta_url, data.cta_text)}
        <p><small>Still have questions? Reply to this email and I'll personally help you get started.</small></p>
      `, data),
      text: `Last Chance: Upgrade to AI Secretary

Hi ${data.name},

This is my last email about AI Secretary, so I'll keep it simple:

Without AI Secretary:
- Missed calls = missed opportunities
- Playing phone tag wastes your time
- Voicemail is where leads go to die

With AI Secretary:
- Every call answered professionally
- Meetings scheduled automatically
- You focus on what matters

Thousands of professionals trust xSwarm. Ready to join them?

Upgrade now: ${data.cta_url}

Questions? Reply to this email.`
    }),

    // =========================================================================
    // AI SECRETARY → PROJECT MANAGER TEMPLATES
    // =========================================================================

    template_secretary_to_pm_welcome: () => ({
      html: renderTemplate('Ready to Supercharge Your Team?', `
        <h1>Introducing AI Project Manager</h1>
        <p>Hi ${data.name},</p>
        <p>You're already using AI Secretary. Smart move.</p>
        <p>But what if your entire <em>team</em> could work with AI?</p>
        <p><strong>AI Project Manager</strong> includes everything in AI Secretary, plus:</p>
        <ul>
          <li>Team collaboration and shared AI agents</li>
          <li>Project management with AI automation</li>
          <li><strong>xSwarm Buzz</strong> - AI marketing platform included</li>
          <li>Multi-channel campaign management</li>
        </ul>
        <p>It's like upgrading from a solo AI to an entire AI department.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `Ready to Supercharge Your Team?

Hi ${data.name},

You're already using AI Secretary. Smart move.

But what if your entire team could work with AI?

AI Project Manager includes everything in AI Secretary, plus:
- Team collaboration and shared AI agents
- Project management with AI automation
- xSwarm Buzz - AI marketing platform included
- Multi-channel campaign management

It's like upgrading from a solo AI to an entire AI department.

Learn more: ${data.cta_url}`
    }),

    template_secretary_to_pm_features: () => ({
      html: renderTemplate('Meet xSwarm Buzz', `
        <h1>Your AI Marketing Platform</h1>
        <p>Hi ${data.name},</p>
        <p>Here's the thing: AI Project Manager includes <strong>xSwarm Buzz</strong>.</p>
        <p>Buzz is an AI marketing platform that runs on auto-pilot:</p>
        <div class="feature-grid">
          <div class="feature">
            <h3>✍️ AI Content Generation</h3>
            <p>Blog posts, social media, email campaigns</p>
          </div>
          <div class="feature">
            <h3>📊 Campaign Management</h3>
            <p>Multi-channel marketing automation</p>
          </div>
          <div class="feature">
            <h3>🎯 Audience Targeting</h3>
            <p>Smart segmentation and personalization</p>
          </div>
          <div class="feature">
            <h3>📈 Analytics Dashboard</h3>
            <p>Real-time performance tracking</p>
          </div>
        </div>
        <p>Buzz alone is worth $99/month. <strong>You get it included with AI Project Manager.</strong></p>
        ${renderCTA(data.cta_url, 'Explore xSwarm Buzz')}
      `, data),
      text: `Meet xSwarm Buzz - Your AI Marketing Platform

Hi ${data.name},

AI Project Manager includes xSwarm Buzz - an AI marketing platform that runs on auto-pilot:

✍️ AI Content Generation - Blog posts, social media, email campaigns
📊 Campaign Management - Multi-channel marketing automation
🎯 Audience Targeting - Smart segmentation and personalization
📈 Analytics Dashboard - Real-time performance tracking

Buzz alone is worth $99/month. You get it included with AI Project Manager.

Explore Buzz: ${data.cta_url}`
    }),

    template_secretary_to_pm_testimonial: () => ({
      html: renderTemplate('Team Productivity Breakthrough', `
        <h1>How Mike's Team Doubled Output</h1>
        <blockquote>
          "We upgraded to AI Project Manager and it transformed how we work.
          The team collaboration features are incredible, and xSwarm Buzz handles
          all our marketing. We doubled output without hiring anyone new."
          <footer>— Mike Rodriguez, Agency Owner</footer>
        </blockquote>
        <div class="stats">
          <div class="stat">
            <div class="stat-number">2x</div>
            <div class="stat-label">Team output</div>
          </div>
          <div class="stat">
            <div class="stat-number">$0</div>
            <div class="stat-label">Marketing costs</div>
          </div>
          <div class="stat">
            <div class="stat-number">15 hrs</div>
            <div class="stat-label">Saved per person/week</div>
          </div>
        </div>
        <p>AI Project Manager pays for itself immediately.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `How Mike's Team Doubled Output

"We upgraded to AI Project Manager and it transformed how we work.
The team collaboration features are incredible, and xSwarm Buzz handles
all our marketing. We doubled output without hiring anyone new."
— Mike Rodriguez, Agency Owner

Results:
- 2x team output
- $0 marketing costs (Buzz handles it)
- 15 hours saved per person per week

AI Project Manager pays for itself immediately.

Read case studies: ${data.cta_url}`
    }),

    template_secretary_to_pm_spotlight: () => ({
      html: renderTemplate('Project Management + Marketing = xSwarm', `
        <h1>Two Powerful Platforms, One Price</h1>
        <p>Hi ${data.name},</p>
        <p>Let me break down what you get with AI Project Manager:</p>
        <div class="comparison">
          <div class="col">
            <h3>Project Management</h3>
            <ul>
              <li>AI-powered task automation</li>
              <li>Team collaboration tools</li>
              <li>Smart scheduling and resource allocation</li>
              <li>Real-time progress tracking</li>
            </ul>
          </div>
          <div class="col">
            <h3>xSwarm Buzz Marketing</h3>
            <ul>
              <li>AI content generation</li>
              <li>Multi-channel campaigns</li>
              <li>Audience segmentation</li>
              <li>Performance analytics</li>
            </ul>
          </div>
        </div>
        <p><strong>Both platforms. One subscription. Incredible value.</strong></p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `Two Powerful Platforms, One Price

Hi ${data.name},

AI Project Manager gives you:

Project Management:
- AI-powered task automation
- Team collaboration tools
- Smart scheduling and resource allocation
- Real-time progress tracking

xSwarm Buzz Marketing:
- AI content generation
- Multi-channel campaigns
- Audience segmentation
- Performance analytics

Both platforms. One subscription. Incredible value.

See the platform: ${data.cta_url}`
    }),

    template_secretary_to_pm_offer: () => ({
      html: renderTemplate('Save $50/Month on AI Project Manager', `
        <h1>Limited Time: Project Manager Pricing</h1>
        <p>Hi ${data.name},</p>
        <div class="offer-box">
          <div class="old-price">$149/month</div>
          <div class="new-price">$99/month</div>
          <div class="offer-badge">TEAM50 - SAVE $50/MONTH</div>
        </div>
        <p><strong>Get team features + xSwarm Buzz at a special rate.</strong></p>
        <p>This upgrade includes:</p>
        <ul>
          <li>✓ Everything in AI Secretary</li>
          <li>✓ Team collaboration (up to 10 members)</li>
          <li>✓ AI Project Management</li>
          <li>✓ xSwarm Buzz marketing platform (value: $99/mo)</li>
          <li>✓ Priority support</li>
        </ul>
        <p><strong>You're already paying $49/mo. Upgrade for just $50 more.</strong></p>
        ${renderCTA(data.cta_url, 'Claim Your $50 Discount')}
        <p><small>Use code TEAM50 at checkout. Limited time offer.</small></p>
      `, data),
      text: `Save $50/Month on AI Project Manager

Hi ${data.name},

Special Offer: $99/month (was $149/month)
Code: TEAM50 - Save $50/month

This upgrade includes:
✓ Everything in AI Secretary
✓ Team collaboration (up to 10 members)
✓ AI Project Management
✓ xSwarm Buzz marketing platform (value: $99/mo)
✓ Priority support

You're already paying $49/mo. Upgrade for just $50 more.

Claim offer: ${data.cta_url}

Use code TEAM50 at checkout.`
    }),

    template_secretary_to_pm_final: () => ({
      html: renderTemplate('Scale Your Business with AI PM', `
        <h1>Your Team is Waiting</h1>
        <p>Hi ${data.name},</p>
        <p>This is my final email about AI Project Manager.</p>
        <p>You've seen what AI Secretary can do for you personally. Now imagine that power
        multiplied across your entire team, with marketing automation included.</p>
        <p>That's AI Project Manager.</p>
        <p><strong>The math is simple:</strong></p>
        <ul>
          <li>AI Secretary: $49/month (just you)</li>
          <li>AI Project Manager: $99/month (entire team + Buzz marketing)</li>
          <li>ROI: Immediate (team saves 15+ hours/week)</li>
        </ul>
        <p>Take the next step in AI-powered business growth.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
        <p><small>Questions? Reply and let's talk about your specific needs.</small></p>
      `, data),
      text: `Scale Your Business with AI PM

Hi ${data.name},

This is my final email about AI Project Manager.

You've seen what AI Secretary can do for you personally. Now imagine that power
multiplied across your entire team, with marketing automation included.

That's AI Project Manager.

The math is simple:
- AI Secretary: $49/month (just you)
- AI Project Manager: $99/month (entire team + Buzz marketing)
- ROI: Immediate (team saves 15+ hours/week)

Take the next step in AI-powered business growth.

Upgrade today: ${data.cta_url}

Questions? Reply to this email.`
    }),

    // =========================================================================
    // PROJECT MANAGER → AI CTO TEMPLATES
    // =========================================================================

    template_pm_to_cto_welcome: () => ({
      html: renderTemplate('Enterprise-Grade AI', `
        <h1>Introducing AI CTO - Unlimited Everything</h1>
        <p>Hi ${data.name},</p>
        <p>AI Project Manager is powerful. But you've hit some limits, haven't you?</p>
        <p>Usage caps. Integration constraints. Support wait times.</p>
        <p><strong>AI CTO removes all limits:</strong></p>
        <ul>
          <li>Unlimited calls, messages, and AI usage</li>
          <li>Custom integrations with your existing tools</li>
          <li>Dedicated support team</li>
          <li>Enterprise SLA and security</li>
          <li>White-label options</li>
        </ul>
        <p>This is xSwarm for serious businesses that refuse to compromise.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `Introducing AI CTO - Unlimited Everything

Hi ${data.name},

AI Project Manager is powerful. But you've hit some limits, haven't you?

Usage caps. Integration constraints. Support wait times.

AI CTO removes all limits:
- Unlimited calls, messages, and AI usage
- Custom integrations with your existing tools
- Dedicated support team
- Enterprise SLA and security
- White-label options

This is xSwarm for serious businesses that refuse to compromise.

Explore AI CTO: ${data.cta_url}`
    }),

    template_pm_to_cto_features: () => ({
      html: renderTemplate('Scale Without Worry', `
        <h1>No More Usage Limits</h1>
        <p>Hi ${data.name},</p>
        <p>Remember checking your usage dashboard? Worried about overage charges?</p>
        <p><strong>With AI CTO, you never think about limits again:</strong></p>
        <div class="unlimited-grid">
          <div class="unlimited-item">
            <h3>∞ Unlimited Calls</h3>
            <p>Handle 10 or 10,000 calls/day. We scale with you.</p>
          </div>
          <div class="unlimited-item">
            <h3>∞ Unlimited AI Usage</h3>
            <p>No token limits. Use AI as much as you need.</p>
          </div>
          <div class="unlimited-item">
            <h3>∞ Unlimited Team Members</h3>
            <p>100+ person teams? No problem.</p>
          </div>
          <div class="unlimited-item">
            <h3>∞ Unlimited Storage</h3>
            <p>Store all your data, transcripts, and analytics forever.</p>
          </div>
        </div>
        <p><strong>AI CTO removes all constraints on your growth.</strong></p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `No More Usage Limits

Hi ${data.name},

Remember checking your usage dashboard? Worried about overage charges?

With AI CTO, you never think about limits again:

∞ Unlimited Calls - Handle 10 or 10,000 calls/day
∞ Unlimited AI Usage - No token limits
∞ Unlimited Team Members - 100+ person teams? No problem
∞ Unlimited Storage - All your data, forever

AI CTO removes all constraints on your growth.

See what's included: ${data.cta_url}`
    }),

    template_pm_to_cto_testimonial: () => ({
      html: renderTemplate('Why TechCorp Chose AI CTO', `
        <h1>Enterprise Success Story</h1>
        <blockquote>
          "We needed AI that could scale with our 200-person team. AI CTO delivered.
          The custom integrations with our CRM and project management tools were seamless.
          Our dedicated support team responds in minutes, not days."
          <footer>— David Kim, CTO at TechCorp</footer>
        </blockquote>
        <div class="stats">
          <div class="stat">
            <div class="stat-number">200+</div>
            <div class="stat-label">Team members</div>
          </div>
          <div class="stat">
            <div class="stat-number">50K+</div>
            <div class="stat-label">Calls/month</div>
          </div>
          <div class="stat">
            <div class="stat-number">99.9%</div>
            <div class="stat-label">Uptime SLA</div>
          </div>
        </div>
        <p>Fortune 500 companies trust xSwarm AI CTO.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
      `, data),
      text: `Why TechCorp Chose AI CTO

"We needed AI that could scale with our 200-person team. AI CTO delivered.
The custom integrations with our CRM and project management tools were seamless.
Our dedicated support team responds in minutes, not days."
— David Kim, CTO at TechCorp

Results:
- 200+ team members using xSwarm
- 50,000+ calls per month
- 99.9% uptime SLA

Fortune 500 companies trust xSwarm AI CTO.

Read enterprise stories: ${data.cta_url}`
    }),

    template_pm_to_cto_spotlight: () => ({
      html: renderTemplate('Custom Integrations Built for You', `
        <h1>Dedicated Engineering Support</h1>
        <p>Hi ${data.name},</p>
        <p>Every business is unique. AI CTO adapts to your workflow, not the other way around.</p>
        <p><strong>Your dedicated engineering team will:</strong></p>
        <ul>
          <li>Build custom integrations with your existing tools</li>
          <li>Configure AI agents for your specific use cases</li>
          <li>Optimize performance for your workflow</li>
          <li>Provide ongoing technical support</li>
        </ul>
        <p><strong>Popular integrations we've built:</strong></p>
        <ul>
          <li>Salesforce, HubSpot, Pipedrive CRM sync</li>
          <li>Slack, Microsoft Teams real-time alerts</li>
          <li>Jira, Asana, Monday.com project management</li>
          <li>Custom ERP and internal tool connections</li>
        </ul>
        ${renderCTA(data.cta_url, 'Book Enterprise Consultation')}
      `, data),
      text: `Custom Integrations Built for You

Hi ${data.name},

Every business is unique. AI CTO adapts to your workflow, not the other way around.

Your dedicated engineering team will:
- Build custom integrations with your existing tools
- Configure AI agents for your specific use cases
- Optimize performance for your workflow
- Provide ongoing technical support

Popular integrations we've built:
- Salesforce, HubSpot, Pipedrive CRM sync
- Slack, Microsoft Teams real-time alerts
- Jira, Asana, Monday.com project management
- Custom ERP and internal tool connections

Book consultation: ${data.cta_url}`
    }),

    template_pm_to_cto_offer: () => ({
      html: renderTemplate('Enterprise Pricing - Lock In Now', `
        <h1>Save 20% with Annual AI CTO</h1>
        <p>Hi ${data.name},</p>
        <div class="offer-box">
          <div class="old-price">$499/month</div>
          <div class="new-price">$399/month</div>
          <div class="offer-badge">ENTERPRISE20 - SAVE 20% ANNUALLY</div>
        </div>
        <p><strong>Get unlimited AI at a price that makes sense.</strong></p>
        <p>AI CTO annual plan includes:</p>
        <ul>
          <li>✓ Everything unlimited (calls, AI, storage, team)</li>
          <li>✓ Custom integrations and dedicated engineering</li>
          <li>✓ 24/7 priority support with 1-hour response SLA</li>
          <li>✓ Enterprise security and compliance (SOC 2, HIPAA)</li>
          <li>✓ White-label options and custom branding</li>
        </ul>
        <p><strong>Lock in today and save $1,200/year.</strong></p>
        ${renderCTA(data.cta_url, 'View Enterprise Pricing')}
        <p><small>Use code ENTERPRISE20. Annual billing required for discount.</small></p>
      `, data),
      text: `Save 20% with Annual AI CTO

Hi ${data.name},

Special Offer: $399/month (was $499/month)
Code: ENTERPRISE20 - Save 20% annually

AI CTO annual plan includes:
✓ Everything unlimited (calls, AI, storage, team)
✓ Custom integrations and dedicated engineering
✓ 24/7 priority support with 1-hour response SLA
✓ Enterprise security and compliance (SOC 2, HIPAA)
✓ White-label options and custom branding

Lock in today and save $1,200/year.

View pricing: ${data.cta_url}

Use code ENTERPRISE20. Annual billing required.`
    }),

    template_pm_to_cto_final: () => ({
      html: renderTemplate('Ready for Unlimited AI?', `
        <h1>Your AI CTO is Waiting</h1>
        <p>Hi ${data.name},</p>
        <p>This is my final email about AI CTO.</p>
        <p>You're running a serious business. You need serious tools.</p>
        <p><strong>AI CTO is for companies that:</strong></p>
        <ul>
          <li>Refuse to compromise on quality</li>
          <li>Need unlimited scale</li>
          <li>Require custom integrations</li>
          <li>Demand enterprise support</li>
          <li>Value their time (and their team's time)</li>
        </ul>
        <p>Join the elite tier of AI-powered businesses.</p>
        ${renderCTA(data.cta_url, data.cta_text)}
        <p><strong>Want to discuss your specific needs?</strong><br>
        Reply to this email and I'll personally connect you with our enterprise team.</p>
      `, data),
      text: `Ready for Unlimited AI?

Hi ${data.name},

This is my final email about AI CTO.

You're running a serious business. You need serious tools.

AI CTO is for companies that:
- Refuse to compromise on quality
- Need unlimited scale
- Require custom integrations
- Demand enterprise support
- Value their time (and their team's time)

Join the elite tier of AI-powered businesses.

Upgrade to AI CTO: ${data.cta_url}

Want to discuss your specific needs?
Reply and I'll connect you with our enterprise team.`
    }),
  };

  const template = templates[templateId];
  if (!template) {
    throw new Error(`Unknown template ID: ${templateId}`);
  }

  return template();
}

/**
 * Render email template with xSwarm branding
 */
function renderTemplate(title, content, data) {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    body {
      font-family: 'Monaco', 'Courier New', monospace;
      line-height: 1.6;
      color: #00ff00;
      background-color: #000000;
      margin: 0;
      padding: 0;
    }
    .container {
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background-color: #0a0a0a;
      border: 1px solid #00ff00;
    }
    .header {
      text-align: center;
      padding: 20px 0;
      border-bottom: 1px solid #00ff00;
      margin-bottom: 30px;
    }
    .logo {
      color: #00ff00;
      font-size: 24px;
      font-weight: bold;
      letter-spacing: 2px;
    }
    .content {
      padding: 20px 0;
    }
    h1 {
      color: #00ff00;
      font-size: 24px;
      margin-bottom: 20px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    h2, h3 {
      color: #00dd00;
      margin-top: 20px;
    }
    p {
      color: #00cc00;
      margin-bottom: 15px;
    }
    ul {
      color: #00cc00;
      margin: 15px 0;
      padding-left: 20px;
    }
    li {
      margin-bottom: 8px;
    }
    .cta-button {
      display: inline-block;
      padding: 15px 30px;
      background-color: #00ff00;
      color: #000000;
      text-decoration: none;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 1px;
      border: 2px solid #00ff00;
      margin: 20px 0;
    }
    .cta-button:hover {
      background-color: #000000;
      color: #00ff00;
    }
    .cta-center {
      text-align: center;
      margin: 30px 0;
    }
    blockquote {
      border-left: 3px solid #00ff00;
      padding-left: 20px;
      margin: 20px 0;
      font-style: italic;
      color: #00dd00;
    }
    blockquote footer {
      margin-top: 10px;
      font-style: normal;
      font-weight: bold;
      color: #00ff00;
    }
    .stats {
      display: flex;
      justify-content: space-around;
      margin: 30px 0;
      text-align: center;
    }
    .stat {
      flex: 1;
      padding: 20px;
      border: 1px solid #00ff00;
      margin: 0 5px;
    }
    .stat-number {
      font-size: 32px;
      font-weight: bold;
      color: #00ff00;
    }
    .stat-label {
      font-size: 12px;
      color: #00cc00;
      text-transform: uppercase;
    }
    .feature-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin: 20px 0;
    }
    .feature {
      border: 1px solid #00ff00;
      padding: 15px;
    }
    .feature h3 {
      margin-top: 0;
      font-size: 16px;
    }
    .offer-box {
      text-align: center;
      padding: 30px;
      border: 2px solid #00ff00;
      background-color: #001100;
      margin: 20px 0;
    }
    .old-price {
      text-decoration: line-through;
      color: #666;
      font-size: 18px;
    }
    .new-price {
      font-size: 36px;
      font-weight: bold;
      color: #00ff00;
      margin: 10px 0;
    }
    .offer-badge {
      display: inline-block;
      background-color: #00ff00;
      color: #000000;
      padding: 10px 20px;
      font-weight: bold;
      letter-spacing: 1px;
      margin-top: 10px;
    }
    .footer {
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid #00ff00;
      text-align: center;
      font-size: 12px;
      color: #006600;
    }
    .footer a {
      color: #00ff00;
      text-decoration: none;
    }
    small {
      color: #008800;
      font-size: 12px;
    }
    .comparison {
      display: flex;
      gap: 20px;
      margin: 20px 0;
    }
    .comparison .col {
      flex: 1;
      border: 1px solid #00ff00;
      padding: 15px;
    }
    .unlimited-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin: 20px 0;
    }
    .unlimited-item {
      border: 1px solid #00ff00;
      padding: 15px;
    }
    .unlimited-item h3 {
      margin-top: 0;
      color: #00ff00;
    }

    /* Mobile responsive */
    @media only screen and (max-width: 600px) {
      .stats {
        flex-direction: column;
      }
      .stat {
        margin: 5px 0;
      }
      .feature-grid, .unlimited-grid {
        grid-template-columns: 1fr;
      }
      .comparison {
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">[ xSWARM AI ]</div>
    </div>
    <div class="content">
      ${content}
    </div>
    <div class="footer">
      <p>xSwarm AI - Your AI-Powered Business Operations Platform</p>
      <p>
        <a href="${data.unsubscribe_url || 'https://xswarm.ai/unsubscribe/' + (data.unsubscribe_token || '')}">Unsubscribe</a> |
        <a href="https://xswarm.ai/privacy">Privacy Policy</a> |
        <a href="https://xswarm.ai/terms">Terms of Service</a>
      </p>
      <p>© 2025 xSwarm. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
  `.trim();
}

/**
 * Render CTA button
 */
function renderCTA(url, text) {
  return `
    <div class="cta-center">
      <a href="${url}" class="cta-button">${text}</a>
    </div>
  `.trim();
}
