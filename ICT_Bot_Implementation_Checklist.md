# ICT Bot - Implementation Checklist
**Based on Gap Analysis Report**  
**Date:** January 29, 2026

---

## Quick Status Overview

| Priority | Category | Items | Status |
|----------|----------|-------|--------|
| 🔴 CRITICAL | Config & Bug Fixes | 3 | ⏳ Pending |
| 🟠 HIGH | Core ICT Features | 2 | ⏳ Pending |
| 🟡 MEDIUM | Quality Improvements | 3 | ⏳ Pending |
| 🟢 LOW | Advanced Features | 5+ | ⏳ Pending |

---

## Phase 1: CRITICAL FIXES (1-2 hours)

### ✅ Task 1.1: Fix London Kill Zone Timing
**File:** `config.json`  
**Current:** Line 36-42 - `"start": [1, 0], "end": [5, 0]`  
**Fix:** Change to `"start": [3, 0], "end": [6, 0]`

```json
{
    "name": "London",
    "start": [3, 0],    // Change from [1, 0]
    "end": [6, 0],      // Change from [5, 0]
    "enabled": true
}
```

**Why:** ICT specifies London Kill Zone as 3AM-6AM EST, not 1AM-5AM

---

### ✅ Task 1.2: Add Missing Config Parameters
**File:** `config.json`  
**Add these fields:**

```json
{
    "trading": {
        "timeframe": "1h",
        "timeframe_smaller": "15m",
        "risk_percent_per_trade": 1.0,
        "take_profit_rr": 2.0,           // ← ADD THIS
        "sl_buffer_points": 50.0,        // ← ADD THIS
        "symbol": ""
    }
}
```

**Why:** 
- `take_profit_rr` - Used in `strategy.py` Line 283 but missing from config
- `sl_buffer_points` - Used in `strategy.py` Line 3 but missing from config

**Note:** These already exist in `config_loader.py` with defaults, but should be in JSON for user customization

---

### ✅ Task 1.3: Verify Config Loads Without Errors
**Test:**
```bash
cd ICT_Bot_App
python -c "from trading_core.config_loader import *; print('Config OK')"
```

**Expected:** Should print "Config OK" without errors

---

## Phase 2: CORE ICT ENHANCEMENTS (4-6 hours)

### 📋 Task 2.1: Implement OTE Fibonacci Levels
**Priority:** 🔴 **HIGH** - This is ICT's core entry technique

**File:** `trading_core/strategy.py`  
**Function:** `evaluate_signal()`

**What to Add:**
1. After price touches PD Array, calculate Fibonacci retracement from the structure
2. Wait for price to reach OTE levels: 0.62, 0.705, or 0.79
3. Only then proceed to LTF confirmation

**Pseudo-code:**
```python
def calculate_fibonacci_levels(swing_high, swing_low):
    """Calculate OTE Fibonacci levels"""
    range_val = swing_high - swing_low
    return {
        0.5: swing_low + (range_val * 0.5),
        0.62: swing_low + (range_val * 0.62),
        0.705: swing_low + (range_val * 0.705),
        0.79: swing_low + (range_val * 0.79),
    }

def is_at_ote_level(price, fib_levels, tolerance=0.0005):
    """Check if price is at an OTE level"""
    for level, price_level in fib_levels.items():
        if level in [0.62, 0.705, 0.79]:  # Primary OTE levels
            if abs(price - price_level) <= tolerance:
                return True, level
    return False, None
```

**Integration Point:** 
- In `evaluate_signal()`, after detecting PD Array touch (Line 100, 115, 130 for bullish)
- Before calling `check_ltf_confirmation()`
- Add OTE check as an additional filter

**Config Addition:**
```json
"ote": {
    "enabled": true,
    "primary_levels": [0.62, 0.705, 0.79],
    "tolerance_percent": 0.05
}
```

---

### 📋 Task 2.2: Add Partial Profit Taking
**Priority:** 🟠 **HIGH** - Improves real-world performance

**File:** `trading_core/connectors/base_connector.py` + `strategy.py`

**What to Add:**
1. Modify `place_order()` to support multiple TP levels
2. Create logic to close positions partially

**ICT Specification:**
- Close 50% at 1:1 R:R (breakeven)
- Close 25% at 1:2 R:R
- Let 25% run to 1:3+ R:R

**Implementation Steps:**

**Step 1:** Add config for partial profits
```json
"partial_profits": {
    "enabled": true,
    "levels": [
        {"rr": 1.0, "percent": 50},
        {"rr": 2.0, "percent": 25},
        {"rr": 3.0, "percent": 25}
    ]
}
```

**Step 2:** Create new function in `strategy.py`
```python
def calculate_partial_tp_levels(entry_price, sl_price, signal):
    """Calculate multiple TP levels for partial profits"""
    sl_distance = abs(entry_price - sl_price)
    tp_levels = []
    
    for level in PARTIAL_PROFIT_LEVELS:
        rr = level['rr']
        percent = level['percent']
        if signal == 'long':
            tp_price = entry_price + (sl_distance * rr)
        else:
            tp_price = entry_price - (sl_distance * rr)
        
        tp_levels.append({
            'price': tp_price,
            'percent': percent,
            'rr': rr
        })
    
    return tp_levels
```

**Step 3:** Modify order placement
- Instead of single TP, place order with multiple TP targets
- Requires MT5/Binance connector support for partial closes

**Note:** This may require significant connector changes. Consider implementing as separate orders if platform doesn't support partial closes.

---

### 📋 Task 2.3: Strengthen Order Block Detection
**Priority:** 🟡 **MEDIUM** - Quality filter

**File:** `trading_core/pd_arrays.py`  
**Function:** `detect_order_block()`

**Current:** Only checks BOS + FVG (2/4 confirmations)  
**ICT Requires:** 4 confirmations:
1. ✅ Imbalance (FVG) - Already implemented
2. ✅ BOS - Already implemented  
3. ❌ Liquidity Sweep - Detected but not required
4. ❌ Displacement - Not implemented

**Changes:**

**Option A (Strict ICT):** Require all 4 confirmations
```python
# Line 73-74: Change from
if bos_found and fvg_found:

# To:
if bos_found and fvg_found and sweep_found and displacement_found:
```

**Option B (Configurable):** Add config toggle
```json
"order_block": {
    "require_sweep": false,
    "require_displacement": false,
    "displacement_threshold": 2.0  // Minimum % move in 1-3 candles
}
```

**Recommendation:** Use Option B for flexibility during backtesting

**Displacement Detection (new function):**
```python
def detect_displacement(df, index, threshold=2.0, lookforward=3):
    """
    Detect rapid price movement (displacement)
    threshold: minimum % move in lookforward candles
    """
    candle = df.iloc[index]
    future_slice = df.iloc[index+1:index+1+lookforward]
    
    if future_slice.empty:
        return False
    
    max_high = future_slice['high'].max()
    min_low = future_slice['low'].min()
    
    bullish_move = ((max_high - candle['close']) / candle['close']) * 100
    bearish_move = ((candle['close'] - min_low) / candle['close']) * 100
    
    return max(bullish_move, bearish_move) >= threshold
```

---

## Phase 3: ADVANCED FEATURES (8-12 hours)

### 📋 Task 3.1: Implement EQH/EQL Liquidity Detection
**Priority:** 🟡 **MEDIUM**

**File:** `trading_core/market_structure.py` (new function)

**What to Add:**
Equal Highs (EQH) and Equal Lows (EQL) detection

```python
def detect_equal_highs_lows(df, tolerance=0.0005):
    """
    Detect Equal Highs (EQH) and Equal Lows (EQL)
    tolerance: % difference to consider "equal"
    """
    df['eqh'] = False
    df['eql'] = False
    
    swing_highs = df[df['swing_high'].notna()]
    swing_lows = df[df['swing_low'].notna()]
    
    # Check for Equal Highs
    for i in range(1, len(swing_highs)):
        current = swing_highs.iloc[i]
        previous = swing_highs.iloc[i-1]
        
        diff_percent = abs(current['swing_high'] - previous['swing_high']) / previous['swing_high']
        if diff_percent <= tolerance:
            df.loc[current.name, 'eqh'] = True
    
    # Check for Equal Lows
    for i in range(1, len(swing_lows)):
        current = swing_lows.iloc[i]
        previous = swing_lows.iloc[i-1]
        
        diff_percent = abs(current['swing_low'] - previous['swing_low']) / previous['swing_low']
        if diff_percent <= tolerance:
            df.loc[current.name, 'eql'] = True
    
    return df
```

**Integration:** Add as filter in `evaluate_signal()` - prefer setups near EQH/EQL

---

### 📋 Task 3.2: Silver Bullet Strategy
**Priority:** 🟡 **MEDIUM**

**File:** `trading_core/strategy.py` (new function)

**ICT Specification:**
- 3 daily 1-hour windows
- Special setup detection logic
- Higher probability than regular Kill Zones

**Implementation:**
```python
SILVER_BULLET_WINDOWS = [
    {'name': 'Asian SB', 'start': (20, 0), 'end': (21, 0)},
    {'name': 'London SB', 'start': (3, 0), 'end': (4, 0)},
    {'name': 'NY SB', 'start': (9, 0), 'end': (10, 0)},
]

def is_silver_bullet_time(timestamp):
    """Check if current time is within Silver Bullet window"""
    # Similar to is_kill_zone_time() but with SB windows
    pass

def detect_silver_bullet_setup(df, timestamp):
    """
    Silver Bullet Setup Logic:
    1. Mark opening gap (first candle of SB window)
    2. Wait for sweep above/below gap
    3. Enter on reversal back into gap
    """
    pass
```

**Config:**
```json
"silver_bullet": {
    "enabled": false,
    "windows": [...]
}
```

---

### 📋 Task 3.3: ICT 2022 Trading Model
**Priority:** 🟢 **LOW** - Complex, requires significant refactoring

**Concept:**
Session-based workflow that analyzes:
1. NY Midnight Open (00:00 EST)
2. Asian Session Range (00:00-08:00)
3. London Open Sweep (02:00-05:00)
4. NY Reversal (NY Kill Zone)

**Implementation:** Too complex for initial release, add later

---

## Phase 4: POLISH & OPTIMIZATION (Ongoing)

### 📋 Task 4.1: Add DST Handling for Kill Zones
**Why:** ICT times are NY local time, need to handle DST transitions

**File:** `trading_core/time_filter.py`

**Enhancement:**
```python
import pytz
from datetime import datetime

def is_dst(timestamp, tz='America/New_York'):
    """Check if timestamp is in Daylight Saving Time"""
    ny_tz = pytz.timezone(tz)
    return bool(timestamp.astimezone(ny_tz).dst())
```

---

### 📋 Task 4.2: Backtest Parameter Optimization
**Goal:** Find optimal values for:
- `swing_length` (current: 10)
- `TAKE_PROFIT_RR` (current: 2.0)
- `SL_BUFFER_POINTS` (current: 50.0)
- OTE tolerance levels

**Method:** Grid search with backtest engine

---

### 📋 Task 4.3: Add Logging Enhancement
**File:** `config_loader.py` Line 34

**Current:** `ENABLE_LOGGING = False` (hardcoded)

**Fix:** Read from config
```python
ENABLE_LOGGING = config_manager.get('logging.enable_logging', False)
```

---

## Testing Checklist

After each phase, run these tests:

### ✅ Unit Tests
- [ ] Config loads without errors
- [ ] All functions return expected types
- [ ] Edge cases handled (empty DataFrames, None values)

### ✅ Integration Tests
- [ ] Backtest completes without crashes
- [ ] Live trading connects successfully
- [ ] Orders placed correctly

### ✅ Validation Tests
- [ ] Compare backtest results before/after changes
- [ ] Verify signal quality improved
- [ ] Check win rate and R:R metrics

---

## Quick Start Guide

**To begin implementation:**

1. **Backup current code:**
   ```bash
   cd C:\Users\ASUS\Documents\research
   git add .
   git commit -m "Pre-Phase 1 backup"
   ```

2. **Start with Phase 1 (Critical Fixes):**
   - Fix London Kill Zone timing
   - Add missing config params
   - Test config loads

3. **Validate Phase 1:**
   ```bash
   python run_backtest_cli.py  # Should run without errors
   ```

4. **Move to Phase 2 only after Phase 1 validated**

---

## Resources

- **Gap Analysis Report:** `ICT_Bot_Gap_Analysis.md`
- **ICT Research:** Previous conversation history (contains full ICT specification)
- **Current Code:** `ICT_Bot_App/trading_core/`
- **Config:** `ICT_Bot_App/config.json`

---

**Last Updated:** January 29, 2026  
**Status:** Ready for Implementation
