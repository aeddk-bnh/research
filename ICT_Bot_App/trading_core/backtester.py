from datetime import datetime
import pandas as pd
from trading_core.connectors import get_connector
from trading_core.strategy import evaluate_signal, calculate_position_size
from trading_core.market_structure import detect_bos_choch, find_swings
from trading_core.pd_arrays import detect_fvg, detect_order_block, detect_breaker_block
from trading_core.config_loader import TIMEFRAME, TIMEFRAME_SMALLER, TAKE_PROFIT_RR
from trading_core.time_filter import is_kill_zone_time # Thêm import

class Backtester:
    def __init__(self, params: dict, signals=None):
        self.params = params
        self.signals = signals
        self.symbol = params.get('symbol', 'BTCUSDm')
        self.timeframe = params.get('timeframe', TIMEFRAME)
        self.start_date = params.get('start_date')
        self.end_date = params.get('end_date')
        
        self.balance = 10000.0 
        self.initial_balance = self.balance
        self.trades = []
        
        self.last_trade_close_time = None
        self.cooldown_period = pd.Timedelta(minutes=30)
        
        self.connector = get_connector('mt5') 
        if self.connector:
             self.connector.connect()

    def run(self):
        if not self.connector:
            if self.signals: self.signals.log_message.emit("Không thể kết nối để lấy dữ liệu lịch sử.")
            return

        if self.signals: self.signals.log_message.emit(f"Đang tải dữ liệu lịch sử cho {self.symbol}...")
        
        df_main = self.connector.fetch_ohlcv(self.timeframe, limit=5000) 
        df_small = self.connector.fetch_ohlcv(TIMEFRAME_SMALLER, limit=10000)

        if df_main is None or df_small is None:
             if self.signals: self.signals.log_message.emit("Không tải được dữ liệu.")
             return

        df_main.index = pd.to_datetime(df_main.index)
        df_small.index = pd.to_datetime(df_small.index)

        start_ts = pd.Timestamp(self.start_date)
        end_ts = pd.Timestamp(self.end_date)
        
        df_main = df_main[(df_main.index >= start_ts) & (df_main.index <= end_ts)]
        
        total_candles = len(df_main)
        if total_candles < 200:
             if self.signals: self.signals.log_message.emit("Dữ liệu không đủ để chạy backtest (cần ít nhất 200 nến).")
             return

        if self.signals: self.signals.log_message.emit(f"Bắt đầu mô phỏng trên {total_candles} cây nến...")

        window_size = 200
        open_positions = []

        for i in range(window_size, total_candles):
            if self.signals and i % 10 == 0:
                progress = int((i / total_candles) * 100)
                self.signals.progress.emit(progress)

            current_idx = df_main.index[i]
            
            df_main_slice = df_main.iloc[i-window_size:i+1].copy()
            df_small_slice = df_small[df_small.index <= current_idx].tail(100).copy()

            if len(df_small_slice) < 50: continue

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
                        close_reason = "SL"
                    elif current_high >= pos['tp']:
                        exit_price = pos['tp']
                        close_reason = "TP"
                elif pos['side'] == 'SHORT':
                    if current_high >= pos['sl']:
                        exit_price = pos['sl']
                        close_reason = "SL"
                    elif current_low <= pos['tp']:
                        exit_price = pos['tp']
                        close_reason = "TP"
                
                if close_reason:
                    if pos['side'] == 'LONG':
                        pnl = (exit_price - pos['entry_price']) * pos['quantity']
                    else: 
                        pnl = (pos['entry_price'] - exit_price) * pos['quantity']

                    self.balance += pnl
                    self.last_trade_close_time = current_idx 

                    trade_record = {
                        'entry_time': str(pos['entry_time']), 'side': pos['side'],
                        'entry_price': pos['entry_price'], 'exit_price': exit_price,
                        'sl': pos['sl'], 'tp': pos['tp'], 'pnl': pnl,
                        'close_reason': close_reason
                    }
                    self.trades.append(trade_record)
                    if self.signals: self.signals.trade_closed.emit(trade_record)
                    positions_to_remove.append(pos)
            
            for pos in positions_to_remove:
                open_positions.remove(pos)

            if self.last_trade_close_time:
                if (current_idx - self.last_trade_close_time) < self.cooldown_period:
                    continue

            if open_positions:
                continue

            # Bỏ qua nếu không trong Kill Zone
            if not is_kill_zone_time(timestamp=current_idx, signals=self.signals):
                continue
            
            try:
                df_with_fvg = detect_fvg(df_main_slice.copy())
                df_with_swings = find_swings(df_with_fvg)
                df_with_bos = detect_bos_choch(df_with_swings)
                df_with_ob = detect_order_block(df_with_bos)
                df_main_analyzed = detect_breaker_block(df_with_ob)
                
                df_small_swings = find_swings(df_small_slice.copy())
                df_small_analyzed = detect_bos_choch(df_small_swings)

                signal, entry_price, sl_price = evaluate_signal(df_main_analyzed, df_small_analyzed, self.connector, signals=self.signals)

                if signal != 'none' and entry_price is not None and sl_price is not None:
                     rr = float(TAKE_PROFIT_RR)
                     sl_distance = abs(entry_price - sl_price)
                     
                     if signal == 'long':
                         tp_price = entry_price + (sl_distance * rr)
                     else:
                         tp_price = entry_price - (sl_distance * rr)
                     
                     risk_percent = 0.01
                     risk_amount = self.balance * risk_percent
                     quantity = (risk_amount / sl_distance) if sl_distance > 0 else 0

                     if quantity > 0:
                         new_pos = {
                             'entry_time': current_idx, 'side': signal.upper(),
                             'entry_price': entry_price, 'sl': sl_price,
                             'tp': tp_price, 'quantity': quantity
                         }
                         open_positions.append(new_pos)
            
            except Exception as e:
                if self.signals:
                    self.signals.log_message.emit(f"[BACKTESTER_ERROR] at candle {current_idx}: {e}")
                    import traceback
                    self.signals.log_message.emit(f"Traceback: {traceback.format_exc()}")
                pass

        total_pnl = self.balance - self.initial_balance
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]
        win_rate = (len(wins) / len(self.trades) * 100) if self.trades else 0
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        
        # Correct Max Drawdown Calculation
        max_dd = 0.0
        peak = self.initial_balance
        equity_curve = [self.initial_balance]
        for t in self.trades:
            equity_curve.append(equity_curve[-1] + t['pnl'])

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown

        results = {
            'total_pnl': total_pnl, 'win_rate': win_rate,
            'profit_factor': profit_factor, 'max_drawdown': max_dd,
        
            'total_trades': len(self.trades)
        }
        
        if self.signals: self.signals.finished.emit(results)
        
        if self.connector:
            self.connector.disconnect()
