# Relatório de Auditoria Cadastral da BDGD: Identificação de Consumidores Desativados e Impacto na Convergência do OpenDSS

**Projeto:** Análise de Integração de Veículos Elétricos e Geração Fotovoltaica em Redes de Distribuição (TCC)  
**Alimentador:** `ESB01S4` (Enel Distribuição Ceará - Base 2024-12-31 V11)  
**Transformador Crítico:** `TRF_TOK5079A` (150 kVA, 13.8 kV / 0.38 kV)  
**Data:** 22 de Outubro de 2026  
**Status:** Diagnóstico, Saneamento Cadastral e Validação Concluídos  

---

## 1. Sumário Executivo

Durante a validação de convergência diária em regime quase-estacionário (144 passos de 10 minutos) no alimentador `ESB01S4`, foram observados dois fenômenos anômalos simultâneos:
1. **Sobrecarga Extrema no Transformador `TRF_TOK5079A`:** Um equipamento nominal de 150 kVA atendendo um pico de demanda agregada de 533 kW (sobrecarga de 355%), com 207 barras em seu ramal secundário;
2. **Instabilidade Numérica no OpenDSS:** Colapso de tensão na cauda da rede secundária para níveis próximos a 0,49–0,50 pu, disparando um ciclo limite (*limit cycle*) oscilatório no limiar de transição de modelo de carga (`vminpu=0.50`), provocando não-convergência em 59,72% do dia.

Para investigar se essa sobrecarga decorria de inconsistência física ou cadastral, realizou-se uma auditoria diretamente no Geodatabase original da ANEEL/Enel Ceará (`Enel_CE_39_2024-12-31_V11_20250822-1151.gdb`), consultando a situação de ativação dos consumidores (`SIT_ATIV`) na tabela `UCBT_tab`.

### Principais Descobertas:
- **No Alimentador Completo (`ESB01S4`):** Das 1.363 unidades consumidoras de Baixa Tensão cadastradas, **673 unidades (49,38%) estão oficialmente DESATIVADAS (`SIT_ATIV == 'DS'`)** e apenas 690 (50,62%) estão ativas (`AT`).
- **No Transformador Crítico (`TRF_TOK5079A`):** Das 164 unidades consumidoras conectadas ao secundário, **107 unidades (65,24%) estão DESATIVADAS (`SIT_ATIV == 'DS'`)** e apenas 57 (34,76%) estão ativas (`AT`).
- **Causa-Raiz no Pipeline do `bdgd2opendss`:** A ferramenta de conversão automática omitiu a leitura e filtragem da coluna `SIT_ATIV` do dicionário de dados da ANEEL ([`bdgd2dss.json`](file:///mnt/c/Users/pvict/anaconda3/envs/bdgd2opendssvenv/Lib/site-packages/bdgd2opendss/config/bdgd2dss.json)), mapeando `load` a partir de `RAMAL` sem checar se a unidade consumidora estava ativa ou desligada. Isso gerou curvas sintéticas de demanda para residências desocupadas, demolidas ou com fornecimento cancelado.
- **Resultado do Saneamento Cadastral:**
  - **955,22 kW de potência fantasma eliminada** em todo o alimentador (1.344 objetos de carga removidos);
  - **429,08 kW eliminados no `TRF_TOK5079A`** (alívio de **81,1%** da demanda anterior);
  - A potência ativa real no `TRF_TOK5079A` normalizou para **100,16 kW** (66,8% de carregamento sobre 150 kVA nominal);
  - A convergência do OpenDSS no Cenário 5 foi de **100%**, com média de iterações caindo para **3,23** (máximo de apenas 4 iterações).

```
                          CADASTRO BDGD ORIGINAL (ESB01S4)
                        ┌─────────────────────────────────┐
                        │      Total: 1.363 UCs de BT     │
                        └───────────────┬─────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │   ATIVOS (SIT_ATIV=AT)│               │ DESATIVADOS (SIT=DS)  │
        │    690 UCs (50,62%)   │               │    673 UCs (49,38%)   │
        └───────────┬───────────┘               └───────────┬───────────┘
                    │                                       │
                    │   Sem filtro no 'bdgd2opendss'       │
                    └───────────────────┬───────────────────┘
                                        ▼
                        ┌─────────────────────────────────┐
                        │ CargasBT_Sintetico_...dss       │
                        │ TODAS as 1.363 UCs convertidas  │
                        │ + 277 pontos de IP (Total 1.619)│
                        └───────────────┬─────────────────┘
                                        ▼
                        ┌─────────────────────────────────┐
                        │  TRF_TOK5079A (150 kVA nominal) │
                        │  - 57 UCs Ativas (34,76%)       │
                        │  - 107 UCs Fantasmas (65,24%)   │
                        │  ------------------------------ │
                        │  Pico Anterior: 533 kW (355%)   │
                        │  Pico Saneado: 100 kW (66,8%)   │
                        │  Convergência: 100% (3.2 iter)  │
                        └─────────────────────────────────┘
```

---

## 2. Fundamentação Cadastral e Regulatória (PRODIST / ANEEL)

### 2.1 O que é a BDGD e o Campo `SIT_ATIV`?
A Base de Dados Geográfica da Distribuidora (BDGD) é regulamentada pelo **Módulo 8 do PRODIST** da ANEEL. Ela consolida o inventário físico, elétrico, geográfico e comercial de todas as instalações de distribuição das concessionárias brasileiras.

Na camada `UCBT_tab` (Tabela de Unidades Consumidoras de Baixa Tensão), a ANEEL define os seguintes campos chave de controle cadastral:

| Campo | Tipo | Descrição ANEEL | Valores Válidos |
| :--- | :--- | :--- | :--- |
| `COD_ID` | String | Identificador do consumidor (anonimizado via SHA-256 pela Enel para cumprimento da LGPD) | Hash hexadecimal de 64 caracteres |
| `RAMAL` | String | Código de identificação do ramal de conexão da UC | Código alfanumérico (ex: `UC1048017`, `U52513810`) |
| `SIT_ATIV` | String | **Situação de Ativação do Consumidor** | **`AT` (Ativo)**: UC ligada e faturada.<br>**`DS` (Desativado)**: UC desligada definitivamente. |
| `DAT_CON` | Date | Data de conexão original da unidade consumidora | Data formato `AAAA-MM-DD` |
| `CAR_INST` | Double | Carga instalada declarada (kW) | Valor numérico positivo |
| `UNI_TR_MT` | String | Transformador de Média Tensão ao qual a UC está conectada | Código do transformador (ex: `TOK5079`) |

### 2.2 Por que existem consumidores `DS` na base enviada à ANEEL?
As concessionárias mantêm registros de consumidores desativados por exigências de rastreabilidade regulatória e patrimonial:
1. Histórico de medição e faturamento para eventuais revisões tarifárias;
2. Cadastro georreferenciado do ramal de ligação e do poste de derivação (o ativo físico de rede ainda existe, mesmo que o medidor tenha sido retirado);
3. Possibilidade de religação ou reativação por novo titular no mesmo lote imobiliário.

No entanto, para modelagem matemática de fluxo de potência em regime quase-estacionário, **apenas unidades consumidoras com `SIT_ATIV == 'AT'` devem ser modeladas como fontes de consumo ativo e reativo**.

---

## 3. Auditoria no Pipeline `bdgd2opendss`

Ao auditar os arquivos do conversor `bdgd2opendss` instalado no ambiente Python (`/mnt/c/Users/pvict/anaconda3/envs/bdgd2opendssvenv/Lib/site-packages/bdgd2opendss`), identificou-se no arquivo [`bdgd2dss.json`](file:///mnt/c/Users/pvict/anaconda3/envs/bdgd2opendssvenv/Lib/site-packages/bdgd2opendss/config/bdgd2dss.json):

```json
"UCBT_tab": {
    "arquivo": "CargasBT",
    "direct_mapping": {
        "bus1": "PAC",
        "load": "RAMAL",
        "data_con": "DAT_CON",
        "daily": "TIP_CC",
        "feeder": "CTMT",
        "transformer": "UNI_TR_MT",
        "energia_01": "ENE_01", ...
    }
}
```

E no arquivo de seleção de colunas:
```json
"columns": [
    "COD_ID", "DIST", "PAC", "PN_CON", "UNI_TR_MT", "CTMT", "UNI_TR_AT",
    "SUB", "CONJ", "MUN", "BRR", "CEP", "CLAS_SUB", "CNAE", "TIP_CC",
    "FAS_CON", "GRU_TEN", "TEN_FORN", "GRU_TAR",
    "ENE_01", "ENE_02", "ENE_03", "ENE_04", "ENE_05", "ENE_06",
    "ENE_07", "ENE_08", "ENE_09", "ENE_10", "ENE_11", "ENE_12"
]
```

> [!CAUTION]
> **Vulnerabilidade Identificada no Pipeline:**  
> A coluna `SIT_ATIV` **não consta na lista de colunas extraídas**. Como a cláusula `WHERE` da consulta no Geodatabase filtrava apenas `CTMT = 'ESB01S4'`, todos os registros cadastrados (ativos e inativos) foram exportados para os arquivos intermediários (`AuxCargaBT_ESB01S4.csv`) e convertidos cegamente em elementos `Load` no OpenDSS, utilizando a coluna `RAMAL` como identificador de carga.

---

## 4. Análise Quantitativa e Resultados do Saneamento

O script [`filtrar_cargas_ativas.py`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/testes_convergencia/filtrar_cargas_ativas.py) realizou o saneamento completo, gerando os seguintes resultados censitários verificados:

### 4.1 Consolidado do Alimentador `ESB01S4`

| Métrica | Antes do Saneamento | Após o Saneamento | Variação / Alívio |
| :--- | :---: | :---: | :---: |
| **Linhas no Arquivo DSS** | 3.259 | 1.915 | -1.344 linhas |
| **Objetos de Carga OpenDSS** | 3.238 | 1.894 | -1.344 objetos |
| — Cargas UCs Ativas | 1.363 | 1.340 | Mantidas |
| — Iluminação Pública (IP) | 277 | 277 (554 loads) | 100% mantida |
| — Cargas UCs Desativadas | 1.344 | **0** | **-1.344 removidas (100%)** |
| **Potência Ativa Total (kW)** | 1.709,72 kW | **754,51 kW** | **-955,22 kW (-55,9%)** |

### 4.2 Consolidado no Transformador Crítico `TRF_TOK5079A` (150 kVA)

| Métrica | Antes do Saneamento | Após o Saneamento | Variação / Diagnóstico |
| :--- | :---: | :---: | :---: |
| **Objetos de Carga Ativos** | 96 | 96 | Cargas reais em operação |
| **Objetos de Cargas Fantasmas** | 228 | **0** | **228 objetos removidos** |
| **Potência Ativa Agregada** | 529,24 kW | **100,16 kW** | **-429,08 kW (-81,1%)** |
| **Carregamento sobre 150 kVA** | **352,8%** (Colapso) | **66,8%** (Ideal) | **Operação perfeitamente normalizada** |

---

## 5. Impacto nos Resultados de Convergência do OpenDSS

Com a execução do orquestrador [`executar_todos_cenarios.py`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/testes_convergencia/executar_todos_cenarios.py), as métricas de convergência do alimentador foram consolidadas:

| Cenário | Elementos Incluídos | Passos Convergidos | Média Iterações | Máx Iterações | Diagnóstico |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Cenário 1: Apenas Rede MT** | SegmentosMT, ChavesMT, ReguladorMT, CargasMT | **144 / 144 (100%)** | **2,07** | 4 | Operação MT 100% estável. |
| **Cenário 2: Rede MT + BT em Vazio** | Master completo em vazio | **144 / 144 (100%)** | **2,03** | 4 | Topologia física íntegra. |
| **Cenário 3: MT + BT Original (Falhas)** | Master + CargasBT (todas) + PVs flutuantes | **144 / 144 (100%)** | **2,00** | 2 | Falso-positivo (aborto silencioso do solver KLU). |
| **Cenário 4: PVs Corrigidos + Cargas vmin=0.5** | Master + CargasBT (todas, vmin=0.5) + PVs corrigidos | **58 / 144 (40,28%)** | **92,14** | 150 | Reprodução fiel do limit cycle provocado pela sobrecarga de 355%. |
| **Cenário 5: Rede Completa Corrigida e Saneada** | Master + CargasBT (saneadas) + PVs corrigidos + EVs | **144 / 144 (100%)** | **3,23** | **4** | **100% convergência. Média de 3,23 iterações (máx 4). Estabilidade total.** |

---

## 6. Rastreabilidade e Reprodutibilidade

Para garantir total integridade aos dados de pesquisa do TCC:
1. **Backup Original Preservado:** [`CargasBT_Sintetico_20250139_ESB01S4_todas.dss`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/data/rede/ESB01S4/CargasBT_Sintetico_20250139_ESB01S4_todas.dss) contém o arquivo original com todas as cargas (ativas e inativas).
2. **Cargas Desativadas Catalogadas:** [`CargasBT_Sintetico_20250139_ESB01S4_desativadas.dss`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/data/rede/ESB01S4/CargasBT_Sintetico_20250139_ESB01S4_desativadas.dss) contém exatamente as 1.344 cargas desativadas removidas, permitindo auditoria elemento por elemento.
3. **Produção Sanitizada:** [`CargasBT_Sintetico_20250139_ESB01S4.dss`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/data/rede/ESB01S4/CargasBT_Sintetico_20250139_ESB01S4.dss) é o arquivo de produção utilizado pelos scripts de simulação e pelo Mosaik.
4. **Notebook Atualizado:** O notebook [`analise_convergencia_opendss.ipynb`](file:///mnt/c/Users/pvict/OneDrive/TCC/ev-analysis-2026/notebooks/analise_convergencia_opendss.ipynb) foi pré-executado e contém todas as curvas e tabelas atualizadas.
