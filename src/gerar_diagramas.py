"""Gera desenhos legíveis dos AFDs diretamente a partir de delta.

Requer pacote graphviz (Python) e executável dot (Graphviz do sistema).
Os SVG/PNG já acompanham o projeto e NÃO precisam ser regenerados para executar o projeto.
"""
from collections import defaultdict
from pathlib import Path
from graphviz import Digraph
from src.r1_afds import cartao, linha, DIGITOS, NAO_ZERO

BASE = Path(__file__).resolve().parent.parent
PASTA = BASE / 'diagramas'
PASTA.mkdir(exist_ok=True)


def rotulo(classes):
    classes = frozenset(classes)
    if classes == DIGITOS:
        return '0–9'
    if classes == NAO_ZERO:
        return '1–9'
    traduzir = {
        'ZERO': '0',
        'UM_A_QUATRO': '1–4',
        'CINCO_A_NOVE': '5–9',
        'PONTO': '.',
        'HIFEN': '−',
        'OUTRO': 'outro',
    }
    return ', '.join(traduzir[c] for c in ('ZERO', 'UM_A_QUATRO', 'CINCO_A_NOVE', 'PONTO', 'HIFEN', 'OUTRO') if c in classes)


def criar_grafo(afd, arquivo):
    dot = Digraph(name=arquivo, comment=f'AFD: {afd.nome}', format='svg')
    dot.attr(rankdir='LR', bgcolor='#ffffff', pad='0.22', nodesep='0.30', ranksep='0.46', splines='polyline', fontname='DejaVu Sans')
    dot.attr('node', shape='circle', style='filled', fillcolor='#eff6ff', color='#2563eb', penwidth='1.5', fontname='DejaVu Sans', fontsize='13')
    dot.attr('edge', color='#334155', arrowsize='0.65', fontname='DejaVu Sans', fontsize='12', penwidth='1.5')
    dot.node('inicio', label='', shape='point', fillcolor='#0f172a', color='#0f172a', width='0.1')
    for estado in afd.estados:
        if estado == 'qerro':
            continue
        if estado in afd.finais:
            dot.node(estado, shape='doublecircle', fillcolor='#dcfce7', color='#16a34a', penwidth='2')
        else:
            dot.node(estado)
    dot.edge('inicio', afd.inicial, color='#2563eb')
    # As arestas vem diretamente de delta, inclusive se os nomes dos estados mudarem.
    grupos = defaultdict(list)
    for (origem, classe), destino in afd.delta.items():
        if origem != 'qerro' and destino != 'qerro':
            grupos[(origem, destino)].append(classe)
    for (origem, destino), classes in grupos.items():
        dot.edge(origem, destino, label=rotulo(classes))
    # O qerro é parte formal do AFD, mas as arestas de erro são suprimidas neste
    # desenho para evitar poluição visual. A tabela imprime todas as transições.
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#fff1f2', color='#be123c', fontcolor='#881337', fontsize='11')
    dot.node('qerro', label='qerro\nestado de erro')
    dot.edge('qerro', 'qerro', label='todas as classes', color='#be123c')
    dot.node('nota', label='Para cada estado, toda classe não indicada\nleva a qerro (veja a tabela completa).', shape='note', style='filled', fillcolor='#f8fafc', color='#94a3b8', fontsize='11')
    dot.attr('edge', style='invis')
    for final in sorted(afd.finais):
        dot.edge(final, 'nota')
    dot.edge('nota', 'qerro')
    dot.attr('edge', style='solid')
    path = PASTA / arquivo
    dot.save(path.with_suffix('.dot'))
    dot.render(str(path), format='svg', cleanup=True)
    dot.render(str(path), format='png', cleanup=True)
    print(f'Gerado: {path}.svg e {path}.png')


if __name__ == '__main__':
    criar_grafo(cartao, 'afd_cartao')
    criar_grafo(linha, 'afd_linha')
