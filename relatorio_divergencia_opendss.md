# Relatório de Investigação e Resolução: Divergência do OpenDSS no Mosaik

## 1. O Problema
Durante a co-simulação no Mosaik, o motor de fluxo de potência (OpenDSS) começava a emitir valores completamente anômalos de tensão para as barras (ex: `1.429.802 PU` ou `1316.44 V` de desvio) logo na primeira iteração da simulação (Passo 0), estragando todos os resultados subsequentes. 
A natureza desafiadora desse bug residia no fato de que rodar o mesmo circuito `.dss` com os mesmos valores por fora do Mosaik (usando a mesma biblioteca `py-dss-interface` em um script puro) resultava em convergência perfeita (tensões em torno de `1.03 PU`).

## 2. O Processo de Investigação e Descoberta
Bugs silenciosos que causam divergência matemática sem gerar rastros de erro (*stacktraces*) padrão costumam levar **dias ou até semanas** para serem mapeados por equipes humanas (visto que a causa fica soterrada nos solvers matemáticos do OpenDSS). Na nossa sessão de *pair programming* (Humano + IA), levamos **algumas horas** de investigação exaustiva para achar a agulha no palheiro.

O diagnóstico exigiu um isolamento cirúrgico de variáveis, depuração sistemática e criação de ferramentas de captura customizadas.

**Como o problema foi rastreado:**
1. Inicialmente, isolei a topologia e tentei alimentá-la com um script manual mimetizando a carga da simulação (Painéis com $P=0$ e EVs com $P=0$). O script manual **convergiu**. Isso provou que a topologia DSS e as configurações paramétricas estavam intactas e funcionais.
2. Sabendo que o motor matemático não falha e é determinístico, a diferença tinha que estar na forma como o Mosaik manipulava o ambiente no exato microssegundo antes do solver de Newton atuar.
3. Para provar isso, injetei comandos maliciosos dentro do arquivo nativo `api_opendss.py` da biblioteca do simulador, obrigando o Mosaik a "cuspir" arquivos `.csv` (Dumps de estado contendo cargas ativas, potências dos painéis e as matrizes de tensão) no microssegundo exato anterior ao comando `self.dss_wrapper.run_dss()` ser despachado no Passo 0.
4. Ao rodar o gerador de `diff` entre os arquivos `.csv` do Mosaik e do Script Isolado, verifiquei que eles estavam **idênticos**. 
5. Foi então que olhei não para o Passo 0, mas para o que acontecia **antes** dele. Injetando prints em todos os callbacks da API (`create`, `setup_done`, `step`), descobri que o Mosaik chama o método `setup_done()` ao término da criação da rede, o qual invoca um `run_dss()` fantasma preliminar para estabilizar a rede inicial. E foi nesse exato comando preliminar que a anomalia ocorria.

## 3. A Causa Raiz
No Mosaik, o método `_bypass_native_pv_curves` (destinado a anular o comportamento do OpenDSS sobre os painéis e repassar a responsabilidade para o PVSimulator) reescrevia a `EffCurve` (Eficiência) e a `P-TCurve` (Temperatura), mas **esquecia de neutralizar a curva solar diária (`daily` / `TDaily`) e a irradiância inicial**.

O evento em cascata se sucedia da seguinte forma:
1. Ao terminar o carregamento da rede, o Mosaik invocava o `setup_done()`, realizando um _solve_ na rede.
2. Como a simulação principal ainda não havia começado, o OpenDSS usava seu relógio neutro: **00:00 (Meia-noite)**.
3. Na meia-noite, a curva `daily` residente forçava o multiplicador de irradiância solar do OpenDSS para 0 ou próximo de zero.
4. Ao chegar a uma irradiância muito baixa, a potência dos mais de 300 painéis solares caía abaixo da margem nativa de desconexão (`%cutout`).
5. Todos os mais de 300 inversores fotovoltaicos sofriam corte abrupto e se ejetavam da matriz elétrica do circuito instantaneamente.
6. Esse choque maciço destrutivo fazia a matriz Jacobiana (Newton-Raphson) divergir instantaneamente, setando a voltagem base internamente para **14 milhões de Volts**.
7. Um décimo de segundo depois, no **Passo 0** legítimo, o Mosaik enviava o comando correto e zerava a irradiância manualmente, porém o solver de Newton agora precisava partir do estado herdado corrompido de 14 Milhões de Volts e, sem conseguir reestabelecer o equilíbrio elétrico, declarava falha matemática e estacionava nos valores divergentes.

## 4. A Solução Aplicada
Para sanar o problema, neutralizamos não apenas as curvas de eficiência e temperatura, mas explicitamente o campo `daily` e o campo de irradiância no método de inibição nativa, assegurando que o OpenDSS estanque o painel sem disparar lógicas temporais parasitas.

**Código antigo (`api_opendss.py` - Linha 742 do repositório base / Linha 514 em nosso fork):**
```python
        for name in pv_infos:
            dss.text(
                f"Edit PVSystem.{name} %cutin=0.0001 %cutout=0.0001 "
                f"EffCurve=EffIdeal_Cosim P-TCurve=PTIdeal_Cosim"
            )
```

**Novo código aplicado:**
```python
        for name in pv_infos:
            dss.text(
                f"Edit PVSystem.{name} %cutin=0.0001 %cutout=0.0001 "
                f"EffCurve=EffIdeal_Cosim P-TCurve=PTIdeal_Cosim daily=\"\" TDaily=\"\" irradiance=0.0"
            )
```

## 5. Justificativas
* **`daily=""` e `TDaily=""`**: Remove a amarração com a curva temporal da rede original, entregando o controle 100% autônomo ao PVSimulator do Mosaik. Garante que, independente do horário (como as 00:00 do fluxo em vazio do `setup_done`), a irradiância obedeça à regra co-simulada estática.
* **`irradiance=0.0`**: Ao amarrar a irradiância nativa inicial do componente para zero absoluto e constante, o motor Newtoniano do OpenDSS converge de forma plana e pacífica no pre-solve (estado inicial a vazio), permitindo que o Passo 0 se inicie com as matrizes condicionadas e tensões perfeitas de `1.03 PU`. O OpenDSS apenas atuará nesses painéis quando o Mosaik ordenar.
* Este mesmo erro está presente e persistente no repositório original gerador do motor (`grei-ufc/tsre-der-opentes`), exigindo o mesmo tratamento estrutural caso for consumido novamente de lá.
