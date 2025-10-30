# Email Verification & JWT Authentication System

## Overview
Implement a complete email verification system with JWT tokens and user authentication flow for the xSwarm SaaS platform.

## Todo Items

### 1. Database Schema Migration
**File**: `packages/server/migrations/auth.sql`
- Add email verification fields to users table:
  - `email_verified` BOOLEAN DEFAULT FALSE
  - `email_verification_token` TEXT (nullable)
  - `email_verification_expires` TEXT (nullable, ISO 8601 timestamp)
  - `password_hash` TEXT (for bcrypt hashed passwords)
  - `password_reset_token` TEXT (nullable)
  - `password_reset_expires` TEXT (nullable, ISO 8601 timestamp)
  - `jwt_version` INTEGER DEFAULT 0 (for token invalidation)
- Add indexes for token lookups
- Add indexes for email verification status

### 2. Install Required Dependencies
**File**: `packages/server/package.json`
- Add `bcryptjs` for password hashing (^2.4.3)
- Add `jsonwebtoken` for JWT token generation/verification (^9.0.2)
- Run `pnpm install` in packages/server

### 3. JWT Authentication Middleware
**File**: `packages/server/src/lib/jwt.js`
- `generateToken(user)` - Generate JWT with user ID, email, tier
- `verifyToken(token)` - Verify and decode JWT
- `generateEmailVerificationToken()` - Generate secure random token
- `generatePasswordResetToken()` - Generate secure password reset token
- Token expiration: 7 days for auth, 24 hours for email verification, 1 hour for password reset
- Include subscription tier in JWT payload

### 4. Password Utilities
**File**: `packages/server/src/lib/password.js`
- `hashPassword(password)` - Hash password with bcrypt (10 rounds)
- `verifyPassword(password, hash)` - Verify password against hash
- Password validation rules (min 8 chars, complexity requirements)

### 5. Email Templates Module
**File**: `packages/server/src/lib/email-templates.js`
- `getVerificationEmailTemplate(verificationLink)` - HTML + text email
- `getPasswordResetEmailTemplate(resetLink)` - HTML + text email
- `getWelcomeEmailTemplate(userName)` - Welcome email after verification
- Use existing SendGrid integration pattern

### 6. Auth Routes - Signup
**File**: `packages/server/src/routes/auth/signup.js`
**Endpoint**: `POST /auth/signup`
- Accept: email, password, firstName, lastName, plan
- Validate email format and uniqueness
- Validate password strength
- Hash password with bcrypt
- Create user record with email_verified=false
- Generate email verification token (expires in 24 hours)
- Send verification email via SendGrid
- Return success message (no JWT yet - email must be verified first)

### 7. Auth Routes - Verify Email
**File**: `packages/server/src/routes/auth/verify-email.js`
**Endpoint**: `POST /auth/verify-email`
- Accept: token (from email link)
- Look up user by verification token
- Check token hasn't expired
- Set email_verified=true, clear verification token
- Generate JWT token
- Send welcome email
- Return JWT + user info

### 8. Auth Routes - Login
**File**: `packages/server/src/routes/auth/login.js`
**Endpoint**: `POST /auth/login`
- Accept: email, password
- Look up user by email
- Check email is verified
- Verify password hash
- Generate new JWT token
- Return JWT + user info

### 9. Auth Routes - Logout
**File**: `packages/server/src/routes/auth/logout.js`
**Endpoint**: `POST /auth/logout`
- Accept: JWT in Authorization header
- Increment user's jwt_version in database (invalidates all existing tokens)
- Return success message

### 10. Auth Routes - Forgot Password
**File**: `packages/server/src/routes/auth/forgot-password.js`
**Endpoint**: `POST /auth/forgot-password`
- Accept: email
- Look up user by email
- Generate password reset token (expires in 1 hour)
- Send password reset email with link
- Return success message (always, even if email not found - security)

### 11. Auth Routes - Reset Password
**File**: `packages/server/src/routes/auth/reset-password.js`
**Endpoint**: `POST /auth/reset-password`
- Accept: token, newPassword
- Look up user by reset token
- Check token hasn't expired
- Validate new password strength
- Hash new password
- Clear reset token
- Increment jwt_version (invalidate existing sessions)
- Return success message

### 12. Auth Routes - Get Current User
**File**: `packages/server/src/routes/auth/me.js`
**Endpoint**: `GET /auth/me`
- Require JWT authentication
- Return current user info from token
- Include subscription tier, features available

### 13. Auth Middleware
**File**: `packages/server/src/lib/auth-middleware.js`
- `requireAuth(request, env)` - Verify JWT, extract user
- `optionalAuth(request, env)` - Extract user if JWT present
- Check jwt_version matches database (token not invalidated)
- Return user object or throw 401 error

### 14. Update Main Router
**File**: `packages/server/src/index.js`
- Import all auth route handlers
- Add routes:
  - `POST /auth/signup`
  - `POST /auth/verify-email`
  - `POST /auth/login`
  - `POST /auth/logout`
  - `POST /auth/forgot-password`
  - `POST /auth/reset-password`
  - `GET /auth/me`
- Add auth routes BEFORE existing routes (for proper ordering)

### 15. Update Signup Page
**File**: `signup-page/index.html`
- Update form submission to call `POST /auth/signup`
- Add password field with validation
- Add password confirmation field
- Show success message with "Check your email" instructions
- Handle API errors (email exists, etc.)
- Add password strength indicator

### 16. Environment Variables
**File**: `.env.example`
- Add `JWT_SECRET` documentation
- Add instructions for generating secure JWT secret

### 17. Database Migration Script
**File**: `packages/server/scripts/migrate-auth.js`
- Run auth.sql migration
- Create indexes
- Output migration results

### 18. Update Users Module
**File**: `packages/server/src/lib/users.js`
- Add `getUserByVerificationToken(token, env)`
- Add `getUserByResetToken(token, env)`
- Add `updateEmailVerified(userId, env)`
- Add `updatePasswordHash(userId, hash, env)`
- Add `incrementJwtVersion(userId, env)`

## Implementation Order
1. Dependencies (#2)
2. Database migration (#1)
3. Utility modules (#3, #4, #5)
4. Users module updates (#18)
5. Auth routes (#6-12)
6. Middleware (#13)
7. Main router (#14)
8. Signup page (#15)
9. Environment setup (#16, #17)

## Security Considerations
- Use bcrypt with 10+ rounds for password hashing
- JWT tokens expire after 7 days
- Email verification tokens expire after 24 hours
- Password reset tokens expire after 1 hour
- Token invalidation via jwt_version incrementing
- Rate limiting on auth endpoints (future enhancement)
- HTTPS only in production
- Secure, httpOnly cookies for JWT (future enhancement)

## Testing Checklist
- [ ] User can signup with email/password
- [ ] Verification email is sent
- [ ] User can verify email with token
- [ ] User receives welcome email after verification
- [ ] User can login with email/password
- [ ] Invalid credentials are rejected
- [ ] Unverified emails cannot login
- [ ] JWT token is valid and contains correct data
- [ ] User can access /auth/me with valid token
- [ ] User can logout (token invalidated)
- [ ] User can request password reset
- [ ] Password reset email is sent
- [ ] User can reset password with token
- [ ] Expired tokens are rejected
- [ ] Invalid tokens are rejected
- [ ] Old JWT tokens are invalid after password reset
- [ ] Signup page integrates with backend
