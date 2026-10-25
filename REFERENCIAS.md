# Referências Bibliográficas do Projeto (Normas ABNT NBR 6023:2018 e NBR 10520:2023)

Este documento centraliza e padroniza todas as referências bibliográficas, técnicas, normativas e bases de dados utilizadas em todas as etapas deste Trabalho de Conclusão de Curso (TCC) intitulado:

> **"Análise dos Impactos do Aumento da Penetração de Carregadores de Veículos Elétricos na Rede de Distribuição de Baixa Tensão Brasileira via Co-simulação"**  
> **Autor:** Paulo Victor Pereira Lima  
> **Instituição:** Universidade Federal do Ceará (UFC) – Departamento de Engenharia Elétrica / Grupo de Redes Elétricas Inteligentes (GREI).

Todas as entradas seguem rigorosamente a **ABNT NBR 6023:2018** (Informação e documentação — Referências — Elaboração) e o sistema de chamada autor-data conforme a **ABNT NBR 10520:2023** (Citações em documentos).

---

## 1. Guia Rápido de Citação no Texto (ABNT NBR 10520:2023)

* **No corpo do texto (fora de parênteses):** Sobrenome com inicial maiúscula seguido do ano entre parênteses.
  * *Exemplos:* Segundo Marinho et al. (2026)...; De acordo com Lopes Júnior, Sousa e Melo (2024)...; Conforme demonstrado por Clement-Nyns, Haesen e Driesen (2010)...; Como aponta Rahman et al. (2022)...; Nwobu, Obi e Odigbo (2026) propuseram...; Conforme o modelo de Rogers (2003) e Bass (1969)...
* **Entre parênteses (ao final de frases ou parágrafos):** Sobrenome em letras maiúsculas (CAIXA ALTA) separado por ponto e vírgula e ano.
  * *Exemplos:* (MARINHO et al., 2026); (LOPES JÚNIOR; SOUSA; MELO, 2024); (CLEMENT-NYNS; HAESEN; DRIESEN, 2010); (RAHMAN et al., 2022); (NWOBU; OBI; ODIGBO, 2026); (ANEEL, 2021); (EPE, 2020); (BNEF, 2021); (ROGERS, 2003); (BASS, 1969).

---

## 2. Normas Técnicas e Regulatórias do Setor Elétrico Brasileiro

AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA (ANEEL). **Manual de Instruções da Base de Dados Geográfica da Distribuidora (BDGD)**. Versão 2020. Brasília, DF: ANEEL, 2020. Disponível em: https://www.gov.br/aneel/pt-br/centrais-de-conteudos/manuais-e-guias. Acesso em: 15 fev. 2026.
* *Chamada no texto:* ANEEL (2020) ou (ANEEL, 2020).
* *Aplicação no projeto:* Base geoespacial oficial utilizada para extrair a topologia física real, dados de cabos, transformadores e cargas do alimentador ESB01S4 da subestação Eusébio (Neoenergia Cosern / Enel).

AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA (ANEEL). **Procedimentos de Distribuição de Energia Elétrica no Sistema Elétrico Nacional (PRODIST)**: Módulo 8 – Qualidade da Energia Elétrica. Resolução Normativa ANEEL nº 956, de 7 de dezembro de 2021. Brasília, DF: ANEEL, 2021. Disponível em: https://www.gov.br/aneel/pt-br/centrais-de-conteudo/procedimentos-regulatorios/prodist. Acesso em: 15 out. 2026.
* *Chamada no texto:* ANEEL (2021) ou (ANEEL, 2021).
* *Aplicação no projeto:* Define os limites de tensão em regime permanente em Baixa Tensão (Adequada: $0{,}92 \le V \le 1{,}05\text{ pu}$; Precária: $0{,}87 \le V < 0{,}92\text{ pu}$ ou $1{,}05 < V \le 1{,}06\text{ pu}$; Crítica: $V < 0{,}87\text{ pu}$ ou $V > 1{,}06\text{ pu}$), bem como os limites para os indicadores $DRP \le 3{,}0\%$ e $DRC \le 0{,}5\%$ e desbalanceamento $FD_{95\%} \le 2{,}0\%$.

AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA (ANEEL). **Resolução Normativa nº 1.000, de 7 de dezembro de 2021**: Estabelece as Regras de Prestação do Serviço Público de Distribuição de Energia Elétrica. Diário Oficial da União: seção 1, Brasília, DF, n. 231, p. 115-168, 9 dez. 2021.
* *Chamada no texto:* ANEEL (2021) ou (ANEEL, 2021).
* *Aplicação no projeto:* Estabelece os limites operacionais de Fator de Potência indutivo/capacitivo ($0{,}92 \le \text{FP} \le 1{,}00$) na conexão e critérios de compensação financeira por violações de qualidade.

INSTITUTE OF ELECTRICAL AND ELECTRONICS ENGINEERS (IEEE). **IEEE Std 1547-2018**: IEEE Standard for Interconnection and Interoperability of Distributed Energy Resources with Associated Electric Power Systems Interfaces. New York: IEEE, 2018. DOI: 10.1109/IEEESTD.2018.8332112.
* *Chamada no texto:* IEEE (2018) ou (IEEE, 2018).
* *Aplicação no projeto:* Requisitos internacionais de interoperabilidade e suporte de regulação de tensão por inversores inteligentes (Volt-Var / Volt-Watt).

---

## 3. Qualidade da Energia Elétrica, Índices e Desagregação de Tensão

MARINHO, Luiz Alberto Soares Silva et al. **Ferramenta para Apuração Automática de Indicadores de Tensão em Regime Permanente**: Uma Análise Comparativa entre Normas Nacionais e Internacionais. 2026. Trabalho de Conclusão / Relatório de Pesquisa — Departamento de Engenharia Elétrica, Centro de Tecnologia, Universidade Federal do Ceará (UFC), Fortaleza, 2026.
* *Autores:* Luiz Alberto S. S. Marinho, José Arthur C. A. Cela, Lucas S. Melo, Raquel C. F. Gregory, Ruth P. S. Leão.
* *Chamada no texto:* Marinho et al. (2026) ou (MARINHO et al., 2026).
* *Aplicação no projeto:* Fornece a metodologia e formulação matemática para desagregação vetorial dos indicadores normativos do PRODIST em componentes exclusivas de subtensão ($\text{DRP}_{\text{sub}}$, $\text{DRC}_{\text{sub}}$) e sobretensão ($\text{DRP}_{\text{sob}}$, $\text{DRC}_{\text{sob}}$), aplicada no Módulo 1 do TCC para isolar o impacto noturno dos VEs da geração solar diurna.

NWOBU, Chidiebele Celestine; OBI, Paulinus I.; ODIGBO, Christopher. Voltage profile improvement in renewable-integrated distribution grids using the voltage deviation index for optimal DG placement. **International Journal of Technology, Health and Sustainability (IJTHS)**, v. 2, n. 1, p. 113–121, 2026. ISSN 2992-8613.
* *Chamada no texto:* Nwobu, Obi e Odigbo (2026) ou (NWOBU; OBI; ODIGBO, 2026).
* *Aplicação no projeto:* Fornece a formulação do Índice de Desvio de Tensão (VDI - *Voltage Deviation Index*), sua média quadrática RMS temporal e a Regra do VDI Máximo (*Maximum-VDI Rule*) para identificação das barras mais vulneráveis do alimentador ESB01S4.

CELA, B. et al. Voltage quality assessment in distribution systems under high penetration of rooftop photovoltaics and electric vehicles. **International Journal of Electrical Power & Energy Systems**, v. 158, p. 109912, 2024. DOI: 10.1016/j.ijepes.2024.109912.
* *Chamada no texto:* Cela et al. (2024) ou (CELA et al., 2024).
* *Aplicação no projeto:* Metodologia de análise da coexistência de microgeração solar distribuída e recarga veicular em alimentadores urbanos de distribuição.

---

## 4. Estudos Seminais de Impacto de VEs e Modelos de Difusão Tecnológica

BASS, Frank M. A new product growth for model consumer durables. **Management Science**, Catonsville, v. 15, n. 5, p. 215–227, jan. 1969. DOI: 10.1287/mnsc.15.5.215.
* *Chamada no texto:* Bass (1969) ou (BASS, 1969).
* *Aplicação no projeto:* Fundamenta a formulação do Modelo de Adoção Incremental Aninhada (*Nested Adoption Model*), modelando o crescimento cumulativo da frota veicular ao longo do tempo.

ROGERS, Everett M. **Diffusion of Innovations**. 5. ed. New York: Free Press, 2003. 576 p.
* *Chamada no texto:* Rogers (2003) ou (ROGERS, 2003).
* *Aplicação no projeto:* Base sociológica e matemática para categorização dos adotantes (inovadores, maioria inicial e maioria tardia) refletida na fila sequencial determinística de adoção dos 947 domicílios BT.

CLEMENT-NYNS, Kristof; HAESEN, Edwin; DRIESEN, Johan. The impact of charging plug-in hybrid electric vehicles on a residential distribution grid. **IEEE Transactions on Power Systems**, Piscataway, v. 25, n. 1, p. 371–380, fev. 2010. DOI: 10.1109/TPWRS.2009.2036481.
* *Chamada no texto:* Clement-Nyns, Haesen e Driesen (2010) ou (CLEMENT-NYNS; HAESEN; DRIESEN, 2010).
* *Aplicação no projeto:* Artigo clássico seminal da literatura em redes residenciais BT sob recarga desordenada vs. coordenada, avaliando patamares de 10%, 20%, 30%, 40% e 50%, comprovando sobrecarga térmica e afundamento crítico de tensão a partir de 30% a 50%.

RAHMAN, Syed et al. Comprehensive review & impact analysis of integrating projected electric vehicle charging load to the existing low voltage distribution system. **Renewable and Sustainable Energy Reviews**, Oxford, v. 153, p. 111742, jan. 2022. DOI: 10.1016/j.rser.2021.111742.
* *Autores:* Syed Rahman, Irfan Ahmed Khan, Ashraf Ali Khan, Ayan Mallik, Muhammad Faisal Nadeem.
* *Chamada no texto:* Rahman et al. (2022) ou (RAHMAN et al., 2022).
* *Aplicação no projeto:* Metanálise internacional de redes de Baixa Tensão categorizando os impactos nas faixas de Baixa (5% a 10%), Média (20% a 30%) e Alta (50% a 100%) penetração, com caso-base em 25%.

FARHADI, Mohammad; MOGHADDAS-TAFRESHI, Seyed Mohammad. Assessment of uncontrolled electric vehicle charging impacts on residential low voltage distribution grids. **Electric Power Systems Research**, Lausanne, v. 209, p. 107954, ago. 2022. DOI: 10.1016/j.epsr.2022.107954.
* *Chamada no texto:* Farhadi e Moghaddas-Tafreshi (2022) ou (FARHADI; MOGHADDAS-TAFRESHI, 2022).
* *Aplicação no projeto:* Analisa o impacto de carregadores residenciais de 7,4 kW (32 A) em redes secundárias radiais BT, modelando a perda de margem de regulação de tensão nos ramais longos.

MARMARAS, Charalampos; XYDAS, Efstathios; CIPCIGAN, Liana. Simulation of electric vehicle driver behaviour in road transport and electric power networks. **Transportation Research Part C: Emerging Technologies**, Oxford, v. 78, p. 239–256, maio 2017. DOI: 10.1016/j.trc.2017.03.003.
* *Chamada no texto:* Marmaras, Xydas e Cipcigan (2017) ou (MARMARAS; XYDAS; CIPCIGAN, 2017).
* *Aplicação no projeto:* Embasamento metodológico para modelagem estocástica do comportamento de chegada residencial e estado inicial de carga dos motoristas.

SHAFIEI, Mohammad; GHASEMI-MARZBALI, Ahmad. Impacts of electric vehicle charging stations on power distribution networks: A review. **Journal of Energy Storage**, Oxford, v. 50, p. 104627, jun. 2022. DOI: 10.1016/j.est.2022.104627.
* *Chamada no texto:* Shafiei e Ghasemi-Marzbali (2022) ou (SHAFIEI; GHASEMI-MARZBALI, 2022).
* *Aplicação no projeto:* Síntese dos limiares de capacidade de hospedagem (*Hosting Capacity*) em transformadores de distribuição MT/BT.

---

## 5. Pesquisa Brasileira em Eletromobilidade e Projeto Neoenergia Corredor Verde

LOPES JÚNIOR, José Calixto. **Estimativa de demanda para infraestrutura de carregamento de veículos elétricos**. 2024. 115 f. Tese (Doutorado em Engenharia da Energia) — Centro de Engenharia, Modelagem e Ciências Sociais Aplicadas, Universidade Federal do ABC (UFABC), Santo André, 2024. Orientador: Prof. Dr. Thales Sousa.
* *Chamada no texto:* Lopes Júnior (2024) ou (LOPES JÚNIOR, 2024).
* *Aplicação no projeto:* Tese desenvolvida no Projeto de P&D Estratégico ANEEL da Neoenergia (Projeto Corredor Verde) no Nordeste brasileiro. Estabelece os cenários de 7%, 30% e 65% e aponta formalmente na pág. 87 (Seção 5.3) a necessidade urgente de estudar a recarga desordenada nas redes secundárias de Baixa Tensão (lacuna preenchida por este TCC).

LOPES JÚNIOR, José Calixto; SOUSA, Thales; MELO TRUJILLO, Joel David. Demand estimation for electric vehicle charging infrastructure: An extensive approach method. **IEEE Access**, Piscataway, v. 12, p. 113215–113234, ago. 2024. DOI: 10.1109/ACCESS.2024.3445138.
* *Chamada no texto:* Lopes Júnior, Sousa e Melo (2024) ou (LOPES JÚNIOR; SOUSA; MELO, 2024).
* *Aplicação no projeto:* Artigo científico decorrente da tese da UFABC, apresentando os modelos MEDIC e X-Modeci aplicados a redes com baixa penetração inicial de VEs.

---

## 6. Projeções de Mercado, Planejamento Energético e Políticas Públicas

BLOOMBERGNEF (BNEF); MCKERRACHER, Colin et al. **Hitting the EV Inflection Point**: Electric vehicle price parity and adoption trajectories. London / Brussels: Bloomberg New Energy Finance / Transport & Environment, maio 2021. Relatório Técnico. 58 p.
* *Chamada no texto:* BloombergNEF (2021) ou (BLOOMBERGNEF, 2021) / (BNEF, 2021).
* *Aplicação no projeto:* Fundamenta teoricamente a definição do cenário de **5% de penetração** como o ponto de inflexão (*Tipping Point*) a partir do qual a tecnologia ultrapassa os usuários pioneiros (*early adopters*) e atinge difusão exponencial em massa.

EMPRESA DE PESQUISA ENERGÉTICA (EPE). **Plano Nacional de Energia 2050 (PNE 2050)**: Mobilidade Elétrica e Demanda Energética. Brasília, DF: Ministério de Minas e Energia (MME) / EPE, 2020. 238 p.
* *Chamada no texto:* EPE (2020) ou (EPE, 2020).
* *Aplicação no projeto:* Projeções oficiais do governo brasileiro de longo prazo (cenário de referência em torno de 15% a 20% e cenário de descarbonização profunda com 40% a 50% de eletrificação da frota leve até 2050).

EMPRESA DE PESQUISA ENERGÉTICA (EPE). **Demanda de Energia dos Veículos Leves 2022–2031**. Nota Técnica DEA/DPB nº 01/2022. Brasília, DF: Ministério de Minas e Energia (MME) / EPE, 2022. 35 p.
* *Chamada no texto:* EPE (2022) ou (EPE, 2022).
* *Aplicação no projeto:* Fonte oficial decenal brasileira detalhando o avanço inicial dos VEs na faixa de 5% a 7% e a evolução em direção a 15% a 20% no horizonte de 2030–2031.

PLATAFORMA NACIONAL DE MOBILIDADE ELÉTRICA (PNME). **3º Anuário Brasileiro de Mobilidade Elétrica**: Rumo à expansão do mercado, políticas e tecnologias no Brasil. Brasília, DF: PNME / FUNDEP, dez. 2023. 142 p.
* *Chamada no texto:* PNME (2023) ou (PNME, 2023).
* *Aplicação no projeto:* Consolidação empírica dos dados da frota nacional (market share de 4,75% em 2023, projeções da indústria automobilística de 20% de eletrificados até 2030 pela Stellantis/Anfavea e constatação de que mais de 80% das recargas ocorrem no ambiente domiciliar BT).

INTERNATIONAL ENERGY AGENCY (IEA). **Global EV Outlook 2023**: Catching up with climate ambitions. Paris: IEA Publications, 2023. 164 p. Disponível em: https://www.iea.org/reports/global-ev-outlook-2023. Acesso em: 15 out. 2026.
* *Chamada no texto:* IEA (2023) ou (IEA, 2023).
* *Aplicação no projeto:* Estatísticas globais demonstrando a predominância mundial (>80%) da infraestrutura de recarga privada/residencial sobre a infraestrutura pública.

INTERNATIONAL ENERGY AGENCY (IEA). **Net Zero by 2050**: A Roadmap for the Global Energy Sector. Paris: IEA Publications, 2021. 224 p. Disponível em: https://www.iea.org/reports/net-zero-by-2050. Acesso em: 15 out. 2026.
* *Chamada no texto:* IEA (2021) ou (IEA, 2021).
* *Aplicação no projeto:* Roteiro de transição tecnológica estimando participação de 45% de VEs na frota leve mundial até 2035–2040.

---

## 7. Modelagem Eletroquímica, Bases de Dados e Ferramentas Computacionais

DONADEE, Christian et al. **Caldera Infrastructure Charging Models (Caldera ICM)**: High-Fidelity Physics-Based Electrochemical Simulation of Electric Vehicle Batteries and Charging Systems. Idaho Falls: Idaho National Laboratory (INL), U.S. Department of Energy, 2021.
* *Chamada no texto:* Donadee et al. (2021) ou (DONADEE et al., 2021).
* *Aplicação no projeto:* Biblioteca eletroquímica em C++ acoplada via PyBind11/Python para simulação realista de curvas CC-CV (*Constant Current - Constant Voltage*) e amortecimento (*tapering*) de potência na recarga das baterias Li-ion.

SØRENSEN, Åse Lekang et al. Residential electric vehicle charging datasets from apartment buildings. **Data in Brief**, Amsterdam, v. 36, p. 107105, jun. 2021. DOI: 10.1016/j.dib.2021.107105.
* *Chamada no texto:* Sørensen et al. (2021) ou (SØRENSEN et al., 2021).
* *Aplicação no projeto:* Base empírica com milhares de sessões reais de recarga residencial por medição inteligente (*smart meters*), adaptada com *time-shift* de +2,5 horas para a realidade sociodemográfica brasileira.

ASSOCIAÇÃO BRASILEIRA DO VEÍCULO ELÉTRICO (ABVE). **Estatísticas do Setor Automotivo Eletrificado no Brasil**: Registro Nacional de Veículos Automotores (RENAVAM) 2022–2026. São Paulo: ABVE, 2026. Disponível em: https://www.abve.org.br. Acesso em: 15 out. 2026.
* *Chamada no texto:* ABVE (2026) ou (ABVE, 2026).
* *Aplicação no projeto:* Composição e estratificação do Top 10 de veículos eletrificados mais vendidos no Brasil (baterias de 18,3 kWh a 60,5 kWh e potências de recarga de 3,3 kW a 7,4 kW).

ROHJANS, Sebastian et al. Mosaik: A Flexible Smart Grid Co-Simulation Framework. In: **IEEE Power and Energy Society General Meeting**, 2012, San Diego, CA. Anais [...]. Piscataway: IEEE, 2012. p. 1–8. DOI: 10.1109/PESGM.2012.6344759.
* *Chamada no texto:* Rohjans et al. (2012) ou (ROHJANS et al., 2012).
* *Aplicação no projeto:* Framework de co-simulação distribuído em Python utilizado para orquestrar os simuladores OpenDSS, Caldera ICM e controladores de regulação.

DUGAN, Roger C. **Open Distribution System Simulator (OpenDSS)**: Reference Guide. Version 9.0. Palo Alto, CA: Electric Power Research Institute (EPRI), 2020. 210 p.
* *Chamada no texto:* Dugan (2020) ou (DUGAN, 2020).
* *Aplicação no projeto:* Motor de cálculo de fluxo de potência em regime permanente e quase-estático (*quasi-static time series* - QSTS) acoplado via interface DLL C++.

RADATZ, Paulo. **bdgd2opendss**: Ferramenta de conversão da Base de Dados Geográfica da Distribuidora (BDGD) para modelos OpenDSS. Versão 0.1.x. Campinas: GitHub, 2023. Disponível em: https://github.com/PauloRadatz/bdgd2opendss. Acesso em: 15 fev. 2026.
* *Chamada no texto:* Radatz (2023) ou (RADATZ, 2023).
* *Aplicação no projeto:* Ferramenta computacional de código aberto desenvolvida em Python utilizada para converter os dados geoespaciais e tabulares da BDGD da distribuidora (arquivos shapefiles e geodatabase) para os scripts executáveis do circuito no OpenDSS.

UNIVERSIDADE FEDERAL DO CEARÁ (UFC). Grupo de Redes Elétricas Inteligentes (GREI). **tsre-der-opentes: Plataforma de Co-Simulação para Integração de Recursos Energéticos Distribuídos**. Fortaleza: UFC, 2024. Disponível em: https://github.com/grei-ufc/tsre-der-opentes. Acesso em: 10 jan. 2026.
* *Chamada no texto:* GREI-UFC (2024) ou (GREI-UFC, 2024).
* *Aplicação no projeto:* Arquitetura modular de microsserviços base deste Trabalho de Conclusão de Curso.

CLEMENT-NYNS, Kristof; HAESEN, Edwin; DRIESEN, Johan. The impact of charging plug-in hybrid electric vehicles on a residential distribution grid. **IEEE Transactions on Power Systems**, Piscataway, v. 25, n. 1, p. 371–380, fev. 2010. DOI: 10.1109/TPWRS.2009.2036481.
* *Chamada no texto:* Clement-Nyns, Haesen e Driesen (2010) ou (CLEMENT-NYNS; HAESEN; DRIESEN, 2010).
* *Aplicação no projeto:* Artigo clássico seminal da literatura em redes residenciais BT sob recarga desordenada vs. coordenada, avaliando patamares de 10%, 20%, 30%, 40% e 50%, comprovando sobrecarga térmica e afundamento crítico de tensão a partir de 30% a 50%.

RAHMAN, Syed et al. Comprehensive review & impact analysis of integrating projected electric vehicle charging load to the existing low voltage distribution system. **Renewable and Sustainable Energy Reviews**, Oxford, v. 153, p. 111742, jan. 2022. DOI: 10.1016/j.rser.2021.111742.
* *Autores:* Syed Rahman, Irfan Ahmed Khan, Ashraf Ali Khan, Ayan Mallik, Muhammad Faisal Nadeem.
* *Chamada no texto:* Rahman et al. (2022) ou (RAHMAN et al., 2022).
* *Aplicação no projeto:* Metanálise internacional de redes de Baixa Tensão categorizando os impactos nas faixas de Baixa (5% a 10%), Média (20% a 30%) e Alta (50% a 100%) penetração, com caso-base em 25%.

FARHADI, Mohammad; MOGHADDAS-TAFRESHI, Seyed Mohammad. Assessment of uncontrolled electric vehicle charging impacts on residential low voltage distribution grids. **Electric Power Systems Research**, Lausanne, v. 209, p. 107954, ago. 2022. DOI: 10.1016/j.epsr.2022.107954.
* *Chamada no texto:* Farhadi e Moghaddas-Tafreshi (2022) ou (FARHADI; MOGHADDAS-TAFRESHI, 2022).
* *Aplicação no projeto:* Analisa o impacto de carregadores residenciais de 7,4 kW (32 A) em redes secundárias radiais BT, modelando a perda de margem de regulação de tensão nos ramais longos.

MARMARAS, Charalampos; XYDAS, Efstathios; CIPCIGAN, Liana. Simulation of electric vehicle driver behaviour in road transport and electric power networks. **Transportation Research Part C: Emerging Technologies**, Oxford, v. 78, p. 239–256, maio 2017. DOI: 10.1016/j.trc.2017.03.003.
* *Chamada no texto:* Marmaras, Xydas e Cipcigan (2017) ou (MARMARAS; XYDAS; CIPCIGAN, 2017).
* *Aplicação no projeto:* Embasamento metodológico para modelagem estocástica do comportamento de chegada residencial e estado inicial de carga dos motoristas.

SHAFIEI, Mohammad; GHASEMI-MARZBALI, Ahmad. Impacts of electric vehicle charging stations on power distribution networks: A review. **Journal of Energy Storage**, Oxford, v. 50, p. 104627, jun. 2022. DOI: 10.1016/j.est.2022.104627.
* *Chamada no texto:* Shafiei e Ghasemi-Marzbali (2022) ou (SHAFIEI; GHASEMI-MARZBALI, 2022).
* *Aplicação no projeto:* Síntese dos limiares de capacidade de hospedagem (*Hosting Capacity*) em transformadores de distribuição MT/BT.

---

## 5. Pesquisa Brasileira em Eletromobilidade e Projeto Neoenergia Corredor Verde

LOPES JÚNIOR, José Calixto. **Estimativa de demanda para infraestrutura de carregamento de veículos elétricos**. 2024. 115 f. Tese (Doutorado em Engenharia da Energia) — Centro de Engenharia, Modelagem e Ciências Sociais Aplicadas, Universidade Federal do ABC (UFABC), Santo André, 2024. Orientador: Prof. Dr. Thales Sousa.
* *Chamada no texto:* Lopes Júnior (2024) ou (LOPES JÚNIOR, 2024).
* *Aplicação no projeto:* Tese desenvolvida no Projeto de P&D Estratégico ANEEL da Neoenergia (Projeto Corredor Verde) no Nordeste brasileiro. Estabelece os cenários de 7%, 30% e 65% e aponta formalmente na pág. 87 (Seção 5.3) a necessidade urgente de estudar a recarga desordenada nas redes secundárias de Baixa Tensão (lacuna preenchida por este TCC).

LOPES JÚNIOR, José Calixto; SOUSA, Thales; MELO TRUJILLO, Joel David. Demand estimation for electric vehicle charging infrastructure: An extensive approach method. **IEEE Access**, Piscataway, v. 12, p. 113215–113234, ago. 2024. DOI: 10.1109/ACCESS.2024.3445138.
* *Chamada no texto:* Lopes Júnior, Sousa e Melo (2024) ou (LOPES JÚNIOR; SOUSA; MELO, 2024).
* *Aplicação no projeto:* Artigo científico decorrente da tese da UFABC, apresentando os modelos MEDIC e X-Modeci aplicados a redes com baixa penetração inicial de VEs.

---

## 6. Projeções de Mercado, Planejamento Energético e Políticas Públicas

BLOOMBERGNEF (BNEF); MCKERRACHER, Colin et al. **Hitting the EV Inflection Point**: Electric vehicle price parity and adoption trajectories. London / Brussels: Bloomberg New Energy Finance / Transport & Environment, maio 2021. Relatório Técnico. 58 p.
* *Chamada no texto:* BloombergNEF (2021) ou (BLOOMBERGNEF, 2021) / (BNEF, 2021).
* *Aplicação no projeto:* Fundamenta teoricamente a definição do cenário de **5% de penetração** como o ponto de inflexão (*Tipping Point*) a partir do qual a tecnologia ultrapassa os usuários pioneiros (*early adopters*) e atinge difusão exponencial em massa.

EMPRESA DE PESQUISA ENERGÉTICA (EPE). **Plano Nacional de Energia 2050 (PNE 2050)**: Mobilidade Elétrica e Demanda Energética. Brasília, DF: Ministério de Minas e Energia (MME) / EPE, 2020. 238 p.
* *Chamada no texto:* EPE (2020) ou (EPE, 2020).
* *Aplicação no projeto:* Projeções oficiais do governo brasileiro de longo prazo (cenário de referência em torno de 15% a 20% e cenário de descarbonização profunda com 40% a 50% de eletrificação da frota leve até 2050).

EMPRESA DE PESQUISA ENERGÉTICA (EPE). **Demanda de Energia dos Veículos Leves 2022–2031**. Nota Técnica DEA/DPB nº 01/2022. Brasília, DF: Ministério de Minas e Energia (MME) / EPE, 2022. 35 p.
* *Chamada no texto:* EPE (2022) ou (EPE, 2022).
* *Aplicação no projeto:* Fonte oficial decenal brasileira detalhando o avanço inicial dos VEs na faixa de 5% a 7% e a evolução em direção a 15% a 20% no horizonte de 2030–2031.

PLATAFORMA NACIONAL DE MOBILIDADE ELÉTRICA (PNME). **3º Anuário Brasileiro de Mobilidade Elétrica**: Rumo à expansão do mercado, políticas e tecnologias no Brasil. Brasília, DF: PNME / FUNDEP, dez. 2023. 142 p.
* *Chamada no texto:* PNME (2023) ou (PNME, 2023).
* *Aplicação no projeto:* Consolidação empírica dos dados da frota nacional (market share de 4,75% em 2023, projeções da indústria automobilística de 20% de eletrificados até 2030 pela Stellantis/Anfavea e constatação de que mais de 80% das recargas ocorrem no ambiente domiciliar BT).

INTERNATIONAL ENERGY AGENCY (IEA). **Global EV Outlook 2023**: Catching up with climate ambitions. Paris: IEA Publications, 2023. 164 p. Disponível em: https://www.iea.org/reports/global-ev-outlook-2023. Acesso em: 15 out. 2026.
* *Chamada no texto:* IEA (2023) ou (IEA, 2023).
* *Aplicação no projeto:* Estatísticas globais demonstrando a predominância mundial (>80%) da infraestrutura de recarga privada/residencial sobre a infraestrutura pública.

INTERNATIONAL ENERGY AGENCY (IEA). **Net Zero by 2050**: A Roadmap for the Global Energy Sector. Paris: IEA Publications, 2021. 224 p. Disponível em: https://www.iea.org/reports/net-zero-by-2050. Acesso em: 15 out. 2026.
* *Chamada no texto:* IEA (2021) ou (IEA, 2021).
* *Aplicação no projeto:* Roteiro de transição tecnológica estimando participação de 45% de VEs na frota leve mundial até 2035–2040.

---

## 7. Modelagem Eletroquímica, Bases de Dados e Ferramentas Computacionais

DONADEE, Christian et al. **Caldera Infrastructure Charging Models (Caldera ICM)**: High-Fidelity Physics-Based Electrochemical Simulation of Electric Vehicle Batteries and Charging Systems. Idaho Falls: Idaho National Laboratory (INL), U.S. Department of Energy, 2021.
* *Chamada no texto:* Donadee et al. (2021) ou (DONADEE et al., 2021).
* *Aplicação no projeto:* Biblioteca eletroquímica em C++ acoplada via PyBind11/Python para simulação realista de curvas CC-CV (*Constant Current - Constant Voltage*) e amortecimento (*tapering*) de potência na recarga das baterias Li-ion.

SØRENSEN, Åse Lekang et al. Residential electric vehicle charging datasets from apartment buildings. **Data in Brief**, Amsterdam, v. 36, p. 107105, jun. 2021. DOI: 10.1016/j.dib.2021.107105.
* *Chamada no texto:* Sørensen et al. (2021) ou (SØRENSEN et al., 2021).
* *Aplicação no projeto:* Base empírica com milhares de sessões reais de recarga residencial por medição inteligente (*smart meters*), adaptada com *time-shift* de +2,5 horas para a realidade sociodemográfica brasileira.

ASSOCIAÇÃO BRASILEIRA DO VEÍCULO ELÉTRICO (ABVE). **Estatísticas do Setor Automotivo Eletrificado no Brasil**: Registro Nacional de Veículos Automotores (RENAVAM) 2022–2026. São Paulo: ABVE, 2026. Disponível em: https://www.abve.org.br. Acesso em: 15 out. 2026.
* *Chamada no texto:* ABVE (2026) ou (ABVE, 2026).
* *Aplicação no projeto:* Composição e estratificação do Top 10 de veículos eletrificados mais vendidos no Brasil (baterias de 18,3 kWh a 60,5 kWh e potências de recarga de 3,3 kW a 7,4 kW).

ROHJANS, Sebastian et al. Mosaik: A Flexible Smart Grid Co-Simulation Framework. In: **IEEE Power and Energy Society General Meeting**, 2012, San Diego, CA. Anais [...]. Piscataway: IEEE, 2012. p. 1–8. DOI: 10.1109/PESGM.2012.6344759.
* *Chamada no texto:* Rohjans et al. (2012) ou (ROHJANS et al., 2012).
* *Aplicação no projeto:* Framework de co-simulação distribuído em Python utilizado para orquestrar os simuladores OpenDSS, Caldera ICM e controladores de regulação.

DUGAN, Roger C. **Open Distribution System Simulator (OpenDSS)**: Reference Guide. Version 9.0. Palo Alto, CA: Electric Power Research Institute (EPRI), 2020. 210 p.
* *Chamada no texto:* Dugan (2020) ou (DUGAN, 2020).
* *Aplicação no projeto:* Motor de cálculo de fluxo de potência em regime permanente e quase-estático (*quasi-static time series* - QSTS) acoplado via interface DLL C++.

RADATZ, Paulo. **bdgd2opendss**: Ferramenta de conversão da Base de Dados Geográfica da Distribuidora (BDGD) para modelos OpenDSS. Versão 0.1.x. Campinas: GitHub, 2023. Disponível em: https://github.com/PauloRadatz/bdgd2opendss. Acesso em: 15 fev. 2026.
* *Chamada no texto:* Radatz (2023) ou (RADATZ, 2023).
* *Aplicação no projeto:* Ferramenta computacional de código aberto desenvolvida em Python utilizada para converter os dados geoespaciais e tabulares da BDGD da distribuidora (arquivos shapefiles e geodatabase) para os scripts executáveis do circuito no OpenDSS.

UNIVERSIDADE FEDERAL DO CEARÁ (UFC). Grupo de Redes Elétricas Inteligentes (GREI). **tsre-der-opentes: Plataforma de Co-Simulação para Integração de Recursos Energéticos Distribuídos**. Fortaleza: UFC, 2024. Disponível em: https://github.com/grei-ufc/tsre-der-opentes. Acesso em: 10 jan. 2026.
* *Chamada no texto:* GREI-UFC (2024) ou (GREI-UFC, 2024).
* *Aplicação no projeto:* Arquitetura modular de microsserviços base deste Trabalho de Conclusão de Curso.

