"""Gera diagrama SVG/PNG/DOT do R4 diretamente da tabela de transições.

Requer Graphviz (biblioteca Python e comando dot). Diagramas já estão
salvos no repositório, sem ser necessário gerar ao executar o notebook.
"""
from pathlib import Path
from graphviz import Digraph
from .r4_catraca import ESTADOS, ESTADO_INICIAL, TRANSICOES


def gerar(destino: Path = None):
    destino = Path(destino) if destino else Path(__file__).resolve().parents[1] / "diagramas"
    destino.mkdir(parents=True, exist_ok=True)
    g = Digraph("catraca", comment="R4 - Máquina de estados da catraca", format="svg")
    g.attr(rankdir="LR", bgcolor="#ffffff", labelloc="t",
           label="R4 — Máquina de Estados da Catraca", fontsize="18",
           fontname="DejaVu Sans", nodesep="0.55", ranksep="1.45", pad="0.4")
    g.attr("node", shape="box", style="rounded,filled", fillcolor="#eff6ff",
           color="#4169a1", fontname="DejaVu Sans", fontsize="11", margin="0.18,0.1")
    g.attr("edge", fontname="DejaVu Sans", fontsize="9", fontcolor="#0f172a", color="#475569", arrowsize="0.7")
    g.node("inicio", label="", shape="point", width="0.08", color="#475569")
    for estado in ESTADOS:
        fundo = "#d1fae5" if estado == "PASSAGEM_REGISTRADA" else ("#fef3c7" if estado == "SEM_SALDO" else "#eff6ff")
        g.node(estado, label=estado.replace("_", "\n"), fillcolor=fundo,
               penwidth="2" if estado == ESTADO_INICIAL else "1")
    g.edge("inicio", ESTADO_INICIAL, label="início")
    for t in TRANSICOES:
        g.edge(t.origem, t.destino, label=t.evento.replace("_", "\n"))
    dot = destino / "catraca_estados.dot"
    dot.write_text(g.source, encoding="utf-8")
    svg = Path(g.render(filename="catraca_estados", directory=str(destino), format="svg", cleanup=True))
    png = Path(g.render(filename="catraca_estados", directory=str(destino), format="png", cleanup=True))
    return dot, svg, png


if __name__ == "__main__":
    for caminho in gerar():
        print("Gerado:", caminho)
