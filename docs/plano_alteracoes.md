# Projeto Leitor de Gabaritos — Plano de Alterações

*Revisão de 19/09/2026. Incorpora o desenho do dataset novo (dia a dia + vestibular) para o retreino do item 7.*

## Princípios que guiam este plano

Três critérios decidem qualquer dúvida de escopo daqui para frente.

**Ninguém usa o sistema ainda.** Não existe hábito instalado, caminho antigo a
preservar nem usuário a reeducar. Toda escolha pode ser feita pelo que é certo,
não pelo que é compatível. Isso é um ativo com prazo de validade: vale enquanto o
primeiro simulado de verdade não rodar.

**O usuário final não deve precisar aprender nada.** O alvo é um voluntário do
CASD, possivelmente sem formação técnica, que precisa corrigir um simulado e ir
embora. Ele sobe os scans num lugar só, preenche três campos, roda as células na
ordem e baixa a planilha. Editar caminho no código, escolher entre pastas ou
saber o que é um `.pth` não podem fazer parte do fluxo.

**O repositório público é um cartão de visitas e um manual de sucessão.** Quem
assumir o projeto depois vai entrar por ele. Estrutura limpa, README que explica
o essencial, nenhum dado de aluno, e histórico de commits que conta o que
aconteceu.

**Critério de desempate (18/09/2026):** entre dois itens quaisquer, ganha o que
deixa a **inferência mais precisa**. A meta é que a correção manual seja mínima —
não que ela seja rápida. Otimizar tempo de máquina vem por último.

## Ordem de implementação

`0 ✅ → 1 ✅ → 2 ⏸️ → 3 ✅ → 4 ✅ → 5 ✅ → 7 → 13 → 12 → 6 + 14 → 8 → 19 → 9 → EXTRA`

Os itens **10, 11, 15, 16, 17 e 18** são independentes e custam minutos cada um —
encaixam em qualquer ponto da fila, inclusive como aquecimento de uma sessão
dedicada a outro item.

O item **2** virou o bloco único do modo local e está adiado por inteiro. O item
**19** fica por último entre os de código, e o **9** (README) fecha tudo, porque
documenta o estado final.

Próximo: **item 7**. A robustez do modelo contra marcação fraca foi considerada
mais central que suportar número de questões variável (decisão de 17/09/2026;
sessão dedicada usará o modelo Opus).

Se a sessão produziu evidência que contradiz o plano — medição, teste, leitura de
código — apontar que o item precisa ser reescrito, e em quê. Não editar o plano
por iniciativa própria: é documento do usuário. Propor a redação e esperar o aval.

---

## Fase 0 — Reorganização estrutural  ✅ CONCLUÍDA

**Problema:** o projeto tinha dados sensíveis na raiz, um `.gitignore` que
apontava para caminhos inexistentes, código espalhado em `src/` com sete
`sys.path.insert` de gambiarra, e uma pasta `src/models/` que misturava o código
da arquitetura com os pesos binários.

**O que foi feito:**

- A pasta intermediária `Exame CM204` sumiu. A raiz do repositório passa a ser a
  própria pasta `CORRETOR DE SIMULADOS` do Drive. Como o git só registra caminhos
  relativos à raiz, nenhum arquivo rastreado tem espaço no caminho.
- Todo o código virou um pacote único `corretor/`, com cinco subpacotes que
  seguem as etapas do pipeline: `visao`, `rede`, `inferencia`, `relatorio`,
  `treino`. Os sete `sys.path.insert` foram eliminados.
- `pesos/` e `dataset/` separados do código, por ciclo de vida: são artefatos,
  não fonte. Ambos versionados (13 KB e 619 PNGs sem dado pessoal).
- `data/` virou a fronteira única de dados, ignorada por inteiro. O `.gitignore`
  tem uma linha para isso — `/data/` — sem negação e sem exceção.
- Entrada unificada em `data/entrada/`. Antes era preciso editar o caminho na
  célula 1 para alternar entre `simulados_brutos` e `simulados_semi`.
- O caminho longo do Drive estava escrito à mão em dois lugares do notebook;
  agora é definido uma vez e reaproveitado.
- `requirements.txt` ganhou `pandas` e `XlsxWriter`, que o código usa e não
  estavam declarados.
- Apagados: `src/models/cnn_bolhas/` (o `.pth` descompactado por acidente),
  `cnn_bolhas_state.pth` (duplicata exata), `notebooks/pipeline_colab (1).ipynb`,
  `outputs/` e `recortes/` da raiz, `__pycache__/` e os três `run_pipeline*.py`
  (substituídos por `scripts/rodar_correcao.py`, que gera o Excel — os antigos
  paravam no CSV).

**O que foi verificado, não suposto:**

- O pipeline roda ponta a ponta na estrutura nova, com o scan SEMI real e os
  pesos reais, e produz o `.xlsx` com as três abas corretas.
- `git init` + `git add -A`: 645 arquivos versionados, **zero** `.tif`, **zero**
  arquivos sob `data/`, **zero** caminhos com espaço.
- O `corretor.config` passou a carregar uma vez por processo. Antes carregava
  duas, porque o notebook importava `src.opencv.X` enquanto os módulos internos
  importavam `opencv.X` — dois objetos distintos no `sys.modules`.
- Num clone limpo, a célula 1 cria `data/entrada` e imprime onde subir os scans.

**Justificativa:** o item 1 da versão anterior deste plano consertava os padrões
do `.gitignore` para bater com uma estrutura que era ela própria o problema. Com
uma fronteira única de dados, esquecer de proteger algo deixa de ser possível por
construção, em vez de depender de alguém lembrar de acrescentar mais uma linha.

---

## 1. Repositório no GitHub e gestão de acesso  ✅ CONCLUÍDO (16/09/2026)

Publicado em `CASD-curso/corretor-de-simulados`, público, MIT, com fork pessoal
em `MenageT29/corretor-de-simulados`. Fluxo de branch e token em uso.
**Pendente:** segundo owner na organização — hoje só Gonzalez tem esse acesso.

<details><summary>Redação original</summary>


**Problema:** o código só existe na pasta do Drive, sem controle de versão.
Testar no Colab é uma operação cega: não há histórico do que mudou nem forma
segura de reverter. E o projeto tem hoje um único desenvolvedor técnico, que sai
da instituição este ano — nenhuma solução de acesso pode depender de uma senha ou
conta pessoal repassada informalmente.

**Solução:**

1. `git init` na estrutura da Fase 0 e primeiro commit, ainda local. Conferir com
   `git status` que nenhum `.tif` aparece antes de qualquer push.
2. Criar o repositório na **organização GitHub da instituição**, não na conta
   pessoal, e publicar. Nome sugerido: `corretor-de-simulados` — o nome do repo
   não precisa bater com o da pasta no Drive.
3. Incluir um arquivo `LICENSE`. Sem licença, um repositório público é
   legalmente inutilizável por terceiros, o que anula o propósito de publicá-lo.
   MIT é a escolha usual para ferramenta institucional.
4. A pasta do Shared Drive vira o próprio repositório (`git clone` dentro dela),
   não uma cópia paralela.
5. Toda alteração em branch própria (`git checkout -b nome-da-mudanca`), nunca
   direto na `main`.
6. Autenticação por **token pessoal de cada colaborador** (GitHub → Developer
   settings → fine-grained token, escopo restrito ao repo, com validade), guardado
   como Colab Secret. Nunca em texto na célula, nunca compartilhado entre pessoas.
7. Um **fork** para a conta pessoal, preservando autoria dos commits e o vínculo
   público "forked from instituição/repo".
8. Antes da saída da instituição: ao menos uma outra pessoa com acesso de admin.

**Ponto de atenção operacional:** com o repositório dentro da pasta do Drive, o
`.git/` mora lá — são milhares de arquivos pequenos, que o Google Drive para
Desktop sincroniza mal. Quem só quer rodar pode usar `git clone --depth 1`, que
baixa o último instantâneo sem o histórico.

**Justificativa:** separa "código institucional em produção" (organização,
colaboradores com credencial própria e revogável individualmente) de "crédito de
autoria pessoal" (fork), sem senha compartilhada — que quebraria todo mundo de
uma vez se revogada e misturaria autoria de commits sob uma conta só.

</details>

---

## 2. Modo local — bloco único  ⏸️ ADIADO POR INTEIRO

**Decisão de 18/09/2026:** tudo que diz respeito a rodar fora do Colab passa a
viver neste item só. Nada aqui é feito antes de o modo local ser organizado como
frente própria — e nenhuma dessas três coisas afeta quem roda no Colab, que é o
caminho normal.

O que é "modo local": rodar por `scripts/rodar_correcao.py`, na máquina, sem
Drive e sem notebook. Existe como redundância — se o Colab ou o Drive caírem no
dia do simulado, o sistema precisa ter por onde rodar.

### 2.1 — Configuração de máquina separada da institucional

**Problema:** não há como um segundo desenvolvedor apontar os caminhos para outro
lugar sem alterar arquivo versionado. Hoje o fallback usa `data/` do próprio
repositório, e ponto.

**Solução:** `config.py` tenta importar um `corretor/config_local.py` opcional e,
se existir, deixa ele sobrepor os caminhos. Versionar apenas
`config_local.exemplo.py` com valores genéricos; o arquivo real já está no
`.gitignore`. Sem o arquivo local, tudo funciona com os padrões — ninguém precisa
criar nada para rodar.

### 2.2 — Caminho POSIX fixo quebra a planilha de revisão no Windows

**Problema:** `gerar_planilha_revisao.py:31` define
`TMP_IMG_DIR = Path("/tmp/corretor_revisao_imgs")`. Essa pasta não existe no
Windows, então o item 5 inteiro — a planilha de revisão — não roda em modo local.
Além disso a pasta nunca é limpa entre rodadas: se uma rodada teve 80 itens e a
seguinte tem 30, os `item_30.png` a `item_79.png` da anterior ficam lá.

**Solução:** trocar por `OUTPUTS_DIR / "revisao_imgs"`, que já respeita o sistema
operacional, e limpar a pasta no começo de cada geração.

### 2.3 — Validar o tamanho do gabarito antes de processar

**Problema:** `gerar_excel.py:51` indexa `gabarito_oficial[i-1]` sem nunca
conferir o tamanho do que leu de `gabarito_atual.txt`. No Colab a célula 3
protege; em modo local não há proteção nenhuma. Dois cenários:

- **Gabarito curto.** 58 letras para uma prova de 60. O script extrai ~15 mil
  recortes e roda a rede em todos eles — minutos de trabalho — e só então quebra
  com `IndexError: string index out of range`, uma mensagem que não menciona
  gabarito em lugar nenhum. Nenhum `.xlsx` é gerado e tudo é descartado.
- **Gabarito longo.** 62 letras para uma prova de 60. **Não quebra.** O laço lê as
  60 primeiras e ignora as duas sobrando, em silêncio. Se as letras extras
  estavam no começo — um cabeçalho colado junto, por exemplo — o gabarito inteiro
  fica deslocado e as 60 notas saem erradas sem nenhum sinal. Este é o caso
  perigoso.

**Solução:** validar **no começo de `scripts/rodar_correcao.py`**, antes da
extração, não dentro do `gerar_excel_final`. A diferença importa: validar no fim
só antecipa a mensagem para depois de dez minutos de processamento. Mensagem
esperada: `o gabarito de SEMI precisa de 60 letras, você forneceu 58`.

**Justificativa do bloco:** preserva a redundância de rodar localmente sem
misturar lógica institucional com caminho de máquina pessoal num repositório
público — e concentra num lugar só as três coisas que hoje fazem o modo local ser
um caminho de segunda classe.

---

## 3. Anulação de questão pela banca  ✅ CONCLUÍDO (16/09/2026)

Um `X` no gabarito faz a questão valer ponto para todos. Maiúscula ou minúscula
dão no mesmo. Testado: acertos foram de 9 para 11 com duas questões anuladas,
inclusive numa em que o aluno tinha feito dupla marcação.

---

## 4. Auditoria de falhas silenciosas  ✅ CONCLUÍDO (verificado direto no repositório em 17/09/2026)

Folha descartada no alinhamento deixou de só imprimir na tela e desaparecer:
`alinhar_gabarito.py` devolve o motivo da falha, `extracao_em_lote.py` grava cada
uma em `falhas_alinhamento.json` (registro persistente, não só print), e
`gerar_excel.py` cruza isso nas colunas `Alinhamento_OK` e `Motivo_Alinhamento`
da aba de resultados brutos, além de uma aba "Falhas de Leitura" dedicada. Bolha
cuja imagem falha ao abrir também é registrada (coluna `Bolhas_Ilegiveis`) em vez
de virar silenciosamente "vazia".

**Pendente:** a coluna `Orientacao_Detectada` (falha por folha girada) só existe
quando o item 8 — correção automática de rotação — for implementado; não fazia
parte do escopo deste item.

**Descartado em 18/09/2026 — não reabrir.** A revisão geral apontou que uma folha
descartada no alinhamento entra no cálculo estatístico como aluno que zerou a
prova: nota 0, contando nos grupos 27% e no ponto bisserial. Decisão: **irrelevante
na prática**, porque todo simulado vai passar pela correção manual sem exceção, e
essa linha nunca chega ao cálculo sem ter sido resolvida antes. O problema só
existiria para quem pulasse o checkpoint de revisão, que não é o fluxo previsto.

---

## 5. Correção manual sem quebrar as estatísticas  ✅ CONCLUÍDO (18/09/2026)

**Problema que existia:** `gerar_excel.py` calculava acertos, estatísticas e
relatório de uma vez e exportava tudo como valores estáticos. Corrigir uma
resposta na aba bruta depois do Excel gerado não recalculava nada — a correção
manual não tinha efeito nenhum no resultado final.

**O que foi construído** (mais ambicioso que a redação original, que previa um
CSV intermediário):

- **`corretor/revisao/gerar_planilha_revisao.py`** — gera um `.xlsx` com duas abas.
  - **Checkup:** visão geral do lote (processados, sem pendência, com pendência
    corrigível, descartados no alinhamento). Traz a seção das folhas descartadas
    no alinhamento, que não têm bolha extraída e por isso só podem ser resolvidas
    reescaneando ou transcrevendo à mão — com link para o scan original no Drive e
    os campos `Inscrição_Manual` e `Respostas_Manual`. E a lista de simulados com
    pendência corrigível, com link interno que pula direto para a linha certa da
    aba Correção.
  - **Correção:** uma linha por **item** pendente — questão ou posição de
    inscrição —, nunca por aluno. Cada linha traz o motivo, um campo `Corrigido`
    com validação de lista, e a **tira de recortes reais lado a lado** (as 5
    alternativas ou os 10 dígitos), montada por `montar_imagem.py`. Recorte
    corrompido vira um X vermelho no lugar, mantendo o rótulo alinhado; item sem
    preview recebe link para o scan original. Banner no topo com fórmula
    `COUNTBLANK` mostrando quantos itens faltam revisar.
- **`corretor/revisao/aplicar_revisao.py`** — lê a planilha preenchida e aplica as
  correções por `(Simulado, Campo)` sobre as linhas originais, devolvendo uma lista
  nova sem alterar a de entrada. Trata o caso do Excel guardar um dígito solto como
  número (`1.0` em vez de `1`, que corromperia as posições vizinhas da inscrição).
  Recalcula o `Link_Revisao`: depois da revisão, `EM BRANCO` e `NULA` deixam de
  contar como erro se foram confirmados pelo operador — o que sinaliza é item que
  ficou sem revisão nenhuma.
- **Células 4.5 e 4.6 do notebook** — baixar a planilha, revisar, subir de volta.
  A 4.6 tem fallback: se a 4.5 não rodou nesta sessão, recalcula a leitura em vez
  de falhar.
- **`gerar_excel_final(dados_brutos=...)`** — aceita o resultado revisado. Com
  `None`, calcula direto da leitura automática, que é o caminho de quem não teve
  nada a corrigir.

**Princípio preservado:** o cálculo estatístico nunca lê a saída do modelo
diretamente — sempre lê a lista que passou, ou não, por revisão humana. E a
revisão não é obrigatória, para não virar etapa chata que o voluntário pula.

**O que ainda toca este item:** o bloco 2.2 (caminho `/tmp`, que impede a planilha
de rodar no Windows) e o item 12, que acrescenta a detecção de inscrição duplicada
às duas abas.

---

## 6. Número de questões variável por aplicação  ⏸️ Depois do item 7

**Problema:** a coordenação às vezes aplica uma versão reduzida de uma prova já
calibrada (o template SEMI suporta 60 questões, mas uma aplicação usou 45). Hoje
não há como truncar sem editar o `config.py` à mão, porque `NUM_QUESTOES` é fixo
por template.

**Solução:** um campo `@param` a mais na célula de configuração do notebook, com
o número de questões efetivamente aplicadas, limitado ao máximo do template
ativo. O valor é gravado num arquivo local e lido pelo `config.py`, sobrepondo o
`NUM_QUESTOES` do template. `extrair_bolhas_respostas` para de recortar ao
atingir o número, e o resto do pipeline já itera sobre `NUM_QUESTOES`.

Validar contra o gabarito digitado: se o usuário informar 45 questões mas colar
um gabarito de 60 letras, avisar antes de rodar, não depois.

**Justificativa:** reaproveita a grade já calibrada em pixels sem exigir nova
calibração para cada aplicação reduzida. Criar entrada nova em `CONFIG_SIMULADOS`
continua sendo o caminho certo só quando a prova é fisicamente diferente, não
apenas mais curta. E mantém o princípio: o usuário preenche um campo, não edita
código.

**Entra junto com o item 14.** Número de questões variável sem faixa de matérias
configurável não fecha: uma prova de 30 questões não tem como saber quais são de
Português e quais de Matemática.

**Depende do item 11**, que precisa estar feito antes: enquanto o multiplicador da
nota for `2 if NUM_QUESTOES == 50 else (100/60)`, qualquer número de questões
diferente de 50 e 60 produz nota errada em silêncio.

---

## 7. Robustez do modelo contra marcação fraca  ▶️ PRÓXIMA FRENTE

**Problema:** o dataset de treino vem de uma única sessão de scan, sem marcação
fraca ou parcial rotulada, e a rede não tem dropout, weight decay nem
augmentation. A validação bate 100% já na época 1–2 — saturação, não
generalização.

**Evidência medida (15/09/2026):** rodando o modelo atual sobre os recortes
rotulados, as probabilidades saem em `0.0001, 0.0005, 0.0004` para preenchidas e
`0.9991, 0.9995, 0.9998` para vazias. Os limiares `LIMIAR_MAXIMO = 0.95` e
`LIMIAR_DUPLA = 0.60` não têm margem alguma para o caso intermediário. A rede tem
**2.621 parâmetros**.

**Causa raiz:** não é o scanner, que é fixo e de boa qualidade. É a variância de
cobertura da marcação após binarização — traço grosso contra traço fino ou leve —
que o dataset atual não representa.

**Solução, em ordem:**

1. Rotular o dataset novo conforme o desenho da seção 7.0 abaixo — dois
   contextos de aplicação, amostragem por questão inteira, sem curadoria manual
   de dificuldade.
2. Adicionar dropout e/ou weight decay, contra a saturação instantânea.
3. Treinar **do zero**, com pesos aleatórios, **sem augmentation** nesta primeira
   rodada. Partir do checkpoint antigo contaminaria o teste do passo 4 com o
   viés do lote velho.
4. **Split por contexto e por corredor, não por imagem.** Treino e validação
   usam as folhas de dia a dia e de vestibular sorteadas para essa finalidade
   (seção 7.0); teste usa folhas de dia a dia não sorteadas (Teste A) e um
   corredor inteiro de vestibular retido (Teste B), nenhum dos dois visto em
   treino.
5. **Augmentation fica condicional ao passo 4.** Se os testes A e B vierem bons,
   inclusive nos ambíguos, não é necessário. Testar em etapas evita não saber,
   no fim, qual mudança foi responsável pelo resultado.
6. **Recalibrar os limiares depois do passo 4.** Com dropout e marcação fraca no
   treino, a distribuição de saída tende a ficar menos extrema; os valores atuais
   podem não servir mais.
7. **Trocar a regra de decisão por uma regra relativa** — decidido em 18/09/2026,
   e só depois do retreino. Detalhe abaixo.

### 7.0 — Desenho do dataset novo (decisão de 19/09/2026)

**Mudança de premissa em relação à versão anterior deste item:** o dataset
deixa de vir de um lote único (620 recortes, 7-8 folhas de simulado tranquilo).
Passa a vir de dois contextos de aplicação distintos:

- **Dia a dia** — o uso real do sistema, simulados semanais do CASD, sem
  pressão de tempo de vestibular. 2 lotes novos, 335 folhas (215 + 120).
- **Vestibular** — aplicação de alta pressão, disponível em volume (1.250
  folhas em 6 corredores). Usado como fonte auxiliar, não como maioria do
  treino, para não deslocar o modelo para longe do cenário de uso real.

**Achado que motivou a proporção:** ao contrário do que se supunha, marcação
fraca é predominante no **dia a dia**, não no vestibular — o cenário de uso
real é o mais difícil, não o mais fácil. Isso inverte a lógica inicial de
"usar vestibular para ensinar o caso difícil": o dia a dia já é essa fonte.

**Proporção de treino:** 70% dia a dia / 30% vestibular, por número de folhas
— 80 folhas de dia a dia e 27 de vestibular (de pools de 335 e ~144
disponíveis, respectivamente; o restante fica de fora do treino, disponível
para ampliar depois se necessário).

**Método de amostragem, para não introduzir viés de curadoria manual:**

- Folhas sorteadas por seed fixa (reprodutível), nunca escolhidas por
  inspeção visual de dificuldade.
- Vestibular sorteado de pelo menos 2-3 corredores distintos, nunca de um
  só — preserva diversidade populacional sem inflar volume.
- Dentro de cada folha sorteada, rotula-se **2 questões inteiras** (as 5
  alternativas de cada, 10 bolhas) — não bolhas soltas. Preserva
  automaticamente a proporção real de 1 marcada / 4 vazias por questão, e
  aproveita `montar_imagem.py` (já existe) para anotar vendo o contexto
  comparativo das 5 alternativas lado a lado.
- Grade de inscrição recebe amostragem reduzida (1 grupo de 10 dígitos, em
  15% das folhas) — decisão deliberada de não replicar o esforço de
  rotulagem ali. Justificativa: o classificador é binário e não distingue de
  qual grade veio o recorte (mesma entrada 32×32, mesma decisão
  preenchida/vazia) — treinar bem em alternativas transfere para inscrição
  por construção da arquitetura. A amostra reduzida serve como checagem de
  que não há desvio sistemático entre grades, não como treino pesado de uma
  tarefa separada.
- Proporção de classe mantida natural (~1:4 marcada:vazia), não forçada a
  50/50 — é a proporção real do problema, e o desbalanceamento moderado não é
  a causa da saturação já diagnosticada (falta de diversidade de traço, não
  de proporção de classe). Ajuste de peso de classe (`pos_weight`) fica
  reservado para depois do treino, só se a matriz de confusão mostrar viés
  sistemático.

**Tabela de anotações necessárias (total: 1.000 recortes):**

| Contexto | Grade | Classe | Nº de recortes |
|---|---|---|---|
| Dia a dia | Alternativas | Marcada | 112 |
| Dia a dia | Alternativas | Vazia | 448 |
| Dia a dia | Inscrição | Marcada | 7 |
| Dia a dia | Inscrição | Vazia | 63 |
| Vestibular | Alternativas | Marcada | 48 |
| Vestibular | Alternativas | Vazia | 192 |
| Vestibular | Inscrição | Marcada | 3 |
| Vestibular | Inscrição | Vazia | 27 |
| **Total** | | | **1.000** |

**Split de teste, revisado:** o lote antigo (620 recortes, a base do dataset
até hoje) é **excluído por inteiro** — não entra em treino nem serve mais
como teste. Passam a existir dois testes com propósitos diferentes:

- **Teste A (uso real):** folhas de dia a dia não sorteadas para
  treino/validação.
- **Teste B (robustez a marcação sob pressão):** 1 corredor inteiro de
  vestibular, retido, nunca visto.

**Ferramentas de apoio, divididas por natureza da tarefa:**

- `corretor/treino/` — script de sorteio/segmentação: decide, a partir dos
  pools de folhas por contexto, quais folhas/questões/grupos de dígito
  entram na amostra, com seed fixa. É preparação de dataset, mesma natureza
  de `dataset_e_dataloaders.py`, que já mora ali.
- `corretor/revisao/` — interface de anotação: reaproveita `montar_imagem.py`
  para montar a tira de 5 alternativas (ou 10 dígitos) e gera uma planilha
  com dropdown de validação, no mesmo padrão que `aplicar_revisao.py` já lê.
  É ferramenta de confirmação humana via planilha, mesma natureza do que já
  existe ali — não mistura com o código de treino da rede.

### 7.1 — Regra de decisão relativa (passo 7)

**O que existe hoje.** Para cada questão, cinco probabilidades (de estar **vazia**
— ver a nota de inversão no fim deste documento). A regra ordena, pega as duas
menores e decide:

```
menor > 0,95          → EM BRANCO
segunda menor < 0,60  → NULA
senão                 → a letra da menor
```

Os dois cortes são **absolutos**: comparam cada probabilidade com um número fixo,
não com as outras bolhas da mesma questão. A docstring de `padrao_da_questao()`
chama a lógica de "relativa", mas o que é relativo ali é só a ordenação.

**O furo.** `(0,94 · 0,95 · 0,99 · 0,99 · 0,99)` — nenhuma bolha realmente
marcada — devolve uma alternativa, porque 0,94 passou por baixo de 0,95.

**A regra nova.** Decidir pela **margem** entre as duas menores
(`segunda − menor > margem`): marcada quando há distância clara; coladas e baixas,
dupla marcação; coladas e altas, em branco. Uma constante em vez de duas, e ela
acompanha qualquer distribuição que a rede produzir.

**Por que só depois do retreino.** Com a rede saturada de hoje, as duas regras dão
o mesmo resultado em praticamente todo caso — 0,0001 contra 0,9995, qualquer regra
acerta. A margem só começa a pagar quando a rede do passo 3 produzir valores
intermediários. Calibrar a constante antes seria ajustá-la contra uma distribuição
prestes a mudar. Este passo também substitui o passo 6: em vez de recalibrar dois
números, troca-se a forma da regra e calibra-se uma constante só.

**Sobre lotes de scan:** um lote é o conjunto de folhas escaneadas na mesma
sessão — mesmo dia, mesma passada de luz, geralmente a mesma remessa de papel e,
na prática, um grupo pequeno de alunos com seu próprio jeito de marcar. A rede
pode estar aprendendo artefatos de um lote específico — exposição, textura do
papel, o traço médio daqueles alunos — em vez do padrão real. E o `random_split`
por imagem não protege contra isso: se treino e validação contêm recortes do
mesmo lote, não é teste de generalização, é teste dentro da mesma distribuição.
O desenho da seção 7.0 substitui esse risco por split por contexto e por
corredor — nenhuma folha de teste (A ou B) pertence ao mesmo lote de scan usado
em treino ou validação.

**Nota de implementação:** o lote antigo (620 recortes, base do dataset até
hoje) sai de cena por inteiro — não entra em treino nem serve mais de teste
(decisão de 19/09/2026, seção 7.0). `preparar_dataloaders()` passa a apontar
para o dataset novo (dia a dia + vestibular, seção 7.0), com o split
treino/validação dentro dele; os testes A e B (folhas retidas) alimentam
`avaliar_teste.py`.

**Ao rotular os recortes de "marcada":** priorizar marcação fraca e parcial,
não só marcas escuras e óbvias, dentro do que a amostragem por questão inteira
(seção 7.0) já trouxer — é o ponto de trazer os dois contextos novos.

**Fazer o item 17 antes de começar:** enquanto `treinar.py` sobrescrever o arquivo
de produção, comparar modelos nesta fase é pedir para perder a referência.

---

## 8. Correção automática de rotação

**Problema:** scans às vezes chegam girados. `alinhar_gabarito.py` assume a
orientação correta e procura os marcadores nos cantos — se a folha está girada, a
detecção falha ou, pior, alinha errado sem avisar.

**Solução:** antes do alinhamento de perspectiva, detectar a orientação — testar
os marcadores nas quatro rotações possíveis, ou usar a proporção do retângulo
exterior — e aplicar `cv2.rotate` antes de seguir com o pipeline existente.
Registrar o resultado em `Orientacao_Detectada` (item 4).

**Justificativa:** sem isso, uma folha girada é descartada ou processada errado
sem sinal de alerta. É o item mais caro em tempo de depuração, e por isso fica
para depois dos que protegem contra nota errada.

---

## 9. README e documentação do repositório  🔚 ÚLTIMO ITEM

**Problema:** o README atual descreve uma estrutura que nunca existiu direito e
que agora está duplamente errada, referencia um script de calibração inexistente,
e não documenta nada do que foi decidido aqui.

**Solução em duas etapas.** Um README **mínimo** junto com o item 1, porque
repositório público sem README não é um repositório excelente: o que o sistema
faz, a estrutura de pastas, e o passo a passo de uso via Colab. Depois, com os
demais itens prontos, a **versão completa**: como cadastrar uma prova nova, como
funciona a revisão manual antes do Excel, como marcar questão anulada, como gerar
token e abrir branch, e uma seção curta de limitações conhecidas do modelo.

Incluir também um teste de fumaça: um script que roda o pipeline sobre um scan de
referência e confere que a saída bate com o esperado. Não é suíte de testes — é
uma rede de segurança para o item 7, que troca o modelo, e para quem assumir o
projeto depois e precisar saber se quebrou alguma coisa. O scan de referência não
pode ir para o repositório; documentar como apontar para um local.

**Acrescentado em 18/09/2026 — dado sensível fora da fronteira `data/`:** a
versão completa precisa dizer o que acontece com os arquivos *depois* do
download. A planilha de revisão e o `.xlsx` final saem do Colab por
`files.download` para o computador do voluntário, contendo matrícula de aluno e
recortes da grade de inscrição. A regra do `/data/` protege o repositório e o
`conferir_publicacao.py` protege o push, mas nada hoje orienta o operador sobre
guardar, apagar ou não reencaminhar esses arquivos. É uma seção curta de texto,
não código.

**Justificativa:** o README é a porta de entrada de quem herdar o projeto.
Escrever a versão completa antes dos outros itens geraria retrabalho, mas deixar
o repositório meses sem README nenhum contradiz o objetivo de publicá-lo bem.

---

# Itens da revisão geral de código (18/09/2026)

Vieram de uma leitura completa dos 16 módulos, dos 2 scripts, do notebook, do
`.gitignore` e do `requirements.txt`.

---

## 10. Ponto bisserial sem a própria questão

**Problema:** `gerar_excel.py:112` calcula o ponto bisserial correlacionando o
acerto de cada questão com `Acertos_Totais` — um total que **inclui aquela mesma
questão**. Acertar a questão 7 aumenta o total da questão 7, então parte da
correlação medida é a questão consigo mesma. O índice sai sistematicamente
inflado, sempre para cima, para todas as questões.

**Solução:** correlacionar o acerto da questão com o total **menos** ela própria:

```python
bisserial = df_acertos[col_q].corr(notas - df_acertos[col_q])
```

**Justificativa:** é a definição padrão do índice em psicometria (*corrected
item-total correlation*). Com 50–60 questões o viés é pequeno, mas é sistemático,
e o relatório é entregue à coordenação como medida de qualidade das questões.
Custo: uma linha.

---

## 11. Nota final sem número escrito à mão

**Problema:** `gerar_excel.py:76` decide o multiplicador com
`2 if NUM_QUESTOES == 50 else (100 / 60)`. Os dois casos existentes são a mesma
conta, e qualquer terceiro caso cai no `else` e sai errado sem avisar — numa
aplicação de 45 questões (o cenário do item 6), a nota máxima viraria 75.

**Solução:** `nota = acertos * 100 / NUM_QUESTOES`, sem condicional.

**Justificativa:** troca dois números escritos à mão por uma fórmula que vale para
qualquer prova. **Precisa estar feito antes do item 6.**

---

## 12. Alerta de inscrição duplicada na planilha de revisão

**Problema:** duas folhas lidas com o mesmo número de inscrição é o sintoma mais
provável de erro de leitura da grade de inscrição — e hoje nada aponta. As duas
linhas seguem para o cálculo como se fossem alunos distintos, ou o mesmo aluno
aparece duas vezes com provas diferentes. O modelo pode ter lido os 7 dígitos
"com confiança" nos dois casos, então nenhum item entra na aba Correção.

**Solução, na planilha de revisão (item 5):**

1. Conferir inscrições repetidas entre os simulados do lote, depois da inferência.
2. **Aba Checkup, logo abaixo da contagem de descartados no alinhamento:** uma
   linha com a contagem de duplicatas encontradas.
3. **Aba Checkup, à direita da seção "Simulados com pendência corrigível":** uma
   tabela que agrupa, por número de inscrição repetido, os simulados que caíram
   nele, cada um com o link para o scan original no Drive. O ponto é o usuário
   abrir os dois cartões lado a lado e ter **certeza** de que são alunos
   diferentes — ou seja, de que houve erro de leitura — em vez de a coincidência
   passar batida.
4. **Aba Correção:** todo simulado com inscrição duplicada passa a gerar item
   pendente do tipo inscrição, permitindo corrigir o número, mesmo quando o modelo
   não marcou nenhum dígito como ambíguo.

**Justificativa:** é a única falha de leitura que não se manifesta como dúvida do
modelo — as duas leituras são confiantes, e só a comparação entre folhas revela o
problema. Sem essa conferência, a revisão manual não tem como pegar o caso.

---

## 13. Fundir os dois módulos de inferência

**Problema:** `inferir_simulado.py` e `inferir_inscricao.py` são ~80% o mesmo
código: mesmo padrão de nome de arquivo, mesmo laço, mesmos limiares, mesma
exportação de CSV. `padrao_da_questao()` e `ler_digito()` são a mesma função, com
formatação diferente no retorno. Duas cópias significam que toda correção precisa
ser feita duas vezes, e que uma delas será esquecida.

**Solução:**

1. Um módulo único — `corretor/inferencia/inferir_simulado_e_inscricao.py` — com
   uma função de decisão compartilhada, que devolve a chave vencedora **e o
   motivo**, e um laço genérico parametrizado pela grade (5 alternativas × N
   questões, ou 10 dígitos × 7 posições).
2. `ler_digito` deixa de devolver `"?"` para os dois casos: passa a devolver
   **`BRANCO`** e **`MULTIPLA`**, como as questões já fazem.

**Justificativa do passo 2:** hoje a informação é jogada fora na inferência, e é
por isso que a planilha de revisão só consegue escrever "Em branco ou dupla
marcação (ambígua)" — ela não sabe qual dos dois foi. Distinguir custa nada e
deixa o operador saber o que está olhando antes de abrir a imagem.

**Atenção ao fundir:** a função de decisão compartilhada é a mesma que o item 7.1
vai trocar por uma regra de margem. Fundir primeiro significa trocar a regra em um
lugar só depois.

---

## 14. Matérias configuráveis por faixa ou por lista de questões

**Problema:** a estrutura de matérias hoje é uma faixa fixa por template
(`CONFIG_SIMULADOS[...]["MATERIAS"]`, com `inicio` e `fim`), e a lista de matérias
que entra na nota está escrita à mão dentro do relatório
(`gerar_excel.py:68-71`, `if SIMULADO_ATIVO == "CASDINHO"`). Com número de
questões variável (item 6), isso não fecha: uma prova de 30 questões não tem como
saber quais são de Português e quais de Matemática.

**Solução:**

1. As provas com padrão fixo continuam como estão — CASDINHO (15 Português, 15
   Matemática, …) e SEMI seguem definidos no `CONFIG_SIMULADOS`, sem o usuário
   precisar preencher nada.
2. Quando o número de questões for variável, o usuário escolhe a faixa de cada
   matéria. Dois casos que precisam funcionar:
   - uma prova de 15 questões, todas marcadas como Matemática;
   - uma prova de 30 questões, as 15 primeiras Português e as 15 últimas
     Matemática.
3. A estrutura aceita tanto **faixa** (`início`–`fim`) quanto **lista de questões
   específicas**, para o caso de uma matéria não ocupar posições contíguas.
4. A lista de matérias que compõe a nota sai do código e vira chave do config.
   Hoje o CASDINHO soma Português + Matemática + CH + CN, ignorando História,
   Geografia, Biologia e Química, que são subdivisões já contadas dentro de CH e
   CN — essa regra só existe escrita dentro do `if`, e some se alguém acrescentar
   uma matéria ao config sem mexer no relatório.

**Entra junto com o item 6.** Um não funciona sem o outro.

---

## 15. Limpeza de resíduos

Nenhum destes muda comportamento; todos deixam o código mais difícil de ler para
quem herdar o projeto, e dois imprimem ruído na tela do operador. Decisões de
18/09/2026 já tomadas — é só executar.

- **Remover `cols_questoes`** (`gerar_excel.py:26`). Monta `["1", …, "50"]`, os
  nomes das colunas num formato antigo; hoje são `Q1`…`Q50`. Nunca é usada, e se
  fosse estaria errada. O comentário acima dela ("Garante que as colunas '1' a
  '50' sejam tratadas como strings") também sai — a linha não faz isso.
- **Remover o print de debug** (`gerar_excel.py:28`,
  `print("Colunas encontradas:", …)`), no código e qualquer impressão equivalente
  no notebook. Ele existia para descobrir se as colunas chegavam como `"1".."50"`
  ou `"Q1".."Q50"` — pergunta já resolvida. Hoje só despeja 60+ nomes de coluna na
  saída do Colab, na frente do voluntário.
- **Trocar a mensagem de `inferir_completo.py:116`** por exatamente:
  `"Nenhum dado consolidado — rode a extração antes."` A atual
  (`"Nenhum dado consolidate."`) mistura português com inglês, e é justamente a
  mensagem do pior cenário — nada foi lido —, então precisa dizer o que fazer.
- **Corrigir a mensagem de erro do modelo** (`modelo_bolhas.py:25`): manda colocar
  `cnn_bolhas.pth` em `models/`, pasta que não existe desde a Fase 0. Hoje é
  `pesos/`. É o texto que alguém lê no momento em que algo já deu errado.
- **Apagar os comentários em inglês** deixados por uma sessão de edição:
  `inferir_completo.py:1, 6, 114` (`# REMOVED RESULTADOS_CSV_PATH from import`,
  `# REMOVED SAVING TO CSV…`).
- **Apagar nove imports mortos** apontados pelo `pyflakes`: `pathlib.Path` em seis
  arquivos (`gerar_excel.py`, `modelo_bolhas.py`, `dataset_e_dataloaders.py`,
  `plotar_historico.py`, `avaliar_teste.py`, `treinar.py`), `csv` e
  `collections.defaultdict` em `inferir_completo.py`,
  `corretor.config.SIMULADOS_DIR` no mesmo arquivo, e `torch` em
  `arquitetura_da_rede.py`.
- **NÃO mexer em `_link`** (`aplicar_revisao.py:124`). O `pyflakes` acusa, mas é
  falso positivo: o underscore é a convenção Python para "recebo e ignoro de
  propósito", e ele existe para o desempacotamento da linha da aba Checkup ficar
  legível na ordem das colunas.

---

## 16. Apagar o arquivo de lixo da raiz do repositório

**Problema:** `criptsconferir_publicacao.py`, 17 KB na raiz, está publicado no
`main`. O conteúdo não é código: é o texto de ajuda do comando `less`, capturado
para um arquivo por um comando que saiu errado — provavelmente
`scripts/conferir_publicacao.py` perdendo o `s` e a barra no caminho. Num
repositório que é cartão de visitas, é o primeiro arquivo estranho que alguém vê.

**Solução:**

1. Apagar o arquivo.
2. Conferir se `scripts/` e `docs/` foram mesmo para o `main` — o README manda
   rodar `python scripts/conferir_publicacao.py` e cita `docs/plano_alteracoes.md`,
   e os dois precisam existir no clone para essas instruções valerem:
   `git ls-files scripts docs`.

---

## 17. Treino não pode sobrescrever os pesos de produção

**Problema:** `treinar.py:85` salva direto em `pesos/cnn_bolhas.pth`. Rodar o
treino para testar qualquer coisa substitui o modelo que está em produção, sem
aviso e sem cópia. Hoje é recuperável porque o arquivo está versionado no git,
mas depende de alguém perceber.

**Solução:** salvar com nome datado e por lote
(ex.: `cnn_bolhas_2026-09-18_lote2.pth`) e promover a produção como passo
manual, separado. É o mesmo esquema de nomes que o item 7 já prevê para a fase de
comparação entre modelos.

**Fazer antes de começar o item 7**, que vai treinar várias vezes seguidas
comparando resultados.

---

## 18. Limpar a resposta uma vez só

**Problema:** `gerar_excel.py` calcula a mesma coisa duas vezes, com o mesmo
regex, em dois pontos distantes (linhas 47 e 95):

```python
resposta_limpa = df_bruto[col_q].astype(str).str.upper().str.replace(r"[^A-Z]", "", regex=True)
```

**O que essa linha faz:** as colunas `Q1`…`Q60` não contêm só letras — contêm
`"A"`, mas também `"EM BRANCO"`, `"NULA(MARCADAS>1)"` e o que o operador digitou
na planilha de revisão. O regex tira tudo que não é letra e o `.isin(['A'…'E'])`
seguinte mantém só as cinco letras válidas, transformando o resto em `""`. O
resultado é **a letra que o aluno marcou, ou vazio** — o filtro que separa uma
resposta de um texto de estado. O regex em si existe para tolerar digitação humana
(`"a "` com espaço, `"B."` com ponto), que passaria direto pelo `.isin` sozinho.

**Solução:** calcular uma vez, num `df_respostas`, e reusar nos dois lugares (o
cálculo de acertos e a contagem de frequência por alternativa).

**Justificativa:** duas cópias da mesma regra significam que uma correção futura
vai acertar uma e esquecer a outra — e as duas alimentam números diferentes da
mesma planilha.

---

## 19. Import do config com efeito colateral  ⏳ POR ÚLTIMO (antes do item 9)

**Problema:** as últimas linhas do `config.py` criam seis pastas no disco:

```python
for pasta in [ENTRADA_DIR, OUTPUTS_DIR, RECORTES_BOLHAS_DIR, RECORTES_INSCRICAO_DIR, PESOS_DIR, SIMULADOS_DIR]:
    try:
        if not pasta.exists():
            pasta.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
```

Um `import` deveria só dar nome a coisas. Aqui, importar `corretor.config` — mesmo
para ler uma constante só — escreve no disco. Duas consequências concretas:

1. **A célula de diagnóstico do notebook não consegue reportar o que falta.** A
   célula "📁 Estrutura: os caminhos batem?" começa com
   `from corretor.config import (…, SIMULADOS_DIR, …)` e depois imprime `OK` ou
   `FALTA` para cada caminho. Só que **o import acabou de criar as pastas**, então
   `SIMULADOS_DIR` imprime `OK` sempre — inclusive quando deveria alertar. Uma
   célula feita para avisar que algo está faltando é incapaz de avisar sobre a
   pasta dos cartões.
2. **O `except OSError: pass` engole falha de escrita em silêncio.** Drive não
   montado, pasta somente leitura, disco cheio: o `mkdir` falha, nada é impresso,
   e minutos depois o código quebra em outro lugar com "arquivo não encontrado",
   longe da causa.

**Solução:** criar cada pasta no ponto onde ela é usada — o que
`extracao_em_lote.py:141-143` já faz por conta própria — e deixar o `config.py`
apenas definindo caminhos.

**Decisão de 18/09/2026:** fica por último entre os itens de código. O problema é
real e está anotado, mas não produz nota errada nem atrapalha o fluxo normal.

---

## EXTRA — tirar o disco do caminho entre recortar e inferir

*Registrado como extra, depois de tudo. Avaliação do usuário (18/09/2026): a
correção já roda rápido o bastante, e o esforço rende muito mais investido em
deixar a inferência excelente — o item 7 — para que a correção manual seja mínima.
Não puxar este item para frente sem motivo novo.*

**Situação:** a extração escreve 370 PNGs por folha em disco; a inferência reabre
cada um com PIL, aplica `Grayscale()` (a imagem já é cinza) e `Resize((32,32))`
(já é 32×32), e roda a rede **uma bolha por vez**.

**Medido (15/09/2026, registro no fim deste plano):** 77% do tempo de inferência
é abrir e preparar PNG, não computar. As mesmas 370 bolhas em lote único levam
17 ms contra 82 ms uma a uma.

**O que a mudança elimina:** o I/O de milhares de arquivos por lote, os dois
regex que reconstroem `simulado → questão → alternativa` a partir do nome do
arquivo, e toda a classe de falha "o PNG não abriu" — que existe hoje e precisou
ser instrumentada no item 4.

**O que continua:** os PNGs seguem sendo salvos. A planilha de revisão precisa
deles para montar as tiras de comparação, e a rotulagem do item 7 precisa deles
para treinar. A diferença é que deixam de ser o caminho por onde o dado passa, e
passam a ser apenas um subproduto guardado.

**Custo honesto:** mexe em `extracao_em_lote.py`, no módulo único de inferência do
item 13 e em `inferir_completo.py`. É a maior redução de complexidade disponível
no projeto e a única da revisão que eu classificaria como refatoração de verdade.

---

# Pendente de decisão — NÃO implementar sem aval do Gonzalez

Quatro achados da revisão de 18/09/2026 que ainda não foram decididos. Estão aqui
para não se perderem, não como tarefa. **Uma sessão que leia este plano não deve
executá-los.**

1. **A lista `["A","B","C","D","E"]` aparece em cinco lugares:**
   `config.ALTERNATIVAS`, `extracao_em_lote.py:97`, `"ABCDE"` em
   `gerar_planilha_revisao.py:208`, e três vezes em `gerar_excel.py`. Junto: o
   `70` escrito à mão na célula 10 do notebook, que é `NUM_DIGITOS_INSCRICAO * 10`.
2. **A célula 1 do notebook instala uma lista de pacotes diferente do
   `requirements.txt`** (`opencv-python-headless torch torchvision xlsxwriter`).
   Faltam `pandas`, `openpyxl` e `Pillow`, que hoje funcionam só porque o Colab já
   os traz. `!pip install -q -r requirements.txt` resolve e acaba com as duas
   listas divergentes.
3. **A célula 3 do notebook duplica o "50 ou 60"** (`esperado = 50 if … else 60`),
   dado que já está em `CONFIG_SIMULADOS` — e esse dicionário não depende dos
   arquivos `.txt`, então dá para ler dele.
4. **`gerar_planilha_revisao.py:201-224`:** os dois ramos (questão e inscrição)
   são quase idênticos, mudando só a lista de crops e os valores aceitos. Escolher
   os dois antes e ter um bloco único de escrita corta ~15 linhas.

---

## Estimativa de tempo

Horas de trabalho ativo, não dias corridos. Não inclui espera por terceiros.
Não há registro de horas reais além do item 0 — as estimativas dos itens já
concluídos são as originais, não o tempo gasto.

| Item | Estimativa | Situação |
|---|---|---|
| 0. Reorganização estrutural | — | ✅ Feita. Consumiu ~4h, incluindo a verificação ponta a ponta |
| 1. Repositório GitHub, licença e acesso | 1,5–2,5h | ✅ Concluído — falta só o segundo owner |
| 2. Modo local (bloco único: 2.1, 2.2, 2.3) | 1,5–2h | ⏸️ Adiado por inteiro |
| 3. Anulação de questão | 0,25h | ✅ Concluído |
| 4. Auditoria de falhas silenciosas | 1–1,5h | ✅ Concluído |
| 5. Checkpoint de correção manual | 1–1,5h | ✅ Concluído |
| 6. Número de questões variável | 1–1,5h | Entra junto com o 14; exige o 11 antes |
| 7. Robustez do modelo (+ regra relativa) | 6–9h (+2–3h se precisar de augmentation) | ▶️ Próxima frente — limitada por atenção humana na rotulagem |
| 8. Correção automática de rotação | 3–5h | Único item que exige depurar casos-limite de visão computacional |
| 9. README, documentação e teste de fumaça | 2–3h | 🔚 Último. Boa parte do conteúdo já está redigida neste plano |
| 10. Ponto bisserial sem a própria questão | 0,1h | Uma linha |
| 11. Nota final sem número escrito à mão | 0,1h | Uma linha; antes do item 6 |
| 12. Alerta de inscrição duplicada | 1,5–2h | Mexe nas duas abas da planilha de revisão |
| 13. Fundir os dois módulos de inferência | 1,5–2h | Reescrita, não conserto — conferir os dois caminhos depois |
| 14. Matérias configuráveis | 1–1,5h | Entra junto com o item 6 |
| 15. Limpeza de resíduos | 0,5h | Nenhum muda comportamento |
| 16. Apagar o lixo da raiz | 0,1h | Mais a conferência de `scripts/` e `docs/` no `main` |
| 17. Treino não sobrescreve produção | 0,1h | Antes de começar o item 7 |
| 18. Limpar a resposta uma vez só | 0,25h | |
| 19. Import do config com efeito colateral | 0,5h | ⏳ Por último entre os de código |
| EXTRA. Tirar o disco do caminho | 3–4h | Não é prioridade — ver a nota no item |

---

## Correções fora do plano

**Limiar dos marcadores de canto (15/09/2026).** `AREA_MINIMA_MARCADOR` estava em
10.000 no CASDINHO e 9.500 no SEMI, ajustado a 2-4% do tamanho medido em um lote
específico. Um lote novo falhou por 3% e nenhuma folha foi corrigida. Medindo
três lotes: marcadores entre 9.376 e 10.520, maior não-marcador ~1.400. Os dois
modelos passaram a usar 5.000, entre os dois grupos. A resolução nunca variou
(todos 2480×3508) — o que muda é quanto do quadrado preto sobrevive à
binarização.

**Arquitetura de execução (16/09/2026).** O notebook passou a clonar o código do
GitHub a cada sessão em vez de lê-lo do Drive, e a gravar a planilha final em
`data/resultados` no Drive. O Drive guarda só dados. Elimina o `.git` sincronizando
mal no Drive e garante que o Colab sempre roda a versão atual da `main`.

**Bug de reexecução no notebook (16/09/2026).** A célula 1 fazia `rmtree` da pasta
em que o Colab estava, quebrando a partir da segunda execução. Corrigido com
`os.chdir("/content")` antes.

**Erro de arredondamento acumulado no recorte (data não registrada).** As
coordenadas de grade eram inteiras e o recorte multiplicava um passo truncado, o
que acumulava desvio ao longo das 16 linhas de cada bloco — chegava a ~20 px na
última questão e produzia os recortes em forma de meia-lua vistos na planilha de
revisão. Hoje `passo_x`/`passo_y` são float e cada borda é arredondada
individualmente.

---

## Registro de medições

Feitas em 15/09/2026, em CPU de 2 threads, com o scan SEMI real e os pesos
atuais. Servem de linha de base para comparar depois do item 7.

| O quê | Valor |
|---|---|
| Parâmetros da CNNBin | 2.621 |
| Bolhas por folha SEMI | 370 (60 questões × 5 + grade de inscrição 7 × 10) |
| Extração OpenCV | ~320 ms por folha (100% CPU; a GPU não participa) |
| Inferência das 370 bolhas | ~360 ms por folha |
| Fração da inferência que é abrir/preparar PNG | ~77% |
| Fração que é cômputo da rede | ~23% |
| Mesmas 370 bolhas em lote único | 17 ms, contra 82 ms uma a uma |

**Leitura:** dos ~680 ms por folha, a GPU T4 encosta em ~80 ms. O notebook pede
runtime T4 e o código usa CUDA quando disponível, mas o gargalo é o laço que
processa uma bolha por vez, não o cômputo. Se o Colab negar GPU num dia de pico,
o sistema roda igual — o que é bom para robustez.

**Inversão das probabilidades — a confusão mais fácil deste código:** o
`ImageFolder` ordena as classes alfabeticamente, então `preenchida=0` e
`vazia=1`, e a sigmoid devolve a probabilidade de a bolha estar **vazia**.
Probabilidade baixa significa bolha marcada. É por isso que `padrao_da_questao()`
ordena crescente e pega a menor.
