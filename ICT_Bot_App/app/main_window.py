import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox, QGroupBox, QMessageBox,
    QDateEdit, QProgressBar
)
from PySide6.QtCore import QTimer, QThread, QDate # Import QThread
from PySide6.QtGui import QCloseEvent

from app.worker import BotWorker, BacktestWorker
from app.config_manager import config_manager
from trading_core.time_filter import get_kill_zone_status

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ICT Trading Bot")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.status_bar = self.statusBar()
        self.status_label = QLabel("Trạng thái: Đã dừng")
        self.platform_label = QLabel("Nền tảng: -")
        self.account_label = QLabel("Tài khoản: -")
        self.pnl_label = QLabel("P/L: -")
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.platform_label)
        self.status_bar.addPermanentWidget(self.account_label)
        self.status_bar.addPermanentWidget(self.pnl_label)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.dashboard_tab = self.create_dashboard_tab()
        self.config_tab = self.create_config_tab()
        self.log_tab = self.create_log_tab()
        self.trades_tab = self.create_trades_tab()
        self.backtesting_tab = self.create_backtesting_tab()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.config_tab, "Cấu hình")
        self.tabs.addTab(self.log_tab, "Nhật ký")
        self.tabs.addTab(self.trades_tab, "Giao dịch")
        self.tabs.addTab(self.backtesting_tab, "Backtesting")

        # Initialize worker and connect signals
        self.worker = BotWorker()
        self._connect_worker_signals()

        self.initial_balance = 0.0
        
        # Open log file
        import os
        self.log_file_path = str(config_manager.get('logging.log_file', 'bot.log'))
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file_handle = open(self.log_file_path, 'a', encoding='utf-8')

        # Timer for periodic updates (e.g., P/L, account balance) - UI Thread
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.periodic_update)
        self.timer.start(5000) # Update every 5 seconds

        # Timer for periodic updates of Kill Zone status directly from UI thread
        self.kz_ui_timer = QTimer(self)
        self.kz_ui_timer.timeout.connect(self.update_kz_status_from_timer)
        self.kz_ui_timer.start(10000) # Update every 10 seconds

        # Initial KZ status update
        self.update_kz_status_from_timer()
        # Initial platform/account info update
        self._update_platform_info_from_config()

    def _connect_worker_signals(self):
        # Disconnect any previous connections to avoid multiple signal emissions
        try:
            self.worker.signals.log_message.disconnect(self.append_to_log)
            self.worker.signals.bot_status.disconnect(self.update_status_bar)
            self.worker.signals.market_bias.disconnect(self.update_market_bias)
            self.worker.signals.account_summary.disconnect(self.update_account_summary)
            self.worker.signals.new_position.disconnect(self.update_open_positions_table)
            self.worker.signals.position_closed.disconnect(self.update_history_table)
        except RuntimeError:
            pass # Ignore if not connected yet

        self.worker.signals.log_message.connect(self.append_to_log)
        self.worker.signals.bot_status.connect(self.update_status_bar)
        self.worker.signals.market_bias.connect(self.update_market_bias)
        self.worker.signals.account_summary.connect(self.update_account_summary)
        self.worker.signals.new_position.connect(self.update_open_positions_table)
        self.worker.signals.position_closed.connect(self.update_history_table)

    def _update_platform_info_from_config(self):
        platform = str(config_manager.get('platform', 'mt5')).upper()
        self.platform_label.setText(f"Nền tảng: {platform}")
        if platform == 'MT5':
            login = config_manager.get('mt5.login', 'N/A')
            self.account_label.setText(f"Tài khoản: {login}")
        elif platform == 'BINANCE':
            symbol = config_manager.get('binance.symbol', 'N/A')
            self.account_label.setText(f"Cặp: {symbol}")

    def create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        control_group = QGroupBox("Điều khiển")
        control_layout = QHBoxLayout(control_group)
        self.start_stop_button = QPushButton("Bắt đầu Bot")
        self.start_stop_button.clicked.connect(self.toggle_bot)
        control_layout.addWidget(self.start_stop_button)
        layout.addWidget(control_group)

        status_group = QGroupBox("Trạng thái")
        status_layout = QFormLayout(status_group)
        self.bot_status_label = QLabel("Đang dừng")
        self.bias_label = QLabel("-")
        self.kz_status_label = QLabel("-") # Đây là label sẽ được update
        status_layout.addRow("Trạng thái Bot:", self.bot_status_label)
        status_layout.addRow("Xu hướng (Bias):", self.bias_label)
        status_layout.addRow("Kill Zone:", self.kz_status_label)
        layout.addWidget(status_group)

        account_group = QGroupBox("Tài khoản")
        account_layout = QFormLayout(account_group)
        self.balance_label = QLabel("$0.00")
        self.pnl_session_label = QLabel("$0.00")
        account_layout.addRow("Số dư:", self.balance_label)
        account_layout.addRow("P/L Phiên:", self.pnl_session_label)
        layout.addWidget(account_group)

        layout.addStretch()

        return widget

    def create_config_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # Platform
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["mt5", "binance"])
        current_platform = str(config_manager.get('platform', 'mt5')) # Ép kiểu an toàn
        self.platform_combo.setCurrentText(current_platform)
        self.platform_combo.currentIndexChanged.connect(self._update_platform_info_from_config) # Update info when platform changes
        layout.addRow("Nền tảng:", self.platform_combo)

        # MT5 Config
        mt5_group = QGroupBox("Cấu hình MT5")
        mt5_layout = QFormLayout(mt5_group)
        self.mt5_login_input = QLineEdit(str(config_manager.get('mt5.login', ''))) # Ép kiểu an toàn
        self.mt5_password_input = QLineEdit(str(config_manager.get('mt5.password', '')))
        self.mt5_server_input = QLineEdit(str(config_manager.get('mt5.server', '')))
        self.mt5_path_input = QLineEdit(str(config_manager.get('mt5.path', '')))
        self.mt5_symbol_input = QLineEdit(str(config_manager.get('mt5.symbol', '')))
        self.mt5_password_input.setEchoMode(QLineEdit.EchoMode.Password) # Sửa lỗi Password
        mt5_layout.addRow("Login:", self.mt5_login_input)
        mt5_layout.addRow("Password:", self.mt5_password_input)
        mt5_layout.addRow("Server:", self.mt5_server_input)
        mt5_layout.addRow("Path:", self.mt5_path_input)
        mt5_layout.addRow("Symbol:", self.mt5_symbol_input)
        layout.addWidget(mt5_group)

        # Binance Config
        binance_group = QGroupBox("Cấu hình Binance")
        binance_layout = QFormLayout(binance_group)
        self.binance_api_key_input = QLineEdit(str(config_manager.get('binance.api_key', '')))
        self.binance_secret_key_input = QLineEdit(str(config_manager.get('binance.secret_key', '')))
        self.binance_symbol_input = QLineEdit(str(config_manager.get('binance.symbol', '')))
        self.binance_secret_key_input.setEchoMode(QLineEdit.EchoMode.Password) # Sửa lỗi Password
        binance_layout.addRow("API Key:", self.binance_api_key_input)
        binance_layout.addRow("Secret Key:", self.binance_secret_key_input)
        binance_layout.addRow("Symbol:", self.binance_symbol_input)
        layout.addWidget(binance_group)

        # Trading Config
        trading_group = QGroupBox("Giao dịch")
        trading_layout = QFormLayout(trading_group)
        self.symbol_input = QLineEdit(str(config_manager.get('trading.symbol', '')))
        self.risk_spinbox = QDoubleSpinBox()
        self.risk_spinbox.setRange(0.1, 100.0)
        self.risk_spinbox.setValue(float(config_manager.get('trading.risk_percent_per_trade', 1.0))) # Ép kiểu an toàn
        self.risk_spinbox.setSuffix("%")
        trading_layout.addRow("Cặp tiền:", self.symbol_input)
        trading_layout.addRow("Rủi ro mỗi lệnh:", self.risk_spinbox)
        layout.addWidget(trading_group)

        # Save Config Button
        self.save_config_button = QPushButton("Lưu Cấu hình")
        self.save_config_button.clicked.connect(self.save_config)
        layout.addWidget(self.save_config_button)

        return widget

    def create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        clear_log_btn = QPushButton("Xóa nhật ký")
        clear_log_btn.clicked.connect(self.clear_log)

        layout.addWidget(self.log_text_edit)
        layout.addWidget(clear_log_btn)

        return widget

    def create_trades_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Open Positions Table
        open_pos_group = QGroupBox("Lệnh đang mở")
        open_pos_layout = QVBoxLayout(open_pos_group)
        self.open_positions_table = QTableWidget()
        self.open_positions_table.setColumnCount(7)
        self.open_positions_table.setHorizontalHeaderLabels(
            ["ID", "Cặp tiền", "Loại", "Khối lượng", "Giá vào", "SL", "TP"]
        )
        header = self.open_positions_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Sửa lỗi Stretch
        open_pos_layout.addWidget(self.open_positions_table)

        # Trade History Table
        hist_group = QGroupBox("Lịch sử giao dịch")
        hist_layout = QVBoxLayout(hist_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9) # ID, Symbol, Side, Qty, Entry, Exit, SL, TP, P/L, Time Closed
        self.history_table.setHorizontalHeaderLabels(
            ["ID", "Cặp tiền", "Loại", "Khối lượng", "Giá vào", "Giá đóng", "SL", "TP", "P/L"]
        )
        header_hist = self.history_table.horizontalHeader()
        header_hist.setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Sửa lỗi Stretch
        hist_layout.addWidget(self.history_table)

        # Simulate Close Position Button
        simulate_close_btn = QPushButton("Giả lập đóng lệnh")
        simulate_close_btn.clicked.connect(self.simulate_close_position)

        layout.addWidget(open_pos_group)
        layout.addWidget(hist_group)
        layout.addWidget(simulate_close_btn) # Add button to layout

        return widget

    def toggle_bot(self):
        if self.worker.isRunning():
            self.worker.stop()
            self.start_stop_button.setText("Bắt đầu Bot")
            self.status_label.setText("Trạng thái: Đang dừng...")
        else:
            if hasattr(self, 'worker') and self.worker.isRunning():
                return
            self.worker = BotWorker()
            self._connect_worker_signals() # Reconnect signals for new worker
            self.worker.start()
            self.start_stop_button.setText("Dừng Bot")
            self.status_label.setText("Trạng thái: Đang chạy")

    def append_to_log(self, message: str):
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{now}] {message}"
        self.log_text_edit.append(formatted_message)
        if self.log_file_handle:
            self.log_file_handle.write(formatted_message + '\n')
            self.log_file_handle.flush()

    def update_status_bar(self, status: str):
        self.bot_status_label.setText(status)
        self.status_label.setText(f"Trạng thái: {status}")

    def update_market_bias(self, bias: str):
        self.bias_label.setText(bias)

    def update_kz_status(self, kz_info: str):
        self.kz_status_label.setText(kz_info)

    def update_account_summary(self, summary: dict):
        self.balance_label.setText(f"${summary.get('balance', 0):.2f}")
        self.pnl_session_label.setText(f"${summary.get('pnl', 0):.2f}")

    def update_open_positions_table(self, position_data: dict):
        row_position = self.open_positions_table.rowCount()
        self.open_positions_table.insertRow(row_position)
        self.open_positions_table.setItem(row_position, 0, QTableWidgetItem(str(position_data.get('id', 'N/A'))))
        self.open_positions_table.setItem(row_position, 1, QTableWidgetItem(str(position_data.get('symbol', ''))))
        self.open_positions_table.setItem(row_position, 2, QTableWidgetItem(str(position_data.get('side', ''))))
        self.open_positions_table.setItem(row_position, 3, QTableWidgetItem(str(position_data.get('quantity', 0))))
        self.open_positions_table.setItem(row_position, 4, QTableWidgetItem(f"{float(position_data.get('entry_price', 0)):.5f}"))
        self.open_positions_table.setItem(row_position, 5, QTableWidgetItem(f"{float(position_data.get('sl', 0)):.5f}"))
        self.open_positions_table.setItem(row_position, 6, QTableWidgetItem(f"{float(position_data.get('tp', 0)):.5f}"))

    def update_history_table(self, position_id: str | int, close_data: dict):
        for row in range(self.open_positions_table.rowCount()):
            item = self.open_positions_table.item(row, 0)
            if item and item.text() == str(position_id):
                closed_item_data = {}
                for col in range(self.open_positions_table.columnCount()):
                    header_item = self.open_positions_table.horizontalHeaderItem(col)
                    table_item = self.open_positions_table.item(row, col) # Rename to avoid conflict with 'item' variable
                    if header_item and table_item:
                        header = header_item.text()
                        closed_item_data[header.lower().replace(" ", "_")] = table_item.text()
                
                history_row = self.history_table.rowCount()
                self.history_table.insertRow(history_row)
                
                exit_price = close_data.get('exit_price', 'N/A')
                pnl = close_data.get('pnl', 'N/A')
                
                self.history_table.setItem(history_row, 0, QTableWidgetItem(closed_item_data.get('id', 'N/A')))
                self.history_table.setItem(history_row, 1, QTableWidgetItem(closed_item_data.get('cặp_tiền', '')))
                self.history_table.setItem(history_row, 2, QTableWidgetItem(closed_item_data.get('loại', '')))
                self.history_table.setItem(history_row, 3, QTableWidgetItem(closed_item_data.get('khối_lượng', '0')))
                self.history_table.setItem(history_row, 4, QTableWidgetItem(closed_item_data.get('giá_vào', '0')))
                self.history_table.setItem(history_row, 5, QTableWidgetItem(str(exit_price)))
                self.history_table.setItem(history_row, 6, QTableWidgetItem(closed_item_data.get('sl', '0')))
                self.history_table.setItem(history_row, 7, QTableWidgetItem(closed_item_data.get('tp', '0')))
                self.history_table.setItem(history_row, 8, QTableWidgetItem(str(pnl)))

                self.open_positions_table.removeRow(row)
                self.append_to_log(f"Lệnh {position_id} đã được chuyển sang lịch sử.")
                break

    def update_kz_status_from_timer(self):
        """Hàm này được gọi bởi QTimer trong luồng UI để cập nhật KZ."""
        is_in_kz, status_str = get_kill_zone_status()
        self.kz_status_label.setText(status_str)

    def periodic_update(self):
        if self.worker and self.worker.isRunning() and self.worker.connector:
            current_balance = self.worker.connector.get_account_balance()
            if current_balance is not None:
                if self.initial_balance == 0.0:
                    self.initial_balance = current_balance
                pnl = current_balance - self.initial_balance
                self.update_account_summary({'balance': current_balance, 'pnl': pnl})
                self.append_to_log(f"Cập nhật tài khoản: Balance=${current_balance:.2f}, P&L=${pnl:.2f}")
            else:
                self.append_to_log("Không thể cập nhật tài khoản.")
        else:
            pass

    def save_config(self):
        try:
            mt5_login_text = self.mt5_login_input.text()
            mt5_login = int(mt5_login_text) if mt5_login_text else 0

            mt5_password = self.mt5_password_input.text()
            if not mt5_password:
                self.append_to_log("Cảnh báo: Mật khẩu MT5 trống.")

            risk_percent = self.risk_spinbox.value()
            if risk_percent <= 0:
                self.append_to_log("Cảnh báo: Tỷ lệ rủi ro nên lớn hơn 0.")

            config_manager.set('platform', self.platform_combo.currentText())
            config_manager.set('mt5.login', mt5_login)
            config_manager.set('mt5.password', mt5_password)
            config_manager.set('mt5.server', self.mt5_server_input.text())
            config_manager.set('mt5.path', self.mt5_path_input.text())
            config_manager.set('mt5.symbol', self.mt5_symbol_input.text())

            config_manager.set('binance.api_key', self.binance_api_key_input.text())
            config_manager.set('binance.secret_key', self.binance_secret_key_input.text())
            config_manager.set('binance.symbol', self.binance_symbol_input.text())

            config_manager.set('trading.symbol', self.symbol_input.text())
            config_manager.set('trading.risk_percent_per_trade', risk_percent)

            config_manager.save_config()
            self.append_to_log("Cấu hình đã được lưu thành công.")
            self._update_platform_info_from_config() # Update platform/account info after saving
        except ValueError as e:
            self.append_to_log(f"Lỗi: Dữ liệu không hợp lệ. Vui lòng kiểm tra lại các trường số. Chi tiết: {e}")
        except Exception as e:
            self.append_to_log(f"Lỗi khi lưu cấu hình: {e}")

    def clear_log(self):
        self.log_text_edit.clear()

    def closeEvent(self, event: QCloseEvent):
        reply = QMessageBox.question(self, 'Thoát ứng dụng',
                                    'Bạn có chắc chắn muốn đóng ứng dụng?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.append_to_log("Đóng ứng dụng...")
            if self.log_file_handle:
                self.log_file_handle.close()
            if self.worker.isRunning():
                self.worker.stop()
            self.kz_ui_timer.stop()
            self.timer.stop()
            event.accept()
        else:
            event.ignore()

    def simulate_close_position(self):
        if self.open_positions_table.rowCount() == 0:
            self.append_to_log("Không có lệnh nào để đóng.")
            return
        
        row_to_close = self.open_positions_table.rowCount() - 1
        item = self.open_positions_table.item(row_to_close, 0)
        if not item:
            self.append_to_log("Không thể lấy ID lệnh để đóng.")
            return
        position_id = item.text()
        
        import random
        closed_data = {
            'exit_price': random.uniform(30000, 40000),
            'pnl': random.uniform(-100, 100)
        }
        
        self.update_history_table(position_id, closed_data)

    def create_backtesting_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)

        # Left side: Configuration
        config_group = QGroupBox("Cấu hình Backtest")
        config_layout = QFormLayout(config_group)

        self.bt_symbol_input = QLineEdit(config_manager.get('mt5.symbol', 'BTCUSDm'))
        self.bt_timeframe_combo = QComboBox()
        self.bt_timeframe_combo.addItems(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'])
        self.bt_timeframe_combo.setCurrentText(config_manager.get('trading.timeframe', 'H1'))
        
        self.bt_start_date_edit = QDateEdit(QDate.currentDate().addMonths(-1))
        self.bt_start_date_edit.setCalendarPopup(True)
        self.bt_end_date_edit = QDateEdit(QDate.currentDate())
        self.bt_end_date_edit.setCalendarPopup(True)

        self.bt_start_button = QPushButton("Bắt đầu Backtest")
        self.bt_start_button.clicked.connect(self.start_backtest)

        config_layout.addRow("Symbol:", self.bt_symbol_input)
        config_layout.addRow("Timeframe:", self.bt_timeframe_combo)
        config_layout.addRow("Từ ngày:", self.bt_start_date_edit)
        config_layout.addRow("Đến ngày:", self.bt_end_date_edit)
        config_layout.addRow(self.bt_start_button)

        # Right side: Results
        results_group = QGroupBox("Kết quả")
        results_layout = QVBoxLayout(results_group)

        # Progress bar
        self.bt_progress_bar = QProgressBar()
        self.bt_progress_bar.setValue(0)
        results_layout.addWidget(self.bt_progress_bar)
        
        # Summary
        summary_layout = QFormLayout()
        self.bt_pnl_label = QLabel("$0.00")
        self.bt_winrate_label = QLabel("0%")
        self.bt_profit_factor_label = QLabel("N/A")
        self.bt_max_drawdown_label = QLabel("0%")
        summary_layout.addRow("Tổng P/L:", self.bt_pnl_label)
        summary_layout.addRow("Tỷ lệ thắng:", self.bt_winrate_label)
        summary_layout.addRow("Profit Factor:", self.bt_profit_factor_label)
        summary_layout.addRow("Max Drawdown:", self.bt_max_drawdown_label)
        results_layout.addLayout(summary_layout)

        # Trades table
        self.bt_trades_table = QTableWidget()
        self.bt_trades_table.setColumnCount(8)
        self.bt_trades_table.setHorizontalHeaderLabels(
            ["Thời gian vào", "Loại", "Giá vào", "Giá đóng", "SL", "TP", "P/L", "Lý do đóng"]
        )
        results_layout.addWidget(self.bt_trades_table)

        main_layout.addWidget(config_group, 1) # 1 part of the width
        main_layout.addWidget(results_group, 3) # 3 parts of the width
        
        return widget

    def start_backtest(self):
        self.append_to_log("Chuẩn bị bắt đầu backtest...")
        
        # Disable button
        self.bt_start_button.setEnabled(False)
        self.bt_start_button.setText("Đang chạy...")
        
        # Reset UI
        self.bt_progress_bar.setValue(0)
        self.bt_pnl_label.setText("$0.00")
        self.bt_winrate_label.setText("0%")
        self.bt_profit_factor_label.setText("N/A")
        self.bt_max_drawdown_label.setText("0%")
        self.bt_trades_table.setRowCount(0)
        
        params = {
            'symbol': self.bt_symbol_input.text(),
            'timeframe': self.bt_timeframe_combo.currentText(),
            'start_date': self.bt_start_date_edit.date().toPython(),
            'end_date': self.bt_end_date_edit.date().toPython(),
        }
        
        self.backtest_worker = BacktestWorker(params)
        self.backtest_worker.signals.log_message.connect(self.append_to_log)
        self.backtest_worker.signals.progress.connect(self.update_backtest_progress)
        self.backtest_worker.signals.trade_closed.connect(self.add_backtest_trade)
        self.backtest_worker.signals.finished.connect(self.finish_backtest)
        
        self.backtest_worker.start()

    def update_backtest_progress(self, value):
        self.bt_progress_bar.setValue(value)

    def add_backtest_trade(self, trade_data):
        row = self.bt_trades_table.rowCount()
        self.bt_trades_table.insertRow(row)
        
        self.bt_trades_table.setItem(row, 0, QTableWidgetItem(trade_data.get('entry_time', '')))
        self.bt_trades_table.setItem(row, 1, QTableWidgetItem(trade_data.get('side', '')))
        self.bt_trades_table.setItem(row, 2, QTableWidgetItem(f"{trade_data.get('entry_price', 0):.5f}"))
        self.bt_trades_table.setItem(row, 3, QTableWidgetItem(f"{trade_data.get('exit_price', 0):.5f}"))
        self.bt_trades_table.setItem(row, 4, QTableWidgetItem(f"{trade_data.get('sl', 0):.5f}"))
        self.bt_trades_table.setItem(row, 5, QTableWidgetItem(f"{trade_data.get('tp', 0):.5f}"))
        self.bt_trades_table.setItem(row, 6, QTableWidgetItem(f"{trade_data.get('pnl', 0):.2f}"))
        self.bt_trades_table.setItem(row, 7, QTableWidgetItem(trade_data.get('close_reason', '')))

    def finish_backtest(self, results):
        self.append_to_log("Backtest hoàn tất!")
        self.bt_start_button.setEnabled(True)
        self.bt_start_button.setText("Bắt đầu Backtest")
        self.bt_progress_bar.setValue(100)
        
        self.bt_pnl_label.setText(f"${results.get('total_pnl', 0):.2f}")
        self.bt_winrate_label.setText(f"{results.get('win_rate', 0):.2f}%")
        self.bt_profit_factor_label.setText(f"{results.get('profit_factor', 'N/A')}")
        self.bt_max_drawdown_label.setText(f"{results.get('max_drawdown', 0):.2f}%")
