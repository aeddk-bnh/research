from datetime import datetime
import pandas as pd
from trading_core.connectors import get_connector
from trading_core.strategy import evaluate_signal, calculate_position_size
from trading_core.market_structure import detect_bos_choch, find_swings
from trading_core.pd_arrays import detect_fvg, detect_order_block, detect_breaker_block
from trading_core.config_loader import TIMEFRAME, TIMEFRAME_SMALLER, TAKE_PROFIT_RR

class Backtester:
    def __init__(self, params: dict, signals=None):
        self.params = params
        self.signals = signals
        self.symbol = params.get('symbol', 'BTCUSDm')
        self.timeframe = params.get('timeframe', TIMEFRAME)
        self.start_date = params.get('start_date')
        self.end_date = params.get('end_date')
        
        # Initial Balance Simulation
        self.balance = 10000.0 
        self.initial_balance = self.balance
        self.trades = []
        
        # Connector for fetching data
        self.connector = get_connector('mt5') # Defaulting to MT5 for historical data
        if self.connector:
             self.connector.connect()

    def run(self):
        if not self.connector:
            if self.signals: self.signals.log_message.emit("Không thể kết nối để lấy dữ liệu lịch sử.")
            return

        # 1. Fetch Historical Data
        if self.signals: self.signals.log_message.emit(f"Đang tải dữ liệu lịch sử cho {self.symbol}...")
        
        # Calculate limit based on date range (approximate)
        # This is a simplification. Ideally, fetch by date range. 
        # Since our connectors fetch by count, we'll fetch a large enough buffer.
        # TODO: Enhance connector to fetch by date range if possible, or fetch huge chunk and filter.
        
        # For now, let's assume we fetch a large chunk.
        df_main = self.connector.fetch_ohlcv(self.timeframe, limit=5000) # Fetch ample data
        df_small = self.connector.fetch_ohlcv(TIMEFRAME_SMALLER, limit=10000) # Higher res for confirmation

        if df_main is None or df_small is None:
             if self.signals: self.signals.log_message.emit("Không tải được dữ liệu.")
             return

        # Filter by date range
        # Ensure index is datetime
        df_main.index = pd.to_datetime(df_main.index)
        df_small.index = pd.to_datetime(df_small.index)

        # Naive date filtering
        start_ts = pd.Timestamp(self.start_date)
        end_ts = pd.Timestamp(self.end_date)
        
        df_main = df_main[(df_main.index >= start_ts) & (df_main.index <= end_ts)]
        # For small timeframe, we need it to cover the same range plus lookback
        # But for simplicity in this V1, let's just align the main loop and look up small timeframe as needed.
        
        total_candles = len(df_main)
        if total_candles < 200:
             if self.signals: self.signals.log_message.emit("Dữ liệu không đủ để chạy backtest (cần ít nhất 200 nến).")
             return

        if self.signals: self.signals.log_message.emit(f"Bắt đầu mô phỏng trên {total_candles} cây nến...")

        # 2. Simulation Loop
        # We need a window of at least 200 candles to start analysis
        window_size = 200
        
        open_positions = [] # List of active trades

        for i in range(window_size, total_candles):
            # Update Progress
            if self.signals and i % 10 == 0:
                progress = int((i / total_candles) * 100)
                self.signals.progress.emit(progress)

            # Current Slice (Look-back window)
            current_idx = df_main.index[i]
            
            # Slice main DF up to current index
            df_main_slice = df_main.iloc[i-window_size:i+1].copy()
            
            # Slice small DF up to current index (approximate alignment)
            # Find the closest timestamp in small DF that is <= current_idx
            # This is slow, but correct for simulation.
            df_small_slice = df_small[df_small.index <= current_idx].tail(100).copy()

            if len(df_small_slice) < 50: continue

            # --- Check Exit Conditions for Open Positions ---
            # We check if the current candle's High/Low hit SL or TP
            current_candle = df_main.iloc[i]
            current_high = current_candle['high']
            current_low = current_candle['low']
            
            positions_to_remove = []
            for pos in open_positions:
                pnl = 0
                close_reason = ""
                exit_price = 0
                
                if pos['side'] == 'LONG':
                    if current_low <= pos['sl']:
                        exit_price = pos['sl']
                        pnl = (exit_price - pos['entry_price']) * pos['quantity'] # Simplified PnL
                        close_reason = "SL"
                    elif current_high >= pos['tp']:
                        exit_price = pos['tp']
                        pnl = (exit_price - pos['entry_price']) * pos['quantity']
                        close_reason = "TP"
                elif pos['side'] == 'SHORT':
                    if current_high >= pos['sl']:
                        exit_price = pos['sl']
                        pnl = (pos['entry_price'] - exit_price) * pos['quantity']
                        close_reason = "SL"
                    elif current_low <= pos['tp']:
                        exit_price = pos['tp']
                        pnl = (pos['entry_price'] - exit_price) * pos['quantity']
                        close_reason = "TP"
                
                if close_reason:
                    self.balance += pnl
                    trade_record = {
                        'entry_time': str(pos['entry_time']),
                        'side': pos['side'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'sl': pos['sl'],
                        'tp': pos['tp'],
                        'pnl': pnl,
                        'close_reason': close_reason
                    }
                    self.trades.append(trade_record)
                    if self.signals: self.signals.trade_closed.emit(trade_record)
                    positions_to_remove.append(pos)
            
            for pos in positions_to_remove:
                open_positions.remove(pos)

            # --- Check Entry Conditions ---
            # Run Analysis Pipeline
            # Note: This is computationally expensive to do every candle. 
            # Optimization: Only re-calculate indicators if necessary, but for correctness we re-run.
            
            try:
                # 1. PD Arrays on Main
                df_with_fvg = detect_fvg(df_main_slice.copy())
                df_with_swings = find_swings(df_with_fvg)
                df_with_bos = detect_bos_choch(df_with_swings)
                df_with_ob = detect_order_block(df_with_bos)
                df_main_analyzed = detect_breaker_block(df_with_ob)
                
                # 2. PD Arrays on Small (for CHOCH confirmation)
                df_small_swings = find_swings(df_small_slice.copy())
                df_small_analyzed = detect_bos_choch(df_small_swings)

                # 3. Evaluate Signal
                signal, entry_price, sl_price = evaluate_signal(df_main_analyzed, df_small_analyzed, signals=self.signals)

                if signal != 'none' and entry_price is not None and sl_price is not None:
                     # Calculate TP
                     rr = float(TAKE_PROFIT_RR)
                     sl_distance = abs(entry_price - sl_price)
                     
                     if signal == 'long':
                         tp_price = entry_price + (sl_distance * rr)
                     else:
                         tp_price = entry_price - (sl_distance * rr)
                     
                     # Calculate Size (Simplified for Backtest: fixed risk %)
                     # We can reuse calculate_position_size but need a dummy connector wrapper or just do math here
                     # Let's do simple math for backtest speed
                     risk_percent = 0.01
                     risk_amount = self.balance * risk_percent
                     
                     # Simple quantity calculation (ignoring tick value/contract size for generic backtest)
                     # Assuming 1.0 lot size = 1 unit for crypto or standard logic
                     # PnL = (PriceDiff) * Quantity
                     # Risk = |Entry - SL| * Quantity
                     # Quantity = Risk / |Entry - SL|
                     
                     if sl_distance > 0:
                        quantity = risk_amount / sl_distance
                     else:
                        quantity = 0

                     if quantity > 0:
                         new_pos = {
                             'entry_time': current_idx,
                             'side': signal.upper(),
                             'entry_price': entry_price,
                             'sl': sl_price,
                             'tp': tp_price,
                             'quantity': quantity
                         }
                         open_positions.append(new_pos)
            
            except Exception as e:
                if self.signals:
                    self.signals.log_message.emit(f"[BACKTESTER_ERROR] at candle {current_idx}: {e}")
                    import traceback
                    self.signals.log_message.emit(f"Traceback: {traceback.format_exc()}")
                pass

        # 3. Calculate Final Stats
        total_pnl = self.balance - self.initial_balance
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]
        
        win_rate = (len(wins) / len(self.trades) * 100) if self.trades else 0
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        
        # Max Drawdown (simplified)
        running_balance = [self.initial_balance]
        for t in self.trades:
            running_balance.append(running_balance[-1] + t['pnl'])
        
        max_dd = 0
        peak = running_balance[0]
        for b in running_balance:
            if b > peak: peak = b
            dd = (peak - b) / peak * 100
            if dd > max_dd: max_dd = dd

        results = {
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'total_trades': len(self.trades)
        }
        
        if self.signals: self.signals.finished.emit(results)
        
        if self.connector:
            self.connector.disconnect()
