# Matching Engine

Implementação de uma matching engine simples para um único ativo, com ordens
limit, market e pegged, mantida inteiramente em memória.

## Como executar

```bash
python3 main.py
```

Também é possível alimentar a engine com um arquivo de comandos, o que serve
como teste de regressão:

```bash
python3 main.py < casos_de_teste.txt
printf 'limit buy 10 100\nlimit sell 20 100\nmarket buy 50\n' | python3 main.py
```

O prompt `>>> ` só aparece em modo interativo, então a saída redirecionada fica
limpa para comparação.

### Comandos

| Comando | Descrição |
|---|---|
| `limit <buy\|sell> <preço> <qty>` | Ordem limite |
| `market <buy\|sell> <qty>` | Ordem a mercado |
| `peg <bid\|offer> <buy\|sell> <qty>` | Ordem pegged |
| `cancel order <id>` | Cancelamento (também aceita `cancel <id>`) |
| `modify <id> [price <p>] [qty <q>]` | Alteração de preço e/ou quantidade |
| `print book` | Visualização do livro |
| `help` | Ajuda |
| `exit` | Encerra |

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `matching_engine.py` | Classe `MatchingEngine`: livro, matching, pegs |
| `main.py` | Interpretador de comandos e validação de entrada |
| `teste_exaustivo.py` | Suíte de 87 testes mais verificação de invariantes |

A separação é deliberada: o `main.py` traduz texto em chamadas e valida o
formato da entrada (preço numérico e positivo, quantidade inteira, campos
conhecidos); a engine valida o domínio (operação válida, quantidade positiva,
peg com referência) e não conhece nada sobre strings de comando.

---

# Estrutura de dados

Cada ordem é uma lista de quatro posições:

```
[preço, identificador, quantidade, peg]
```

- **preço** — no lado da compra é armazenado **negado**, o que transforma o
  `heapq` (min-heap) em max-heap sem estrutura auxiliar.
- **identificador** — contador único **compartilhado pelos dois lados**. Além
  de identificar a ordem, funciona como carimbo de chegada, e é isso que
  permite comparar a antiguidade de uma compra com a de uma venda.
- **quantidade** — quantidade remanescente.
- **peg** — `None`, `"bid"` ou `"offer"`.

Como a comparação de listas em Python é lexicográfica, a ordenação natural do
heap já é *preço, depois tempo* — exatamente a prioridade preço-tempo exigida
pelo requisito 2, sem função de comparação customizada.

O estado da engine é composto por:

- `buy_orders` / `sell_orders` — heaps do livro visível;
- `inactive_buy_orders` / `inactive_sell_orders` — ordens pegged retidas por
  falta de preço de referência;
- `reference_buy_price` / `reference_sell_price` — melhor bid e melhor offer
  considerando apenas ordens não-peg.

---

# Decisões de projeto

## D1. Limit agressiva é preenchida, não ignorada

O enunciado permite ignorar ou preencher, exigindo justificativa. Optamos por
**preencher**: o trade acontece ao preço da ordem passiva e o saldo não
executado descansa no livro ao preço original.

Ignorar seria mais simples, mas inviabilizaria dois requisitos do próprio
enunciado:

- **Requisito 4** — nada impede que uma alteração de preço mova uma ordem para
  dentro do spread. Se limit agressiva não fosse permitida, seria preciso
  reimplementar a mesma decisão dentro do `order_modify`.
- **Requisito 5** — as ordens pegged coladas ao lado oposto do livro
  (`peg offer buy`, `peg bid sell`) cruzam o spread por definição.

Além disso, nenhuma bolsa real recusa uma ordem por ela ser executável.

## D2. O preço do trade é o da ordem passiva

A ordem passiva recebe exatamente o preço que anunciou; quem chega agredindo
fica com a melhora de preço, se houver.

O exemplo do enunciado não distingue esta regra de "o preço é sempre o da
venda", porque nele a venda sempre foi a passiva. A diferença aparece quando
os papéis se invertem:

```
limit buy 25 100     → descansa no livro
limit sell 20 100    → chega agredindo
Trade, price: 25, qty: 100
```

A compra tinha se comprometido publicamente com 25 e o recebe. Aplicar "preço
da venda" daria 20, entregando ao comprador um preço melhor do que aquele com
que ele se comprometeu, às custas do vendedor.

A implementação identifica a passiva como a de **menor identificador**, o que
só é possível porque o contador é único para os dois lados.

## D3. Market order não descansa no livro

A quantidade não executada é descartada. É o comportamento do exemplo do
enunciado: `market buy 200` contra um livro com apenas 150 executa 150 e
descarta o restante, sem mensagem de erro.

## D4. Saída da market order agregada por nível de preço

O exemplo mostra `market buy 150` consumindo duas ordens de 100 e 50 e
produzindo **uma** linha:

```
Trade, price: 20, qty: 150
```

Como todos os fills saíram a 20, o exemplo é compatível com três leituras: uma
linha por fill, uma por nível de preço, ou uma por ordem a mercado. A terceira
é impossível com preços distintos (exigiria inventar um preço médio ao qual
nenhum negócio ocorreu). Adotamos **uma linha por nível de preço**, que
reproduz o exemplo e generaliza:

```
>>> market buy 300
Trade, price: 20, qty: 150     (agregou duas ordens do nível 20)
Trade, price: 21, qty: 100
Trade, price: 22, qty: 50
```

**Assimetria conhecida:** a limit agressiva imprime uma linha por par de
ordens, não por nível. As duas operações podem produzir o mesmo resultado
econômico com formatos diferentes. Mantivemos assim porque o enunciado só
define o formato no contexto de market orders; uniformizar exigiria que
`__execute_best_pair` acumulasse num buffer descarregado ao fim do
`match_orders`.

## D5. Reprecificação de peg preserva a prioridade na fila

No exemplo do requisito 5, a ordem pegged é reprecificada de 10 para 10.1 e
aparece **à frente** dos 300 que criaram esse nível — apesar de a limit ter
chegado depois. A engine preserva o identificador original na reprecificação,
o que reproduz esse comportamento.

Ver a seção **Ambiguidades** para a discussão da relação com o requisito 4.

## D6. Peg não aceita alteração de preço

Uma ordem pegged não tem preço próprio: ela tem uma instrução ("meu preço é
sempre o bid"). Um comando de preço é incompatível com essa instrução, e é
rejeitado com mensagem explícita. Alteração de **quantidade** continua
permitida, inclusive em pegs inativas.

As alternativas foram descartadas: converter em limit mudaria silenciosamente
o *tipo* da ordem; aceitar e reprecificar de volta seria confirmar um comando
que a engine não honra.

O mercado real segue a mesma linha — as bolsas expõem o *offset* do peg como
campo alterável, não o preço absoluto.

## D7. Peg sem referência: rejeitado na entrada, inativo em runtime

São dois momentos distintos e recebem tratamentos distintos:

- **Na entrada**, sem referência disponível, a ordem é **rejeitada**. Não há a
  que se colar, e falhar rápido é melhor que aceitar algo indefinido.
- **Em runtime**, se a referência desaparecer, a ordem fica **inativa**: sai do
  livro visível, é retida pela engine e volta a ser inserida — com o
  identificador original, portanto sem perder prioridade — assim que a
  referência reaparecer.

Congelar no último preço foi descartado por ser o comportamento mais perigoso
dos três: transformaria silenciosamente o peg numa limit a um preço que
ninguém escolheu, e a engine executaria algo que o operador não pediu.
Cancelar destruiria uma ordem válida por uma condição transitória.

O `print book` exibe as pegs inativas numa seção própria, para que não
desapareçam da vista sem explicação.

## D8. Pegs não servem de referência para outras pegs

`__update_reference_prices` considera apenas ordens não-peg. Isso resolve dois
problemas de uma vez:

- **Autorreferência** — uma peg que fosse a única ordem do seu lado passaria a
  ser a própria referência, congelando o preço por acidente.
- **Ciclo** — um `peg offer buy` e um `peg bid sell` poderiam se perseguir
  indefinidamente, cada um tentando colar num preço que o outro acabou de
  abandonar.

Esta decisão é o que torna o laço de estabilização provadamente finito.

## D9. Pegs cruzados são suportados

As quatro combinações são aceitas. `peg bid buy` e `peg offer sell` são
passivas; `peg offer buy` e `peg bid sell` colam no lado oposto, cruzam o
spread e são resolvidas pelo laço de estabilização — possivelmente em cascata:

```
>>> peg bid sell 500        (livro: 200 @ 10, 100 @ 9.99)
Trade, price: 10, qty: 200      executa contra o bid
Trade, price: 9.99, qty: 100    bid mudou, a peg desceu e executou de novo
                                 saldo de 200 fica inativo por falta de bid
```

## D10. Ordem de processamento determinística

Reativação e reprecificação de pegs são processadas em ordem crescente de
identificador (`sorted(..., key=lambda x: x[1])`). Sem esse critério fixo, o
resultado dependeria da ordem interna do heap, tornando o comportamento
não determinístico e os testes instáveis.

## D11. `float` é suficiente para os preços

A engine nunca faz aritmética com preços — apenas atribui, nega e compara.
Sem operações de soma ou multiplicação não há acúmulo de erro, e literais
distintos (`9.98`, `9.99`, `10.1`) comparam corretamente. Verificado em teste:
o livro ordena esses valores na sequência certa.

`Decimal` passaria a ser necessário se fossem introduzidos *offsets* de peg
(por exemplo `peg bid buy + 0.01`), que envolveriam soma.

## D12. Matching é responsabilidade da engine, não do chamador

Todos os métodos públicos que alteram o livro terminam chamando
`match_orders()`. Livro cruzado é um estado inválido, e a invariante "o livro
nunca está cruzado ao fim de um comando" pertence a quem é dono do estado.

Isso vale inclusive para `cancel_order`, onde à primeira vista não seria
necessário. A análise mostra que cancelar de fato **não pode** criar
cruzamento — as referências só pioram, então as pegs passivas se afastam do
spread e as cruzadas já foram resolvidas na entrada. Mas a chamada é mantida
por dois motivos: a reprecificação das pegs é obrigatória de qualquer forma
(uma peg pode precisar ser inativada), e a garantia acima depende inteiramente
da decisão D8. Se D8 mudar no futuro, a análise deixa de valer e o bug
apareceria justamente no método onde se concluiu que a chamada era dispensável.

---

# Ambiguidades identificadas no enunciado

## A perda de prioridade do requisito 4

O requisito 4 exemplifica a alteração de uma compra de 200 unidades do preço
10 para 9.98 e conclui: *"Ou seja, perdeu prioridade na fila."*

Há duas leituras possíveis:

1. **Regra própria** — toda alteração de preço envia a ordem para o fim da
   fila do novo nível.
2. **Descrição do exemplo** — a ordem foi reposicionada por preço, e como
   9.98 < 9.99 ela naturalmente caiu abaixo da outra compra.

O exemplo não distingue as duas, porque 9.98 ficaria abaixo de 9.99 sob
qualquer regra. A distinção só apareceria se o preço novo coincidisse com o de
uma ordem existente.

**Adotamos a leitura 2**, e o argumento decisivo é a consistência interna do
enunciado. Sob a leitura 1, o requisito 4 contradiria o exemplo do requisito 5,
onde uma ordem pegged tem o preço alterado de 10 para 10.1 e **mantém** a
prioridade sobre uma limit mais recente. Seria preciso inventar uma regra
adicional — "mudança pedida pelo usuário perde prioridade, reprecificação
automática preserva" — que não está escrita em lugar nenhum.

Sob a leitura 2, ambos os requisitos seguem a mesma regra: reposiciona por
preço, desempata pela chegada original. Nenhuma exceção é necessária.

Consequência prática: `order_modify` altera o preço e preserva o identificador.

**Observação:** a maioria das bolsas reais adota a leitura 1, tanto para
modify quanto para reprecificação de peg. A escolha aqui privilegia a
coerência com o enunciado sobre a convenção de mercado.

## Ordens pegged cruzadas

O enunciado descreve `peg to the bid` e menciona que *"o mesmo funciona para
uma ordem peg to offer"*, sem esclarecer se as quatro combinações são válidas
ou apenas as duas passivas. Optamos por implementar as quatro (D9).

---

# Análise de complexidade

Notação: **n** = ordens no livro; **k** = ordens pegged; **t** = trades
gerados por um comando; **f** = fills de uma market order.

## Métodos auxiliares

| Método | Complexidade | Observação |
|---|---|---|
| `__update_reference_prices` | O(n) | varre os dois lados filtrando não-pegs |
| `__peg_reference_price` | O(1) | |
| `__update_peg_orders` | **O(n + k log n)** | referência O(n), reprecificação O(k), dois `heapify` O(n), reinserções O(k log n) |
| `__execute_best_pair` | O(log n) | leitura do topo O(1), até dois `heappop` |

O `heapify` é obrigatório: alterar o preço de um elemento por fora quebra a
invariante do heap, e sem reconstruí-la o índice 0 deixa de ser a melhor ordem
do lado — com o agravante de que o `print_order_book` usa `sorted` e continuaria
exibindo o livro corretamente, mascarando o erro.

## Métodos públicos

| Método | Complexidade | Dominado por |
|---|---|---|
| `limit_order` | O(log n) + custo do `match_orders` | inserção é O(log n); o matching domina |
| `market_order` | **O(f · (n + k log n))** | reprecificação a cada fill |
| `match_orders` | **O((t+1) · (n + k log n))** | uma reprecificação por iteração |
| `print_order_book` | O(n log n) | dois `sorted` |
| `cancel_order` | O(n) + custo do `match_orders` | busca linear + `heapify` |
| `order_modify` | O(n) + custo do `match_orders` | busca linear + `heapify` |
| `peg_order` | igual a `limit_order` | delega |

### Por que `match_orders` reprecifica a cada iteração

O laço alterna reprecificação e execução:

```python
while True:
    self.__update_peg_orders()
    if not self.__execute_best_pair():
        break
```

A ordem importa. Cada trade consome ordens do topo do livro, o que pode mudar
o bid ou o offer, o que move as pegs, o que pode criar um cruzamento novo.
Executar todos os pares primeiro e só depois reprecificar perderia os
cruzamentos criados pela própria reprecificação.

**Terminação:** cada iteração que gera trade remove pelo menos uma ordem do
livro, então o número de iterações é limitado pela quantidade de ordens. A
reprecificação isolada não pode gerar um ciclo, porque pegs não servem de
referência para pegs (D8).

### Por que `market_order` reprecifica a cada fill

Sem isso, uma peg no topo do livro negociaria a um preço já obsoleto. Exemplo
concreto — vendas de 100 @ 10 (não-peg), 100 @ 50 (não-peg) e uma
`peg offer sell 100` colada em 10:

```
>>> market buy 200
Trade, price: 10, qty: 100     consome a não-peg; o offer passa a ser 50
Trade, price: 50, qty: 100     a peg subiu para 50 antes de negociar
```

Sem a reprecificação intermediária, o segundo trade sairia a 10.

A verificação de lado vazio vem **depois** da chamada, porque a reprecificação
pode inativar pegs e esvaziar o lado do livro no meio da varredura.

## Escalonamento medido

Tempos em segundos, com a razão entre medidas consecutivas ao dobrar n:

| n | Inserção | Cancelamento | Market varrendo tudo |
|---|---|---|---|
| 250 | 0,005 | 0,005 | 0,004 |
| 500 | 0,015 (3,0×) | 0,020 (3,7×) | 0,013 (3,7×) |
| 1000 | 0,057 (3,8×) | 0,079 (4,0×) | 0,052 (3,9×) |
| 2000 | 0,222 (3,9×) | 0,317 (4,0×) | 0,204 (4,0×) |
| 4000 | 0,860 (3,9×) | — | — |

A razão consistente de ~4× ao dobrar n confirma comportamento **quadrático**.
Isso é esperado: cada comando dispara ao menos um `__update_peg_orders`, que é
O(n), e uma sequência de n comandos custa O(n²).

Na prática, 5000 ordens são processadas em 1,4 s — suficiente para o escopo do
projeto, que não exige escalabilidade.


---

# Testes

`teste_exaustivo.py` contém 87 testes organizados em dez grupos. Todos passam.

| Grupo | Cobertura |
|---|---|
| 1 | Comparação **literal** da saída com os quatro exemplos do enunciado, via CLI |
| 2 | 33 entradas malformadas: preço textual/negativo/zero, quantidade decimal/negativa/zero, contagem de argumentos, IDs inválidos, comando desconhecido, recuperação após erro |
| 3 | Limit passiva, agressiva, parcial, exata, varredura multi-nível, preço da passiva nos dois sentidos |
| 4 | Market: agregação por nível, sem liquidez, saldo descartado, varredura nos dois lados |
| 5 | Prioridade FIFO com duas e três ordens no mesmo preço |
| 6 | Cancelamento do meio do heap, duplicado, de peg inativa |
| 7 | Modify de preço, quantidade, ambos; rejeição em peg ativa e inativa; modify que cruza |
| 8 | Os quatro tipos de peg, cascata, inativação, reativação com prioridade, não-autorreferência, reprecificação durante market |
| 9 | ~59.000 operações aleatórias verificando invariantes a cada passo |
| 10 | Conservação de quantidade entre os dois lados |

## Invariantes verificadas sob carga aleatória

- O livro nunca fica cruzado ao fim de um comando
- A invariante do heap é preservada nos dois lados
- Nenhuma ordem no livro tem quantidade menor ou igual a zero
- Nenhum trade é emitido com quantidade menor ou igual a zero
- Identificadores permanecem únicos entre livro e listas de inativas
- A quantidade total inserida menos a remanescente é igual à negociada, nos
  dois lados

Nenhuma violação foi observada em 59.000 operações.

---
