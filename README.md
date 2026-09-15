# Corretor de Simulados

Correção automática de cartões-resposta escaneados. Lê os cartões, identifica a
inscrição e as alternativas marcadas de cada aluno, e gera uma planilha com as
notas e a análise estatística da prova.

Feito para os simulados do CASD, onde a correção manual de algumas centenas de
cartões consumia um tempo que ninguém tinha.

## Como funciona

O cartão passa por quatro etapas:

1. **Alinhamento** — quatro marcadores quadrados nos cantos da folha são
   localizados por contornos, e a imagem é reprojetada para um tamanho fixo de
   800×1130 px. Se só três marcadores forem encontrados, o quarto é reconstruído
   geometricamente.
2. **Recorte** — a folha alinhada é fatiada em bolhas individuais de 32×32 px:
   a grade de inscrição (7 dígitos × 10 posições) e a grade de respostas.
3. **Classificação** — uma CNN binária pequena (2.621 parâmetros, treinada do
   zero) decide, para cada bolha, se está preenchida ou vazia.
4. **Consolidação** — as probabilidades das 5 alternativas de cada questão são
   comparadas entre si para decidir a resposta, detectar questão em branco e
   dupla marcação. O resultado é cruzado com o gabarito oficial e vira a planilha.

Duas provas estão calibradas: **CASDINHO** (50 questões) e **SEMI** (60), cada
uma com sua própria geometria de grade em `corretor/config.py`.

## Uso (Google Colab)

É o caminho normal. Requer acesso ao Shared Drive do CASD.

1. Suba os cartões escaneados (`.tif` ou `.tiff`) em **`data/entrada/`**.
2. Abra `Corretor_Simulados.ipynb` no Colab, com runtime **GPU T4**.
3. Rode as células na ordem. Você preenche três campos: o nome do simulado, o
   modelo (CASDINHO ou SEMI) e o gabarito oficial.
4. Baixe o `.xlsx` gerado.

> ⚠️ A pasta `/content/dados_locais/` do Colab é apagada quando a sessão encerra.
> Baixe a planilha antes de fechar.

A planilha tem três abas: **Resultados Brutos** (inscrição e alternativa lida por
questão, com link para o scan quando há erro de leitura), **Estatísticas por
Aluno** (acertos por matéria e nota final) e **Relatório Sintético dos Testes**
(por questão: frequência de cada alternativa, percentual de acerto no total e nos
grupos 27% superior e inferior, e ponto bisserial).

## Uso (local)

Sem Colab, para desenvolvimento:

```bash
pip install -r requirements.txt

# data/ precisa conter:
#   entrada/*.tif        os cartoes
#   simulado_ativo.txt   CASDINHO ou SEMI
#   gabarito_atual.txt   as letras do gabarito, sem espacos
#   nome_simulado.txt    nome do .xlsx de saida (opcional)

python scripts/rodar_correcao.py
```

## Estrutura

```
corretor/          codigo, um pacote so
  visao/           alinhamento e recorte das bolhas (OpenCV)
  rede/            arquitetura da CNN
  inferencia/      leitura das bolhas e consolidacao das respostas
  relatorio/       geracao da planilha
  treino/          treino e avaliacao do modelo
pesos/             cnn_bolhas.pth, os pesos treinados (versionado, 13 KB)
dataset/           619 recortes de bolha rotulados, para retreino
scripts/           entrypoint de linha de comando e conferencia pre-publicacao
data/              entrada e saida. IGNORADA pelo git - ver abaixo
```

## Dados de aluno

**Os cartões escaneados contêm a grade de inscrição preenchida, ou seja, a
matrícula do aluno.** Tudo que entra ou sai da correção fica em `data/`, que é
ignorada por inteiro pelo git. Não existe exceção nessa regra, e não deve passar
a existir.

Antes de qualquer push, rode:

```bash
python scripts/conferir_publicacao.py
```

Ele falha se um scan, uma planilha de notas ou um caminho pessoal estiver
prestes a ser publicado — e também se os pesos da rede tiverem saído do
versionamento por engano, o que deixaria o repositório inutilizável para quem
clonasse.

## Limitações conhecidas

O modelo foi treinado com recortes de uma única sessão de escaneamento, sem
exemplos de marcação fraca ou parcial. Na prática ele satura: as probabilidades
saem próximas de 0,0001 para bolha preenchida e 0,9995 para vazia, o que deixa os
limiares de decisão sem margem real para o caso intermediário. Uma marcação leve,
de lápis fino ou pouca pressão, é território que o modelo não viu.

Folhas escaneadas de cabeça para baixo ou giradas não são corrigidas
automaticamente — a detecção de marcadores falha e a folha é descartada.

Quando uma folha é descartada por falha de alinhamento, isso hoje aparece apenas
como mensagem na tela, sem registro na planilha final.

Os três pontos acima estão endereçados em `docs/plano_alteracoes.md`.

## Autores

Menage T29 e Fóton T26.

## Licenca

MIT. Ver o arquivo [LICENSE](LICENSE).
