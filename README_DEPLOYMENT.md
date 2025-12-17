# Burnout Competition Scoring System - Deployment Guide

## Overview
A comprehensive web application for managing and scoring burnout competitions with judge authentication, competitor management, real-time scoring, and leaderboard functionality.

## Features
- **Admin Dashboard**: Manage judges, competition classes, competitors, and rounds
- **Judge Scoring Interface**: Touch-friendly scoring with automatic calculations
- **Leaderboard**: Class-filtered rankings with judge score averaging
- **Bulk Import**: CSV import for competitors
- **Export**: Download scores as CSV for external hosting
- **Authentication**: Secure JWT-based login for admins and judges

## Default Credentials
- **Admin**: username: `admin`, password: `admin123`

## Tech Stack
- **Backend**: FastAPI (Python) with MongoDB
- **Frontend**: React with Tailwind CSS
- **Authentication**: JWT tokens with bcrypt password hashing

## Database Structure

### Collections:
1. **users** - Judges and admins
2. **classes** - Competition classes (e.g., Pro, Amateur, Street)
3. **competitors** - Competitor details with car info
4. **rounds** - Competition rounds with dates
5. **scores** - Judge scores with automatic calculations

## Scoring System

### Score Categories:
- Instant Smoke: 0-10 points
- Constant Smoke: 0-20 points
- Volume of Smoke: 0-20 points
- Driving Skill: 0-40 points
- Tyres Popped: 5 points each

### Penalties:
- Reversing: -5 points
- Stopping: -5 points
- Contact with Barrier: -5 points
- Small Fire: -5 points
- Failed to Drive Off Pad: -10 points
- Large Fire: -10 points

**Final Score = Score Subtotal - Penalty Total**

## Exporting Data for External Hosting

### Option 1: MongoDB Export
```bash
# Export all data
mongodump --uri="mongodb://localhost:27017/test_database" --out=/app/backup

# To restore on your hosting:
mongorestore --uri="your-mongodb-connection-string" /app/backup/test_database
```

### Option 2: CSV Export per Round
1. Login as admin
2. Navigate to "Rounds" tab
3. Click "Export" button for any round
4. CSV file will download with all scores

### Option 3: Manual Database Migration
Export collections individually:
```bash
mongoexport --uri="mongodb://localhost:27017/test_database" --collection=users --out=users.json
mongoexport --uri="mongodb://localhost:27017/test_database" --collection=classes --out=classes.json
mongoexport --uri="mongodb://localhost:27017/test_database" --collection=competitors --out=competitors.json
mongoexport --uri="mongodb://localhost:27017/test_database" --collection=rounds --out=rounds.json
mongoexport --uri="mongodb://localhost:27017/test_database" --collection=scores --out=scores.json
```

## Hosting on Your Own Webspace

### Requirements:
- MongoDB database (MongoDB Atlas recommended for cloud hosting)
- Node.js hosting (for frontend) or static hosting
- Python hosting (for backend API)

### Steps:

#### 1. Set Up MongoDB
- Create a MongoDB Atlas account (free tier available)
- Create a new cluster
- Get your connection string

#### 2. Configure Backend
Update `/app/backend/.env`:
```
MONGO_URL=your-mongodb-atlas-connection-string
DB_NAME=burnout_competition
JWT_SECRET=your-secure-random-secret-key
CORS_ORIGINS=your-frontend-domain.com
```

#### 3. Deploy Backend
Deploy to platforms like:
- **Heroku**: `git push heroku main`
- **Railway**: Connect GitHub repo
- **DigitalOcean App Platform**: Deploy from Git
- **AWS Elastic Beanstalk**: Upload application

#### 4. Build Frontend
```bash
cd /app/frontend
yarn build
```

Update `/app/frontend/.env` with your backend URL:
```
REACT_APP_BACKEND_URL=https://your-backend-domain.com
```

#### 5. Deploy Frontend
Deploy the `build` folder to:
- **Netlify**: Drag & drop build folder
- **Vercel**: Import from Git
- **GitHub Pages**: Push build folder
- **Your cPanel**: Upload to public_html

### Environment Variables for Production

**Backend (.env)**:
```
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=burnout_competition
JWT_SECRET=change-this-to-secure-random-string
CORS_ORIGINS=https://your-frontend-domain.com
```

**Frontend (.env)**:
```
REACT_APP_BACKEND_URL=https://your-backend-domain.com
```

## CSV Bulk Import Format

To bulk import competitors, use this CSV format:
```csv
name,car_number,vehicle_info,class_id
John Doe,42,Ford Mustang,class-id-here
Jane Smith,88,Chevy Camaro,class-id-here
Mike Johnson,13,Dodge Challenger,class-id-here
```

**Important**: Get the `class_id` from the Classes tab first before importing competitors.

## User Workflows

### Admin Workflow:
1. Login with admin credentials
2. Create competition classes (Pro, Amateur, etc.)
3. Add competitors (manually or bulk CSV import)
4. Create judges with login credentials
5. Create rounds for the competition
6. View leaderboard and export scores

### Judge Workflow:
1. Login with provided credentials
2. Select active round
3. Select competitor to score
4. Enter scores using touch-friendly steppers
5. Mark any penalties
6. Submit score (auto-calculated)
7. Review previous submissions via "My Scores"
8. View leaderboard

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Create judge (admin only)

### Admin - Judges
- `GET /api/admin/judges` - List judges
- `DELETE /api/admin/judges/{id}` - Delete judge

### Admin - Classes
- `GET /api/admin/classes` - List classes
- `POST /api/admin/classes` - Create class
- `PUT /api/admin/classes/{id}` - Update class
- `DELETE /api/admin/classes/{id}` - Delete class

### Admin - Competitors
- `GET /api/admin/competitors` - List competitors
- `POST /api/admin/competitors` - Create competitor
- `POST /api/admin/competitors/bulk` - Bulk import CSV
- `PUT /api/admin/competitors/{id}` - Update competitor
- `DELETE /api/admin/competitors/{id}` - Delete competitor

### Admin - Rounds
- `GET /api/admin/rounds` - List rounds
- `POST /api/admin/rounds` - Create round
- `PUT /api/admin/rounds/{id}` - Update round
- `DELETE /api/admin/rounds/{id}` - Delete round

### Judge - Scoring
- `GET /api/judge/competitors/{round_id}` - Get competitors for round
- `POST /api/judge/scores` - Submit score
- `GET /api/judge/scores` - Get judge's scores

### Leaderboard
- `GET /api/leaderboard/{round_id}?class_id={class_id}` - Get leaderboard
- `GET /api/export/scores/{round_id}` - Export CSV (admin only)

## Security Notes
- Change default admin password immediately
- Use strong JWT_SECRET in production
- Enable HTTPS for production deployment
- Regularly backup your MongoDB database
- Keep dependencies updated

## Support
For issues or questions about deployment, refer to:
- FastAPI Documentation: https://fastapi.tiangolo.com
- React Documentation: https://react.dev
- MongoDB Atlas: https://www.mongodb.com/cloud/atlas

## Design
The application features a high-octane dark theme inspired by pit boards and digital timing displays, with:
- Asphalt black background (#09090b)
- Fire orange primary color (#f97316)
- Touch-friendly scoring interface for judges
- Glass-morphism effects and neon glows
- Custom fonts: Unbounded (headings), Rajdhani (UI), JetBrains Mono (data)
