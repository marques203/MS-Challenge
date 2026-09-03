import heapq

class MatchingEngine:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []

    def limit_order(self, operation, order):
        if operation == "buy":
            order[0] = -order[0]
            heapq.heappush(self.buy_orders, order)
        elif operation == "sell":
            heapq.heappush(self.sell_orders, order)
        else:
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")

    