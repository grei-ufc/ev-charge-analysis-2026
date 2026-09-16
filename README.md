# Plataforma de Co-Simulação de Redes Elétricas (Mosaik + OpenDSS)

Plataforma desenvolvida para análise do impacto de Recursos Energéticos Distribuídos (DERs), como Veículos Elétricos (EVs) e Sistemas Fotovoltaicos (PVs), em redes elétricas de distribuição. O projeto utiliza co-simulação baseada na biblioteca [Mosaik](https://mosaik.offis.de/) e no simulador de redes [OpenDSS](https://www.epri.com/pages/sa/opendss), com regras de inversores inteligentes (Smart Inverters) baseadas na norma IEEE 1547-2018 (via OpenDER).

Este projeto é uma adaptação da arquitetura `tsre-der-opentes` desenhada especialmente para estudos avançados em TCC.

## 🚀 Tecnologias Utilizadas

* **Python**: Linguagem principal (gerenciamento de dependências e ambientes via `uv`).
* **Mosaik (API v3)**: Framework de orquestração de co-simulação.
* **OpenDSS (`py-dss-interface`)**: Motor de cálculo de fluxo de potência.
* **OpenDER**: Lógicas de controle para Inversores Inteligentes.
* **Docker / Docker Compose**: Isolamento e execução assíncrona dos simuladores.
* **Pandas / NumPy**: Processamento e injeção de séries temporais (dados climáticos e curvas de carga).

## 📂 Mapa de Diretórios

```text
ev-analysis-2026/
├── docker-compose.yml         # Orquestração dos simuladores (Portas 57xx)
├── scenarios/                 # Scripts executáveis de simulação (ex: scenario_ESB01S4.py)
├── src/
│   ├── ajuste-dados/          # Scripts de tratamento e preparação de dados (EVs, Cargas, PV)
│   └── simulators/            # Adaptadores Mosaik (OpenDSS, PV, Inversores, Collector)
├── data/
│   ├── datasets/              # Base de dados (curvas-de-carga, geradores-fv, veiculos-eletricos)
│   └── rede/                  # Scripts e arquivos nativos .dss das redes (ESB01S4, 13Bus)
├── output/                    # Saídas (CSV de resultados e JSON com a topologia renderizada)
├── tests/                     # Testes unitários
└── docs/                      # Documentações adicionais
```

## 📊 Pipeline de Preparação de Dados (Pré-Simulação)

Antes da co-simulação, os dados brutos de cargas residenciais, geração fotovoltaica e demanda de veículos elétricos passam por um rigoroso processo de engenharia de dados. Eles são limpos, discretizados e equalizados para a mesma base temporal (passos de 10 minutos) requerida pelo OpenDSS, divididos em três grandes frentes na pasta `src/ajuste-dados/`:

### 1. Processamento de Cargas Residenciais
Orquestrado pelo `pipeline_cargas.py`, o processamento da demanda residencial é feito em 4 passos:
- **Passo 1 (Extração):** Converte as definições nativas de LoadShapes do OpenDSS para formato CSV tratável.
- **Passo 2 (Telemetria):** Processa dados brutos de telemetria das unidades consumidoras, limpando anomalias e padronizando os carimbos de tempo.
- **Passo 3 (Clusterização):** Aplica algoritmos de agrupamento (clustering) para classificar os perfis de consumo em comportamentos típicos, reduzindo a complexidade computacional.
- **Passo 4 (Montagem Semanal):** Reconstrói as curvas de demanda em janelas de semanas contínuas para o OpenDSS, realizando emendas perfeitas nas bordas noturnas.

### 2. Processamento de Geração Fotovoltaica (GD)
Focado na conversão de dados reais de irradiação solar brasileira (dataset BR-PVGen), é gerenciado pelo `converter_gd_para_pvsystem.py`:
- **Sanitização de Ruído:** Sensores de irradiação noturna frequentemente acusam pequenos ruídos negativos. O código aplica restrições baseadas em limites físicos (`clip(lower=0)`), impedindo falhas na injeção de potência.
- **Exclusão de Outliers:** Identifica e remove permanentemente curvas de estações meteorológicas corrompidas (ex: anomalias de temperatura).
- **Otimização de I/O:** Em vez de gerar um arquivo pesado e redundante de `LoadShape` para cada casa da rede, a arquitetura consolida as curvas solares em perfis matemáticos únicos (`shape_irrad_{id}`), reduzindo o peso computacional das simulações em mais de 90%.

### 3. Processamento de Veículos Elétricos (EVs)
O pipeline matemático de modelagem dos VEs é orquestrado pelo arquivo `orquestrador_ev.py`, estruturado em 4 passos:
1. **Passo 1 (Limpeza):** Sanitização de separadores decimais e formatação de datas via Pandas (filtrando apenas colunas necessárias para aliviar a RAM).
2. **Passo 2 (Filtragem e Time-Shift):** Extração exata das semanas de Setembro. É aplicado um deslocamento de **+2.5 horas** no dataset norueguês para que o pico local coincida com o horário de pico residencial brasileiro (18h30 - 19h00).
3. **Passo 3 (Agrupamento):** Organização hierárquica das sessões por usuário e por índice numérico da semana, garantindo que os carros que recarregam na virada da noite mantenham a integridade temporal.
4. **Passo 4 (Motor Físico):** Sob a premissa de *Carga Imediata*, o algoritmo varre o dataset simulando potências de **3.6 kW** e **7.2 kW**. Ele cria uma malha super fina de 1 minuto, aloca a energia cirurgicamente a partir da hora da conexão, e aplica o *resample* (média) para exportar os pontos em blocos de 10 minutos normalizados.

**Artefatos Gerados:** Todos os orquestradores finalizam gravando planilhas enxutas e pré-formatadas (`ev_loadshapes_normalized.csv`, etc) totalmente prontas para injeção rápida no OpenDSS.

## ⚙️ Arquitetura dos Simuladores

O projeto divide a responsabilidade computacional através de microsserviços. O Mosaik troca dados no início de cada "step" com os seguintes contêineres:

| Serviço Docker | Porta | Função |
| :--- | :--- | :--- |
| **opendss** | `5771` | Calcula tensões, correntes e resolve a topologia AC. |
| **pv-panel** | `5778` | Calcula a potência DC gerada com base no clima. |
| **smart-inverter** | `5780` | Converte DC/AC aplicando funções de rede avançadas. |
| **inverter-std** | `5777` | Converte DC/AC no modo clássico (sem funções de rede). |
| **csv-data-1 e 2** | `5775 / 5776` | Injetam temperatura e irradiância a cada passo. |
| **collector** | `5773` | Escuta os resultados de todos e agrupa no `result.csv`. |
| **battery** | `5772` | Simula o armazenamento e despacho de baterias BESS. |

## 🛠️ Como Executar

### 1. Preparação
Certifique-se de que você possui o **Docker** e o **uv** instalados. 

#### Instalação do Docker
Antes de executar, é necessário ter o Docker (e o Docker Compose) instalados no computador. Para Windows recomenda-se instalar o Docker Desktop.

- Baixe e instale: https://www.docker.com/get-started
- Página do Docker Desktop (Windows/macOS): https://www.docker.com/products/docker-desktop/

**Para Linux**
Se for usar Linux (ex.: Ubuntu/Debian), instale o Docker Engine seguindo a documentação oficial:
- Guia de instalação do Docker Engine (Ubuntu): https://docs.docker.com/engine/install/ubuntu/
- Guia geral de instalação: https://docs.docker.com/engine/install/

Exemplo rápido (Ubuntu) — execute como root ou com `sudo`:
```bash
sudo apt update
sudo apt install ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
```

Para confirmar a instalação, verifique as versões:
```bash
docker --version
docker compose version
```

> **Importante:** durante a execução o Docker precisa estar em execução. No Windows, abra o Docker Desktop e aguarde até o daemon estar ativo; no Linux, verifique que o serviço `docker` esteja em execução (`sudo systemctl status docker`).

#### Configurando dependências locais (uv)
Para a primeira execução, instale as dependências e prepare o ambiente virtual executando na raiz do projeto:
```bash
uv sync
```

### 2. Iniciando os Simuladores
Levante a infraestrutura Docker em background. Os contêineres ficarão num loop aguardando a conexão do Mosaik (regra `restart: always` garante que eles reabram a porta após um cenário terminar):
```bash
docker compose up -d
```

### 3. Executando um Cenário
Dispare o script principal desejado através do `uv run`:
```bash
uv run scenarios/scenario_ESB01S4.py
```
*(O andamento não imprimirá logs poluídos na tela, mas ao final será notificado a geração do CSV e do JSON da rede na pasta `output/`)*

