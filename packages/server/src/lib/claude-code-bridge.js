/**
 * Claude Code Bridge
 *
 * Connects Boss Assistant webhooks to Claude Code capabilities
 * Allows users to execute development tasks via SMS and email
 *
 * Features:
 * - Task detection and classification
 * - Secure execution environment
 * - Progress tracking and reporting
 * - Safety whitelisting
 * - Mock mode for testing
 */

/**
 * Task types that can be executed
 */
export const TASK_TYPES = {
  GIT: 'git',
  BUILD: 'build',
  TEST: 'test',
  DEPLOY: 'deploy',
  DEPENDENCIES: 'dependencies',
  CODE_ANALYSIS: 'code_analysis',
  FILE_OPERATIONS: 'file_operations',
  DEBUG: 'debug',
  UNKNOWN: 'unknown'
};

/**
 * Task risk levels for safety checks
 */
export const RISK_LEVELS = {
  SAFE: 'safe',           // Read-only operations
  LOW: 'low',             // Non-destructive changes
  MEDIUM: 'medium',       // Potentially risky operations
  HIGH: 'high',           // Destructive operations
  CRITICAL: 'critical'    // Requires explicit confirmation
};

/**
 * Whitelist of allowed operations per risk level
 */
const ALLOWED_OPERATIONS = {
  [RISK_LEVELS.SAFE]: [
    'git status',
    'git log',
    'git diff',
    'git branch',
    'npm list',
    'cat',
    'ls',
    'pwd',
    'grep',
    'find',
    'head',
    'tail'
  ],
  [RISK_LEVELS.LOW]: [
    'npm install',
    'npm update',
    'git checkout',
    'git pull',
    'npm run build',
    'npm run test',
    'cargo build',
    'cargo test'
  ],
  [RISK_LEVELS.MEDIUM]: [
    'git commit',
    'git push',
    'npm publish',
    'cargo publish'
  ],
  [RISK_LEVELS.HIGH]: [
    'git reset --hard',
    'rm -rf',
    'npm run deploy',
    'cargo clean'
  ],
  [RISK_LEVELS.CRITICAL]: [
    'git push --force',
    'git rebase',
    'npm unpublish',
    'system operations'
  ]
};

/**
 * Detect task type from user message
 *
 * @param {string} message - User's message text
 * @returns {Object} Task information { type, commands, risk, needsConfirmation }
 */
export function detectTask(message) {
  const text = message.toLowerCase().trim();

  // Git operations
  if (text.match(/\b(git|commit|push|pull|merge|branch|checkout|status|diff|log)\b/i)) {
    return analyzeGitTask(text);
  }

  // Build operations
  if (text.match(/\b(build|compile|bundle|webpack|rollup|vite)\b/i)) {
    return {
      type: TASK_TYPES.BUILD,
      commands: ['npm run build'],
      risk: RISK_LEVELS.LOW,
      needsConfirmation: false,
      description: 'Build the project'
    };
  }

  // Test operations
  if (text.match(/\b(test|spec|jest|mocha|vitest|cargo test|run test)\b/i) ||
      text.match(/\brun\s+tests?\b/i)) {
    return {
      type: TASK_TYPES.TEST,
      commands: ['npm run test'],
      risk: RISK_LEVELS.SAFE,
      needsConfirmation: false,
      description: 'Run test suite'
    };
  }

  // Deploy operations
  if (text.match(/\b(deploy|publish|release)\b/i)) {
    return {
      type: TASK_TYPES.DEPLOY,
      commands: ['npm run deploy'],
      risk: RISK_LEVELS.HIGH,
      needsConfirmation: true,
      description: 'Deploy application'
    };
  }

  // Dependency management
  if (text.match(/\b(dependencies|packages|npm install|npm update|yarn|pnpm)\b/i)) {
    return analyzeDependencyTask(text);
  }

  // Code analysis
  if (text.match(/\b(lint|eslint|prettier|format|analyze|check)\b/i)) {
    return {
      type: TASK_TYPES.CODE_ANALYSIS,
      commands: ['npm run lint'],
      risk: RISK_LEVELS.SAFE,
      needsConfirmation: false,
      description: 'Run code analysis'
    };
  }

  // Debug operations
  if (text.match(/\b(debug|fix|error|bug|issue)\b/i)) {
    return {
      type: TASK_TYPES.DEBUG,
      commands: [], // Requires AI analysis
      risk: RISK_LEVELS.MEDIUM,
      needsConfirmation: false,
      description: 'Debug and fix issues'
    };
  }

  // File operations
  if (text.match(/\b(create|delete|move|copy|read|write|file|directory)\b/i)) {
    return {
      type: TASK_TYPES.FILE_OPERATIONS,
      commands: [], // Specific to request
      risk: RISK_LEVELS.MEDIUM,
      needsConfirmation: true,
      description: 'File system operations'
    };
  }

  return {
    type: TASK_TYPES.UNKNOWN,
    commands: [],
    risk: RISK_LEVELS.SAFE,
    needsConfirmation: false,
    description: 'Unknown task type'
  };
}

/**
 * Analyze Git-related tasks
 */
function analyzeGitTask(text) {
  // Status check (safe)
  if (text.match(/\b(git status|status|what changed|changes)\b/i)) {
    return {
      type: TASK_TYPES.GIT,
      commands: ['git status', 'git diff --stat'],
      risk: RISK_LEVELS.SAFE,
      needsConfirmation: false,
      description: 'Check git status'
    };
  }

  // Pull changes (low risk)
  if (text.match(/\b(git pull|pull|update|sync)\b/i)) {
    return {
      type: TASK_TYPES.GIT,
      commands: ['git pull'],
      risk: RISK_LEVELS.LOW,
      needsConfirmation: false,
      description: 'Pull latest changes'
    };
  }

  // Force push (critical risk) - Check this FIRST
  if (text.match(/\b(force\s+push|push\s+--force|push\s+-f)\b/i)) {
    return {
      type: TASK_TYPES.GIT,
      commands: ['git push --force'],
      risk: RISK_LEVELS.CRITICAL,
      needsConfirmation: true,
      description: 'Force push (DANGEROUS)'
    };
  }

  // Commit changes (medium risk)
  if (text.match(/\b(git\s+commit|commit\s+(these\s+)?changes|save\s+changes)\b/i)) {
    return {
      type: TASK_TYPES.GIT,
      commands: ['git add .', 'git commit -m "Auto-commit via Boss"'],
      risk: RISK_LEVELS.MEDIUM,
      needsConfirmation: true,
      description: 'Commit changes'
    };
  }

  // Push changes (medium risk)
  if (text.match(/\b(git\s+push|push\s+to|push\s+changes|publish\s+changes)\b/i)) {
    return {
      type: TASK_TYPES.GIT,
      commands: ['git push'],
      risk: RISK_LEVELS.MEDIUM,
      needsConfirmation: true,
      description: 'Push to remote'
    };
  }

  // Default git status
  return {
    type: TASK_TYPES.GIT,
    commands: ['git status'],
    risk: RISK_LEVELS.SAFE,
    needsConfirmation: false,
    description: 'Check git status'
  };
}

/**
 * Analyze dependency-related tasks
 */
function analyzeDependencyTask(text) {
  // Check dependencies (safe)
  if (text.match(/\b(list|show|check) (dependencies|packages)\b/i)) {
    return {
      type: TASK_TYPES.DEPENDENCIES,
      commands: ['npm list --depth=0'],
      risk: RISK_LEVELS.SAFE,
      needsConfirmation: false,
      description: 'List dependencies'
    };
  }

  // Install dependencies (low risk)
  if (text.match(/\b(install|add) (dependencies|packages)\b/i)) {
    return {
      type: TASK_TYPES.DEPENDENCIES,
      commands: ['npm install'],
      risk: RISK_LEVELS.LOW,
      needsConfirmation: false,
      description: 'Install dependencies'
    };
  }

  // Update dependencies (medium risk)
  if (text.match(/\b(update|upgrade) (dependencies|packages)\b/i)) {
    return {
      type: TASK_TYPES.DEPENDENCIES,
      commands: ['npm update'],
      risk: RISK_LEVELS.MEDIUM,
      needsConfirmation: true,
      description: 'Update dependencies'
    };
  }

  return {
    type: TASK_TYPES.DEPENDENCIES,
    commands: ['npm list --depth=0'],
    risk: RISK_LEVELS.SAFE,
    needsConfirmation: false,
    description: 'Check dependencies'
  };
}

/**
 * Execute task in mock mode (for testing)
 *
 * @param {Object} task - Task information from detectTask()
 * @param {Object} user - User information
 * @returns {Promise<Object>} Mock execution results
 */
export async function executeMockTask(task, user) {
  // Simulate execution delay
  await new Promise(resolve => setTimeout(resolve, 500));

  const mockResults = {
    success: true,
    taskType: task.type,
    risk: task.risk,
    commands: task.commands,
    output: generateMockOutput(task),
    executionTime: Math.floor(Math.random() * 3000) + 500,
    timestamp: new Date().toISOString()
  };

  return mockResults;
}

/**
 * Generate realistic mock output for different task types
 */
function generateMockOutput(task) {
  switch (task.type) {
    case TASK_TYPES.GIT:
      return `On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  modified:   packages/server/src/lib/claude.js
  modified:   packages/server/src/lib/claude-code-bridge.js

Untracked files:
  packages/server/src/lib/task-executor.js

no changes added to commit`;

    case TASK_TYPES.BUILD:
      return `> xswarm-server@0.1.0 build
> webpack --mode production

asset main.js 125 KiB [emitted] [minimized] (name: main)
webpack 5.89.0 compiled successfully in 2847ms`;

    case TASK_TYPES.TEST:
      return `PASS  src/__tests__/claude.test.js
✓ detects development tasks (24ms)
✓ formats SMS responses correctly (12ms)
✓ handles email responses (18ms)

Test Suites: 1 passed, 1 total
Tests:       3 passed, 3 total
Snapshots:   0 total
Time:        2.451s`;

    case TASK_TYPES.DEPENDENCIES:
      return `xswarm-server@0.1.0
├── @libsql/client@0.5.6
├── stripe@17.5.0
└── wrangler@4.45.0

All dependencies up to date.`;

    case TASK_TYPES.CODE_ANALYSIS:
      return `✓ 47 files checked
✓ No ESLint errors
✓ Code formatted with Prettier
✓ All type checks passed`;

    default:
      return `Task "${task.description}" executed successfully.`;
  }
}

/**
 * Format task results for SMS (concise)
 *
 * @param {Object} results - Task execution results
 * @returns {string} Formatted SMS message
 */
export function formatResultsForSMS(results) {
  if (!results.success) {
    return `Task failed: ${results.error || 'Unknown error'}`;
  }

  const statusEmoji = results.success ? '✅' : '❌';
  const taskName = results.taskType.toUpperCase();

  return `${statusEmoji} ${taskName} completed in ${Math.round(results.executionTime / 1000)}s

${truncateOutput(results.output, 200)}

- Boss`;
}

/**
 * Format task results for Email (detailed)
 *
 * @param {Object} results - Task execution results
 * @param {Object} task - Original task information
 * @param {Object} user - User information
 * @returns {string} Formatted email message
 */
export function formatResultsForEmail(results, task, user) {
  const statusEmoji = results.success ? '✅' : '❌';
  const timestamp = new Date(results.timestamp).toLocaleString();

  return `Hello ${user.name},

${statusEmoji} Task Completed: ${task.description}

**Task Details:**
- Type: ${task.type}
- Risk Level: ${task.risk}
- Execution Time: ${Math.round(results.executionTime / 1000)}s
- Completed: ${timestamp}

**Commands Executed:**
${task.commands.map(cmd => `  $ ${cmd}`).join('\n')}

**Output:**
\`\`\`
${results.output}
\`\`\`

${results.success ? 'Task completed successfully!' : 'Task encountered errors.'}

Best regards,
Your Boss Assistant 🤖

---
This is an automated development task execution report.`;
}

/**
 * Truncate output to fit within character limit
 */
function truncateOutput(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }

  const lines = text.split('\n');
  let result = '';

  for (const line of lines) {
    if (result.length + line.length + 1 > maxLength - 20) {
      result += '\n... (truncated)';
      break;
    }
    result += (result ? '\n' : '') + line;
  }

  return result;
}

/**
 * Validate if task is allowed to execute
 *
 * @param {Object} task - Task information
 * @param {Object} user - User information
 * @param {Object} options - Execution options
 * @returns {Object} Validation result { allowed, reason }
 */
export function validateTaskExecution(task, user, options = {}) {
  // Check if user is authorized
  if (!user || !user.username) {
    return {
      allowed: false,
      reason: 'User not authenticated'
    };
  }

  // Check if task type is supported
  if (task.type === TASK_TYPES.UNKNOWN) {
    return {
      allowed: false,
      reason: 'Task type not recognized'
    };
  }

  // Check risk level
  if (task.risk === RISK_LEVELS.CRITICAL && !options.forceConfirmed) {
    return {
      allowed: false,
      reason: 'Critical task requires explicit confirmation'
    };
  }

  // Check if commands are whitelisted
  const allAllowedOps = Object.values(ALLOWED_OPERATIONS).flat();
  for (const cmd of task.commands) {
    const cmdBase = cmd.split(' ')[0];
    const isAllowed = allAllowedOps.some(allowed =>
      allowed.includes(cmdBase) || cmd.includes(allowed)
    );

    if (!isAllowed && !options.mockMode) {
      return {
        allowed: false,
        reason: `Command not whitelisted: ${cmdBase}`
      };
    }
  }

  return {
    allowed: true,
    reason: 'Task validated successfully'
  };
}

/**
 * Main entry point: Process development task
 *
 * @param {Object} user - User information
 * @param {string} message - User's message/request
 * @param {Object} options - Execution options { mockMode, forceConfirmed }
 * @returns {Promise<Object>} Execution results
 */
export async function processDevTask(user, message, options = {}) {
  const { mockMode = true, forceConfirmed = false } = options;

  try {
    // 1. Detect task type and requirements
    const task = detectTask(message);

    console.log(`Detected task: ${task.type} (risk: ${task.risk})`);

    // 2. Validate task execution
    const validation = validateTaskExecution(task, user, { ...options, mockMode });

    if (!validation.allowed) {
      return {
        success: false,
        error: validation.reason,
        task,
        needsConfirmation: task.needsConfirmation
      };
    }

    // 3. Execute task (mock mode for safety)
    let results;
    if (mockMode) {
      console.log(`Executing task in MOCK mode: ${task.description}`);
      results = await executeMockTask(task, user);
    } else {
      // Real execution would go here
      // This requires actual Claude Code integration
      throw new Error('Real execution not yet implemented - use mock mode');
    }

    // 4. Return results
    return {
      success: true,
      task,
      results,
      mockMode
    };

  } catch (error) {
    console.error('Error processing dev task:', error);
    return {
      success: false,
      error: error.message,
      task: null
    };
  }
}

/**
 * Check if message contains a development task request
 *
 * @param {string} message - User's message
 * @returns {boolean} True if message contains dev task
 */
export function isDevTask(message) {
  const text = message.toLowerCase().trim();

  const devKeywords = [
    'git', 'commit', 'push', 'pull', 'merge', 'branch',
    'build', 'compile', 'bundle', 'deploy', 'publish',
    'test', 'spec', 'jest', 'mocha', 'vitest',
    'npm', 'yarn', 'pnpm', 'install', 'update', 'dependencies',
    'lint', 'eslint', 'prettier', 'format',
    'debug', 'fix', 'error', 'bug',
    'run tests', 'run build', 'check status'
  ];

  return devKeywords.some(keyword => text.includes(keyword));
}

/**
 * Get confirmation message for risky tasks
 *
 * @param {Object} task - Task information
 * @param {string} channel - Communication channel ('sms' or 'email')
 * @returns {string} Confirmation message
 */
export function getConfirmationMessage(task, channel) {
  if (channel === 'sms') {
    return `⚠️ "${task.description}" is a ${task.risk} risk operation.

Commands:
${task.commands.map(c => `• ${c}`).join('\n')}

Reply "CONFIRM" to proceed or "CANCEL" to abort.

- Boss`;
  } else {
    return `Hello,

You've requested a **${task.risk} risk** operation:

**Task:** ${task.description}

**Commands to be executed:**
${task.commands.map(c => `\`${c}\``).join('\n')}

**⚠️ Warning:** This operation may make significant changes to your codebase.

To proceed, reply with "CONFIRM" in the subject or body.
To cancel, reply with "CANCEL" or simply ignore this message.

Best regards,
Your Boss Assistant 🤖

---
Safety confirmation required for ${task.risk} risk operations.`;
  }
}
