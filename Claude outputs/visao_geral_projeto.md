# Projeto Leitor de Gabaritos — Visão Geral

*Atualizado em 16/09/2026.*

## O que o sistema faz

Corrige automaticamente cartões-resposta escaneados dos simulados do CASD. Lê a
inscrição e as alternativas marcadas de cada aluno e gera uma planilha com notas
por matéria e análise estatística da prova.

## Onde cada coisa vive

**Código:** repositório público no GitHub, `CASD-curso/corretor-de-simulados`,
licença MIT. Pertence à organização da instituição, não a uma conta pessoal.
Existe um fork em `MenageT29/corretor-de-simulados` que preserva a autoria.

**Dados:** pasta `CORRETOR DE SIMULADOS` do Shared Drive, que passou a guardar
apenas `data/entrada` (os `.tif` que alguém sobe) e `data/resultados` (as
planilhas geradas). O código não mora mais no Drive.

**Execução:** Google Colab, runtime GPU T4. O notebook clona o repositório do
GitHub a cada sessão (`git clone --depth 1`), então roda sempre a versão mais
recente da `main` sem ninguém precisar atualizar o Drive à mão.

## Pipeline, em ordem

1. **Alinhamento** (`corretor/visao/alinhar_gabarito.py`): binariza a folha
   inteira com Otsu, localiza quatro marcadores quadrados nos cantos por
   contornos, reconstrói o quarto geometricamente se achar só três, e reprojeta
   a imagem para 800×1130 px.
2. **Recorte** (`corretor/visao/extracao_em_lote.py`): fatia a folha alinhada em
   bolhas de 32×32 px — grade de inscrição (7 dígitos × 10) e grade de respostas.
   Cada recorte passa por padding, gamma e threshold adaptativo.
3. **Classificação** (`corretor/inferencia/`): a `CNNBin`
   (`corretor/rede/arquitetura_da_rede.py`, 2.621 parâmetros) decide se cada
   bolha está preenchida ou vazia.
4. **Consolidação** (`corretor/relatorio/gerar_excel.py`): compara as
   probabilidades das 5 alternativas entre si para decidir a resposta, detectar
   questão em branco e dupla marcação; cruza com o gabarito oficial e gera o
   `.xlsx` com três abas — resultados brutos, estatísticas por aluno e relatório
   psicométrico por questão (frequência por alternativa, acerto nos grupos 27%
   superior e inferior, ponto bisserial).

Duas provas calibradas em `corretor/config.py`: **CASDINHO** (50 questões) e
**SEMI** (60), cada uma com sua geometria de grade.

## Convenções

**Questão anulada:** um `X` na posição correspondente do gabarito oficial faz a
questão valer ponto para todos os alunos, independentemente do que foi lido no
cartão. Maiúscula ou minúscula dão no mesmo.

**Dado sensível:** os `.tif` contêm a grade de inscrição preenchida, ou seja,
matrícula de aluno. Tudo que entra ou sai da correção fica em `data/`, ignorada
por inteiro pelo git, sem exceção. O `scripts/conferir_publicacao.py` falha se um
scan, uma planilha de notas ou um caminho pessoal estiver prestes a ser
publicado — e também se os pesos da rede saírem do versionamento por engano.

## Medições (15/09/2026, CPU 2 threads, 1 folha SEMI = 370 bolhas)

| | |
|---|---|
| Extração OpenCV | ~320 ms por folha, 100% CPU |
| Inferência das 370 bolhas | ~360 ms por folha |
| Fração da inferência que é abrir/preparar PNG | ~77% |
| Fração que é cômputo da rede | ~23% |
| As mesmas 370 bolhas em lote único | 17 ms, contra 82 ms uma a uma |

Dos ~680 ms por folha, a GPU T4 encosta em ~80 ms. O gargalo é o laço que
processa uma bolha por vez, não o cômputo. Se o Colab negar GPU, o sistema roda
igual.

**Inversão das probabilidades:** o `ImageFolder` ordena as classes em ordem
alfabética, então `preenchida=0` e `vazia=1`, e a sigmoid devolve a probabilidade
de a bolha estar **vazia**. Probabilidade baixa significa bolha marcada. É por
isso que `padrao_da_questao()` ordena crescente e pega a menor.

## Limitações conhecidas

O modelo foi treinado com recortes de uma única sessão de escaneamento, sem
exemplos de marcação fraca ou parcial. As probabilidades saem saturadas — em
torno de 0,0001 para preenchida e 0,9995 para vazia — o que deixa os limiares de
decisão sem margem real para o caso intermediário.

Folhas giradas não são corrigidas automaticamente: a detecção de marcadores falha
e a folha é descartada.

Quando uma folha é descartada por falha de alinhamento, isso aparece apenas como
mensagem na tela, sem registro na planilha final.

Os três pontos estão endereçados no `plano_alteracoes.md`.
