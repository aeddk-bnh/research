from datetime import datetime, date
import pandas as pd
from trading_core.connectors import get_connector
from trading_core.strategy import evaluate_signal
from trading_core.market_structure import detect_bos_choch, find_swings, get_htf_bias
from trading_core.pd_arrays import detect_fvg, detect_order_block, detect_breaker_block
from trading_core.config_loader import TIMEFRAME, TIMEFRAME_SMALLER, TAKE_PROFIT_RR
from trading_core.time_filter import is_kill_zone_time

class Backtester:
    def __init__(self, params: dict, signals=None):
        self.params = params
        self.signals = signals
        self.symbol = params.get('symbol', 'BTCUSDm')
        self.timeframe = params.get('timeframe', TIMEFRAME)
        
        start_date_param = params.get('start_date')
        end_date_param = params.get('end_date')
        
        if isinstance(start_date_param, str):
            self.start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        else:
            self.start_date = start_date_param if isinstance(start_date_param, (date, datetime)) else date.today()
            
        if isinstance(end_date_param, str):
            self.end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        else:
            self.end_date = end_date_param if isinstance(end_date_param, (date, datetime)) else date.today()

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
        
        htf_timeframe = self.params.get('htf_timeframe', 'H4')
        
        df_main = self.connector.fetch_ohlcv(self.timeframe, limit=50000) 
        df_small = self.connector.fetch_ohlcv(TIMEFRAME_SMALLER, limit=50000)
        df_htf = self.connector.fetch_ohlcv(htf_timeframe, limit=50000)

        if df_main is None or df_small is None or df_htf is None:
             if self.signals: self.signals.log_message.emit("Không tải được toàn bộ dữ liệu.")
             return

        df_main.index = pd.to_datetime(df_main.index).tz_localize(None)
        df_small.index = pd.to_datetime(df_small.index).tz_localize(None)
        df_htf.index = pd.to_datetime(df_htf.index).tz_localize(None)

        start_ts = pd.to_datetime(self.start_date).replace(tzinfo=None)
        end_ts = pd.to_datetime(self.end_date).replace(tzinfo=None)
        
        df_main = df_main[(df_main.index >= start_ts) & (df_main.index <= end_ts)]
        
        if len(df_main) < 200:
             if self.signals: self.signals.log_message.emit("Dữ liệu không đủ để chạy backtest.")
             return

        if self.signals: self.signals.log_message.emit(f"Bắt đầu mô phỏng trên {len(df_main)} cây nến...")

        open_positions = []
        
        for i in range(200, len(df_main)):
            if self.signals and i % 20 == 0:
                self.signals.progress.emit(int((i / len(df_main)) * 100))

            current_idx = df_main.index[i]
            
            # --- Quản lý vị thế ---
            positions_to_close = [pos for pos in open_positions if self._check_exit_conditions(pos, df_main.iloc[i])[0] is not None]
            for pos in positions_to_close:
                exit_price, close_reason = self._check_exit_conditions(pos, df_main.iloc[i])
                if exit_price and close_reason:
                    self._close_position(pos, exit_price, close_reason, current_idx)
            open_positions = [p for p in open_positions if p not in positions_to_close]

            # --- Logic vào lệnh ---
            if self.last_trade_close_time:
                current_ts = pd.to_datetime(current_idx).replace(tzinfo=None)
                if current_ts - self.last_trade_close_time.replace(tzinfo=None) < self.cooldown_period:
                    continue
            
            if open_positions: continue
            if not is_kill_zone_time(timestamp=current_idx, signals=self.signals): continue
            
            try:
                df_main_slice = df_main.iloc[i-200:i+1]
                df_small_slice = df_small[df_small.index <= current_idx].tail(100)
                df_htf_slice = df_htf[df_htf.index <= current_idx].tail(200)

                if len(df_small_slice) < 50 or len(df_htf_slice) < 50 or not isinstance(df_main_slice, pd.DataFrame) or not isinstance(df_small_slice, pd.DataFrame) or not isinstance(df_htf_slice, pd.DataFrame):
                    continue

                df_main_analyzed = self._analyze_dataframe(df_main_slice.copy())
                df_small_analyzed = self._analyze_dataframe(df_small_slice.copy(), is_ltf=True)
                
                htf_df_analyzed = self._analyze_dataframe(df_htf_slice.copy())
                if isinstance(htf_df_analyzed, pd.DataFrame):
                    htf_bias = get_htf_bias(htf_df_analyzed, htf_label=htf_timeframe)
                else:
                    htf_bias = 'neutral'

                signal, entry, sl, reason = evaluate_signal(df_main_analyzed, df_small_analyzed, htf_bias, self.connector, signals=self.signals)

                if signal != 'none' and entry is not None and sl is not None:
                    self._open_position(signal, entry, sl, reason, current_idx, open_positions)
            
            except Exception as e:
                if self.signals:
                    self.signals.log_message.emit(f"[ERROR] at {current_idx}: {e}")
        
        self._report_results()

    def _analyze_dataframe(self, df: pd.DataFrame, is_ltf=False) -> pd.DataFrame:
        df_fvg = detect_fvg(df.copy())
        df_swings = find_swings(df_fvg)
        df_bos = detect_bos_choch(df_swings)
        if not is_ltf:
            df_ob = detect_order_block(df_bos)
            return detect_breaker_block(df_ob)
        return df_bos

    def _check_exit_conditions(self, pos, candle):
        if pos['side'] == 'LONG':
            if candle['low'] <= pos['sl']: return pos['sl'], "SL"
            if candle['high'] >= pos['tp']: return pos['tp'], "TP"
        else: # SHORT
            if candle['high'] >= pos['sl']: return pos['sl'], "SL"
            if candle['low'] <= pos['tp']: return pos['tp'], "TP"
        return None, None
        
    def _open_position(self, signal, entry, sl, reason, idx, open_positions):
        sl_dist = abs(entry - sl)
        if sl_dist == 0: return

        tp = entry + (sl_dist * float(TAKE_PROFIT_RR)) if signal == 'long' else entry - (sl_dist * float(TAKE_PROFIT_RR))
        quantity = (self.balance * 0.01) / sl_dist

        open_positions.append({
            'entry_time': idx, 'side': signal.upper(), 'entry_price': entry, 
            'sl': sl, 'tp': tp, 'quantity': quantity, 'reason': reason or 'N/A'
        })
        if self.signals: self.signals.log_message.emit(f"OPEN {signal.upper()} @ {entry:.5f} | Reason: {reason}")
    
    def _close_position(self, pos, exit_price, reason, idx):
        pnl = (exit_price - pos['entry_price']) * pos['quantity'] if pos['side'] == 'LONG' else (pos['entry_price'] - exit_price) * pos['quantity']
        self.balance += pnl
        self.last_trade_close_time = pd.Timestamp(idx)

        trade_record = {
            'entry_time': str(pos['entry_time']), 'side': pos['side'], 'entry_price': pos['entry_price'], 
            'exit_price': exit_price, 'sl': pos['sl'], 'tp': pos['tp'], 'pnl': pnl, 'reason': pos.get('reason', 'N/A')
        }
        self.trades.append(trade_record)
        if self.signals: 
            self.signals.trade_closed.emit(trade_record)
            self.signals.log_message.emit(f"CLOSE {pos['side']} @ {exit_price:.5f} | PnL: {pnl:.2f} | Reason: {reason}")

    def _report_results(self):
        total_pnl = self.balance - self.initial_balance
        wins = [t for t in self.trades if t['pnl'] > 0]
        win_rate = (len(wins) / len(self.trades) * 100) if self.trades else 0
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] <= 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        
        equity_curve = [self.initial_balance]
        for t in self.trades:
            equity_curve.append(equity_curve[-1] + t['pnl'])

        peak = self.initial_balance
        max_dd = 0.0
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
