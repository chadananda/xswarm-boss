/**
 * Turso Database Client
 *
 * LibSQL client for edge-optimized database access.
 * Uses embedded replica mode for local SQLite with cloud sync.
 *
 * IMPORTANT: This file is deprecated for user management.
 * Use src/lib/users.js for all user operations instead.
 *
 * User Architecture:
 * - Admin user: config.toml [admin] section (NOT in database)
 * - Regular users: Turso database (use users.js module)
 */

// Re-export user functions from users.js
export {
  getUserById,
  getUserByEmail,
  getUserByPhone,
  getUserByXswarmPhone,
  getUserByStripeCustomerId,
  createUser,
  updateUserTier,
  updateUserPhone,
  updateUserStripeInfo,
  listUsers,
  deleteUser,
  userHasFeature,
} from './users.js';
