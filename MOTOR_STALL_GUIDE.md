# Motor Stall Detection & Retry Guide

## Overview

The system uses **audio frequency analysis (FFT)** to detect when excavator motors stall against resistance. When a stall is detected, the system automatically tries different pickup approaches.

---

## How Stall Detection Works

### Normal Operation
- Motor running: **200-800 Hz** dominant frequency
- Smooth sound with high-frequency whine

### Stalled Motor
- Frequency drops to: **< 100 Hz**
- Low grinding/struggling sound
- Increased amplitude at low frequencies

---

## Tuning Instructions

### Step 1: Initial Calibration

Run calibration to record baseline motor frequencies:

```bash
python main.py --calibrate-audio
```

**During calibration:**
1. System will prompt for each motor
2. Activate the motor (e.g., boom up)
3. Let it run for 5 seconds
4. System records the frequency profile
5. Repeat for all motors

**Saved to:** `models/audio_calibration.json`

### Step 2: Adjust Thresholds

Edit `config.yaml`:

```yaml
audio:
  stall_frequency_threshold: 100  # ← TUNE THIS
  frequency_drop_percent: 50      # ← TUNE THIS
```

#### `stall_frequency_threshold`
**What it does:** Absolute minimum Hz - any frequency below triggers stall

**Tuning Guide:**
- **Too Low (< 50 Hz):** Won't detect stalls, motors damaged
- **Too High (> 200 Hz):** False positives during normal operation
- **Recommended:** Start at 100 Hz

**Adjust if:**
- Stalls not detected → **DECREASE by 20** (try 80)
- Too many false positives → **INCREASE by 20** (try 120)

#### `frequency_drop_percent`
**What it does:** Percent drop from baseline to trigger stall

**Tuning Guide:**
- **Too Low (< 30%):** Too sensitive, false alarms
- **Too High (> 70%):** Only detects severe stalls
- **Recommended:** Start at 50%

**Adjust if:**
- Stalls not detected → **DECREASE by 10** (try 40%)
- False positives → **INCREASE by 10** (try 60%)

### Step 3: Testing

**Deliberate Stall Test:**
1. Start excavator
2. Push bucket against ground to cause stall
3. Watch logs for: `[WARNING] STALL DETECTED`

**If not detected:**
```yaml
# Try more sensitive settings:
stall_frequency_threshold: 80   # Decreased from 100
frequency_drop_percent: 40      # Decreased from 50
```

**If too many false positives:**
```yaml
# Try less sensitive settings:
stall_frequency_threshold: 120  # Increased from 100
frequency_drop_percent: 60      # Increased from 50
```

---

## Retry Strategies

When a stall is detected, the system tries these approaches **in order**:

### Retry #1: BACK_UP
**What it does:**
- Reverse excavator 0.5 meters
- Approach target again
- Try same pickup motion

**Use case:** Hit unexpected resistance (rock, stick)

### Retry #2: ADJUST_ANGLE
**What it does:**
- Turn 15° left or right
- Approach from different angle
- Try pickup

**Use case:** Poop on slope or uneven ground

### Retry #3: REDUCE_DEPTH
**What it does:**
- Reduce `arm_down` timing by 30%
- Shallower scoop motion
- Try pickup

**Use case:** Digging too deep into grass/soil

### Retry #4: SKIP
**What it does:**
- Give up on this target
- Mark as failed in database
- Continue patrol

**Use case:** Object too difficult (may not be poop)

---

## Implementation in Code

### In Behavior Tree (`control/behavior_tree.py`):

```python
def PickupWithRetry(target):
    """Pickup with automatic stall retry"""

    for attempt in range(4):
        # Execute pickup
        excavator.pickup_sequence()

        # Check for stall
        if audio_monitor.check_for_stall("arm_motor"):
            # Get retry strategy
            strategy = audio_monitor.handle_stall("arm_motor")

            if strategy == StallRetryStrategy.BACK_UP:
                excavator.move_backward(0.5)
                time.sleep(0.5)
                continue  # Retry

            elif strategy == StallRetryStrategy.ADJUST_ANGLE:
                excavator.turn_left(0.3)  # 15 degrees
                excavator.move_forward(0.3)
                continue  # Retry

            elif strategy == StallRetryStrategy.REDUCE_DEPTH:
                # Reduce timing by 30%
                excavator.set_timing('arm_down',
                    excavator.timing['arm_down'] * 0.7)
                continue  # Retry

            elif strategy == StallRetryStrategy.SKIP:
                logger.warning("Giving up on target after 3 retries")
                database.log_pickup_attempt(
                    success=False,
                    failure_reason="stall_max_retries"
                )
                return False

        else:
            # No stall - success!
            audio_monitor.reset_stall_flag()
            return True

    return False
```

---

## Monitoring Stalls

### In Logs
```
[WARNING] STALL DETECTED: arm_motor at 75.3 Hz (baseline: 450.2 Hz)
[WARNING] Stall on arm_motor - Retry #1: back_up
[INFO] Retry strategy: backing up 0.5m
[WARNING] STALL DETECTED: arm_motor at 68.1 Hz (baseline: 450.2 Hz)
[WARNING] Stall on arm_motor - Retry #2: adjust_angle
[INFO] Retry strategy: adjusting approach angle
[INFO] Pickup successful after 2 retries
```

### In Web Interface
- Activity log shows stall events
- Analytics page shows stall frequency
- Can see which retry strategies work best

---

## Advanced Tuning

### Per-Motor Thresholds

If different motors need different settings, modify `check_for_stall()`:

```python
# In audio_monitor.py
def check_for_stall(self, motor_name: str) -> bool:
    # Custom thresholds per motor
    thresholds = {
        'boom_motor': 120,
        'arm_motor': 100,
        'bucket_motor': 80,
    }

    threshold = thresholds.get(motor_name, self.stall_threshold)

    # Use custom threshold
    stall_condition_1 = current_freq < threshold
    # ... rest of logic
```

### Microphone Placement

**For best results:**
- Place microphone 10-20cm from excavator body
- Avoid wind noise (use foam windscreen)
- Point toward motors, away from tracks/wheels
- Test different positions, re-calibrate each time

---

## Troubleshooting

### Problem: Stalls never detected

**Solutions:**
1. Check microphone is connected: `arecord -l`
2. Verify audio levels: Record manually and check volume
3. Lower both thresholds by 20-30%
4. Re-run calibration in quieter environment
5. Check `models/audio_calibration.json` has values

### Problem: Constant false positives

**Solutions:**
1. Increase both thresholds by 20-30%
2. Move microphone away from motor vibrations
3. Re-calibrate with motor under normal load
4. Check for electrical interference

### Problem: Different stall behavior per motor

**Solution:**
Implement per-motor thresholds (see Advanced Tuning above)

---

## Quick Reference

| Setting | Default | Sensitive | Conservative |
|---------|---------|-----------|--------------|
| `stall_frequency_threshold` | 100 Hz | 80 Hz | 120 Hz |
| `frequency_drop_percent` | 50% | 40% | 60% |

**Rule of thumb:**
- Decrease = more sensitive (detects more, may false alarm)
- Increase = less sensitive (detects less, misses minor stalls)

Start with defaults, test with deliberate stalls, adjust by ±20 until reliable.

---

## Summary

1. ✅ Run calibration once: `python main.py --calibrate-audio`
2. ✅ Test with deliberate stall
3. ✅ Adjust thresholds in `config.yaml` if needed
4. ✅ System automatically retries with different approaches
5. ✅ Monitor logs/web interface for stall events
6. ✅ Fine-tune over time based on real-world performance

The system learns which retry strategies work best and logs everything to the database for analysis!
