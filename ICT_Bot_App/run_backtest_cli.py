import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from trading_core.backtester import Backtester

class MockSignal:
    def emit(self, *args):
        if args:
            msg = str(args[0])
            if not msg.startswith("[EVAL]"):
                try:
                    print(msg)
                except UnicodeEncodeError:
                    print(msg.encode('utf-8', 'ignore').decode('ascii', 'ignore'))

class MockSignals:
    def __init__(self):
        self.log_message = MockSignal()
        self.progress = MockSignal()
        self.trade_closed = MockSignal()
        self.finished = MockSignal()
        self.market_bias = MockSignal()
        self.new_position = MockSignal()
        self.bot_status = MockSignal()
        self.account_summary = MockSignal()

class NoOpMockSignal(MockSignal):
    def emit(self, *args):
        pass

if __name__ == "__main__":
    params = {
        'symbol': 'BTCUSDm',
        'timeframe': 'M5',
        'start_date': '2024-02-16', 
        'end_date': '2024-08-08'
    }
    
    print("--- STARTING CLI BACKTEST WITH PREMIUM/DISCOUNT LOGIC ---")
    signals = MockSignals()
    
    # Replace the progress signal with a no-op version
    signals.progress = NoOpMockSignal()
    
    backtester = Backtester(params, signals)
    
    try:
        backtester.run()
    finally:
        import pandas as pd
        if backtester.trades:
            df_results = pd.DataFrame(backtester.trades)
            csv_file = "backtest_results_cli.csv"
            df_results.to_csv(csv_file, index=False)
            try:
                print(f"\n[INFO] Đã lưu kết quả giao dịch vào: {csv_file}")
            except UnicodeEncodeError:
                print(f"\n[INFO] Saved results to: {csv_file}")
            
            try:
                print("\n--- THỐNG KÊ NHANH ---")
            except UnicodeEncodeError:
                print("\n--- QUICK STATS ---")
            total_pnl = df_results['pnl'].sum()
            win_rate = (len(df_results[df_results['pnl'] > 0]) / len(df_results)) * 100 if len(df_results) > 0 else 0
            profit_factor = df_results[df_results['pnl'] > 0]['pnl'].sum() / abs(df_results[df_results['pnl'] < 0]['pnl'].sum()) if abs(df_results[df_results['pnl'] < 0]['pnl'].sum()) > 0 else 999
            
            try:
                print(f"Tổng PnL: {total_pnl:.2f}")
                print(f"Tổng số lệnh: {len(df_results)}")
                print(f"Tỷ lệ thắng: {win_rate:.2f}%")
                print(f"Profit Factor: {profit_factor:.2f}")
            except UnicodeEncodeError:
                print(f"Total PnL: {total_pnl:.2f}")
                print(f"Total Trades: {len(df_results)}")
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Profit Factor: {profit_factor:.2f}")

        else:
            try:
                print("\n[INFO] Không có giao dịch nào được thực hiện.")
            except UnicodeEncodeError:
                print("\n[INFO] No trades executed.")
    
    print("--- BACKTEST COMPLETED ---")
