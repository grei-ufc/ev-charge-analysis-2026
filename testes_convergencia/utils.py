#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de utilitários para os testes de convergência do alimentador ESB01S4 no OpenDSS.
Fornece funções para inicialização do py_dss_interface, execução de simulações
em modo Snapshot e Daily (passo a passo), coleta de métricas e formatação de resultados.
"""

from pathlib import Path
import json
import py_dss_interface

BASE_DIR = Path(__file__).resolve().parents[1]
REDE_DIR = BASE_DIR / "data" / "rede" / "ESB01S4"


def inicializar_dss():
    """Inicializa a interface OpenDSS com proteção contra caixas de diálogo modais."""
    dss = py_dss_interface.DSS()
    try:
        dss.dssinterface.allow_forms = 0
    except Exception:
        pass
    return dss


def executar_simulacao_diaria(dss, n_passos=144, step_size="10m"):
    """
    Executa a simulação Daily passo a passo e coleta métricas detalhadas.
    
    Args:
        dss: Instância ativa do py_dss_interface.DSS
        n_passos: Número de passos diários (144 passos de 10 min = 24 horas)
        step_size: Intervalo de tempo do passo (ex: '10m')
        
    Returns:
        dict com métricas de convergência, iterações, tensões min/max e potências.
    """
    dss.text(f"Set mode=Daily stepsize={step_size} number=1")
    
    passos_convergidos = 0
    iteracoes_por_passo = []
    v_min_global = float("inf")
    v_max_global = float("-inf")
    historico = []

    for step in range(n_passos):
        dss.solution.solve()
        conv = int(dss.solution.converged)
        iters = int(dss.solution.iterations)
        
        # Checagem de integridade física: detecção de aborto silencioso / matriz singular
        erro_solver = False
        try:
            total_power = dss.circuit.total_power
            p_sub = -float(total_power[0])
            q_sub = -float(total_power[1])
            # Se a subestação reporta 0 kW em circuito com dezenas de cargas ativas, o solve abortou
            n_loads = dss.loads.count if hasattr(dss, "loads") else 0
            if n_loads > 50 and abs(p_sub) < 1e-3 and abs(q_sub) < 1e-3:
                erro_solver = True
        except Exception:
            p_sub = 0.0
            q_sub = 0.0
            erro_solver = True

        # Se houve erro fatal/aborto do solver, a convergência é nula e iterações atingem o limite
        if erro_solver or conv == 0:
            conv = 0
            if iters <= 2 and erro_solver:
                iters = 150
        
        if conv == 1:
            passos_convergidos += 1
        iteracoes_por_passo.append(iters)
        
        # Leitura das tensões de todas as barras em pu
        v_mag = dss.circuit.buses_vmag_pu
        # Filtrar nós desconectados ou com tensão residual nula (< 0.01 pu)
        v_validos = [v for v in v_mag if v > 0.01]
        
        step_vmin = min(v_validos) if v_validos else 0.0
        step_vmax = max(v_validos) if v_validos else 0.0
        
        v_min_global = min(v_min_global, step_vmin)
        v_max_global = max(v_max_global, step_vmax)
        
        # Potências na subestação (inversão de sinal: OpenDSS retorna negativo para injeção)
        try:
            total_power = dss.circuit.total_power
            p_sub = -float(total_power[0])
            q_sub = -float(total_power[1])
        except Exception:
            p_sub = 0.0
            q_sub = 0.0

        # Perdas totais (convertendo Watts/Vars para kW/kvar)
        try:
            losses = dss.circuit.losses
            p_loss = float(losses[0]) / 1000.0
            q_loss = float(losses[1]) / 1000.0
        except Exception:
            p_loss = 0.0
            q_loss = 0.0

        historico.append({
            "step": step,
            "converged": bool(conv == 1),
            "iterations": iters,
            "vmin_pu": round(step_vmin, 4),
            "vmax_pu": round(step_vmax, 4),
            "p_sub_kw": round(p_sub, 2),
            "q_sub_kvar": round(q_sub, 2),
            "p_loss_kw": round(p_loss, 2),
            "q_loss_kvar": round(q_loss, 2)
        })

    resumo = {
        "passos_totais": n_passos,
        "passos_convergidos": passos_convergidos,
        "pct_convergencia": round((passos_convergidos / n_passos) * 100.0, 2),
        "media_iteracoes": round(sum(iteracoes_por_passo) / len(iteracoes_por_passo), 2) if iteracoes_por_passo else 0.0,
        "min_iteracoes": min(iteracoes_por_passo) if iteracoes_por_passo else 0,
        "max_iteracoes": max(iteracoes_por_passo) if iteracoes_por_passo else 0,
        "vmin_pu_global": round(v_min_global, 4),
        "vmax_pu_global": round(v_max_global, 4),
        "historico": historico
    }
    return resumo


def executar_snapshot(dss):
    """Executa um fluxo de carga Snapshot simples e extrai status e tensões."""
    dss.text("Set mode=Snapshot")
    dss.solution.solve()
    conv = int(dss.solution.converged)
    iters = int(dss.solution.iterations)
    
    v_mag = dss.circuit.buses_vmag_pu
    v_validos = [v for v in v_mag if v > 0.01]
    
    vmin = min(v_validos) if v_validos else 0.0
    vmax = max(v_validos) if v_validos else 0.0
    
    return {
        "converged": bool(conv == 1),
        "iterations": iters,
        "vmin_pu": round(vmin, 4),
        "vmax_pu": round(vmax, 4)
    }


def imprimir_tabela_resumo(nome_cenario, res):
    """Exibe no terminal um resumo formatado das métricas obtidas."""
    print("=" * 70)
    print(f"📊 RESULTADO: {nome_cenario}")
    print("=" * 70)
    print(f"• Passos Convergidos: {res['passos_convergidos']} / {res['passos_totais']} ({res['pct_convergencia']}%)")
    print(f"• Média de Iterações: {res['media_iteracoes']:.2f}")
    print(f"• Iterações (Min / Máx): {res['min_iteracoes']} / {res['max_iteracoes']}")
    print(f"• Faixa de Tensão (pu): [{res['vmin_pu_global']:.4f}, {res['vmax_pu_global']:.4f}]")
    print("=" * 70)

