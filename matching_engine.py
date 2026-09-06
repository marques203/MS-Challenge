import heapq

class MatchingEngine:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        #Ordens pegged que ficaram sem preço de referência. Elas continuam vivas,
        #mas saem do livro visível até a referência reaparecer.
        self.inactive_buy_orders = []
        self.inactive_sell_orders = []
        self.buy_order_id_counter = 0
        self.sell_order_id_counter = 0
        self.reference_buy_price = None
        self.reference_sell_price = None

    #O(n)
    def __update_reference_prices(self):
        #O topo do heap não serve como referência porque ele pode ser uma ordem pegged.
        #Uma peg não pode servir de referência para outra peg (nem para si mesma),
        #senão dois pegs cruzados se perseguiriam indefinidamente.
        #Por isso varremos as listas considerando apenas as ordens não-peg.
        not_peg_buy_prices = []
        not_peg_sell_prices = []
        for order in self.buy_orders:
            if not order[3]:  # Verifica se a ordem não é peg
                not_peg_buy_prices.append(-order[0])  # Inverte o preço de volta para positivo
        for order in self.sell_orders:
            if not order[3]:  # Verifica se a ordem não é peg
                not_peg_sell_prices.append(order[0])  # O preço já está em formato positivo

        if not_peg_buy_prices:
            self.reference_buy_price = max(not_peg_buy_prices)
        else:
            self.reference_buy_price = None

        if not_peg_sell_prices:
            self.reference_sell_price = min(not_peg_sell_prices)
        else:
            self.reference_sell_price = None

    def __peg_reference_price(self, reference):
        #Devolve o preço de referência (sempre positivo) de acordo com o tipo de peg.
        if reference == "bid":
            return self.reference_buy_price
        return self.reference_sell_price

    #O(n)
    def __update_peg_orders(self):
        self.__update_reference_prices()

        #1) Reativa as ordens pegged cuja referência voltou a existir.
        #O identificador original é preservado, então a ordem não perde prioridade na fila.
        still_inactive_buy = []
        for order in sorted(self.inactive_buy_orders, key=lambda x: x[1]):
            price = self.__peg_reference_price(order[3])
            if price is None:
                still_inactive_buy.append(order)
            else:
                #Lado da compra: o preço é sempre armazenado invertido, independente
                #de a referência ser o bid ou o offer.
                order[0] = -price
                heapq.heappush(self.buy_orders, order)
        self.inactive_buy_orders = still_inactive_buy

        still_inactive_sell = []
        for order in sorted(self.inactive_sell_orders, key=lambda x: x[1]):
            price = self.__peg_reference_price(order[3])
            if price is None:
                still_inactive_sell.append(order)
            else:
                #Lado da venda: o preço é sempre armazenado positivo.
                order[0] = price
                heapq.heappush(self.sell_orders, order)
        self.inactive_sell_orders = still_inactive_sell

        #2) Reprecifica as ordens pegged que estão no livro.
        #Quem perdeu a referência sai do livro e vai para a lista de inativas.
        active_buy = []
        for order in self.buy_orders:
            if not order[3]:
                active_buy.append(order)
                continue
            price = self.__peg_reference_price(order[3])
            if price is None:
                order[0] = None
                self.inactive_buy_orders.append(order)
            else:
                order[0] = -price
                active_buy.append(order)
        self.buy_orders = active_buy

        active_sell = []
        for order in self.sell_orders:
            if not order[3]:
                active_sell.append(order)
                continue
            price = self.__peg_reference_price(order[3])
            if price is None:
                order[0] = None
                self.inactive_sell_orders.append(order)
            else:
                order[0] = price
                active_sell.append(order)
        self.sell_orders = active_sell

        #3) Alterar o preço de um elemento quebra a invariante do heap.
        #Sem o heapify abaixo, o índice 0 deixa de ser a melhor ordem do lado.
        heapq.heapify(self.buy_orders)
        heapq.heapify(self.sell_orders)


    #O(log(n))
    def limit_order(self, operation, order, peg = None):
        if operation == "buy":
            self.buy_order_id_counter += 1
            # Invertendo o preço da ordem de compra para que o heapq funcione como uma max-heap.
            # Usamos uma variável local para não alterar a lista recebida pelo chamador.
            price = -order[0]
            order_plus_id = [price, self.buy_order_id_counter, order[1], peg]
            heapq.heappush(self.buy_orders, order_plus_id)
        elif operation == "sell":
            self.sell_order_id_counter += 1
            order_plus_id = [order[0], self.sell_order_id_counter, order[1], peg]
            heapq.heappush(self.sell_orders, order_plus_id)
        else:
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")
        self.__update_peg_orders()

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
        self.__update_peg_orders()

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
        self.__update_peg_orders()

    #O(n.log(n))
    def print_order_book(self):
        print("Livro de Ordens:")
        print("Ordens de Compra:")
        #O preço já está invertido na lista, então ordenar por x[0] crescente
        #devolve o maior preço real primeiro, que é a ordenação correta do bid.
        for order in sorted(self.buy_orders, key=lambda x: (x[0], x[1])):
            peg_tag = f", peg: {order[3]}" if order[3] else ""
            print(f"Preço: {-order[0]}, Quantidade: {order[2]}, ID: b{order[1]}{peg_tag}")
        print("Ordens de Venda:")
        for order in sorted(self.sell_orders, key=lambda x: (x[0], x[1])):
            peg_tag = f", peg: {order[3]}" if order[3] else ""
            print(f"Preço: {order[0]}, Quantidade: {order[2]}, ID: s{order[1]}{peg_tag}")

        #Ordens pegged sem referência continuam existindo, apenas fora do livro.
        #Mostrar essa lista evita que elas sumam da vista sem explicação.
        if self.inactive_buy_orders or self.inactive_sell_orders:
            print("Ordens pegged inativas (sem referência):")
            for order in sorted(self.inactive_buy_orders, key=lambda x: x[1]):
                print(f"Compra, Quantidade: {order[2]}, ID: b{order[1]}, peg: {order[3]}")
            for order in sorted(self.inactive_sell_orders, key=lambda x: x[1]):
                print(f"Venda, Quantidade: {order[2]}, ID: s{order[1]}, peg: {order[3]}")


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
            else:
                #A ordem também pode estar inativa por falta de referência.
                for i, order in enumerate(self.inactive_buy_orders):
                    if order[1] == order_id_num:
                        self.inactive_buy_orders.pop(i)
                        break
                else:
                    raise ValueError("ID de ordem de compra não encontrado.")

        elif order_id.startswith("s"):
            order_id_num = int(order_id[1:])
            for i, order in enumerate(self.sell_orders):
                if order[1] == order_id_num:
                    self.sell_orders.pop(i)
                    heapq.heapify(self.sell_orders)
                    break
            else:
                for i, order in enumerate(self.inactive_sell_orders):
                    if order[1] == order_id_num:
                        self.inactive_sell_orders.pop(i)
                        break
                else:
                    raise ValueError("ID de ordem de venda não encontrado.")
        else:
            raise ValueError("ID de ordem inválido.")
        self.__update_peg_orders()

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
                        if order[3]:
                            raise ValueError("Não é possível modificar o preço de uma ordem pegged.")
                        else:
                            self.buy_orders[i][0] = -new_price  # Atualiza o preço (invertido para max-heap)
                    if new_quantity is not None:
                        self.buy_orders[i][2] = new_quantity  # Atualiza a quantidade
                    heapq.heapify(self.buy_orders)  # Reorganiza o heap
                    break
            else:
                raise ValueError("ID de ordem de compra não encontrado.")
        elif order_id.startswith("s"):
            order_id_num = int(order_id[1:])
            for i, order in enumerate(self.sell_orders):
                if order[1] == order_id_num:
                    #Caso o preço esteja no input da modificação, atualiza o preço da ordem
                    if new_price is not None:
                        if order[3]:
                            raise ValueError("Não é possível modificar o preço de uma ordem pegged.")
                        else:
                            self.sell_orders[i][0] = new_price  # Atualiza o preço
                    if new_quantity is not None:
                        self.sell_orders[i][2] = new_quantity  # Atualiza a quantidade
                    heapq.heapify(self.sell_orders)  # Reorganiza o heap
                    break
            else:
                raise ValueError("ID de ordem de venda não encontrado.")
        else:
            raise ValueError("ID de ordem inválido.")
        self.__update_peg_orders()

    #O(n)
    def peg_order(self, reference, operation, quantity):
        if reference not in ("bid", "offer"):
            raise ValueError("Referência inválida. Use 'bid' ou 'offer'.")
        if operation not in ("buy", "sell"):
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")

        #A referência define o preço; a operação define em qual livro a ordem entra.
        #As quatro combinações são aceitas, inclusive as cruzadas
        #(peg offer buy e peg bid sell), que atravessam o spread.
        price = self.__peg_reference_price(reference)
        if price is None:
            raise ValueError(
                f"Não há {reference} no livro para referenciar; ordem pegged rejeitada."
            )

        self.limit_order(operation, [price, quantity], peg=reference)