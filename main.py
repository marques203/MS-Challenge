import sys

from matching_engine import MatchingEngine


AJUDA = """Comandos disponíveis:

  limit <buy|sell> <preço> <qty>      Ordem limite. Ex: limit buy 10 100
  market <buy|sell> <qty>             Ordem a mercado. Ex: market buy 150
  peg <bid|offer> <buy|sell> <qty>    Ordem pegged. Ex: peg bid buy 150

  cancel order <id>                   Cancela uma ordem. Ex: cancel order b1
  modify <id> [price <p>] [qty <q>]   Altera preço e/ou quantidade.
                                      Ex: modify b1 price 9.98
                                          modify b1 qty 300
                                          modify b1 price 9.98 qty 300

  print book                          Mostra o livro de ordens.
  help                                Mostra esta ajuda.
  exit                                Encerra.

Os identificadores das ordens aparecem no 'print book'."""


def parse_preco(texto):
    #Aceita tanto ponto quanto vírgula como separador decimal.
    try:
        preco = float(texto.replace(",", "."))
    except ValueError:
        raise ValueError(f"Preço inválido: '{texto}'.")
    if preco <= 0:
        raise ValueError("Preço deve ser positivo.")
    #Preços inteiros viram int para a saída ficar como no enunciado
    #('Trade, price: 20' em vez de 'Trade, price: 20.0').
    if preco.is_integer():
        return int(preco)
    return preco


def parse_quantidade(texto):
    try:
        quantidade = int(texto)
    except ValueError:
        raise ValueError(f"Quantidade inválida: '{texto}'.")
    if quantidade <= 0:
        raise ValueError("Quantidade deve ser positiva.")
    return quantidade


def executar(engine, linha):
    #Traduz uma linha de texto em uma chamada da engine.
    #Devolve False quando o comando pede o encerramento do programa.
    partes = linha.split()
    if not partes:
        return True

    comando = partes[0].lower()

    if comando in ("exit", "quit", "sair"):
        return False

    if comando in ("help", "ajuda", "?"):
        print(AJUDA)
        return True

    if comando == "print":
        #Aceita tanto 'print book' quanto apenas 'print'.
        engine.print_order_book()
        return True

    if comando == "limit":
        if len(partes) != 4:
            raise ValueError("Uso: limit <buy|sell> <preço> <qty>")
        operacao = partes[1].lower()
        preco = parse_preco(partes[2])
        quantidade = parse_quantidade(partes[3])
        engine.limit_order(operacao, [preco, quantidade])
        return True

    if comando == "market":
        if len(partes) != 3:
            raise ValueError("Uso: market <buy|sell> <qty>")
        operacao = partes[1].lower()
        quantidade = parse_quantidade(partes[2])
        engine.market_order(operacao, quantidade)
        return True

    if comando == "peg":
        if len(partes) != 4:
            raise ValueError("Uso: peg <bid|offer> <buy|sell> <qty>")
        referencia = partes[1].lower()
        operacao = partes[2].lower()
        quantidade = parse_quantidade(partes[3])
        engine.peg_order(referencia, operacao, quantidade)
        return True

    if comando == "cancel":
        #Aceita 'cancel order b1' (como no enunciado) e 'cancel b1'.
        argumentos = partes[1:]
        if argumentos and argumentos[0].lower() == "order":
            argumentos = argumentos[1:]
        if len(argumentos) != 1:
            raise ValueError("Uso: cancel order <id>")
        engine.cancel_order(argumentos[0])
        return True

    if comando == "modify":
        if len(partes) < 4:
            raise ValueError("Uso: modify <id> [price <p>] [qty <q>]")
        order_id = partes[1]
        novo_preco = None
        nova_quantidade = None

        #Percorre os pares 'chave valor' que vêm depois do identificador.
        i = 2
        while i < len(partes):
            chave = partes[i].lower()
            if i + 1 >= len(partes):
                raise ValueError(f"Falta o valor de '{chave}'.")
            valor = partes[i + 1]

            if chave in ("price", "preco", "preço"):
                novo_preco = parse_preco(valor)
            elif chave in ("qty", "quantidade"):
                nova_quantidade = parse_quantidade(valor)
            else:
                raise ValueError(f"Campo desconhecido: '{chave}'. Use 'price' ou 'qty'.")
            i += 2

        if novo_preco is None and nova_quantidade is None:
            raise ValueError("Informe ao menos 'price' ou 'qty'.")
        engine.order_modify(order_id, novo_preco, nova_quantidade)
        return True

    raise ValueError(f"Comando desconhecido: '{comando}'. Digite 'help' para ver a lista.")


def main():
    engine = MatchingEngine()

    #O prompt só é impresso em modo interativo. Assim dá para redirecionar
    #um arquivo de comandos para a entrada padrão sem poluir a saída.
    interativo = sys.stdin.isatty()
    if interativo:
        print("Matching Engine. Digite 'help' para ver os comandos ou 'exit' para sair.")

    while True:
        if interativo:
            print(">>> ", end="", flush=True)
        linha = sys.stdin.readline()

        #Fim da entrada (Ctrl+D ou fim do arquivo redirecionado).
        if not linha:
            if interativo:
                print()
            break

        try:
            if not executar(engine, linha):
                break
        except ValueError as erro:
            #Erros de uso e de validação da engine são mostrados sem derrubar o programa.
            print(f"Erro: {erro}")
        except Exception as erro:
            print(f"Erro inesperado: {erro}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()