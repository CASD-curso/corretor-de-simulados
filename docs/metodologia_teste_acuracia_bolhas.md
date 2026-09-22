# Relatório de metodologia — teste de acurácia por bolha

*Registrado em 22/09/2026. Documenta o desenho experimental, o embasamento estatístico e as decisões tomadas para medir "o software acerta a leitura de X% das bolhas, marcadas ou não" e para calibrar a regra de decisão do sistema com prioridade de minimizar falsos positivos. Escrito para reprodutibilidade — qualquer sessão futura deve conseguir repetir o experimento a partir daqui, sem depender da conversa que o originou.*

## 1. Objetivo e por que as medidas existentes não respondem a isso

Nenhuma métrica hoje disponível isola "o software leu a bolha certo" de outras fontes de erro. Comparar a leitura final com o gabarito oficial da prova mistura erro de leitura do software com erro do aluno na prova, e não serve para medir a acurácia do software isoladamente.

A **acurácia de validação** do treino (~99,3–99,5%) vem do mesmo processo de sorteio/rotulagem usado para montar o dataset de treino — mesmos lotes, mesmos anotadores — e foi usada indiretamente para decidir quando parar o treino (early stopping), o que tende a inflá-la. Não passa pelas folhas reservadas como teste, isoladas do treino desde o desenho do dataset justamente para evitar esse tipo de contaminação.

**O que falta e o que este experimento produz:** uma medição por bolha (marcada/vazia), sobre um conjunto nunca visto pelo modelo em nenhuma fase (nem treino, nem validação), com rótulo de verdade obtido por anotação humana cega à predição do modelo.

## 2. Desenho experimental

**Nome técnico: avaliação single-blind, com amostragem aleatória por questão.**

- **Single-blind:** só o anotador humano é cegado — não vê a predição do modelo antes de julgar a imagem, o que evita viés de ancoragem em marcação fraca/ambígua. O modelo não recebe a anotação humana antes de prever, mas isso não é "cegamento" no mesmo sentido: ele é uma função fixa (mesma entrada → mesma saída sempre), sem viés cognitivo a controlar — dar a ele a anotação não seria uma fonte de viés a mitigar, seria vazamento de dado (problema diferente, que invalidaria o teste, não o enviesaria). Por isso o cegamento é uma escolha metodológica só do lado humano.
- **Amostragem aleatória por questão inteira, não por bolha solta:** cada questão sorteada preserva o contexto comparativo das 5 alternativas lado a lado (o mesmo formato de tira de imagens já usado na revisão manual e na rotulagem do dataset de treino), e cada questão anotada rende 5 pontos de dado (1 bolha marcada + 4 vazias, na maioria dos casos), em vez de 1.

### 2.1 Isolamento do pool de teste

O sorteio precisa vir exclusivamente de folhas que o modelo nunca viu em nenhuma fase (nem treino, nem validação):

- **Teste A** (dia a dia): pool de 335 folhas (`215-simu` + `extra`) **menos** as folhas que já constam no `amostra_sorteada.csv` gerado por `corretor/treino/sortear_amostra.py` na sessão de treino — sem essa exclusão, parte da amostra cairia em folhas já vistas pelo modelo, contaminando a métrica.
- **Teste B**: corredor `G2` (138 folhas), já isolado por design desde o sorteio original — `sortear_amostra.py` já o exclui do pool de treino, então nenhuma adaptação é necessária aqui.

### 2.2 Reaproveitamento de código existente

Uma sessão anterior já produziu infraestrutura equivalente para rotular o dataset de treino, que este experimento adapta em vez de recriar:

| Script | Uso original (treino) | Adaptação para este teste |
|---|---|---|
| `sortear_amostra.py` | Sorteia folhas/questões do pool de treino elegível | Passa a sortear do pool isolado de teste (seção 2.1) — Teste A/B — em vez do pool de treino |
| `gerar_planilha_anotacao.py` | Gera planilha cega (tira de imagens + campo `Marcada`) | Reaproveitado sem alteração — já não mostra a predição do modelo |
| `aplicar_anotacao.py` | Copia recortes anotados para as pastas de classe do dataset de treino | Não reaproveitado como está — este teste não alimenta o treino; precisa de uma leitura da planilha que preserve a predição do modelo ao lado da anotação, para a comparação (passo novo, seção 5) |

Passos novos necessários: (1) rodar o modelo em produção sobre a mesma amostra sorteada, salvando a **probabilidade bruta** por bolha (não só a decisão final — necessária para a calibração de margem da seção 5); (2) cruzar anotação × predição para montar a matriz de confusão e as métricas.

### 2.3 Parâmetros definidos

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `n` (questões sorteadas) | 200 | Orçamento de anotação definido pelo usuário — ver seção 3.3 para o que isso garante em margem de erro |
| Granularidade do sorteio | Questão inteira (2 por folha, como no sorteio original do dataset de treino) | Preserva contexto comparativo das 5 alternativas na anotação; cada questão rende ~5 pontos de dado por bolha |
| Seed | 29 | Fixa, reprodutível — qualquer inteiro serve; documentado aqui para permitir repetir o sorteio exato |
| `p` a priori | 0,99 | Vindo da acurácia de validação (seção 1) — usado só para estimar a margem esperada antes de rodar (seção 3.3), nunca como resultado |

## 3. Fundamentação estatística

### 3.1 Modelo

Cada bolha lida é `Xᵢ ~ Bernoulli(p)`, com `p` = taxa de acerto real do software (desconhecida). A soma das `n` bolhas segue `Binomial(n,p)`, e `p̂ = (Σ Xᵢ)/n` é o estimador natural de `p`.

### 3.2 Estatística pivotal e origem de `z = 1,96`

Pelo Teorema Central do Limite:

```
Z = (p̂ - p) / √(p(1-p)/n)     ~ aproximadamente N(0,1), para n grande
```

Um IC de 95% pede o intervalo `[-z, z]` que concentra 95% da área da normal padrão, sobrando 5% dividido igualmente nas duas caudas (2,5% cada, por simetria). Sendo `Φ` a função de distribuição acumulada da normal padrão:

```
Φ(z) = 0,975   →   z = Φ⁻¹(0,975) ≈ 1,95996 ≈ 1,96
```

Não há solução fechada para essa equação (`Φ` não tem inversa algébrica simples); o valor vem de tabela ou software. (Para IC de 90%: `z≈1,645`; para 99%: `z≈2,576`.)

### 3.3 Tamanho de amostra e cenários para `n = 200`

Isolando `n` a partir da margem desejada `e`:

```
n = z² · p(1-p) / e²
```

`p` é desconhecido antes de amostrar. A prática conservadora usa `p=0,5` (que maximiza `p(1-p)=0,25`), garantindo que a margem real nunca ultrapasse a pedida — é o pior caso possível, superestimando `n` quando a taxa real está longe de 50%, como se espera aqui.

Em vez de calcular `n` a partir de uma margem desejada, a pergunta foi invertida: com `n=200` fixo, qual margem se obtém dependendo do resultado observado?

| Se observar | `p̂` (acerto) | Margem (±, 95%) | Faixa provável do valor real |
|---|---|---|---|
| 100 erros em 200 (pior caso, `p=0,5`) | 50% | ±6,9% | 43,1%–56,9% |
| ~18 erros em 200 | 91% | ±4,0% | 87%–95% |
| ~4 erros em 200 | 98% | ±1,9% | 96,1%–99,9% |
| 2 erros em 200 | 99% | ±1,4% | 97,6%–100%¹ |
| 0 erros em 200 | 100% | ≤ ~1,5%² | acerto real ≥ ~98,5% |

¹ o intervalo normal simples pode ultrapassar 100% perto do extremo — sintoma de que essa aproximação falha aqui (seção 3.4/3.5). ² com zero erros, usa-se a regra de três / Clopper-Pearson exato: limite superior do erro real ≈ `3/n`.

**Conclusão:** a margem de ±6,9% (pior caso) só se materializa se o modelo estiver de fato perto de 50%, cenário que ficaria óbvio de cara. Se a taxa real estiver perto de 99% (seção 1), 200 questões já entregam margem bem mais apertada (~±1,4–1,9%) — e, sorteando por questão inteira (seção 2), essas 200 linhas rendem ~200 bolhas marcadas e ~800 vazias, mais dado ainda do que a tabela assume por bolha isolada.

### 3.4 Dedução do intervalo de Wald e por que ele falha

Partindo da mesma pivotal `Z`, o IC de 95% pede `P(-z ≤ Z ≤ z) = 0,95`. Isolando `p`:

```
p̂ - z·√(p(1-p)/n)  ≤  p  ≤  p̂ + z·√(p(1-p)/n)
```

Aqui `p` (o parâmetro, desconhecido) ainda está **dentro da raiz**, dos dois lados. O intervalo de Wald resolve isso trocando o `p` de dentro da raiz pelo `p̂` já observado:

```
√(p(1-p)/n)  ≈  √(p̂(1-p̂)/n)         →   IC (Wald) = p̂ ± z·√(p̂(1-p̂)/n)
```

**É exatamente essa troca que causa a falha do Wald.** Ela é válida apenas *assintoticamente*: como `p̂ → p` quando `n` cresce, o Teorema de Slutsky garante que trocar `p` por `p̂` dentro da raiz não muda a distribuição limite de `Z` — mas é uma aproximação extra em cima da normal, feita por conveniência algébrica (evita resolver a inequação quadrática em `p` que o Wilson resolve, seção 3.5). Em `n` pequeno ou `p` perto de um extremo (aqui, `p≈0,99`), essa segunda aproximação degrada rápido: no caso-limite `p̂=1` (zero erros), `p̂(1-p̂)=0` e a margem colapsa para zero, sugerindo certeza absoluta — absurdo com só 200 observações. Esse colapso é o que obriga a usar Wilson (ou Clopper-Pearson) no cenário mais provável deste experimento.

### 3.5 Intervalo de Wilson — o método para o resultado final

Perto dos extremos (0% ou 100%), o intervalo normal falha (seção 3.4) — pode sugerir valores fora de `[0%,100%]`. A correção padrão é o intervalo de Wilson, que resolve a inequação quadrática em `p` sem substituir `p` por `p̂` dentro da raiz:

```
centro = (p̂ + z²/(2n)) / (1 + z²/n)
meia-largura = [z / (1 + z²/n)] × √[ p̂(1-p̂)/n + z²/(4n²) ]
```

Aplicando com `p̂=0,99`, `n=200`, `z=1,96` (cálculo de planejamento — ver ressalva abaixo):

```
z²/n = 0,019208
centro = (0,99+0,009604)/1,019208 = 0,9808  (98,08%)
meia-largura = (1,96/1,019208) × √(0,0000495+0,000024) ≈ 0,0165  (±1,65%)
IC 95% (Wilson): [96,4% ; 99,7%]
```

Comparado ao cálculo simples (que deu `[97,6%; 100,4%]`, estourando 100%), o Wilson recentraliza a estimativa e produz um intervalo sempre contido em `[0,1]`.

**Regra de uso:** `p=0,99` só entra no planejamento (seção 2.3, 3.3) — para saber que margem esperar antes de rodar o teste. O intervalo final reportado usa o `p̂` observado na anotação cega real, sempre calculado com Wilson (nunca Wald), dado que o cenário esperado (`p` perto de um extremo) é exatamente onde Wald falha.

### 3.6 Interpretação do intervalo de confiança

`p` é uma constante fixa desconhecida, não uma variável aleatória (visão frequentista) — o que varia de execução para execução é a amostra, não `p`. A leitura correta de "IC de 95%": **se o procedimento fosse repetido muitas vezes, 95% dos intervalos construídos conteriam o `p` real**. Depois de rodar uma vez, o intervalo obtido ou contém `p`, ou não contém — não há mais probabilidade correndo sobre aquele intervalo específico. Não é correto dizer "há 5% de chance de `p` estar fora do intervalo" (isso trataria `p` como aleatório, o que pertence a outro framework, o bayesiano, com outra matemática). A incerteza residual (a possibilidade de cair no 5%) é inerente a qualquer medição por amostra finita — o valor do método está em tornar essa incerteza um número conhecido e ajustável (subindo a confiança para 99%, por exemplo, ao custo de um intervalo mais largo), não em eliminá-la.

## 4. Métricas de avaliação por bolha

### 4.1 Matriz de confusão

|  | Anotação real: **Marcada** | Anotação real: **Vazia** |
|---|---|---|
| Modelo previu **Marcada** | TP (verdadeiro positivo) | FP (falso positivo) |
| Modelo previu **Vazia** | FN (falso negativo) | TN (verdadeiro negativo) |

No sistema, os dois erros têm consequência diferente: **FN** (marcação real perdida) resulta em "EM BRANCO" na questão, que já é sinalizado na aba Correção da planilha de revisão para conferência manual. **FP** (marcação inventada em bolha vazia) pode produzir uma resposta errada com aparência de confiante, sem disparar nenhum sinalizador — **passa despercebido pelo sistema**. Essa assimetria motiva a decisão da seção 5: priorizar a eliminação de FP, mesmo ao custo de mais FN.

### 4.2 Por que precisão, não especificidade, para monitorar FP

```
sensibilidade  = TP / (TP + FN)      — não contém FP; cega a esse tipo de erro por construção
especificidade = TN / (TN + FP)      — denominador dominado por TN (classe majoritária)
precisão       = TP / (TP + FP)      — denominador da ordem de TP (classe minoritária)
```

A proporção natural do problema é ~1 bolha marcada para 4 vazias (`TP+FN ≈ (TP+FN+TN+FP)/5`, `TN+FP ≈ 4×(TP+FN)`). Isso faz `TN` ser ~4× maior que `TP` — e um mesmo punhado de FPs pesa muito menos num denominador grande (`TN+FP`, especificidade) do que num pequeno (`TP+FP`, precisão).

**Exemplo, com os números esperados do sorteio por questão (seção 3.3): ~200 marcadas reais, ~800 vazias reais.** Suponha 5 falsos positivos e 3 falsos negativos:

```
TP=197, TN=795
especificidade = 795/800 = 99,4%   ← quase não se move
precisão       = 197/202 = 97,5%   ← cai quase 2 pontos, com o MESMO erro
```

Os mesmos 5 FPs praticamente não afetam a especificidade (diluídos pelos 800 vazias), mas derrubam a precisão de forma bem mais visível — é por isso que a precisão é o indicador escolhido para acompanhar o objetivo de eliminar FP, em vez da especificidade.

### 4.3 Curva ROC vs. curva precisão-revocação

- **ROC**: eixo Y = sensibilidade (TPR), eixo X = `1 − especificidade` (FPR = `FP/(FP+TN)`). Herda o mesmo problema da seção 4.2: como `FPR` divide por `TN` (grande), a curva pode parecer "melhor" do que a situação real é, diluindo o efeito de poucos FPs.
- **Precisão-revocação** (escolhida aqui): eixo Y = precisão (`TP/(TP+FP)`), eixo X = revocação (= sensibilidade, `TP/(TP+FN)`). Reage diretamente a cada FP novo, porque o denominador da precisão é da ordem da classe minoritária — consistente com o objetivo da seção 5.

## 5. Calibração da margem de decisão, com prioridade de eliminar FP

A regra de decisão por margem (`segunda_menor − menor > margem`) tem um único parâmetro livre — a constante da margem. Subir essa constante torna o sistema mais exigente para declarar "marcada": só declara quando a diferença entre a bolha mais escura e a segunda mais escura for grande e inequívoca. Efeito: **menos FP** (menos risco de dizer "marcada" por engano), ao custo de **mais FN** — mas um FN vira "EM BRANCO", que já é sinalizado para revisão manual (seção 4.1), então o custo cai num lugar visível, não escondido.

**Protocolo de calibração, usando os dados deste experimento:**

1. O script de inferência (seção 2.2) salva a **probabilidade bruta** de cada bolha da amostra, não só a decisão final sob a margem atual — pré-requisito para testar outras margens depois, sem precisar rodar o modelo de novo.
2. Define-se um conjunto de valores candidatos de margem (ex.: uma varredura de 0,05 a 0,60, em passos de 0,05).
3. **Para cada valor candidato**, recalcula-se a decisão de cada questão da amostra (usando as probabilidades já salvas) e monta-se a matriz de confusão correspondente (seção 4.1) contra a anotação real.
4. Disso resulta a curva precisão-revocação (seção 4.3) — um ponto por margem candidata.
5. **Critério de seleção:** escolhe-se a menor margem candidata que ainda garanta a precisão mínima aceitável definida pelo usuário (ex.: "precisão ≥ 99%, custe o que custar em revocação/sensibilidade") — não a margem "mais alta possível", porque isso levaria a excesso de EM BRANCO desnecessário.

Esse protocolo substitui a calibração "a olho" prevista originalmente — a escolha da constante passa a ser baseada no trade-off real medido contra a anotação cega, com o critério de seleção definido a priori (precisão mínima), e não ajustada post-hoc para parecer melhor.
