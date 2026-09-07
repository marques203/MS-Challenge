import heapq

class MatchingEngine:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        #Ordens pegged que ficaram sem preço de referência. Elas continuam vivas,
        #mas saem do livro visível até a referência reaparecer.
        self.inactive_buy_orders = []
        self.inactive_sell_orders = []
        self.order_id_counter = 0
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
    def __execute_best_pair(self):
        #Executa no máximo um par de ordens. Devolve True se houve trade.
        if not self.buy_orders or not self.sell_orders:
            return False

        best_buy = self.buy_orders[0]
        best_sell = self.sell_orders[0]
        buy_price = -best_buy[0]
        sell_price = best_sell[0]

        #Sem sobreposição de preços não há negócio.
        if buy_price < sell_price:
            return False

        #O preço do trade é o da ordem passiva, ou seja, a que chegou primeiro.
        #Como o identificador é um contador único para os dois lados, o menor
        #identificador é sempre a ordem mais antiga.
        trade_price = buy_price if best_buy[1] < best_sell[1] else sell_price
        trade_quantity = min(best_buy[2], best_sell[2])
        print(f"Trade, price: {trade_price}, qty: {trade_quantity}")

        #Alterar a quantidade não quebra a invariante do heap, porque a
        #quantidade não faz parte da chave de ordenação.
        best_buy[2] -= trade_quantity
        best_sell[2] -= trade_quantity
        if best_buy[2] == 0:
            heapq.heappop(self.buy_orders)
        if best_sell[2] == 0:
            heapq.heappop(self.sell_orders)
        return True

    #O(log(n))
    def limit_order(self, operation, order, peg = None):
        if order[1] <= 0:
            raise ValueError("Quantidade deve ser positiva.")
        if operation == "buy":
            self.order_id_counter += 1
            # Invertendo o preço da ordem de compra para que o heapq funcione como uma max-heap.
            # Usamos uma variável local para não alterar a lista recebida pelo chamador.
            price = -order[0]
            order_plus_id = [price, self.order_id_counter, order[1], peg]
            heapq.heappush(self.buy_orders, order_plus_id)
            prefixo = "b"
        elif operation == "sell":
            self.order_id_counter += 1
            order_plus_id = [order[0], self.order_id_counter, order[1], peg]
            heapq.heappush(self.sell_orders, order_plus_id)
            prefixo = "s"
        else:
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")

        #A confirmação vem antes do matching para que a saída fique em ordem
        #cronológica: a ordem é criada e só depois pode gerar trades.
        peg_tag = f"peg {peg} " if peg else ""
        print(f"Order created: {peg_tag}{operation} {order[1]} @ {order[0]} "
              f"{prefixo}{self.order_id_counter}")

        self.match_orders()

    #O(n².log(n)) no pior caso, por causa da reprecificação a cada fill
    def market_order(self, operation, quantity):
        if quantity <= 0:
            raise ValueError("Quantidade deve ser positiva.")

        #Fills consecutivos no mesmo preço são agregados numa única linha de saída,
        #como no exemplo do enunciado. Ao mudar de nível de preço, a linha é impressa.
        trade_price = None
        trade_quantity = 0

        if operation == "buy":
            while quantity > 0:
                #Cada fill pode mudar o offer, o que reprecifica ou inativa as pegs.
                #Sem isso a próxima iteração negociaria contra um preço desatualizado.
                self.__update_peg_orders()
                #A verificação vem depois da reprecificação porque ela pode inativar
                #pegs e esvaziar o lado do livro no meio da varredura.
                if not self.sell_orders:
                    break

                best_sell = self.sell_orders[0]
                executed = min(quantity, best_sell[2])

                if trade_price is not None and best_sell[0] != trade_price:
                    print(f"Trade, price: {trade_price}, qty: {trade_quantity}")
                    trade_quantity = 0
                trade_price = best_sell[0]
                trade_quantity += executed

                quantity -= executed
                best_sell[2] -= executed
                if best_sell[2] == 0:
                    heapq.heappop(self.sell_orders)

        elif operation == "sell":
            while quantity > 0:
                self.__update_peg_orders()
                if not self.buy_orders:
                    break

                best_buy = self.buy_orders[0]
                executed = min(quantity, best_buy[2])

                if trade_price is not None and -best_buy[0] != trade_price:
                    print(f"Trade, price: {trade_price}, qty: {trade_quantity}")
                    trade_quantity = 0
                trade_price = -best_buy[0]
                trade_quantity += executed

                quantity -= executed
                best_buy[2] -= executed
                if best_buy[2] == 0:
                    heapq.heappop(self.buy_orders)
        else:
            raise ValueError("Operação inválida. Use 'buy' ou 'sell'.")

        #Descarrega o último nível acumulado.
        #A quantidade não executada é descartada: uma market order não descansa no livro.
        if trade_price is not None:
            print(f"Trade, price: {trade_price}, qty: {trade_quantity}")

        self.match_orders()


    def match_orders(self):
        #Executa todos os pares de ordens possíveis até que não haja mais
        #sobreposição de preços. Reprecificar as pegs pode criar novos cruzamentos,
        #e cada trade pode mudar o topo do livro e disparar nova reprecificação.
        while True:
            self.__update_peg_orders()
            if not self.__execute_best_pair():
                break


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

        #Chegar até aqui significa que a ordem foi de fato removida, porque
        #os casos de identificador inválido ou inexistente levantam exceção.
        print("Order cancelled")

        #Cancelar não pode criar cruzamento (as referências só pioram), mas a
        #reprecificação das pegs é obrigatória e acontece dentro do match_orders.
        self.match_orders()

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
                        if new_quantity <= 0:
                            raise ValueError("Quantidade deve ser positiva.")
                        else:
                            self.buy_orders[i][2] = new_quantity  # Atualiza a quantidade
                    heapq.heapify(self.buy_orders)  # Reorganiza o heap
                    break
            else:
                #A ordem também pode estar inativa por falta de referência.
                for i, order in enumerate(self.inactive_buy_orders):
                    if order[1] == order_id_num:
                        if new_price is not None:
                            raise ValueError("Não é possível modificar o preço de uma ordem pegged inativa.")
                        if new_quantity is not None:
                            if new_quantity <= 0:
                                raise ValueError("Quantidade deve ser positiva.")
                            else:
                                self.inactive_buy_orders[i][2] = new_quantity  # Atualiza a quantidade
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
                        if new_quantity <= 0:
                            raise ValueError("Quantidade deve ser positiva.")
                        else:
                            self.sell_orders[i][2] = new_quantity  # Atualiza a quantidade
                    heapq.heapify(self.sell_orders)  # Reorganiza o heap
                    break
            else:
                #A ordem também pode estar inativa por falta de referência.
                for i, order in enumerate(self.inactive_sell_orders):
                    if order[1] == order_id_num:
                        if new_price is not None:
                            raise ValueError("Não é possível modificar o preço de uma ordem pegged inativa.")
                        if new_quantity is not None:
                            if new_quantity <= 0:
                                raise ValueError("Quantidade deve ser positiva.")
                            else:
                                self.inactive_sell_orders[i][2] = new_quantity  # Atualiza a quantidade
                        break
                else:
                    raise ValueError("ID de ordem de venda não encontrado.")
        else:
            raise ValueError("ID de ordem inválido.")
        self.match_orders()

    #O(n)
    def peg_order(self, reference, operation, quantity):
        if quantity <= 0:
            raise ValueError("Quantidade deve ser positiva.")
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