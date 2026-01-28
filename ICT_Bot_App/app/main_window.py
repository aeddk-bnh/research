import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox, QGroupBox
)
from PySide6.QtCore import QTimer

from app.worker import BotWorker
from app.config_manager import config_manager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ICT Trading Bot")
        self.setGeometry(100, 100, 1000, 700)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Status Bar
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Trạng thái: Đã dừng")
        self.platform_label = QLabel("Nền tảng: -")
        self.account_label = QLabel("Tài khoản: -")
        self.pnl_label = QLabel("P/L: -")
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.platform_label)
        self.status_bar.addPermanentWidget(self.account_label)
        self.status_bar.addPermanentWidget(self.pnl_label)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create tabs
        self.dashboard_tab = self.create_dashboard_tab()
        self.config_tab = self.create_config_tab()
        self.log_tab = self.create_log_tab()
        self.trades_tab = self.create_trades_tab()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.config_tab, "Cấu hình")
        self.tabs.addTab(self.log_tab, "Nhật ký")
        self.tabs.addTab(self.trades_tab, "Giao dịch")

        # Initialize worker
        self.worker = BotWorker()

        # Connect worker signals to UI slots
        self.worker.signals.log_message.connect(self.append_to_log)
        self.worker.signals.bot_status.connect(self.update_status_bar)
        self.worker.signals.market_bias.connect(self.update_market_bias)
        self.worker.signals.account_summary.connect(self.update_account_summary)
        self.worker.signals.new_position.connect(self.update_open_positions_table)
        self.worker.signals.position_closed.connect(self.update_history_table)
        self.worker.signals.kill_zone_status.connect(self.update_kz_status)

        # Initialize initial balance
        self.initial_balance = 0.0
        # Initialize initial balance
        self.initial_balance = 0.0
        # Open log file
        import os
        self.log_file_path = config_manager.get('logging.log_file', 'bot.log') or 'bot.log' # Ensure it's a string
        # Ensure the directory exists
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_file_handle = open(self.log_file_path, 'a', encoding='utf-8')
        # Timer for periodic updates (e.g., P/L, account balance)
        self.timer = QTimer()
        self.timer.timeout.connect(self.periodic_update)
        self.timer.start(5000) # Update every 5 seconds

    def create_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Control Group
        control_group = QGroupBox("Điều khiển")
        control_layout = QHBoxLayout(control_group)
        self.start_stop_button = QPushButton("Bắt đầu Bot")
        self.start_stop_button.clicked.connect(self.toggle_bot)
        control_layout.addWidget(self.start_stop_button)
        layout.addWidget(control_group)

        # Status Group
        status_group = QGroupBox("Trạng thái")
        status_layout = QFormLayout(status_group)
        self.bot_status_label = QLabel("Đang dừng")
        self.bias_label = QLabel("-")
        self.kz_status_label = QLabel("-")
        status_layout.addRow("Trạng thái Bot:", self.bot_status_label)
        status_layout.addRow("Xu hướng (Bias):", self.bias_label)
        status_layout.addRow("Kill Zone:", self.kz_status_label)
        layout.addWidget(status_group)

        # Account Group
        account_group = QGroupBox("Tài khoản")
        account_layout = QFormLayout(account_group)
        self.balance_label = QLabel("$0.00")
        self.pnl_session_label = QLabel("$0.00")
        account_layout.addRow("Số dư:", self.balance_label)
        account_layout.addRow("P/L Phiên:", self.pnl_session_label)
        layout.addWidget(account_group)

        # Spacer
        layout.addStretch()

        return widget

    def create_config_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # Platform
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["mt5", "binance"])
        self.platform_combo.setCurrentText(config_manager.get('platform', 'mt5'))
        layout.addRow("Nền tảng:", self.platform_combo)

        # MT5 Config
        mt5_group = QGroupBox("Cấu hình MT5")
        mt5_layout = QFormLayout(mt5_group)
        self.mt5_login_input = QLineEdit(str(config_manager.get('mt5.login', '')))
        self.mt5_password_input = QLineEdit(config_manager.get('mt5.password', ''))
        self.mt5_server_input = QLineEdit(config_manager.get('mt5.server', ''))
        self.mt5_path_input = QLineEdit(config_manager.get('mt5.path', ''))
        self.mt5_symbol_input = QLineEdit(config_manager.get('mt5.symbol', ''))
        self.mt5_password_input.setEchoMode(QLineEdit.Password)
        mt5_layout.addRow("Login:", self.mt5_login_input)
        mt5_layout.addRow("Password:", self.mt5_password_input)
        mt5_layout.addRow("Server:", self.mt5_server_input)
        mt5_layout.addRow("Path:", self.mt5_path_input)
        mt5_layout.addRow("Symbol:", self.mt5_symbol_input)
        layout.addWidget(mt5_group)

        # Binance Config
        binance_group = QGroupBox("Cấu hình Binance")
        binance_layout = QFormLayout(binance_group)
        self.binance_api_key_input = QLineEdit(config_manager.get('binance.api_key', ''))
        self.binance_secret_key_input = QLineEdit(config_manager.get('binance.secret_key', ''))
        self.binance_symbol_input = QLineEdit(config_manager.get('binance.symbol', ''))
        self.binance_secret_key_input.setEchoMode(QLineEdit.Password)
        binance_layout.addRow("API Key:", self.binance_api_key_input)
        binance_layout.addRow("Secret Key:", self.binance_secret_key_input)
        binance_layout.addRow("Symbol:", self.binance_symbol_input)
        layout.addWidget(binance_group)

        # Trading Config
        trading_group = QGroupBox("Giao dịch")
        trading_layout = QFormLayout(trading_group)
        self.symbol_input = QLineEdit(config_manager.get('trading.symbol', ''))
        self.risk_spinbox = QDoubleSpinBox()
        self.risk_spinbox.setRange(0.1, 100.0)
        self.risk_spinbox.setValue(config_manager.get('trading.risk_percent_per_trade', 1.0))
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
        header.setSectionResizeMode(QHeaderView.Stretch)
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
        header_hist.setSectionResizeMode(QHeaderView.Stretch)
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
            # Không gọi wait() ở đây vì nó sẽ block UI
            self.start_stop_button.setText("Bắt đầu Bot")
            self.status_label.setText("Trạng thái: Đang dừng...")
        else:
            # Khởi tạo lại worker để đảm bảo trạng thái sạch
            # (tránh lỗi nếu người dùng nhấn Start sau khi Stop mà thread cũ chưa thực sự kết thúc)
            if hasattr(self, 'worker') and self.worker.isRunning():
                return # Tránh trường hợp nhấn nhanh 2 lần
            self.worker = BotWorker()
            self.worker.signals.log_message.connect(self.append_to_log)
            self.worker.signals.bot_status.connect(self.update_status_bar)
            self.worker.signals.market_bias.connect(self.update_market_bias)
            self.worker.signals.account_summary.connect(self.update_account_summary)
            self.worker.signals.new_position.connect(self.update_open_positions_table)
            self.worker.start()
            self.start_stop_button.setText("Dừng Bot")
            self.status_label.setText("Trạng thái: Đang chạy")

    def append_to_log(self, message):
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{now}] {message}"
        self.log_text_edit.append(formatted_message)
        if self.log_file_handle:
            self.log_file_handle.write(formatted_message + '\\n')
            self.log_file_handle.flush() # Ensure it's written immediately

    def update_status_bar(self, status):
        self.bot_status_label.setText(status)
        self.status_label.setText(f"Trạng thái: {status}")

    def update_market_bias(self, bias):
        self.bias_label.setText(bias)

    def update_account_summary(self, summary):
        self.balance_label.setText(f"${summary.get('balance', 0):.2f}")
        self.pnl_session_label.setText(f"${summary.get('pnl', 0):.2f}")

    def update_kz_status(self, kz_info):
        self.kz_status_label.setText(kz_info)

    def update_open_positions_table(self, position_data):
        row_position = self.open_positions_table.rowCount()
        self.open_positions_table.insertRow(row_position)
        self.open_positions_table.setItem(row_position, 0, QTableWidgetItem(str(position_data.get('id', 'N/A'))))
        self.open_positions_table.setItem(row_position, 1, QTableWidgetItem(position_data.get('symbol', '')))
        self.open_positions_table.setItem(row_position, 2, QTableWidgetItem(position_data.get('side', '')))
        self.open_positions_table.setItem(row_position, 3, QTableWidgetItem(str(position_data.get('quantity', 0))))
        self.open_positions_table.setItem(row_position, 4, QTableWidgetItem(f"{position_data.get('entry_price', 0):.5f}"))
        self.open_positions_table.setItem(row_position, 5, QTableWidgetItem(f"{position_data.get('sl', 0):.5f}"))
        self.open_positions_table.setItem(row_position, 6, QTableWidgetItem(f"{position_data.get('tp', 0):.5f}"))

    def update_history_table(self, position_id, close_data):
        # Tìm hàng có ID khớp trong bảng "Lệnh đang mở"
        for row in range(self.open_positions_table.rowCount()):
            item = self.open_positions_table.item(row, 0) # Cột ID
            if item and item.text() == str(position_id):
                # Lấy dữ liệu từ hàng đó
                closed_item_data = {}
                for col in range(self.open_positions_table.columnCount()):
                    header_item = self.open_positions_table.horizontalHeaderItem(col)
                    item = self.open_positions_table.item(row, col)
                    if header_item and item:
                        header = header_item.text()
                        closed_item_data[header.lower().replace(" ", "_")] = item.text()
                
                # Thêm dữ liệu vào bảng "Lịch sử giao dịch"
                history_row = self.history_table.rowCount()
                self.history_table.insertRow(history_row)
                
                # Giả sử dữ liệu close_data có 'exit_price' và 'pnl'
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

                # Xóa hàng khỏi bảng "Lệnh đang mở"
                self.open_positions_table.removeRow(row)
                self.append_to_log(f"Lệnh {position_id} đã được chuyển sang lịch sử.")
                break

    def periodic_update(self):
        # Fetch live data from the connector if bot is running
        if self.worker and self.worker.isRunning() and self.worker.connector:
            current_balance = self.worker.connector.get_account_balance()
            if current_balance is not None:
                # Calculate P&L based on initial balance
                if self.initial_balance == 0.0:
                    self.initial_balance = current_balance
                pnl = current_balance - self.initial_balance
                # Update UI
                self.update_account_summary({'balance': current_balance, 'pnl': pnl})
                self.append_to_log(f"Cập nhật tài khoản: Balance=${current_balance:.2f}, P&L=${pnl:.2f}")
            else:
                self.append_to_log("Không thể cập nhật tài khoản.")
        else:
            # Bot không chạy, có thể hiển thị thông báo hoặc giữ nguyên
            pass

    def save_config(self):
        try:
            # Validate and convert MT5 Login
            mt5_login_text = self.mt5_login_input.text()
            if mt5_login_text:
                mt5_login = int(mt5_login_text)
            else:
                mt5_login = 0 # Default value if empty

            # Validate and convert MT5 Password
            mt5_password = self.mt5_password_input.text()
            if not mt5_password:
                self.append_to_log("Cảnh báo: Mật khẩu MT5 trống.")

            # Validate and convert Risk Percent
            risk_percent = self.risk_spinbox.value()
            if risk_percent <= 0:
                self.append_to_log("Cảnh báo: Tỷ lệ rủi ro nên lớn hơn 0.")

            # Set all config values
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
        except ValueError as e:
            self.append_to_log(f"Lỗi: Dữ liệu không hợp lệ. Vui lòng kiểm tra lại các trường số. Chi tiết: {e}")
        except Exception as e:
            self.append_to_log(f"Lỗi khi lưu cấu hình: {e}")

    def clear_log(self):
        self.log_text_edit.clear()

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ."""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, 'Thoát ứng dụng',
                                    'Bạn có chắc chắn muốn đóng ứng dụng?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.append_to_log("Đóng ứng dụng...")
            if self.log_file_handle:
                self.log_file_handle.close()
            # Đảm bảo worker cũng được dừng
            if self.worker.isRunning():
                self.worker.stop()
            event.accept()
        else:
            event.ignore()

    def simulate_close_position(self):
        # Chọn một lệnh ngẫu nhiên từ bảng "Mở"
        if self.open_positions_table.rowCount() == 0:
            self.append_to_log("Không có lệnh nào để đóng.")
            return
        
        row_to_close = self.open_positions_table.rowCount() - 1 # Đóng lệnh cuối cùng
        item = self.open_positions_table.item(row_to_close, 0)
        if not item:
            self.append_to_log("Không thể lấy ID lệnh để đóng.")
            return
        position_id = item.text()
        
        # Tạo dữ liệu đóng lệnh giả lập
        import random
        closed_data = {
            'exit_price': random.uniform(30000, 40000),
            'pnl': random.uniform(-100, 100)
        }
        
        # Gọi hàm xử lý đóng lệnh
        self.update_history_table(position_id, closed_data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
