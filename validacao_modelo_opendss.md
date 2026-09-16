# Guia de Validação do Modelo OpenDSS para o TCC

Para garantir que a rede ajustada (`ADT01C2`) está 100% confiável e pronta para as análises avançadas do seu projeto (como inserção de veículos elétricos), você deve realizar uma série de "testes de sanidade" (Sanity Checks) elétricos. 

Abaixo está o passo a passo dos **6 Pilares de Validação**.

---

## 1. Verificação de Convergência (O Básico)
O primeiro e mais fundamental passo é garantir que as matrizes matemáticas do circuito estão bem condicionadas.
- **O que verificar:** Após o comando `solve`, cheque se a rede convergiu.
- **Sintoma de erro:** Se não convergiu, geralmente há ilhas, impedâncias muito próximas de zero ou cargas/geradores definidos com tensões nominais completamente diferentes das bases declaradas.

## 2. Validação da Topologia (Ilhas)
A rede precisa estar perfeitamente conectada, sem "galhos" elétricos soltos.
- **O que verificar:** A ferramenta `dss.topology` deve retornar `0` tanto para `num_isolated_branches` quanto para `num_isolated_loads`.
- **Sintoma de erro:** Linhas desconectadas por chaves abertas incorretamente ou falha no mapeamento das ramificações.

## 3. Balanço de Potência e Perdas Técnicas
Verificar se a energia injetada bate com a energia consumida mais as perdas.
- **O que verificar:** Extraia as perdas totais do circuito. Em redes de distribuição brasileiras, as perdas técnicas costumam ficar entre **2% e 8%** da potência total injetada.
- **Sintoma de erro:** Se as perdas derem `30%` ou `99%`, indica problemas críticos: comprimentos de linha em unidade errada, bitolas super resistivas ou curto-circuito não intencional (ex: colocar uma linha ligando primário ao secundário de um trafo).

## 4. Validação dos Níveis de Tensão (PU)
A tensão é o melhor indicador de "saúde" de uma rede elétrica simulada.
- **O que verificar:** Extraia as tensões em PU de todas as barras da rede. O valor deve estar na faixa de operação, tipicamente entre **0.93 pu e 1.05 pu**.
- **Sintoma de erro:** 
  - Tensões absurdas (ex: `0.1 pu`): A barra está sobrecarregada ou ligada a um ramal muito fraco e longo.
  - Tensões muito altas (ex: `1.2 pu`): Injeção excessiva por Geração Distribuída ou bases de tensão configuradas erroneamente.

## 5. Carregamento de Cabos e Transformadores
Nenhum elemento passivo deve operar em sobrecarga extrema no cenário base.
- **O que verificar:** A corrente de fluxo não deve ultrapassar a nominal do cabo (`NormAmps`). 
- **Sintoma de erro:** Ramais com bitolas incompatíveis com a carga suportada.

## 6. Verificação Dinâmica e Visual
Se você estiver utilizando a biblioteca `py_dss_toolkit`, é possível plotar um mapa de calor das sobrecargas para localizar rapidamente onde o reforço da rede é necessário. (Cuidado visual: como a biblioteca não desenha transformadores, aplicamos um truque de criar chaves abertas em paralelo com eles para preencher o buraco visual no mapa).

---

## 🛠️ Script Python Automático para Validação

Este script já contém as correções avançadas: **integração do mapa**, **workaround para o Windows WSL (gio)**, e a **correção visual dos transformadores (chaves abertas)**.

```python
import os
import pathlib
import py_dss_interface
from py_dss_toolkit import dss_tools

# --- CORREÇÃO AGRESSIVA PARA O WSL (Erro gio: Operation not supported) ---
import webbrowser
import subprocess

def wsl_browser_open(url, new=0, autoraise=True):
    try:
        subprocess.Popen(['/mnt/c/Windows/explorer.exe', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

webbrowser.open = wsl_browser_open
# -------------------------------------------------------------------------

def validar_rede():
    dss = py_dss_interface.DSS()
    
    # Conecta o DSS ao Toolkit para habilitar plotagens gráficas
    dss_tools.update_dss(dss)
    
    # 1. Compilação
    base_dir = pathlib.Path(__file__).resolve().parent.parent
    dss_file = base_dir / "rede" / "dados-rede" / "ADT01C2-ajustada" / "Master_20250139_ADT01C2.dss"
    
    os.chdir(dss_file.parent)
    dss.text(f"compile [{dss_file.name}]")
    
    # --- PREPARAÇÃO DO MODELO GEOMÉTRICO ---
    dss_tools.model.add_line_in_vsource(add_meter=True)
    
    # --- CORREÇÃO VISUAL PARA OS TRANSFORMADORES ---
    dss.transformers.first()
    for _ in range(dss.transformers.count):
        bus1 = dss.cktelement.bus_names[0]
        bus2 = dss.cktelement.bus_names[1]
        nome_linha = f"dummy_{dss.transformers.name}"
        # Criamos uma chave e a abrimos em seguida. 
        # Assim o gráfico desenha a linha (unindo MT e BT visualmente), 
        # mas sem causar um curto-circuito elétrico de verdade!
        dss.text(f"New Line.{nome_linha} bus1={bus1} bus2={bus2} switch=y")
        dss.text(f"Open Line.{nome_linha} term=1")
        dss.transformers.next()
    # -----------------------------------------------
    
    # --- CORREÇÃO DA DISTORÇÃO (Coordenada da Fonte) ---
    dss.circuit.set_active_element("line.feeder_head")
    bus_irreal = dss.cktelement.bus_names[0].split(".")[0]
    bus_real = dss.cktelement.bus_names[1].split(".")[0]

    dss.circuit.set_active_bus(bus_real)
    x_real, y_real = dss.bus.x, dss.bus.y
    dss.circuit.set_active_bus(bus_irreal)
    dss.bus.x, dss.bus.y = x_real, y_real
    # ---------------------------------------------------------------------

    # Executa o Fluxo de Potência
    dss.text("solve")
    
    print("\n" + "="*50)
    print(" 🕵️ DIAGNÓSTICO DE SAÚDE DA REDE (SNAPSHOT)")
    print("="*50)

    # 1. Convergência
    convergencia = dss.solution.converged
    print(f"[1] Convergiu? {'✅ SIM' if convergencia else '❌ NÃO'}")
    if not convergencia:
        print("🚨 Pare aqui! A rede não convergiu. Verifique chaves abertas ou ilhas.")
        return

    # 2. Verificação de Topologia (Ilhas e Elementos Desconectados)
    num_isolated_branches = dss.topology.num_isolated_branches
    num_isolated_loads = dss.topology.num_isolated_loads
    
    print(f"\n[2] Topologia (Elementos Isolados):")
    if num_isolated_branches == 0 and num_isolated_loads == 0:
        print("    ✅ Toda a rede está conectada. Nenhum elemento isolado!")
    else:
        print(f"    ❌ Encontrados {num_isolated_branches} trecho(s) de linha desconectado(s).")
        if num_isolated_branches > 0:
            print(f"       Exemplos: {dss.topology.all_isolated_branches[:5]}")
        print(f"    ❌ Encontradas {num_isolated_loads} carga(s) desconectada(s).")
        if num_isolated_loads > 0:
            print(f"       Exemplos: {dss.topology.all_isolated_loads[:5]}")

    # 3. Perdas e Potência
    kw_perdas, kvar_perdas = dss.circuit.losses
    kw_perdas, kvar_perdas = kw_perdas / 1000, kvar_perdas / 1000 # Convertendo W para kW
    
    kw_total, kvar_total = dss.circuit.total_power
    kw_total = abs(kw_total) # Potência injetada é mostrada negativa
    
    perc_perdas = (kw_perdas / kw_total) * 100
    
    print(f"\n[3] Balanço de Potência:")
    print(f"    - Potência Injetada (Carga + Perdas): {kw_total:.2f} kW")
    print(f"    - Perdas Técnicas Ativas: {kw_perdas:.2f} kW ({perc_perdas:.2f}%)")
    if perc_perdas > 15:
        print("    ⚠️ ALERTA: Perdas muito altas! Verifique comprimentos de linha ou resistências.")

    # 4. Níveis de Tensão (Foco na Média Tensão para checagem rápida)
    v_pu = dss.circuit.buses_vmag_pu
    v_pu_ativos = [v for v in v_pu if v > 0.1]
    v_max = max(v_pu_ativos)
    v_min = min(v_pu_ativos)
    
    print(f"\n[4] Tensões (PU):")
    print(f"    - Tensão Mínima: {v_min:.4f} pu")
    print(f"    - Tensão Máxima: {v_max:.4f} pu")
    
    if v_min < 0.90:
        print("    ⚠️ ALERTA: Subtensão grave detectada. Verifique conectividade ou sobrecarga de ramais.")
    if v_max > 1.05:
        print("    ⚠️ ALERTA: Sobretensão detectada. Verifique tap de trafos ou geração distribuída (GD).")

    # 5. Verificação de Sobrecarga
    elementos_sobrecarregados = 0
    dss.lines.first()
    for _ in range(dss.lines.count):
        if dss.cktelement.norm_amps > 0:
            correntes = dss.cktelement.currents_mag_ang
            corrente_maxima = max(correntes[0::2]) # Pega apenas as magnitudes das fases
            carregamento = corrente_maxima / dss.cktelement.norm_amps
            if carregamento > 1.0:
                elementos_sobrecarregados += 1
        dss.lines.next()
        
    print(f"\n[5] Carregamento (Linhas):")
    if elementos_sobrecarregados == 0:
        print("    ✅ Nenhuma linha operando em sobrecarga.")
    else:
        print(f"    ❌ {elementos_sobrecarregados} linha(s) com sobrecarga (> 100% da capacidade nominal).")
        
    print("="*50 + "\n")
    
    # 6. Visualização Gráfica Interativa
    if elementos_sobrecarregados > 0:
        print("💡 Abrindo o mapa interativo com as Violações Térmicas (sobrecargas) destacadas no seu navegador...")
        dss_tools.interactive_view.circuit_plot(parameter="thermal violations", title="Violações Térmicas (Sobrecargas)", show=True)

if __name__ == '__main__':
    validar_rede()
```
