# Pooper Scooper - Quick Reference Card

## 🚀 Getting Started (5 Minutes)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Calibrate audio (one-time)
python main.py --calibrate-audio

# 3. Calibrate home position (optional, auto-runs on startup)
python main.py --calibrate-home

# 4. Configure your yard in config.yaml
patrol:
  area:
    width: 10  # meters
    height: 10  # meters

# 5. Run system (auto-calibrates home position)
python main.py

# 6. Open browser
http://localhost:5000

# 7. Click "Start Patrol"
```

---

## ⚙️ Motor Stall Tuning (2 Parameters)

### In `config.yaml`:
```yaml
audio:
  stall_frequency_threshold: 100  # Start here
  frequency_drop_percent: 50       # Start here
```

### If stalls NOT detected:
```yaml
stall_frequency_threshold: 80   # ↓ DECREASE
frequency_drop_percent: 40       # ↓ DECREASE
```

### If too many FALSE positives:
```yaml
stall_frequency_threshold: 120  # ↑ INCREASE
frequency_drop_percent: 60       # ↑ INCREASE
```

**Adjust by ±20 until reliable**

---

## 🔁 Stall Retry Sequence

When stall detected, system tries:
1. **BACK_UP** - Reverse 0.5m, try again
2. **ADJUST_ANGLE** - Turn 15°, approach from different angle
3. **REDUCE_DEPTH** - Shallower scoop (70% depth)
4. **SKIP** - Give up, continue patrol

All logged to database automatically!

---

## 📁 File Structure

```
pooperscooper/
├── config.yaml          ← Configure everything here
├── main.py              ← Run this
├── requirements.txt     ← Install dependencies
│
├── hardware/
│   ├── excavator.py     ← GPIO control
│   └── audio_monitor.py ← Stall detection
│
├── vision/
│   ├── camera.py        ← Arducam interface
│   ├── detector.py      ← Poop detection
│   └── marker_detection.py ← Red flag finder
│
├── control/
│   ├── patrol_planner.py    ← Area coverage
│   ├── behavior_tree.py     ← Main logic
│   └── state_machines.py    ← State tracking
│
├── learning/
│   ├── pickup_database.py   ← SQLite logging
│   ├── adaptive_optimizer.py ← Parameter learning
│   └── performance_tracker.py ← Metrics
│
├── navigation/
│   ├── map_manager.py   ← Occupancy grid
│   └── path_planner.py  ← A* pathfinding
│
├── web/
│   ├── app.py          ← Flask server
│   └── templates/      ← HTML dashboards
│
├── utils/
│   ├── position_tracker.py ← Odometry
│   └── logging_setup.py    ← Logging config
│
└── models/
    └── poop_detector.tflite ← Your trained model
```

---

## 🌐 Web Interface

### Dashboard (`http://localhost:5000`)
- **Start Patrol** - Begin autonomous operation
- **Stop** - Emergency stop
- **Return Home** - Manual home navigation
- **Live Stats** - Coverage %, pickups, success rate
- **Patrol Map** - Real-time visualization
- **Activity Log** - Event stream

### Analytics (`http://localhost:5000/analytics`)
- Overall performance metrics
- Learned parameters
- Failure modes analysis
- Hotspot locations

---

## 🗄️ Database Schema

### Tables Created Automatically:
- `pickup_attempts` - Every pickup logged
- `patrol_sessions` - Session summaries
- `learned_parameters` - Optimized timings
- `hotspot_locations` - Poop frequency map

**Location:** `data/pooperscooper.db` (SQLite)

---

## 📊 Key Config Parameters

### Patrol
```yaml
patrol:
  grid_cell_size: 0.5        # Coverage grid resolution
  pattern: "lawnmower"       # or "spiral", "grid"
  coverage_threshold: 95     # % to consider complete
  max_patrol_time: 1200      # Seconds (20 min)
```

### Learning
```yaml
learning:
  enabled: true
  min_attempts_before_learning: 10
  success_rate_threshold: 0.7
  parameter_adjustment_rate: 0.1
```

### Vision
```yaml
vision:
  confidence_threshold: 0.7  # Detection confidence
  multi_frame_verification: 3 # Frames to confirm
```

### Safety
```yaml
safety:
  watchdog_timeout: 5.0
  max_operation_time: 1800   # 30 min max
  stall_retry_attempts: 2
```

---

## 🔍 Logging & Debugging

### Log Levels
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### Log Location
```
logs/pooperscooper.log
```

### Key Log Messages
```
[INFO] Patrol started
[INFO] Poop detected at (2.5, 3.1)
[WARNING] STALL DETECTED: arm_motor at 75 Hz
[WARNING] Retry #1: back_up
[INFO] Pickup successful after retry
[INFO] Coverage: 85.3%
[INFO] Returning to home
```

---

## 🎯 Troubleshooting

| Problem | Solution |
|---------|----------|
| Stalls never detected | Decrease thresholds in config.yaml |
| Too many false positives | Increase thresholds in config.yaml |
| Poor pickup success | System will learn - check after 10+ attempts |
| Web interface won't load | Check: `netstat -an \| grep 5000` |
| No poop detection | Verify model file exists |
| Camera not found | Run: `libcamera-hello` |
| GPIO permission error | Add user to gpio group |

---

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `FINAL_SUMMARY.md` | Complete overview |
| `MOTOR_STALL_GUIDE.md` | Stall tuning (detailed) |
| `QUICKSTART.md` | Setup guide |
| `IMPLEMENTATION_STATUS.md` | Integration tasks |
| `CODE_CLEANUP_SUMMARY.md` | What was simplified |
| `QUICK_REFERENCE.md` | This file |

---

## 🧪 Testing Commands

```bash
# Test all systems
python scripts/test_system.py

# Test specific module
python -m vision.camera
python -m hardware.excavator --simulate
python -m learning.pickup_database

# Calibrate audio
python main.py --calibrate-audio

# Run in simulation mode
python main.py --simulate

# Run with specific config
python main.py --config my_config.yaml
```

---

## 🔑 Key Commands

### System Control
```bash
python main.py                    # Start system
python main.py --simulate         # Test without hardware
python main.py --calibrate-audio  # Audio calibration
Ctrl+C                            # Emergency stop
```

### Web Interface
```
http://localhost:5000/            # Dashboard
http://localhost:5000/analytics   # Analytics
```

### Database Queries
```python
from learning.pickup_database import PickupDatabase
db = PickupDatabase()
stats = db.get_statistics()
success_rate = db.get_success_rate(last_n=20)
hotspots = db.get_hotspots(min_count=3)
```

---

## 🎚️ Tuning Priorities

### 1. Motor Stall Detection (CRITICAL)
- Calibrate motors first
- Test with deliberate stalls
- Tune `stall_frequency_threshold` and `frequency_drop_percent`

### 2. Vision Confidence (IMPORTANT)
- Start at 0.7
- Adjust based on false positives
- System learns optimal value over time

### 3. Patrol Coverage (MEDIUM)
- Default 95% is good
- Can lower to 90% for faster patrols
- Can raise to 98% for thorough coverage

### 4. Learning Rate (LOW)
- Default 0.1 (10% adjustment) works well
- Don't change unless you understand ML

---

## 📈 Expected Timeline

### Setup: ~30 minutes
- Install dependencies: 5 min
- Configure yaml: 5 min
- Audio calibration: 10 min
- Test run: 10 min

### First Patrol: ~20 minutes
- Coverage depends on yard size
- Expect 60-70% pickup success initially

### After 10 Patrols: Optimized
- Success rate: 75-85%
- System knows optimal timings
- Hotspots identified
- Faster navigation

---

## 🎯 Success Metrics

### Good Performance:
- ✅ Coverage > 90%
- ✅ Success rate > 70%
- ✅ Stall detection working
- ✅ Returns home reliably
- ✅ Web interface responsive

### Needs Tuning:
- ⚠️ Coverage < 80%
- ⚠️ Success rate < 60%
- ⚠️ Frequent stalls not detected
- ⚠️ Gets lost, doesn't return home
- ⚠️ Web interface slow

---

## 💡 Pro Tips

1. **Start small:** Test in small area (5x5m) first
2. **Calibrate often:** Re-run audio calibration monthly
3. **Monitor learning:** Check analytics after each session
4. **Adjust gradually:** Change one parameter at a time
5. **Use simulation:** Test changes without hardware first
6. **Check logs:** Review `logs/pooperscooper.log` for issues
7. **Database is gold:** All learning data saved, never delete
8. **Web interface:** Keep browser open during patrol
9. **RC override:** Always have manual remote ready
10. **Be patient:** Learning takes 10+ patrols to optimize

---

## 🏁 Quick Start Checklist

- [ ] `pip install -r requirements.txt`
- [ ] Configure yard dimensions in `config.yaml`
- [ ] Run `python main.py --calibrate-audio`
- [ ] Place red flag at disposal location
- [ ] Place trained model in `models/poop_detector.tflite`
- [ ] Run `python main.py`
- [ ] Open `http://localhost:5000`
- [ ] Click "Start Patrol"
- [ ] Monitor in real-time
- [ ] Check analytics after completion

---

## 🎉 You're Ready!

Everything you need is in this reference card. For details, see the full documentation.

**Happy autonomous poop scooping!** 🚜💩🤖
