# Burnout Competition Scoring Application - PRD

## Original Problem Statement
Build a full-stack web application to score a burnout competition with:
- Judge scoring interface with multiple scoring categories
- Admin management for events, rounds, classes, competitors, and judges
- Leaderboard and reporting functionality with printable reports
- Email integration for sending reports to competitors (future)

## Core Requirements

### Authentication & Authorization
- **Admin role**: Full access to manage all data, upload logo, configure settings
- **Judge role**: Score competitors, view leaderboard
- Credentials: Admin (admin/admin123)

### Scoring Categories (0.5 increments except Tyres)
1. Tip In: 0-10 points
2. Instant Smoke: 0-10 points
3. Constant Smoke: 0-20 points
4. Volume of Smoke: 0-20 points
5. Driving Skill: 0-40 points
6. Tyres Popped: 0-2 (integer increments)

### Penalties
- **Cumulative (-5 each)**: Reversing, Stopping, Contact with Barrier, Small Fire
- **One-time (-10)**: Failed to Drive Off Pad, Large Fire

### Data Management
- Events: Name, date, active status
- Rounds: Name, status, is_minor checkbox (for cumulative scoring)
- Classes: Competition categories
- Competitors: Car number, name, vehicle info, plate, class
- Bulk CSV import (by class name)

### Leaderboard & Reporting
- View by single round or cumulative minor rounds
- Toggle between Average and Total score display
- Filter by class
- Print Report with:
  - Organization logo (uploaded via settings)
  - Event name and date
  - Class and round info
  - Ranked competitor list with scores
  - Footer with timestamp and website

---

## What's Been Implemented (January 2026)

### Phase 1: Core Features (Complete)
- [x] User authentication (JWT-based)
- [x] Admin dashboard with tabs: Judges, Classes, Competitors, Events, Rounds, Scores
- [x] Judge scoring page with all categories
- [x] Score submission and editing
- [x] Leaderboard with rankings

### Phase 2: Scoring Enhancements (Complete)
- [x] 0.5-point increments for scoring categories
- [x] Integer-only Tyres Popped
- [x] "Tip In" category added
- [x] One-time toggle for Failed Drive Off and Large Fire penalties
- [x] Judges can edit their submitted scores

### Phase 3: Admin Features (Complete)
- [x] Admin can edit/delete competitors
- [x] Admin can delete individual scores from Scores tab
- [x] Data reset options (scores only, competition data, full reset)
- [x] CSV import with class name support
- [x] CSV export with Tip In score included

### Phase 4: Events & Rounds Restructure (Complete)
- [x] Events entity with name, date, active status
- [x] Rounds simplified: name, status, is_minor checkbox
- [x] Minor rounds cumulative leaderboard

### Phase 5: Leaderboard & Reports (Complete - Current)
- [x] Leaderboard Type toggle (Single Round / Minor Rounds Cumulative)
- [x] Score Display toggle (Average / Total)
- [x] Class filter on leaderboard
- [x] Print Report button
- [x] **Logo upload in Admin Settings**
- [x] **Website & Organization settings**
- [x] **Professional print layout matching PDF examples**
- [x] Footer with timestamp and website URL
- [x] **Settings persistence (Score Display, Show Scores) via localStorage**
- [x] **Logo properly displays in print preview (waits for image load)**

### Phase 6: Judge Management & Scoring Validation (Complete - Current)
- [x] **Active/Inactive toggle for judges** - Flexible judge count per event (2-4 judges)
- [x] **Active judge count display** - Shown in header and Judges panel
- [x] **Scoring error detection** - Missing scores and duplicate scores
- [x] **Error alerts on Admin Dashboard** - Red alert with details when issues exist
- [x] **Success indicator** - Green banner when no scoring issues
- [x] **Refresh Errors button** - Re-check scoring issues on demand

### Phase 7: Disqualification & Admin Score Editing (Complete)
- [x] **Disqualified penalty** - When toggled, final score becomes 0
- [x] **Disqualified UI** - Prominent toggle button on Judge Scoring page with "YES - Score will be 0"
- [x] **Final score display** - Shows "0 (DQ)" when disqualified
- [x] **Admin Edit Score** - Edit button in Scores tab opens dialog with all scoring fields
- [x] **Admin Edit recalculates** - Updates score_subtotal, penalty_total, final_score including DQ logic
- [x] **Email tracking field** - `email_sent` boolean on scores (defaults to false)
- [x] **Pending emails count** - Orange indicator on dashboard showing competitors needing email

### Phase 8: Email Function & Report Formatting (Complete)
- [x] **SMTP Configuration** - Settings dialog has Email Settings section with server, port, email, password, TLS
- [x] **Test Connection button** - Validates SMTP credentials with better error messages
- [x] **Improved SMTP handling** - Proper timeout (30s), SSL vs STARTTLS auto-detection based on port
- [x] **Score status display** - "Not emailed" / "✓ Emailed" status column in Scores tab
- [x] **Email button per score** - Blue button opens Send Score Report dialog
- [x] **Send email dialog** - Shows competitor info and email input
- [x] **Comprehensive email report** - HTML email with all scoring categories, penalties, round-by-round breakdown
- [x] **Auto-mark as emailed** - Scores automatically marked as `email_sent: true` after successful send
- [x] **Bulk Email feature** - "Bulk Email" button to send to multiple competitors at once
- [x] **Bulk Email dialog** - List of pending competitors with email inputs, select/deselect, batch send
- [x] **Date format fix** - DD/MM/YYYY format (Australian) in print reports
- [x] **Print report layout** - Event name on line 1, date on line 2 (separate lines)
- [x] **Competitor email field** - Added email field to competitor model for storing emails

### Phase 9: Bulk Email Round Scoping Fix (Complete - January 26, 2026)
- [x] **Round-scoped bulk emails** - Each email now sent for a specific round, not all rounds
- [x] **Pending emails includes round_id** - Backend returns round_id for each pending email entry
- [x] **Frontend sends round_id** - Bulk email dialog now includes round_id in the payload
- [x] **Only specific round marked as sent** - Fixed bug where all rounds were marked as emailed
- [x] **Partial scoring exclusion** - Competitor/round combos only appear in pending emails when ALL active judges have scored
- [x] **Comprehensive email reports** - Bulk email includes ALL completed rounds (previously emailed + newly completed) in one email
- [x] **Cumulative progress tracking** - Only the newly completed round is marked as "emailed", allowing future rounds to trigger new comprehensive emails

---

## Prioritized Backlog

### P1: Email Integration (Future)
- [ ] SMTP configuration in Admin Settings
- [ ] Individual competitor report generation
- [ ] Send report to competitor's email

### P2: Code Refactoring
- [ ] Break down AdminDashboard.js (monolithic)
- [ ] Break down JudgeScoring.js (monolithic)
- [ ] Break down server.py into modules (routes, models, services)

### P3: Enhancements
- [ ] Multi-event support (switch between events)
- [ ] Historical data/archives
- [ ] Judge assignment to specific classes

---

## Technical Stack
- **Frontend**: React, Tailwind CSS, shadcn/ui
- **Backend**: Python, FastAPI, Motor (async MongoDB)
- **Database**: MongoDB
- **Auth**: JWT tokens

## Key Files
- `/app/backend/server.py` - Main backend API
- `/app/frontend/src/pages/AdminDashboard.js` - Admin control panel
- `/app/frontend/src/pages/JudgeScoring.js` - Judge scoring interface
- `/app/frontend/src/pages/Leaderboard.js` - Leaderboard with print
- `/app/frontend/src/pages/Login.js` - Authentication

## API Endpoints (Key)
- `POST /api/auth/login` - Login
- `GET/POST /api/admin/settings/logo` - Logo management
- `GET/PUT /api/admin/settings/website` - Website settings
- `GET /api/leaderboard/{round_id}` - Round leaderboard
- `GET /api/leaderboard/minor-rounds/cumulative` - Minor rounds cumulative
