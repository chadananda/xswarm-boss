# Suggestion Collection System Implementation

## Phase 1: Database Schema
- [ ] Create suggestions.sql migration with suggestions and suggestion_votes tables
- [ ] Add indexes for performance optimization
- [ ] Create views for analytics and reporting
- [ ] Add triggers for auto-updating timestamps

## Phase 2: Email Templates
- [ ] Add suggestion submission confirmation template
- [ ] Add admin notification template for new suggestions
- [ ] Add status update notification template
- [ ] Add weekly digest template

## Phase 3: Core API Implementation
- [ ] Create suggestions route handlers
- [ ] Implement POST /suggestions endpoint (public submission)
- [ ] Implement GET /suggestions endpoint (list with filtering/sorting)
- [ ] Implement GET /suggestions/:id endpoint (detail view)
- [ ] Implement POST /suggestions/:id/vote endpoint (upvote)
- [ ] Implement DELETE /suggestions/:id/vote endpoint (remove vote)

## Phase 4: Admin API
- [ ] Implement PUT /suggestions/:id endpoint (admin update)
- [ ] Implement DELETE /suggestions/:id endpoint (admin delete)
- [ ] Implement GET /suggestions/stats endpoint (analytics)
- [ ] Create suggestions-admin.js library functions

## Phase 5: Public Portal
- [ ] Create suggestions.html page with xSwarm aesthetic
- [ ] Implement submission form with validation
- [ ] Build suggestion display with voting UI
- [ ] Add category filtering and search
- [ ] Implement responsive design

## Phase 6: Integration
- [ ] Wire up email notifications on submission
- [ ] Create weekly digest email cron job
- [ ] Add suggestions link to navigation
- [ ] Test end-to-end flow

## Phase 7: Testing
- [ ] Test submission flow (authenticated and anonymous)
- [ ] Test voting system
- [ ] Test admin functions
- [ ] Test email notifications
- [ ] Test spam protection
