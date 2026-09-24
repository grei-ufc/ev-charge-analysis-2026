# TCC: Análise dos Impactos do Aumento da Penetração de Carregadores de Veículos Elétricos na Rede de Distribuição de Baixa Tensão Brasileira via Co-simulação

**👨‍💻 Autor:** Paulo Victor Pereira Lima  
*Estudante de Engenharia Elétrica na Universidade Federal do Ceará (UFC) e membro do **GREI** (Grupo de Redes Elétricas Inteligentes).*

---

Plataforma desenvolvida para análise do impacto da integração em larga escala de Veículos Elétricos (EVs) e Sistemas Fotovoltaicos (PVs) em redes elétricas de distribuição. O projeto utiliza co-simulação assíncrona baseada no framework [Mosaik](https://mosaik.offis.de/) e no motor de fluxo de potência [OpenDSS](https://www.epri.com/pages/sa/opendss), expandindo a infraestrutura modular do projeto OpenTES.

## 🎯 Objetivo e Escopo (TCC)

Este repositório consolida o ambiente de testes do Trabalho de Conclusão de Curso (TCC). A pesquisa avalia diferentes **cenários de penetração** de veículos elétricos (ex: conservador, moderado e agressivo) alocados estocasticamente nas barras de baixa tensão. 

O impacto na rede é mensurado segundo as seguintes métricas:
* **Indicadores PRODIST:** Duração Relativa da Transgressão de Tensão Precarizada (DRP) e Tensão Crítica (DRC) em janelas semanais (1008 leituras de 10 min).
* **Análise de Carregamento:** Avaliação térmica de alimentadores e sobrecarga em transformadores/barras críticas.
* **VDI (Voltage Deviation Index):** Soma dos desvios quadráticos das tensões nas barras em relação a 1 pu.
* **Outros:** Perdas ativas totais e níveis de desequilíbrio entre fases.

**A Rede Elétrica:** Em vez de utilizar redes sintéticas ou sistemas padrão IEEE, a co-simulação é ancorada no **alimentador real ESB01S4 da subestação ESB (Eusébio)**, na Região Metropolitana de Fortaleza (ENEL), extraído da Base de Dados Geográfica da Distribuidora (BDGD) e convertido para OpenDSS através do `bdgd2dss`.

> 💡 **Nota de Arquitetura:** Este projeto é uma adaptação da arquitetura **tsre-der-opentes**, desenhada para estudos avançados de co-simulação. O repositório original base pode ser encontrado em: [https://github.com/grei-ufc/tsre-der-opentes](https://github.com/grei-ufc/tsre-der-opentes).

## 🚀 Tecnologias Utilizadas

* **Python**: Linguagem principal (gerenciamento de dependências e ambientes via `uv`).
* **Mosaik (API v3)**: Framework de orquestração de co-simulação.
* **OpenDSS (`py-dss-interface`)**: Motor de cálculo de fluxo de potência.
* **Docker / Docker Compose**: Isolamento e execução assíncrona dos simuladores em microsserviços.
* **Pandas / NumPy**: Processamento e injeção de séries temporais.

## 📂 Mapa de Diretórios

```text
ev-analysis-2026/
├── docker-compose.yml         # Orquestração dos simuladores (Portas 57xx)
├── scenarios/                 # Scripts executáveis de simulação
├── src/                       # Códigos-fonte (orquestradores de dados e simuladores)
├── data/                      # Base de dados brutos e arquivos nativos .dss das redes
├── output/                    # Saídas geradas pelas simulações (CSV de resultados e JSON da rede)
└── docs/                      # Documentações detalhadas do processamento de dados e simuladores
```

> **Para detalhes técnicos e metodológicos:** O funcionamento interno da clusterização de cargas, sanitização de dados fotovoltaicos, equacionamento da demanda dos VEs e fluxo de microsserviços estão documentados em profundidade na pasta `docs/`.

## 🛠️ Como Executar

A arquitetura do projeto requer que a preparação dos dados, a infraestrutura dos contêineres e o orquestrador sejam rodados em uma sequência específica. Siga os passos abaixo detalhadamente:

### 1. Preparação e Instalação de Dependências

Certifique-se de que você possui o **Docker** e o gerenciador de pacotes **uv** instalados no seu sistema.

#### Instalação do Docker
A co-simulação utiliza contêineres para isolar os microsserviços (OpenDSS, PVs, Baterias, EVs). O Docker precisa estar ativo durante toda a execução.
- **Windows / macOS:** Baixe e instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/). Após instalar, abra o programa e certifique-se de que o motor do Docker está rodando.
- **Linux:** Instale o Docker Engine seguindo a documentação oficial ou os comandos da sua distribuição (ex: `sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin`). Lembre-se de iniciar o serviço (`sudo systemctl enable --now docker`).

#### Configuração do Ambiente Virtual (Python)
Para instalar todas as bibliotecas necessárias e preparar o ambiente isolado do projeto, execute o comando abaixo na raiz do diretório:
```bash
uv sync
```

### 2. Preparação dos Dados e da Rede (Pré-Requisito)

Antes de rodar a co-simulação, é obrigatório processar os datasets brutos para gerar as matrizes temporais e alocar fisicamente os novos equipamentos na rede do OpenDSS.

**Passo 2.1:** Gere a matriz de curvas de recarga normalizadas dos Veículos Elétricos a partir do dataset original. Isso criará arquivos CSV leves que serão lidos na simulação:
```bash
uv run python src/ajuste-dados/codigos-evs/pipeline_ev.py
```

**Passo 2.2:** Realize a alocação estocástica (sorteio geográfico) e instancie as casas que possuirão carros elétricos. Este comando compilará a rede do OpenDSS invisivelmente para descobrir os nós válidos e escreverá as definições no arquivo `ESB01S4_evs.dss`:
```bash
uv run python src/simulators/util/ev_creator.py
```

### 3. Subindo a Infraestrutura de Microsserviços

Levante todos os simuladores (as APIs do Mosaik) em background via Docker. 
A arquitetura conta com regras de tolerância a falhas (`restart: always`) e tempo limite estendido (`-t 600`) para suportar o tempo de compilação de redes massivas no OpenDSS sem que os contêineres morram por inatividade:
```bash
docker compose up -d
```

### 4. Executando um Cenário de Co-Simulação

Com os dados limpos, a rede preparada e o Docker escutando nas portas locais, dispare o script orquestrador correspondente ao cenário que deseja testar. Uma barra de progresso do Mosaik indicará o andamento passo a passo.

**Cenário Completo (Rede + Geração Solar + Veículos Elétricos):**
```bash
uv run python scenarios/scenario_ESB01S4_EVs.py
```

**Cenário Base de Comparação (Apenas Rede + Geração Solar):**
```bash
uv run python scenarios/scenario_ESB01S4.py
```

Ao final de qualquer simulação, um arquivo consolidado em CSV (ex: `result_run_ESB01S4.csv`) contendo todas as variáveis temporais e um arquivo `topologia_*.json` serão exportados e salvos na pasta `output/` para que você possa gerar seus gráficos e análises.

