# Base Connector
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def get_symbol(self):
        pass

    @abstractmethod
    def fetch_ohlcv(self, timeframe, limit):
        pass

    @abstractmethod
    def place_order(self, order_type, quantity, sl, tp):
        pass

    @abstractmethod
    def get_open_positions(self):
        pass
