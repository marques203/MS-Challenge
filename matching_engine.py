import heapq

class MatchingEngine:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        self.buy_order_id_counter = 0
        self.sell_order_id_counter = 0

    def limit_order(self, operation, order):
        if operation == "buy":
            self.buy_order_id_counter += 1
            # Invertendo o preço da ordem de compra para que o heapq funcione como uma max-heap
            order[0] = -order[0]
            order_plus_id = [order[0], self.buy_order_id_counter, order[1]]
            heapq.heappush(self.buy_orders, order_plus_id)
        elif operation == "sell":
            self.sell_order_id_counter += 1
            order_plus_id = [order[0], self.sell_order_id_counter, order[1]]
            heapq.heappush(self.sell_orders, order_plus_id)
        else:
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")

    #O(nlog(n))
    def market_order(self, operation, quantity):
        #Caso a operação seja de compra, vamos executar a ordem de compra contra as ordens de venda
        if operation == "buy":
            #Enquanto houver quantidade a ser comprada e ordens de venda disponíveis, executo a ordem
            while quantity > 0 and self.sell_orders:
                best_sell = self.sell_orders[0]
                #Se a quantidade da ordem de compra for maior ou igual a quantidade da melhor ordem de venda,
                #subtraimos a quantidade da ordem de compra e tiramos a ordem de venda da fila
                if quantity >= best_sell[2]:
                    quantity -= best_sell[2]
                    heapq.heappop(self.sell_orders)
                else:
                    #subtraimos a quantidade da melhor ordem de venda e zeramos a quantidade da ordem agressiva
                    best_sell[2] -= quantity
                    quantity = 0

        elif operation == "sell":
            while quantity > 0 and self.buy_orders:
                best_buy = self.buy_orders[0]
                if quantity >= best_buy[2]:
                    quantity -= best_buy[2]
                    heapq.heappop(self.buy_orders)
                else:
                    best_buy[2] -= quantity
                    quantity = 0
        else:
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")


    #O(log(n))
    def match_orders(self):
        if self.buy_orders and self.sell_orders:
            #Pegando as melhores ordens de compra e venda
            best_buy = -self.buy_orders[0][0]
            best_sell = self.sell_orders[0][0]
            #Compatibilidade de preços
            if best_buy >= best_sell:
                #Se a quantidade da ordem de compra for maior que a quantidade da ordem de venda
                if self.buy_orders[0][2] > self.sell_orders[0][2]:
                    #Executando a ordem de compra contra a ordem de venda
                    self.buy_orders[0][2] -= self.sell_orders[0][2]
                    heapq.heappop(self.sell_orders)
                #Se a quantidade da ordem de venda for maior que a quantidade da ordem de compra
                elif self.buy_orders[0][2] < self.sell_orders[0][2]:
                    #Executando a ordem de venda contra a ordem de compra
                    self.sell_orders[0][2] -= self.buy_orders[0][2]
                    heapq.heappop(self.buy_orders)
                else:
                    #se as quantidades forem iguais, removemos ambas as ordens
                    heapq.heappop(self.buy_orders)
                    heapq.heappop(self.sell_orders)
    #O(n.log(n))
    def print_order_book(self):
        print("Livro de Ordens:")
        print("Ordens de Compra:")
        for order in sorted(self.buy_orders, key=lambda x: (-x[0], x[1])):
            print(f"Preço: {-order[0]}, Quantidade: {order[2]}, ID: b{order[1]}")
        print("Ordens de Venda:")
        for order in sorted(self.sell_orders, key=lambda x: (x[0], x[1])):
            print(f"Preço: {order[0]}, Quantidade: {order[2]}, ID: s{order[1]}")

    #O(n)
    def cancel_order(self, order_id):
        #caso o inicio do identificador seja de uma ordem de compra
        if order_id.startswith("b"):
            order_id_num = int(order_id[1:])
            #procurar na lista de ordens o numero do identificador
            for i, order in enumerate(self.buy_orders):
                #caso ache, remove a ordem da lista e refaz o heap: 
                if order[1] == order_id_num:
                    self.buy_orders.pop(i)
                    heapq.heapify(self.buy_orders)
                    break

        elif order_id.startswith("s"):
            order_id_num = int(order_id[1:])
            for i, order in enumerate(self.sell_orders):
                if order[1] == order_id_num:
                    self.sell_orders.pop(i)
                    heapq.heapify(self.sell_orders)
                    break
        else:
            raise ValueError("ID de ordem inválido.")
    #O(n)
    def order_modify(self, order_id, new_price = None, new_quantity = None):
        if order_id.startswith("b"):
            order_id_num = int(order_id[1:])
            #Itera sobre a lista de orders
            for i, order in enumerate(self.buy_orders):
                #Caso ache o identificador, atualiza o preço e a quantidade da ordem e refaz o heap
                if order[1] == order_id_num:
                    #Caso o preço esteja no input da modificação, atualiza o preço da ordem (invertido para max-heap)
                    if new_price is not None:
                        self.buy_orders[i][0] = -new_price  # Atualiza o preço (invertido para max-heap)
                    if new_quantity is not None:
                        self.buy_orders[i][2] = new_quantity  # Atualiza a quantidade
                    heapq.heapify(self.buy_orders)  # Reorganiza o heap
                    break
        elif order_id.startswith("s"):
            order_id_num = int(order_id[1:])
            for i, order in enumerate(self.sell_orders):
                if order[1] == order_id_num:
                    #Caso o preço esteja no input da modificação, atualiza o preço da ordem
                    if new_price is not None:
                        self.sell_orders[i][0] = new_price  # Atualiza o preço
                    if new_quantity is not None:
                        self.sell_orders[i][2] = new_quantity  # Atualiza a quantidade
                    heapq.heapify(self.sell_orders)  # Reorganiza o heap
                    break
        else:
            raise ValueError("ID de ordem inválido.")


    
