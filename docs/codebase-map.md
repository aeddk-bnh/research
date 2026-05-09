# Codebase Map

## Snapshot
- **Purpose:** An automated ICT (Inner Circle Trader) trading bot with a PySide6 Desktop UI, backtesting engine, and multi-platform live trading (Binance/MT5).
- **Primary stack:** Python (PySide6 for UI, Pandas/NumPy for data processing, CCXT/MetaTrader5 for connectors).
- **Main runtimes:** Python 3 (Desktop Application).
- **Entry points:** 
  - `ICT_Bot_App/main.py` (Desktop UI Application)
  - `ICT_Bot_App/run_backtest_cli.py` (CLI Backtesting entry point)

## Top-Level Layout
- `ICT_Bot_App/`: Main application directory containing UI, core logic, and configurations.
- `ICT_Bot/`: (Currently empty, legacy directory).
- `docs/`: Documentation folder containing context and codebase maps.
- `*.md`: Various markdown documents detailing methods, gaps, and implementation plans.

## Module Map
| Module | Role | Key files | Edit here when | Depends on | Used by |
| --- | --- | --- | --- | --- | --- |
| **App (UI)** | Desktop interface using PySide6. | `ICT_Bot_App/app/main_window.py`, `worker.py`, `config_manager.py` | Modifying UI components, adding dashboard features, or changing config handling. | `trading_core` | `ICT_Bot_App/main.py` |
| **Trading Core** | The brain of the bot containing ICT rules, indicators, and logic. | `strategy.py`, `market_structure.py`, `pd_arrays.py`, `time_filter.py`, `backtester.py` | Tuning ICT logic (BOS, CHOCH, FVG, OTE, Kill Zones), risk management, and order entries. | `connectors` | `App (UI)`, `run_backtest_cli.py` |
| **Connectors** | API wrappers for interacting with exchanges. | `connectors/binance_connector.py`, `mt5_connector.py`, `mock_connector.py` | Fixing connection issues, adding new exchange support, or modifying order execution methods. | ccxt, MetaTrader5 | `trading_core` |

## Interaction Map
- **Request flow (Live):** UI configures -> `worker.py` starts background thread -> `strategy.py` loops -> `connectors` fetch data -> `market_structure.py`/`pd_arrays.py` analyze data -> `strategy.py` sends orders via `connectors`.
- **Request flow (Backtest):** `run_backtest_cli.py` -> `backtester.py` -> feeds historical data to `strategy.py` -> returns metrics.
- **Data flow:** OHLCV Data (DataFrame) -> Market Structure (BOS/CHOCH) -> PD Arrays (OB/FVG) -> Entry/Risk Logic -> Orders.
- **External integrations:** Binance API (via ccxt), Exness MT5 (via MetaTrader5 python library).
- **Background work:** `worker.py` in `app/` runs the bot logic in a `QThread` to prevent UI freezing.

## Change Guide
- **If changing ICT Logic:** Edit `trading_core/market_structure.py`, `trading_core/pd_arrays.py`, or `trading_core/strategy.py`.
- **If adding a new configuration:** Update `ICT_Bot_App/config.json`, then modify `ICT_Bot_App/trading_core/config_loader.py` and the UI in `ICT_Bot_App/app/main_window.py`.
- **If debugging signals/entries:** Enable `ENABLE_LOGGING` in config, check `ICT_Bot_App/bot.log`, and review `ICT_Bot_App/trading_core/strategy.py` entry conditions.

## Validation Guide
- **Main test or check commands:** Run `python ICT_Bot_App/run_backtest_cli.py` to verify logic against historical data without financial risk.
- **Fastest suites or files:** `ICT_Bot_App/trading_core/run_test.py`
- **Regression attention:** When changing `market_structure.py`, heavily verify backtest results as it drastically alters signal frequency and accuracy.

## Cross-Cutting Concerns
- **Config and env:** Handled by `config.json` and loaded via `config_loader.py` / `config_manager.py`.
- **Testing:** Primarily relies on the `backtester.py` module to validate trading logic correctness over time.
- **Hotspots:** `market_structure.py` (swing detection is complex and dictates everything else), `strategy.py` (contains complex order tracking and OTE logic).
- **Concurrency:** `worker.py` must safely emit signals to `main_window.py` to update the GUI without thread collisions.

## Unknowns
- Integration tests or unit tests (e.g. `pytest` setup) are not explicitly defined outside of `run_test.py`.
- Robust error handling for MT5 API connection drops or Binance rate limits might be basic.

## Quant Extension
- ICT_Bot_App/trading_core/quant_strategy.py: Adds Quantitative Trading Mode (SMA Crossover + RSI filter). Selected via UI or config.json.

*   **`trading_core/quant_strategy.py`**
    *   **Mô tả:** Chứa thuật toán phân tích định lượng (Quantitative Analysis) bằng pandas-ta. Cung cấp tín hiệu giao dịch dựa trên SMA Crossover và RSI làm bộ lọc xu hướng. Hoạt động độc lập với logic Price Action của ICT.
