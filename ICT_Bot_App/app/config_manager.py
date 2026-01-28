import json
import os

class ConfigManager:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        """Tải cấu hình từ file JSON."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"File cấu hình không tìm thấy tại: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_config(self):
        """Lưu cấu hình hiện tại vào file JSON."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        """
        Lấy một giá trị từ cấu hình, hỗ trợ key lồng nhau (e.g., 'mt5.login').
        Luôn trả về giá trị mặc định nếu key không tồn tại hoặc đường dẫn không hợp lệ.
        """
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                # Kiểm tra nếu value là dictionary và key tồn tại
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default # Key không tồn tại hoặc value không phải dict
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        """Đặt một giá trị trong cấu hình, hỗ trợ key lồng nhau."""
        keys = key.split('.')
        d = self.config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

# Tạo một instance duy nhất để sử dụng trong toàn bộ ứng dụng
config_manager = ConfigManager()

if __name__ == '__main__':
    # Test
    print("Nền tảng:", config_manager.get('platform'))
    print("Login MT5:", config_manager.get('mt5.login'))
    
    # Thay đổi và lưu
    config_manager.set('platform', 'binance')
    config_manager.save_config()
    print("Nền tảng sau khi thay đổi:", config_manager.get('platform'))
    
    # Reset
    config_manager.set('platform', 'mt5')
    config_manager.save_config()
    print("Nền tảng sau khi reset:", config_manager.get('platform'))
