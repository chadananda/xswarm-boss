# User Dashboard Implementation Todo List

## 1. Database Schema Extensions
- [ ] Create usage_records table for tracking voice/SMS/email usage
- [ ] Create billing_history table for invoice tracking
- [ ] Add indexes for efficient queries
- [ ] Create migration script for new tables

## 2. Backend API Routes - Dashboard Data
- [ ] GET /api/dashboard/overview - Summary stats and current plan info
- [ ] GET /api/dashboard/usage - Detailed usage analytics with time series data
- [ ] GET /api/dashboard/billing - Billing history and invoices
- [ ] GET /api/dashboard/subscription - Current subscription details
- [ ] PUT /api/dashboard/subscription - Update subscription preferences

## 3. Backend API Routes - User Profile
- [ ] GET /api/dashboard/profile - User profile information
- [ ] PUT /api/dashboard/profile - Update profile (name, preferences)
- [ ] PUT /api/dashboard/settings - Update account settings

## 4. Backend API Routes - Stripe Integration
- [ ] POST /api/dashboard/upgrade - Initiate subscription upgrade (Stripe checkout)
- [ ] POST /api/dashboard/downgrade - Downgrade subscription
- [ ] POST /api/dashboard/cancel - Cancel subscription
- [ ] GET /api/dashboard/invoices/:id/download - Download invoice PDF

## 5. Usage Tracking System
- [ ] Create usage-tracker.js module for recording usage
- [ ] Implement voice minutes tracking
- [ ] Implement SMS message counting
- [ ] Implement email volume tracking
- [ ] Add overage calculation logic
- [ ] Integrate usage tracking into existing routes

## 6. Dashboard Utilities Library
- [ ] Create dashboard-utils.js for data aggregation
- [ ] Implement usage statistics calculations
- [ ] Implement billing period calculations
- [ ] Create chart data formatters
- [ ] Add comparative analytics functions

## 7. Frontend - Dashboard HTML Page
- [ ] Create admin-pages/dashboard.html with terminal aesthetic
- [ ] Implement responsive navigation with tabs
- [ ] Add mobile-first responsive design
- [ ] Create loading states and error handling

## 8. Frontend - Overview Section
- [ ] Quick stats display (current plan, usage summary)
- [ ] Account status indicators
- [ ] Recent activity feed
- [ ] Quick action buttons

## 9. Frontend - Usage Analytics Section
- [ ] Voice minutes chart with Chart.js
- [ ] SMS message count display
- [ ] Email volume visualization
- [ ] Usage limit progress bars
- [ ] Month-over-month comparison
- [ ] Export usage data functionality

## 10. Frontend - Subscription Management Section
- [ ] Current plan display with feature list
- [ ] Upgrade/downgrade flow UI
- [ ] Billing cycle information
- [ ] Payment method management
- [ ] Cancel subscription dialog

## 11. Frontend - Billing History Section
- [ ] Invoice list table with pagination
- [ ] Invoice download links
- [ ] Payment history display
- [ ] Usage charges breakdown
- [ ] Upcoming charges preview

## 12. Frontend - Team Management Section (Pro+ only)
- [ ] Team overview display
- [ ] Member list with roles
- [ ] Invite member functionality
- [ ] Remove member functionality
- [ ] Conditional display based on plan

## 13. Frontend - Buzz Listings Section (Pro+ only)
- [ ] Buzz listings overview
- [ ] Analytics dashboard for buzz listings
- [ ] Create/edit buzz listing links
- [ ] Performance metrics display
- [ ] Conditional display based on plan

## 14. Frontend - Suggestions Section
- [ ] User's submitted suggestions list
- [ ] Status display (pending, approved, implemented)
- [ ] Submit new suggestion form
- [ ] Voting display

## 15. Frontend - Account Settings Section
- [ ] Profile information form
- [ ] Password change form
- [ ] Email preferences
- [ ] Notification settings
- [ ] Security settings (2FA placeholder)

## 16. Real-time Updates Integration
- [ ] WebSocket connection setup for live updates
- [ ] Auto-refresh mechanism for critical metrics
- [ ] Notification system for events
- [ ] Live usage counter updates

## 17. Chart.js Integration
- [ ] Add Chart.js library
- [ ] Create voice usage chart
- [ ] Create SMS usage chart
- [ ] Create email volume chart
- [ ] Create cost breakdown chart
- [ ] Make charts responsive for mobile

## 18. Stripe Checkout Integration
- [ ] Create Stripe Checkout session endpoint
- [ ] Implement upgrade flow with Stripe
- [ ] Add success/cancel redirect handling
- [ ] Test subscription upgrade flow
- [ ] Test subscription downgrade flow

## 19. Authentication & Authorization
- [ ] Add JWT authentication to all dashboard routes
- [ ] Implement user context middleware
- [ ] Add authorization checks for premium features
- [ ] Secure sensitive endpoints

## 20. Testing & Documentation
- [ ] Test all API endpoints
- [ ] Test dashboard UI on desktop
- [ ] Test dashboard UI on mobile
- [ ] Test upgrade/downgrade flows
- [ ] Create dashboard API documentation
- [ ] Add usage tracking documentation

## Notes
- Use existing xSwarm terminal aesthetic from index.html
- All charts should use Chart.js for consistency
- Mobile-first responsive design is critical
- WebSocket integration is optional for MVP
- Pro+ features should be conditionally displayed
- All monetary values in cents, display in dollars
