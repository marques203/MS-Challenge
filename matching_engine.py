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

    def match_orders(self):
        while self.buy_orders and self.sell_orders:
            #Pegando as melhores ordens de compra e venda
            best_buy = -self.buy_orders[0][0]
            best_sell = self.sell_orders[0][0]
            #Compatibilidade de preços
            if best_buy >= best_sell:
                #Se a quantidade da ordem de compra for maior que a quantidade da ordem de venda
                if self.buy_orders[0][1] > self.sell_orders[0][1]:
                    #Executando a ordem de compra contra a ordem de venda
                    self.buy_orders[0][1] -= self.sell_orders[0][1]
                    heapq.heappop(self.sell_orders)
                #Se a quantidade da ordem de venda for maior que a quantidade da ordem de compra
                elif self.buy_orders[0][1] < self.sell_orders[0][1]:
                    #Executando a ordem de venda contra a ordem de compra
                    self.sell_orders[0][1] -= self.buy_orders[0][1]
                    heapq.heappop(self.buy_orders)
                else:
                    #se as quantidades forem iguais, removemos ambas as ordens
                    heapq.heappop(self.buy_orders)
                    heapq.heappop(self.sell_orders)