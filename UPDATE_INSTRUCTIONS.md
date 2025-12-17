# Update Instructions for Rock 3A

## Changes Made:
1. ✅ Tyres popped limited to max 2
2. ✅ Penalties are now cumulative counters (not toggles)
3. ✅ Added "plate" field to competitors
4. ✅ Competitor display shows plate and vehicle info separately
5. ✅ Added sliders to all score inputs
6. ✅ Dropdown shows competitor number and name

## To Deploy These Changes:

### Step 1: Transfer Updated Files to Rock 3A

Copy these updated files to your Rock 3A:
- `/app/backend/server.py`
- `/app/frontend/src/pages/AdminDashboard.js`
- `/app/frontend/src/pages/JudgeScoring.js`

```bash
# From your computer (if using SCP):
scp /path/to/backend/server.py burnouts@rock-ip:/home/burnouts/burnout-scoring/backend/
scp /path/to/frontend/src/pages/AdminDashboard.js burnouts@rock-ip:/home/burnouts/burnout-scoring/frontend/src/pages/
scp /path/to/frontend/src/pages/JudgeScoring.js burnouts@rock-ip:/home/burnouts/burnout-scoring/frontend/src/pages/
```

### Step 2: On Your Rock 3A - Rebuild Frontend

```bash
# SSH into Rock 3A
ssh burnouts@rock-ip

# Navigate to frontend
cd /home/burnouts/burnout-scoring/frontend

# Rebuild
export NODE_OPTIONS="--max-old-space-size=1536"
yarn build

# Should complete successfully
```

### Step 3: Restart Backend Service

```bash
# Restart backend to pick up model changes
sudo systemctl restart burnout-backend

# Check status
sudo systemctl status burnout-backend
```

### Step 4: Reload Nginx

```bash
# Reload nginx to serve new frontend
sudo systemctl reload nginx
```

### Step 5: Verify Changes

```bash
# Check all services are running
echo "=== Services Status ==="
docker ps | grep mongodb
sudo systemctl status burnout-backend --no-pager
sudo systemctl status nginx --no-pager

echo ""
echo "Access at: http://$(hostname -I | awk '{print $1}')"
```

## Testing the New Features:

1. **Admin Dashboard:**
   - Create a new competitor - you'll see the "Plate" field
   - The competitor list will show the plate in green

2. **Judge Scoring:**
   - Select a competitor - vehicle and plate show in separate boxes
   - Use sliders OR +/- buttons for scoring
   - Tyres popped max is now 2
   - Penalties have counters - click + multiple times for cumulative penalties
   - Example: Reversing 4 times = click + button 4 times = -20 points

3. **CSV Import Format:**
   - Old: `name,car_number,vehicle_info,class_id`
   - New: `name,car_number,vehicle_info,plate,class_id`

## If Existing Competitors Don't Have Plates:

You'll need to either:
1. Delete and recreate them with plates
2. Or manually update MongoDB:

```bash
# Access MongoDB container
docker exec -it mongodb mongosh

# Switch to database
use burnout_competition

# Add plate field to existing competitors
db.competitors.updateMany(
  { plate: { $exists: false } },
  { $set: { plate: "TBA" } }
)

# Exit
exit
```

## Rollback if Needed:

If something goes wrong, you can rollback:

```bash
# Restore from Git (if you committed before changes)
cd /home/burnouts/burnout-scoring
git checkout backend/server.py
git checkout frontend/src/pages/AdminDashboard.js
git checkout frontend/src/pages/JudgeScoring.js

# Rebuild
cd frontend
yarn build
sudo systemctl restart burnout-backend
sudo systemctl reload nginx
```
