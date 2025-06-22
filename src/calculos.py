"""
Funções para cálculo de médias, índice Rexp e dimensões para o diagnóstico ICE³-R + DREXUS.
"""

def calcular_medias(respostas, variaveis_siglas):
    """
    Calcula a média ponderada de cada variável, normalizando para 0-1.
    :param respostas: Dicionário {variável: [(nota, peso), ...]}
    :param variaveis_siglas: Dicionário de nomes para siglas
    :return: Dicionário {sigla: média normalizada}
    """
    medias = {}
    for var, vals in respostas.items():
        notas = [nota for nota, peso in vals]
        pesos = [peso for nota, peso in vals]
        if sum(pesos) > 0:
            media = sum(n * p for n, p in zip(notas, pesos)) / sum(pesos)
        else:
            media = 0
        sigla = variaveis_siglas[var] if var in variaveis_siglas else var
        medias[sigla] = round(media / 5, 3)  # Normaliza em 0-1
    return medias

def calcular_rexp(medias):
    """
    Calcula o índice Rexp com base nas médias das variáveis.
    :param medias: Dicionário {sigla: média normalizada}
    :return: Valor de Rexp arredondado (float) ou None se incompleto
    """
    try:
        rexpb = medias["If"] * medias["Cm"] * medias["Et"]
        rexpa = 1 + medias["DREq"] * (1 + medias["Lc"] * medias["Im"] * medias["Pv"])
        rexp = round(rexpb * rexpa, 3)
        return rexp
    except KeyError:
        return None

def calcular_dimensoes(medias):
    """
    Calcula as 4 dimensões para o radar.
    :param medias: Dicionário {sigla: média normalizada}
    :return: Dicionário {dimensão: valor}
    """
    return {
        "Cognitiva": round(
            medias.get("Lc", 0) * 0.5 + medias.get("Et", 0) * 0.3 + medias.get("DREq", 0) * 0.2, 3),
        "Estratégica": round(
            medias.get("Pv", 0) * 0.4 + medias.get("Im", 0) * 0.3 + medias.get("DREq", 0) * 0.3, 3),
        "Operacional": round(
            medias.get("If", 0) * 0.4 + medias.get("Cm", 0) * 0.3 + medias.get("Et", 0) * 0.3, 3),
        "Cultural": round(
            medias.get("Et", 0) * 0.4 + medias.get("DREq", 0) * 0.3 + medias.get("Pv", 0) * 0.3, 3),
    }

def interpretar_rexp(rexp):
    """
    Retorna o texto da zona de maturidade de acordo com o valor do Rexp.
    """
    if rexp is None:
        return "Não calculado"
    elif rexp >= 0.80:
        return "Antifragilidade Regenerativa"
    elif rexp >= 0.60:
        return "Resiliência Estratégica"
    elif rexp >= 0.40:
        return "Maturidade Tática"
    elif rexp >= 0.20:
        return "Resiliência Reativa"
    else:
        return "Fragilidade Total"