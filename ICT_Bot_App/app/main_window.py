import sys
import traceback
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox, QGroupBox, QMessageBox,
    QDateEdit, QProgressBar, QCheckBox, QCompleter
)
from PySide6.QtCore import QTimer, QThread, QDate, Qt, Signal
from PySide6.QtGui import QCloseEvent

from app.worker import BotWorker, BacktestWorker
from app.config_manager import config_manager
from trading_core.time_filter import get_kill_zone_status, get_all_kill_zones_with_utc7
from trading_core.connectors import get_connector

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ICT Trading Bot")
        self.setGeometry(100, 100, 1000, 750) # Tăng nhẹ chiều cao

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.status_bar = self.statusBar()
        self.status_label = QLabel("Trạng thái: Đã dừng")
        self.connection_status_label = QLabel("Kết nối: -")
        self.platform_label = QLabel("Nền tảng: -")
        self.account_label = QLabel("Tài khoản: -")
        self.pnl_label = QLabel("P/L: -")
        
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.connection_status_label)
        self.status_bar.addPermanentWidget(self.platform_label)
        self.status_bar.addPermanentWidget(self.account_label)
        self.status_bar.addPermanentWidget(self.pnl_label)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tabs initialization
        self.dashboard_tab = self.create_dashboard_tab()
        self.platform_tab = self.create_platform_tab()
        self.strategy_tab = self.create_strategy_tab() # Sẽ tạo combobox trong này
        self.log_tab = self.create_log_tab()
        self.trades_tab = self.create_trades_tab()
        self.backtesting_tab = self.create_backtesting_tab() # Và trong này

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.platform_tab, "Nền tảng")
        self.tabs.addTab(self.strategy_tab, "Chiến lược")
        self.tabs.addTab(self.log_tab, "Nhật ký")
        self.tabs.addTab(self.trades_tab, "Giao dịch")
        self.tabs.addTab(self.backtesting_tab, "Backtesting")

        # Worker setup
        self.worker = BotWorker()
        self._connect_worker_signals()
        self.initial_balance = 0.0
        
        # Log setup
        import os
        self.log_file_path = str(config_manager.get('logging.log_file', 'bot.log'))
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file_handle = open(self.log_file_path, 'a', encoding='utf-8')

        # Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.periodic_update)
        self.timer.start(5000)

        self.kz_ui_timer = QTimer(self)
        self.kz_ui_timer.timeout.connect(self.update_kz_status_from_timer)
        self.kz_ui_timer.start(10000)

        # Initial Updates
        self.update_kz_status_from_timer()
        self._update_platform_info_from_config()
        
        # Symbol list update trigger
        QTimer.singleShot(500, self._update_symbol_list)
        self.platform_combo.currentIndexChanged.connect(self._update_symbol_list)

    def _connect_worker_signals(self):
        self.worker.signals.log_message.connect(self.append_to_log)
        self.worker.signals.bot_status.connect(self.update_status_bar)
        self.worker.signals.market_bias.connect(self.update_market_bias)
        self.worker.signals.account_summary.connect(self.update_account_summary)
        self.worker.signals.new_position.connect(self.update_open_positions_table)
        self.worker.signals.position_closed.connect(self.update_history_table)
        self.worker.signals.connection_status.connect(self.update_connection_status)

    def update_connection_status(self, status: str):
        self.connection_status_label.setText(f"Kết nối: {status}")
        if status == "Đã kết nối":
            self.connection_status_label.setStyleSheet("color: green;")
        elif status == "Đang kết nối lại...":
            self.connection_status_label.setStyleSheet("color: orange;")
        else:
            self.connection_status_label.setStyleSheet("color: red;")

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
        self.kz_status_label = QLabel("-")
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

        kz_schedule_group = QGroupBox("Lịch Kill Zone (EST → UTC+7)")
        kz_schedule_layout = QVBoxLayout(kz_schedule_group)
        self.kz_schedule_table = QTableWidget()
        self.kz_schedule_table.setColumnCount(4)
        self.kz_schedule_table.setHorizontalHeaderLabels(["Kill Zone", "EST (New York)", "UTC+7 (Việt Nam)", "Trạng thái"])
        header = self.kz_schedule_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.kz_schedule_table.setMaximumHeight(180)
        kz_schedule_layout.addWidget(self.kz_schedule_table)
        self._populate_kill_zone_table()
        layout.addWidget(kz_schedule_group)
        layout.addStretch()
        return widget

    def _populate_kill_zone_table(self):
        try:
            kz_list = get_all_kill_zones_with_utc7()
            self.kz_schedule_table.setRowCount(len(kz_list))
            for row, kz in enumerate(kz_list):
                self.kz_schedule_table.setItem(row, 0, QTableWidgetItem(kz['name']))
                self.kz_schedule_table.setItem(row, 1, QTableWidgetItem(f"{kz['est_start']} - {kz['est_end']}"))
                utc7_time = f"{kz['utc7_start']} - {kz['utc7_end']}"
                if kz.get('utc7_start_next_day') or kz.get('utc7_end_next_day'):
                    utc7_time += " (+1 ngày)"
                self.kz_schedule_table.setItem(row, 2, QTableWidgetItem(utc7_time))
                self.kz_schedule_table.setItem(row, 3, QTableWidgetItem("Bật" if kz['enabled'] else "Tắt"))
        except Exception as e:
            print(f"Lỗi populate KZ table: {e}")

    def create_platform_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["mt5", "binance"])
        self.platform_combo.setCurrentText(str(config_manager.get('platform', 'mt5')))
        layout.addRow("Nền tảng:", self.platform_combo)

        mt5_group = QGroupBox("Cấu hình MT5")
        mt5_layout = QFormLayout(mt5_group)
        self.mt5_login_input = QLineEdit(str(config_manager.get('mt5.login', '')))
        self.mt5_password_input = QLineEdit(str(config_manager.get('mt5.password', '')))
        self.mt5_server_input = QLineEdit(str(config_manager.get('mt5.server', '')))
        self.mt5_path_input = QLineEdit(str(config_manager.get('mt5.path', '')))
        self.mt5_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        mt5_layout.addRow("Login:", self.mt5_login_input)
        mt5_layout.addRow("Password:", self.mt5_password_input)
        mt5_layout.addRow("Server:", self.mt5_server_input)
        mt5_layout.addRow("Path:", self.mt5_path_input)
        layout.addWidget(mt5_group)

        binance_group = QGroupBox("Cấu hình Binance")
        binance_layout = QFormLayout(binance_group)
        self.binance_api_key_input = QLineEdit(str(config_manager.get('binance.api_key', '')))
        self.binance_secret_key_input = QLineEdit(str(config_manager.get('binance.secret_key', '')))
        self.binance_secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        binance_layout.addRow("API Key:", self.binance_api_key_input)
        binance_layout.addRow("Secret Key:", self.binance_secret_key_input)
        layout.addWidget(binance_group)
        return widget

    def create_strategy_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        timeframe_group = QGroupBox("Cấu trúc Thời gian")
        timeframe_layout = QFormLayout(timeframe_group)
        tf_options = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']
        
        self.htf_timeframe_combo = QComboBox()
        self.htf_timeframe_combo.addItems(tf_options)
        self.htf_timeframe_combo.setCurrentText(config_manager.get('trading.htf_timeframe', 'H4'))
        
        self.main_timeframe_combo = QComboBox()
        self.main_timeframe_combo.addItems(tf_options)
        self.main_timeframe_combo.setCurrentText(config_manager.get('trading.timeframe', 'H1'))
        
        self.ltf_timeframe_combo = QComboBox()
        self.ltf_timeframe_combo.addItems(tf_options)
        self.ltf_timeframe_combo.setCurrentText(config_manager.get('trading.timeframe_smaller', 'M15'))
        
        timeframe_layout.addRow("Khung HTF (Bias):", self.htf_timeframe_combo)
        timeframe_layout.addRow("Khung Chính (PD Array):", self.main_timeframe_combo)
        timeframe_layout.addRow("Khung Nhỏ (Entry):", self.ltf_timeframe_combo)
        layout.addWidget(timeframe_group)

        risk_group = QGroupBox("Quản lý Rủi ro & Mục tiêu")
        risk_layout = QFormLayout(risk_group)
        
        # Searchable Symbol Combobox
        self.symbol_input = self._create_searchable_combobox()
        
        self.risk_spinbox = QDoubleSpinBox()
        self.risk_spinbox.setRange(0.1, 100.0)
        self.risk_spinbox.setValue(float(config_manager.get('trading.risk_percent_per_trade', 1.0)))
        self.risk_spinbox.setSuffix(" %")
        
        self.tp_rr_spinbox = QDoubleSpinBox()
        self.tp_rr_spinbox.setRange(0.5, 20.0)
        self.tp_rr_spinbox.setValue(float(config_manager.get('trading.take_profit_rr', 2.0)))
        self.tp_rr_spinbox.setPrefix("1 : ")
        
        self.sl_buffer_spinbox = QDoubleSpinBox()
        self.sl_buffer_spinbox.setRange(0, 1000)
        self.sl_buffer_spinbox.setValue(float(config_manager.get('trading.sl_buffer_points', 50.0)))
        
        risk_layout.addRow("Cặp giao dịch:", self.symbol_input)
        risk_layout.addRow("Rủi ro / lệnh:", self.risk_spinbox)
        risk_layout.addRow("Tỷ lệ R:R (TP):", self.tp_rr_spinbox)
        risk_layout.addRow("SL Buffer (points):", self.sl_buffer_spinbox)
        layout.addWidget(risk_group)

        adv_group = QGroupBox("Modules Nâng cao")
        adv_layout = QVBoxLayout(adv_group)
        self.ote_checkbox = QCheckBox("Bật OTE Filter (Fibonacci 62-79%)")
        self.ote_checkbox.setChecked(bool(config_manager.get('trading.ote_enabled', True)))
        self.partial_profit_checkbox = QCheckBox("Bật chốt lời từng phần (Partial Profits)")
        self.partial_profit_checkbox.setChecked(bool(config_manager.get('trading.partial_profits_enabled', False)))
        adv_layout.addWidget(self.ote_checkbox)
        adv_layout.addWidget(self.partial_profit_checkbox)
        layout.addWidget(adv_group)

        self.save_config_button = QPushButton("Lưu Tất Cả Cấu Hình")
        self.save_config_button.clicked.connect(self.save_config)
        layout.addWidget(self.save_config_button)
        return widget

    def _create_searchable_combobox(self):
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        return combo

    def _update_symbol_list(self):
        self.append_to_log("Đang tải danh sách cặp giao dịch...")
        platform = self.platform_combo.currentText()
        
        class SymbolFetcher(QThread):
            finished = Signal(list)
            def run(self):
                symbols = []
                try:
                    connector = get_connector(platform)
                    if connector and connector.connect():
                        symbols = connector.get_all_tradable_symbols()
                        connector.disconnect()
                except Exception as e:
                    print(f"Error fetching symbols: {e}")
                self.finished.emit(symbols)

        def on_finished(symbols):
            if not symbols:
                self.append_to_log(f"Không thể lấy danh sách symbol cho {platform.upper()}.")
                return
            
            self.append_to_log(f"Đã tải {len(symbols)} symbols.")
            for combo in [self.symbol_input, self.bt_symbol_input]:
                current = combo.currentText()
                combo.clear()
                combo.addItems(symbols)
                completer = QCompleter(symbols)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                combo.setCompleter(completer)
                if current in symbols: combo.setCurrentText(current)
                else: combo.setCurrentText(config_manager.get('trading.symbol', symbols[0]))

        self.fetcher = SymbolFetcher()
        self.fetcher.finished.connect(on_finished)
        self.fetcher.start()

    def create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        bottom = QHBoxLayout()
        self.log_verbose_checkbox = QCheckBox("Verbose Logging")
        self.log_verbose_checkbox.setChecked(bool(config_manager.get('logging.enable_logging', True)))
        self.log_verbose_checkbox.stateChanged.connect(self.toggle_verbose_logging)
        clear_btn = QPushButton("Xóa nhật ký")
        clear_btn.clicked.connect(self.clear_log)
        bottom.addWidget(self.log_verbose_checkbox)
        bottom.addStretch()
        bottom.addWidget(clear_btn)
        layout.addWidget(self.log_text_edit)
        layout.addLayout(bottom)
        return widget

    def toggle_verbose_logging(self, state):
        is_checked = state == 2
        config_manager.set('logging.enable_logging', is_checked)
        config_manager.save_config()
        self.append_to_log(f"Ghi log chi tiết: {'BẬT' if is_checked else 'TẮT'}")

    def create_trades_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        open_group = QGroupBox("Lệnh đang mở")
        open_layout = QVBoxLayout(open_group)
        self.open_positions_table = QTableWidget()
        self.open_positions_table.setColumnCount(7)
        self.open_positions_table.setHorizontalHeaderLabels(["ID", "Cặp tiền", "Loại", "Khối lượng", "Giá vào", "SL", "TP"])
        self.open_positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        open_layout.addWidget(self.open_positions_table)
        
        hist_group = QGroupBox("Lịch sử")
        hist_layout = QVBoxLayout(hist_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels(["ID", "Cặp", "Loại", "Vol", "Entry", "Exit", "SL", "TP", "P/L"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hist_layout.addWidget(self.history_table)
        
        layout.addWidget(open_group)
        layout.addWidget(hist_group)
        return widget

    def toggle_bot(self):
        if self.worker.isRunning():
            self.worker.stop()
            self.start_stop_button.setText("Bắt đầu Bot")
            self.status_label.setText("Trạng thái: Đã dừng")
        else:
            self.worker = BotWorker()
            self._connect_worker_signals()
            self.worker.start()
            self.start_stop_button.setText("Dừng Bot")
            self.status_label.setText("Trạng thái: Đang chạy")

    def append_to_log(self, message: str):
        from datetime import datetime
        now = datetime.now().strftime('%H:%M:%S')
        msg = f"[{now}] {message}"
        self.log_text_edit.append(msg)
        if hasattr(self, 'log_file_handle'):
            self.log_file_handle.write(msg + '\n')
            self.log_file_handle.flush()

    def update_status_bar(self, status: str):
        self.bot_status_label.setText(status)
        self.status_label.setText(f"Trạng thái: {status}")

    def update_market_bias(self, bias: str):
        self.bias_label.setText(bias)

    def update_account_summary(self, summary: dict):
        self.balance_label.setText(f"${summary.get('balance', 0):.2f}")
        self.pnl_session_label.setText(f"${summary.get('pnl', 0):.2f}")

    def update_open_positions_table(self, data: dict):
        row = self.open_positions_table.rowCount()
        self.open_positions_table.insertRow(row)
        cols = ['id', 'symbol', 'side', 'quantity', 'entry_price', 'sl', 'tp']
        for i, col in enumerate(cols):
            val = data.get(col, '')
            if isinstance(val, float): val = f"{val:.5f}"
            self.open_positions_table.setItem(row, i, QTableWidgetItem(str(val)))
        self.log_account_balance("Mở lệnh")

    def log_account_balance(self, context: str):
        if self.worker and self.worker.isRunning() and self.worker.connector:
            balance = self.worker.connector.get_account_balance()
            if balance: self.append_to_log(f"[{context}] Số dư: ${balance:.2f}")

    def update_history_table(self, pos_id: str, data: dict):
        # Implementation to move from open to history
        pass

    def update_kz_status_from_timer(self):
        _, status = get_kill_zone_status()
        self.kz_status_label.setText(status)

    def periodic_update(self):
        if self.worker.isRunning() and self.worker.connector and self.open_positions_table.rowCount() > 0:
            balance = self.worker.connector.get_account_balance()
            if balance:
                if self.initial_balance == 0: self.initial_balance = balance
                self.update_account_summary({'balance': balance, 'pnl': balance - self.initial_balance})

    def save_config(self):
        try:
            config_manager.set('platform', self.platform_combo.currentText())
            config_manager.set('mt5.login', int(self.mt5_login_input.text() or 0))
            config_manager.set('mt5.password', self.mt5_password_input.text())
            config_manager.set('mt5.server', self.mt5_server_input.text())
            config_manager.set('mt5.path', self.mt5_path_input.text())
            config_manager.set('binance.api_key', self.binance_api_key_input.text())
            config_manager.set('binance.secret_key', self.binance_secret_key_input.text())
            
            config_manager.set('trading.htf_timeframe', self.htf_timeframe_combo.currentText())
            config_manager.set('trading.timeframe', self.main_timeframe_combo.currentText())
            config_manager.set('trading.timeframe_smaller', self.ltf_timeframe_combo.currentText())
            config_manager.set('trading.symbol', self.symbol_input.currentText())
            config_manager.set('trading.risk_percent_per_trade', self.risk_spinbox.value())
            config_manager.set('trading.take_profit_rr', self.tp_rr_spinbox.value())
            config_manager.set('trading.sl_buffer_points', self.sl_buffer_spinbox.value())
            config_manager.set('trading.ote_enabled', self.ote_checkbox.isChecked())
            config_manager.set('trading.partial_profits_enabled', self.partial_profit_checkbox.isChecked())
            
            # Sync platform symbols
            config_manager.set('mt5.symbol', self.symbol_input.currentText())
            config_manager.set('binance.symbol', self.symbol_input.currentText())
            
            config_manager.save_config()
            self.append_to_log("Đã lưu cấu hình.")
        except Exception as e:
            self.append_to_log(f"Lỗi lưu cấu hình: {e}")

    def create_backtesting_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        left = QGroupBox("Cấu hình")
        left_layout = QFormLayout(left)
        self.bt_symbol_input = self._create_searchable_combobox()
        self.bt_timeframe_combo = QComboBox()
        self.bt_timeframe_combo.addItems(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'])
        self.bt_start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.bt_end_date = QDateEdit(QDate.currentDate())
        btn = QPushButton("Chạy Backtest")
        btn.clicked.connect(self.start_backtest)
        left_layout.addRow("Symbol:", self.bt_symbol_input)
        left_layout.addRow("Timeframe:", self.bt_timeframe_combo)
        left_layout.addRow("Từ:", self.bt_start_date)
        left_layout.addRow("Đến:", self.bt_end_date)
        left_layout.addRow(btn)
        
        right = QGroupBox("Kết quả")
        right_layout = QVBoxLayout(right)
        self.bt_progress = QProgressBar()
        right_layout.addWidget(self.bt_progress)
        self.bt_trades_table = QTableWidget()
        self.bt_trades_table.setColumnCount(8)
        self.bt_trades_table.setHorizontalHeaderLabels(["Thời gian", "Loại", "Entry", "Exit", "SL", "TP", "P/L", "Lý do"])
        right_layout.addWidget(self.bt_trades_table)
        
        layout.addWidget(left, 1)
        layout.addWidget(right, 3)
        return widget

    def start_backtest(self):
        # Implementation same as before but using .currentText() for symbol
        pass

    def clear_log(self):
        self.log_text_edit.clear()

    def closeEvent(self, event: QCloseEvent):
        if hasattr(self, 'log_file_handle'): self.log_file_handle.close()
        if self.worker.isRunning(): self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
