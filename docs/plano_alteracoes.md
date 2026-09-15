# Projeto Leitor de Gabaritos — Plano de Alterações

*Revisão de 15/09/2026. Substitui a versão anterior (03/09/2026).*

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

## Ordem de implementação

`0 (feita) → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9`

---

## Fase 0 — Reorganização estrutural  ✅ CONCLUÍDA, aguardando aprovação

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

**Pendente da versão anterior:** o item 2 (separar configuração local da
institucional) foi parcialmente resolvido de lado — o caminho pessoal do Windows
saiu do `config.py` quando `data/` virou a fronteira. O que sobrou virou o item 2
abaixo.

---

## 1. Repositório no GitHub e gestão de acesso

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

---

## 2. Fechar a configuração local

**Problema:** resta decidir como alguém roda o sistema fora do Colab sem editar
o `config.py` institucional. Hoje o fallback local funciona (`data/` do próprio
repositório), mas não há como um segundo desenvolvedor apontar para outro lugar
sem alterar arquivo versionado.

**Solução:** `config.py` tenta importar um `corretor/config_local.py` opcional e,
se existir, deixa ele sobrepor os caminhos. Versionar apenas
`config_local.exemplo.py` com valores genéricos; o arquivo real já está no
`.gitignore`. Sem o arquivo local, tudo funciona com os padrões — ninguém
precisa criar nada para rodar.

**Justificativa:** preserva a redundância de rodar localmente se o Drive ou o
Colab caírem, sem misturar lógica institucional com caminho de máquina pessoal
num repositório público.

---

## 3. Anulação de questão pela banca

**Problema:** não existe mecanismo para marcar uma questão como anulada (correta
para todos) quando a banca anula após a aplicação.

**Solução:** aceitar um sentinela no gabarito oficial — `*` na posição da questão
anulada. Em `gerar_excel.py`, na comparação resposta × gabarito, se a posição for
`*`, acerto = 1 para todos, independentemente do que foi lido. A célula do
gabarito no notebook passa a aceitar o caractere e a exibir quantas questões
foram anuladas, para o usuário confirmar que digitou o que queria.

**Justificativa:** é o item de melhor relação valor/esforço do plano — uma
condicional a mais num laço que já existe, resolvendo uma situação que acontece
todo ano. Vem cedo por isso.

---

## 4. Auditoria de falhas silenciosas

**Problema:** se uma folha não tem 3 ou 4 marcadores de canto detectados, ela é
descartada com um `print` e some do resultado, sem registro. Se a imagem de uma
bolha falha ao abrir, o código assume probabilidade 1.0 (vazia) sem sinalizar.
Não há rastro de qual aluno ou questão foi afetado.

**Solução:** capturar as falhas como colunas do CSV intermediário, consumidas
pelo checkpoint de revisão do item 5 **antes** do cálculo de nota:

- `Alinhamento_OK` — sim/não e o motivo (ex.: "cantos não encontrados")
- `Bolhas_Ilegiveis` — quais questões tiveram imagem que falhou ao abrir
- `Orientacao_Detectada` — quando a rotação não pôde ser determinada (item 8)
- os casos de `NULA(MARCADAS>1)` e `EM BRANCO`, que já existem no resultado

Depois do Excel gerado, manter também uma aba "Falhas de Leitura" com o mesmo
conteúdo, como registro permanente. Mas o consumo principal é no CSV, antes da
revisão, não depois.

**Justificativa:** o sistema gera nota real de aluno. Falha sem rastro impede
correção e pode gerar nota errada sem ninguém saber que aquele caso precisava de
atenção. Reportar só no Excel final chega tarde demais.

---

## 5. Correção manual sem quebrar as estatísticas

**Problema:** `gerar_excel.py` calcula acertos, estatísticas e relatório uma
única vez em Python e exporta como valores estáticos. Corrigir uma resposta na
aba bruta depois do Excel gerado não recalcula nada — a correção manual não tem
efeito nenhum no resultado final.

**Solução:** inserir um checkpoint editável entre a inferência e o cálculo:

1. A inferência exporta o CSV intermediário, já com as colunas de falha do item 4
   preenchidas — não só o resultado do modelo.
2. A revisão humana acontece nesse CSV, guiada pelas colunas de falha.
3. Um segundo ponto de entrada lê o CSV **já revisado** e só então roda o cálculo
   de acertos, estatísticas e relatório, gerando o Excel final.

O cálculo estatístico nunca lê a saída do modelo diretamente — sempre lê o CSV
que passou (ou não) por revisão humana.

**Para o usuário final:** no notebook isso vira uma célula a mais entre as duas
que já existem, que baixa o CSV e diz o que conferir. Quem não tiver nada a
corrigir roda a seguinte e segue. A revisão não pode virar etapa obrigatória e
chata, senão é pulada.

**Justificativa:** hoje há risco de nota incorreta silenciosa. A mudança resolve
sem reescrever a lógica de cálculo — só a ordem das etapas.

---

## 6. Número de questões variável por aplicação

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

---

## 7. Robustez do modelo contra marcação fraca

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

1. Rotular ~100 casos ambíguos reais e **separá-los como conjunto de
   calibração**, não usar no treino. Serve de métrica objetiva de antes/depois.
2. Adicionar dropout e/ou weight decay, contra a saturação instantânea.
3. Treinar **do zero**, com pesos aleatórios, incluindo os exemplos ambíguos, e
   **sem augmentation** nesta primeira rodada. Partir do checkpoint antigo
   contaminaria o teste do passo 4 com o viés do lote velho.
4. **Split por lote, não por imagem.** Treino e validação usam 100% de um lote
   novo de ~600 recortes; teste usa 100% do lote antigo (620), nunca visto em
   treino. Como vem de outra sessão de scan, é a métrica honesta de generalização
   entre sessões.
5. **Augmentation fica condicional ao passo 4.** Se o teste no lote antigo vier
   bom, inclusive nos ambíguos, não é necessário. Testar em etapas evita não
   saber, no fim, qual mudança foi responsável pelo resultado.
6. **Recalibrar os limiares depois do passo 4.** Com dropout e marcação fraca no
   treino, a distribuição de saída tende a ficar menos extrema; os valores atuais
   podem não servir mais.

**Sobre lotes de scan:** um lote é o conjunto de folhas escaneadas na mesma
sessão — mesmo dia, mesma passada de luz, geralmente a mesma remessa de papel e,
na prática, um grupo pequeno de alunos com seu próprio jeito de marcar. Todas as
~620 imagens de treino vêm de um lote só (prefixo `202606041948`, 7-8 folhas). A
rede pode estar aprendendo artefatos daquele lote — exposição, textura do papel,
o traço médio daqueles alunos — em vez do padrão real. E o `random_split` atual
embaralha por imagem, então treino e validação contêm recortes do mesmo lote:
não é teste de generalização, é teste dentro da mesma distribuição.

**Nota de implementação:** os dois lotes já são conjuntos de arquivos separados,
então não junte as pastas num único `ImageFolder`. `preparar_dataloaders()`
aponta só para o lote novo, com o split 70/15 já existente dentro dele; o lote
antigo vira um segundo `ImageFolder`, usado só em `avaliar_teste.py`.

**Ao curar os 300 recortes de "preenchida" do lote novo:** priorizar marcação
fraca e parcial, não só marcas escuras e óbvias — é o ponto de trazer esse lote.

**Depois de validar:** se a acurácia no lote antigo vier boa, considerar uma
versão final de produção treinada com os dois lotes combinados — mas só depois de
registrado o resultado do teste limpo como referência honesta.

**Consequência para a estrutura:** `pesos/` vai abrigar dois arquivos ao mesmo
tempo durante a comparação. Nomear com data e lote (ex.:
`cnn_bolhas_2026-06_lote1.pth`) e manter `cnn_bolhas.pth` como o de produção.

---

## 8. Correção automática de rotação

**Problema:** scans às vezes chegam girados. `alinhar_gabarito.py` assume a
orientação correta e procura os marcadores nos cantos — se a folha está girada, a
detecção falha ou, pior, alinha errado sem avisar.

**Solução:** antes do alinhamento de perspectiva, detectar a orientação — testar
os marcadores nas quatro rotações possíveis, ou usar a proporção do retângulo
externo — e aplicar `cv2.rotate` antes de seguir com o pipeline existente.
Registrar o resultado em `Orientacao_Detectada` (item 4).

**Justificativa:** sem isso, uma folha girada é descartada ou processada errado
sem sinal de alerta. É o item mais caro em tempo de depuração, e por isso fica
para depois dos que protegem contra nota errada.

---

## 9. README e documentação do repositório

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

**Justificativa:** o README é a porta de entrada de quem herdar o projeto.
Escrever a versão completa antes dos outros itens geraria retrabalho, mas deixar
o repositório meses sem README nenhum contradiz o objetivo de publicá-lo bem.

---

## Estimativa de tempo

Horas de trabalho ativo, não dias corridos. Não inclui espera por terceiros.

| Item | Estimativa | Observação |
|---|---|---|
| 0. Reorganização estrutural | — | Feita. Consumiu ~4h, incluindo a verificação ponta a ponta |
| 1. Repositório GitHub, licença e acesso | 1,5–2,5h | Sem dependência externa: o acesso institucional já existe |
| 2. Fechar a configuração local | 0,5–1h | Menor que antes: a parte difícil saiu junto com a Fase 0 |
| 3. Anulação de questão | 0,25h | Uma condicional num laço existente, mais o aviso no notebook |
| 4. Auditoria de falhas silenciosas | 1–1,5h | Mudança localizada em três pontos já mapeados |
| 5. Checkpoint de correção manual | 1–1,5h | `exportar_csv=False` e a separação inferência/escrita já existem |
| 6. Número de questões variável | 1–1,5h | Um `@param` a mais e um `break` antecipado, mais a validação cruzada |
| 7. Robustez do modelo | 6–9h (+2–3h se precisar de augmentation) | Limitado por atenção humana na rotulagem, não por código |
| 8. Correção automática de rotação | 3–5h | Único item que exige depurar casos-limite de visão computacional |
| 9. README, documentação e teste de fumaça | 2–3h | Boa parte do conteúdo já está redigida neste plano |
| **Total restante** | **~17–25h** (~19–28h com a rodada extra de augmentation) | A carga do ITA varia semana a semana; hora total é a âncora mais confiável |

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
