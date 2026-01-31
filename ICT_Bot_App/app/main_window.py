import sys
import os
import subprocess
import traceback
import platform
import random
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
        self.setGeometry(100, 100, 1000, 750)

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

        # Tabs initialization (order matters)
        self.dashboard_tab = self.create_dashboard_tab()
        self.platform_tab = self.create_platform_tab()
        self.strategy_tab = self.create_strategy_tab()
        self.log_tab = self.create_log_tab()
        self.trades_tab = self.create_trades_tab()
        self.backtesting_tab = self.create_backtesting_tab()

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
        
        # Log file setup
        log_file_path = str(config_manager.get('logging.log_file', 'bot.log'))
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file_handle = open(log_file_path, 'a', encoding='utf-8')

        # Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.periodic_update)
        self.timer.start(5000)

        self.kz_ui_timer = QTimer(self)
        self.kz_ui_timer.timeout.connect(self.update_kz_status_from_timer)
        self.kz_ui_timer.start(10000)

        # Initial data loading
        self.update_kz_status_from_timer()
        self._update_platform_info_from_config()
        
        # Symbol list initialization
        QTimer.singleShot(1000, self._update_symbol_list)
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
        color = "green" if status == "Đã kết nối" else "orange" if "..." in status else "red"
        self.connection_status_label.setStyleSheet(f"color: {color};")

    def _update_platform_info_from_config(self):
        platform_name = str(config_manager.get('platform', 'mt5')).upper()
        self.platform_label.setText(f"Nền tảng: {platform_name}")
        if platform_name == 'MT5':
            login = config_manager.get('mt5.login', 'N/A')
            self.account_label.setText(f"Tài khoản: {login}")
        else:
            symbol = config_manager.get('binance.symbol', 'N/A')
            self.account_label.setText(f"Cặp: {symbol}")

    def create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Control
        control_group = QGroupBox("Điều khiển")
        control_layout = QHBoxLayout(control_group)
        self.start_stop_button = QPushButton("Bắt đầu Bot")
        self.start_stop_button.clicked.connect(self.toggle_bot)
        control_layout.addWidget(self.start_stop_button)
        layout.addWidget(control_group)

        # Status
        status_group = QGroupBox("Trạng thái hiện tại")
        status_layout = QFormLayout(status_group)
        self.bot_status_label = QLabel("Đang dừng")
        self.bias_label = QLabel("-")
        self.kz_status_label = QLabel("-")
        status_layout.addRow("Bot:", self.bot_status_label)
        status_layout.addRow("Xu hướng (HTF):", self.bias_label)
        status_layout.addRow("Kill Zone:", self.kz_status_label)
        layout.addWidget(status_group)

        # Account
        account_group = QGroupBox("Tài khoản")
        account_layout = QFormLayout(account_group)
        self.balance_label = QLabel("$0.00")
        self.pnl_session_label = QLabel("$0.00")
        account_layout.addRow("Số dư:", self.balance_label)
        account_layout.addRow("P/L Phiên:", self.pnl_session_label)
        layout.addWidget(account_group)

        # KZ Table
        kz_group = QGroupBox("Lịch Kill Zone (UTC+7)")
        kz_layout = QVBoxLayout(kz_group)
        self.kz_schedule_table = QTableWidget()
        self.kz_schedule_table.setColumnCount(4)
        self.kz_schedule_table.setHorizontalHeaderLabels(["Name", "EST", "UTC+7", "Status"])
        self.kz_schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.kz_schedule_table.setMaximumHeight(180)
        kz_layout.addWidget(self.kz_schedule_table)
        self._populate_kill_zone_table()
        layout.addWidget(kz_group)
        
        layout.addStretch()
        return widget

    def _populate_kill_zone_table(self):
        try:
            kz_list = get_all_kill_zones_with_utc7()
            self.kz_schedule_table.setRowCount(len(kz_list))
            for row, kz in enumerate(kz_list):
                self.kz_schedule_table.setItem(row, 0, QTableWidgetItem(kz['name']))
                self.kz_schedule_table.setItem(row, 1, QTableWidgetItem(f"{kz['est_start']} - {kz['est_end']}"))
                utc7 = f"{kz['utc7_start']} - {kz['utc7_end']}"
                if kz.get('utc7_start_next_day') or kz.get('utc7_end_next_day'): utc7 += " (+1d)"
                self.kz_schedule_table.setItem(row, 2, QTableWidgetItem(utc7))
                self.kz_schedule_table.setItem(row, 3, QTableWidgetItem("ON" if kz['enabled'] else "OFF"))
        except Exception: pass

    def create_platform_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["mt5", "binance"])
        self.platform_combo.setCurrentText(str(config_manager.get('platform', 'mt5')))
        layout.addRow("Nền tảng:", self.platform_combo)

        # MT5
        mt5_group = QGroupBox("Cài đặt MT5")
        mt5_layout = QFormLayout(mt5_group)
        self.mt5_login_input = QLineEdit(str(config_manager.get('mt5.login', '')))
        self.mt5_password_input = QLineEdit(str(config_manager.get('mt5.password', '')))
        self.mt5_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mt5_server_input = QLineEdit(str(config_manager.get('mt5.server', '')))
        self.mt5_path_input = QLineEdit(str(config_manager.get('mt5.path', '')))
        
        mt5_layout.addRow("Login ID:", self.mt5_login_input)
        mt5_layout.addRow("Password:", self.mt5_password_input)
        mt5_layout.addRow("Server:", self.mt5_server_input)
        mt5_layout.addRow("Path to terminal64.exe:", self.mt5_path_input)
        
        self.install_ea_btn = QPushButton("Tự động cài đặt EA Chụp Ảnh vào MT5")
        self.install_ea_btn.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold;")
        self.install_ea_btn.clicked.connect(self.auto_install_ea)
        mt5_layout.addRow(self.install_ea_btn)
        layout.addWidget(mt5_group)

        # Binance
        binance_group = QGroupBox("Cài đặt Binance")
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
        
        # Timeframes
        tf_group = QGroupBox("Cấu trúc Thời gian")
        tf_layout = QFormLayout(tf_group)
        options = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']
        self.htf_timeframe_combo = QComboBox()
        self.htf_timeframe_combo.addItems(options)
        self.htf_timeframe_combo.setCurrentText(config_manager.get('trading.htf_timeframe', 'H4') or 'H4')
        
        self.main_timeframe_combo = QComboBox()
        self.main_timeframe_combo.addItems(options)
        self.main_timeframe_combo.setCurrentText(config_manager.get('trading.timeframe', 'M15') or 'M15')
        
        self.ltf_timeframe_combo = QComboBox()
        self.ltf_timeframe_combo.addItems(options)
        self.ltf_timeframe_combo.setCurrentText(config_manager.get('trading.timeframe_smaller', 'M1') or 'M1')
        
        tf_layout.addRow("Higher TF (Bias):", self.htf_timeframe_combo)
        tf_layout.addRow("Main TF (Setup):", self.main_timeframe_combo)
        tf_layout.addRow("Lower TF (Entry):", self.ltf_timeframe_combo)
        layout.addWidget(tf_group)

        # Risk & Symbol
        risk_group = QGroupBox("Quản lý Rủi ro & Cặp giao dịch")
        risk_layout = QFormLayout(risk_group)
        self.symbol_input = self._create_searchable_combobox()
        self.risk_spinbox = QDoubleSpinBox()
        self.risk_spinbox.setRange(0.1, 10.0)
        self.risk_spinbox.setValue(float(config_manager.get('trading.risk_percent_per_trade', 1.0) or 1.0))
        self.risk_spinbox.setSuffix(" %")
        
        self.tp_rr_spinbox = QDoubleSpinBox()
        self.tp_rr_spinbox.setRange(0.5, 10.0)
        self.tp_rr_spinbox.setValue(float(config_manager.get('trading.take_profit_rr', 2.0) or 2.0))
        
        self.sl_buffer_spinbox = QDoubleSpinBox()
        self.sl_buffer_spinbox.setRange(0, 500)
        self.sl_buffer_spinbox.setValue(float(config_manager.get('trading.sl_buffer_points', 50.0) or 50.0))

        risk_layout.addRow("Cặp giao dịch:", self.symbol_input)
        risk_layout.addRow("Rủi ro mỗi lệnh:", self.risk_spinbox)
        risk_layout.addRow("Take Profit (R:R):", self.tp_rr_spinbox)
        risk_layout.addRow("SL Buffer (points):", self.sl_buffer_spinbox)
        layout.addWidget(risk_group)

        # Modules
        adv_group = QGroupBox("Modules Nâng cao")
        adv_layout = QVBoxLayout(adv_group)
        self.ote_checkbox = QCheckBox("Bật OTE Fibonacci (62-79%)")
        self.ote_checkbox.setChecked(bool(config_manager.get('trading.ote_enabled', True)))
        self.partial_profit_checkbox = QCheckBox("Bật Chốt lời từng phần (Partial Profits)")
        self.partial_profit_checkbox.setChecked(bool(config_manager.get('trading.partial_profits_enabled', False)))
        adv_layout.addWidget(self.ote_checkbox)
        adv_layout.addWidget(self.partial_profit_checkbox)
        layout.addWidget(adv_group)

        self.save_config_button = QPushButton("LƯU TẤT CẢ CẤU HÌNH")
        self.save_config_button.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 40px;")
        self.save_config_button.clicked.connect(self.save_config)
        layout.addWidget(self.save_config_button)

        return widget

    def _create_searchable_combobox(self):
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        return combo

    def _update_symbol_list(self):
        self.append_to_log("Đang tải danh sách symbol từ nền tảng...")
        platform_name = self.platform_combo.currentText()
        
        class SymbolFetcher(QThread):
            finished = Signal(list)
            def run(self):
                symbols = []
                try:
                    conn = get_connector(platform_name)
                    if conn and conn.connect():
                        symbols = conn.get_all_tradable_symbols()
                        conn.disconnect()
                except Exception: pass
                self.finished.emit(symbols)

        def on_finished(symbols):
            if not symbols:
                self.append_to_log(f"Không thể tải symbol cho {platform_name.upper()}.")
                return
            self.append_to_log(f"Đã tải thành công {len(symbols)} symbols.")
            for combo in [self.symbol_input, self.bt_symbol_input]:
                current = combo.currentText()
                combo.clear()
                combo.addItems(symbols)
                completer = QCompleter(symbols)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                combo.setCompleter(completer)
                if current in symbols: 
                    combo.setCurrentText(current)
                else: 
                    symbol_from_config = config_manager.get('trading.symbol', symbols[0])
                    combo.setCurrentText(symbol_from_config if symbol_from_config else symbols[0])

        self.fetcher = SymbolFetcher()
        self.fetcher.finished.connect(on_finished)
        self.fetcher.start()

    def create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        bottom = QHBoxLayout()
        self.log_verbose_checkbox = QCheckBox("Ghi log chi tiết")
        self.log_verbose_checkbox.setChecked(bool(config_manager.get('logging.enable_logging', True)))
        self.log_verbose_checkbox.stateChanged.connect(self.toggle_verbose_logging)
        clear_btn = QPushButton("Xóa trắng")
        clear_btn.clicked.connect(lambda: self.log_text_edit.clear())
        bottom.addWidget(self.log_verbose_checkbox)
        bottom.addStretch()
        bottom.addWidget(clear_btn)
        layout.addWidget(self.log_text_edit)
        layout.addLayout(bottom)
        return widget

    def toggle_verbose_logging(self, state):
        config_manager.set('logging.enable_logging', state == 2)
        config_manager.save_config()
        self.append_to_log(f"Ghi log chi tiết: {'BẬT' if state == 2 else 'TẮT'}")

    def create_trades_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Open
        open_group = QGroupBox("Vị thế đang mở")
        open_layout = QVBoxLayout(open_group)
        self.open_positions_table = QTableWidget()
        self.open_positions_table.setColumnCount(7)
        self.open_positions_table.setHorizontalHeaderLabels(["ID", "Cặp", "Loại", "Vol", "Entry", "SL", "TP"])
        self.open_positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        open_layout.addWidget(self.open_positions_table)
        
        # History
        hist_group = QGroupBox("Lịch sử giao dịch")
        hist_layout = QVBoxLayout(hist_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels(["ID", "Cặp", "Loại", "Vol", "Entry", "Exit", "SL", "TP", "P/L"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hist_layout.addWidget(self.history_table)
        
        layout.addWidget(open_group)
        layout.addWidget(hist_group)
        return widget

    def create_backtesting_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        left = QGroupBox("Cấu hình Backtest")
        left_layout = QFormLayout(left)
        self.bt_symbol_input = self._create_searchable_combobox()
        self.bt_timeframe_combo = QComboBox()
        self.bt_timeframe_combo.addItems(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'])
        self.bt_start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.bt_end_date = QDateEdit(QDate.currentDate())
        self.bt_start_btn = QPushButton("Bắt đầu")
        self.bt_start_btn.clicked.connect(self.start_backtest)
        
        left_layout.addRow("Cặp tiền:", self.bt_symbol_input)
        left_layout.addRow("Timeframe:", self.bt_timeframe_combo)
        left_layout.addRow("Từ ngày:", self.bt_start_date)
        left_layout.addRow("Đến ngày:", self.bt_end_date)
        left_layout.addRow(self.bt_start_btn)
        
        right = QGroupBox("Kết quả")
        right_layout = QVBoxLayout(right)
        self.bt_progress = QProgressBar()
        right_layout.addWidget(self.bt_progress)
        self.bt_trades_table = QTableWidget()
        self.bt_trades_table.setColumnCount(8)
        self.bt_trades_table.setHorizontalHeaderLabels(["Time", "Side", "Entry", "Exit", "SL", "TP", "P/L", "Reason"])
        self.bt_trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.bt_trades_table)
        
        layout.addWidget(left, 1)
        layout.addWidget(right, 3)
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
        self.log_account_balance("VÀO LỆNH")

    def log_account_balance(self, context: str):
        if self.worker.isRunning() and self.worker.connector:
            balance = self.worker.connector.get_account_balance()
            if balance: self.append_to_log(f"[{context}] Cập nhật tài khoản: ${balance:.2f}")

    def update_history_table(self, pos_id: str, data: dict):
        for row in range(self.open_positions_table.rowCount()):
            item = self.open_positions_table.item(row, 0)
            if item and item.text() == str(pos_id):
                h_row = self.history_table.rowCount()
                self.history_table.insertRow(h_row)
                for c in range(7):
                    cell_item = self.open_positions_table.item(row, c)
                    self.history_table.setItem(h_row, c, QTableWidgetItem(cell_item.text() if cell_item else ""))
                self.history_table.setItem(h_row, 5, QTableWidgetItem(f"{data.get('exit_price', 0):.5f}"))
                self.history_table.setItem(h_row, 8, QTableWidgetItem(f"{data.get('pnl', 0):.2f}"))
                self.open_positions_table.removeRow(row)
                self.log_account_balance("ĐÓNG LỆNH")
                break

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
            config_manager.set('mt5.symbol', self.symbol_input.currentText())
            config_manager.set('binance.symbol', self.symbol_input.currentText())
            config_manager.save_config()
            self.append_to_log("Cấu hình đã được lưu thành công!")
        except Exception as e:
            self.append_to_log(f"Lỗi khi lưu cấu hình: {e}")

    def auto_install_ea(self):
        self.append_to_log("[AUTO-INSTALL] Đang bắt đầu cài đặt EA...")
        try:
            mt5_path = self.mt5_path_input.text()
            if not mt5_path or not os.path.exists(mt5_path):
                QMessageBox.critical(self, "Lỗi", "Đường dẫn terminal64.exe không hợp lệ.")
                return
            
            terminal_dir = os.path.dirname(mt5_path)
            metaeditor = os.path.join(terminal_dir, "metaeditor64.exe")
            
            if not os.path.exists(metaeditor):
                self.append_to_log(f"[LỖI] Không tìm thấy MetaEditor tại: {metaeditor}")
                return

            appdata = os.getenv('APPDATA')
            if not appdata:
                self.append_to_log("[LỖI] Không thể truy cập thư mục APPDATA.")
                return

            base_terminal = os.path.join(appdata, 'MetaQuotes', 'Terminal')
            
            if not os.path.exists(base_terminal):
                self.append_to_log("[LỖI] Không tìm thấy thư mục dữ liệu MetaQuotes.")
                return

            # Tìm thư mục MQL5 của terminal hiện tại
            data_dirs = []
            self.append_to_log("Đang tìm kiếm thư mục dữ liệu MT5...")
            
            # Quét tất cả các folder terminal để tìm folder hợp lệ nhất
            for d in os.listdir(base_terminal):
                p = os.path.join(base_terminal, d)
                if os.path.isdir(p):
                    mql5_path = os.path.join(p, "MQL5")
                    if os.path.exists(mql5_path):
                        # Lấy thời gian sửa đổi cuối cùng để ưu tiên folder đang dùng
                        mtime = os.path.getmtime(p)
                        
                        # Kiểm tra origin.txt (nếu có)
                        is_exact_match = False
                        origin_file = os.path.join(p, "origin.txt")
                        if os.path.exists(origin_file):
                            try:
                                with open(origin_file, 'r', encoding='utf-16le') as f:
                                    origin_path = f.read().strip().replace('\x00', '')
                                    if origin_path.lower().rstrip('\\') == terminal_dir.lower().rstrip('\\'):
                                        is_exact_match = True
                            except Exception: pass
                        
                        data_dirs.append({
                            'path': mql5_path,
                            'mtime': mtime,
                            'exact': is_exact_match
                        })
            
            # Sắp xếp: Ưu tiên exact match, sau đó đến folder mới nhất
            data_dirs.sort(key=lambda x: (x['exact'], x['mtime']), reverse=True)

            if not data_dirs:
                self.append_to_log("[LỖI] Không thể xác định thư mục MQL5 của MT5 này.")
                return
            
            data_dir = data_dirs[0]['path']
            self.append_to_log(f"Sử dụng thư mục dữ liệu: {os.path.dirname(data_dir)}")

            # Kiểm tra xem có thư mục con 'Advisors' không
            base_experts_dir = os.path.join(data_dir, "Experts")
            advisors_subdir = os.path.join(base_experts_dir, "Advisors")
            
            target_install_dir = base_experts_dir
            if os.path.isdir(advisors_subdir):
                self.append_to_log("Phát hiện thư mục 'Advisors' chuyên dụng. Sẽ cài đặt vào đó.")
                target_install_dir = advisors_subdir

            experts_dir = os.path.join(target_install_dir, "ICTBot")
            os.makedirs(experts_dir, exist_ok=True)
            
            ea_path = os.path.join(experts_dir, "ScreenShotEA.mq5")
            with open(ea_path, "w", encoding="utf-8") as f:
                f.write(self._get_ea_source_code())
            
            self.append_to_log(f"Đã tạo mã nguồn tại: {ea_path}")
            
            self.append_to_log("Đang biên dịch... (vui lòng đợi)")
            log_file = os.path.join(experts_dir, "compile.log")
            
            # Chạy biên dịch (dùng dấu ngoặc kép cho path có khoảng trắng)
            cmd = f'"{metaeditor}" /compile:"{ea_path}" /log:"{log_file}"'
            self.append_to_log(f"Lệnh: {cmd}")
            
            process = subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            process.wait(timeout=30)
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-16le') as f:
                        compile_output = f.read()
                    self.append_to_log("--- KẾT QUẢ BIÊN DỊCH ---")
                    self.append_to_log(compile_output.strip())
                    self.append_to_log("-------------------------")
                except Exception as e:
                    self.append_to_log(f"Không thể đọc file log biên dịch: {e}")

            ex5_path = ea_path.replace(".mq5", ".ex5")
            if os.path.exists(ex5_path):
                QMessageBox.information(self, "Thành công", 
                    f"Đã cài đặt thành công!\\n\\nFile: {os.path.basename(ex5_path)}\\nThư mục: {experts_dir}\\n\\nHãy chuột phải vào 'Expert Advisors' trong MT5 -> Refresh.")
            else:
                self.append_to_log("[LỖI] File .ex5 không được tạo ra. Kiểm tra log biên dịch ở trên.")
                
        except Exception as e:
            self.append_to_log(f"[CRITICAL ERROR] {str(e)}")
            traceback.print_exc()

    def _get_ea_source_code(self):
        return """// ScreenShotEA
#property version "1.00"
#property strict
input string Folder="ICT_Bot_Signals";
input string Journal="ICT_Bot_Journal";
int OnInit(){ EventSetTimer(1); FolderCreate(Folder,0); FolderCreate(Journal,0); return(INIT_SUCCEEDED); }
void OnTimer(){
   string name; long handle=FileFindFirst(Folder+"\\\\*.txt",name,0);
   if(handle!=INVALID_HANDLE){
      do{
         string id=StringSubstr(name,10,StringLen(name)-14);
         if(ChartScreenShot(0,Journal+"\\\\trade_"+id+"_entry.png",1280,720)) FileDelete(Folder+"\\\\"+name,0);
      }while(FileFindNext(handle,name));
      FileFindClose(handle);
   }
}"""

    def start_backtest(self):
        params = {
            'symbol': self.bt_symbol_input.currentText(),
            'timeframe': self.bt_timeframe_combo.currentText(),
            'start_date': self.bt_start_date.date().toPython(),
            'end_date': self.bt_end_date.date().toPython(),
        }
        self.bt_worker = BacktestWorker(params)
        self.bt_worker.signals.progress.connect(self.bt_progress.setValue)
        self.bt_worker.signals.log_message.connect(self.append_to_log)
        self.bt_worker.start()
        self.bt_start_btn.setEnabled(False)

    def closeEvent(self, event: QCloseEvent):
        if hasattr(self, 'log_file_handle'): self.log_file_handle.close()
        if self.worker.isRunning(): self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
