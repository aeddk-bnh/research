import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from trading_core.backtester import Backtester

class MockSignal:
    def emit(self, *args):
        # In ra nội dung của signal, lọc bỏ bớt nếu cần
        if args:
            msg = str(args[0])
            if not msg.startswith("[EVAL]"):
                print(msg)

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

if __name__ == "__main__":
    # Cấu hình tham số backtest
    params = {
        'symbol': 'BTCUSDm',
        'timeframe': 'M5',
        'start_date': '2026-01-19', 
        'end_date': '2026-01-23'
    }
    
    print("--- STARTING CLI BACKTEST WITH PREMIUM/DISCOUNT LOGIC ---")
    signals = MockSignals()
    
    # Ghi đè phương thức progress để không spam console
    signals.progress.emit = lambda x: None 
    
    backtester = Backtester(params, signals)
    
    try:
        backtester.run()
    finally:
        # Xuất kết quả ra CSV
        import pandas as pd
        if backtester.trades:
            df_results = pd.DataFrame(backtester.trades)
            csv_file = "backtest_results_cli.csv"
            df_results.to_csv(csv_file, index=False)
            print(f"\n[INFO] Đã lưu kết quả giao dịch vào: {csv_file}")
            
            # In thống kê nhanh
            print("\n--- THỐNG KÊ NHANH ---")
            total_pnl = df_results['pnl'].sum()
            win_rate = (len(df_results[df_results['pnl'] > 0]) / len(df_results)) * 100
            profit_factor = df_results[df_results['pnl'] > 0]['pnl'].sum() / abs(df_results[df_results['pnl'] < 0]['pnl'].sum()) if abs(df_results[df_results['pnl'] < 0]['pnl'].sum()) > 0 else 999
            
            print(f"Tổng PnL: {total_pnl:.2f}")
            print(f"Tổng số lệnh: {len(df_results)}")
            print(f"Tỷ lệ thắng: {win_rate:.2f}%")
            print(f"Profit Factor: {profit_factor:.2f}")

        else:
            print("\n[INFO] Không có giao dịch nào được thực hiện.")

    print("--- BACKTEST COMPLETED ---")


