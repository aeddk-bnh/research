import sys
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow

def main():
    """Hàm chính để khởi chạy ứng dụng."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
