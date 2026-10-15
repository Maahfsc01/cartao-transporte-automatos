"""R6 — Laboratório interativo em Jupyter para o Cartão de Transporte.

A camada de interface usa ipywidgets, mas NÃO implementa novamente as
regras de AFD, RegEx, scanner ou máquina de estados. A lógica testável
(geração de resultados e HTML) funciona sem instalar ipywidgets.

A interface é local e didática: não efetua recargas nem movimenta catracas reais.
"""

from dataclasses import dataclass
from html import escape
from typing import Optional

from .r1_afds import cartao, linha
from .r2_rastreamento import Rastreamento, rastrear_detalhado
from .r3_equivalencia import REGEX_CARTAO, REGEX_LINHA, aceita_regex
from .r4_catraca import Catraca, CENARIOS, DESCRICOES_ESTADOS, EVENTOS, PassoCatraca, ResultadoFluxo
from .r5_scanner import analisar, EXEMPLO_VALIDO, EXEMPLO_COM_ERROS, ResultadoScanner



CSS_PAINEL_COMPACTO = """
<style>
/* Tipografia compacta, legivel e isolada da interface do Jupyter. */
.transporte-painel-compacto {font-size:13px;line-height:1.45;}
.transporte-painel-compacto .widget-label,
.transporte-painel-compacto .jupyter-widgets,
.transporte-painel-compacto .widget-tab > .p-TabBar {font-size:13px;}
.transporte-painel-compacto .widget-button,
.transporte-painel-compacto .jupyter-button,
.transporte-painel-compacto input,
.transporte-painel-compacto select,
.transporte-painel-compacto textarea {font-size:13px;}
.transporte-painel-compacto .widget-button,
.transporte-painel-compacto .jupyter-button {min-height:30px;}
.transporte-painel-compacto .widget-tab > .p-TabBar .p-TabBar-tab {padding:5px 10px;}
.transporte-painel-compacto table {font-size:12.5px;line-height:1.35;}
.transporte-painel-compacto td,
.transporte-painel-compacto th {overflow-wrap:anywhere;}
@media (max-width:650px) {
 .transporte-painel-compacto {font-size:12.5px;}
 .transporte-painel-compacto .widget-button,
 .transporte-painel-compacto .jupyter-button {max-width:100%;}
}
</style>
"""

VALIDADORES = {
    "cartao": (cartao, REGEX_CARTAO, "12.34.56789012-3", "12.34.56789012-3X"),
    "linha": (linha, REGEX_LINHA, "8700-10", "8700-50"),
}


@dataclass(frozen=True)
class Avaliacao:
    chave: str
    rastreamento: Rastreamento
    padrao_regex: str
    aceito_regex: bool

    @property
    def coincide(self) -> bool:
        return self.rastreamento.aceita == self.aceito_regex


def avaliar_entrada(chave: str, palavra: str) -> Avaliacao:
    """Calcula uma avaliação sem estado compartilhado, a partir de R1, R2 e R3."""
    if chave not in VALIDADORES:
        raise ValueError(f"Validador desconhecido: {chave!r}")
    afd, regex, _, _ = VALIDADORES[chave]
    rastreamento = rastrear_detalhado(afd, palavra)
    return Avaliacao(chave, rastreamento, regex.pattern, aceita_regex(regex, palavra))


def _esc(valor: object) -> str:
    """Não interpretar texto digitado pelo usuário como marcação HTML."""
    return escape(str(valor), quote=True)


def _codigo(valor: object) -> str:
    return '<code style="font-family:ui-monospace,Consolas,monospace;font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere">' + _esc(valor) + '</code>'


def _tabela(colunas, linhas, titulo: str) -> str:
    """Exibe dados como tabela com título acessível e rolagem horizontal."""
    th = "".join('<th scope="col" style="text-align:left;padding:5px 8px;border-bottom:2px solid #777">'
                 + _esc(col) + "</th>" for col in colunas)
    if linhas:
        linhas_html = "".join(
            "<tr>" + "".join('<td style="padding:5px 8px;border-bottom:1px solid #bbb;vertical-align:top">'
                                + _codigo(celula) + "</td>" for celula in linha) + "</tr>"
            for linha in linhas
        )
    else:
        linhas_html = f'<tr><td colspan="{len(colunas)}" style="padding:8px">Nenhum item.</td></tr>'
    return ('<div style="max-width:100%;overflow-x:auto;margin:7px 0">'
            '<table style="border-collapse:collapse;width:100%;font-size:12.5px;line-height:1.35">'
            '<caption style="text-align:left;font-weight:600;padding:4px 0">'
            + _esc(titulo) + '</caption><thead><tr>' + th + '</tr></thead><tbody>'
            + linhas_html + '</tbody></table></div>')


def _resumo(texto: str, sucesso: Optional[bool] = None) -> str:
    if sucesso is None:
        cor = "#44515f"
    else:
        cor = "#14643c" if sucesso else "#9a2b27"
    # A informação textual não depende da cor.
    return ('<div role="status" style="border-left:4px solid ' + cor +
            ';padding:7px 10px;background:rgba(127,127,127,.08);margin:6px 0;font-size:12.5px;line-height:1.4">' + texto + '</div>')


def html_validacao(avaliacao: Avaliacao) -> str:
    r = avaliacao.rastreamento
    estado = "ACEITA" if r.aceita else "REJEITADA"
    titulo = "✅ ACEITA" if r.aceita else "❌ REJEITADA"
    regex = "ACEITA" if avaliacao.aceito_regex else "REJEITA"
    consistencia = "✅ Concordância AFD × RegEx" if avaliacao.coincide else "❌ Divergência AFD × RegEx"
    palavras = '<em>(palavra vazia — nenhum caractere)</em>' if r.palavra == "" else _codigo(repr(r.palavra))
    cabecalho = (
        '<div><strong>Validador: ' + _esc(r.afd) + '</strong></div>'
        '<div>Entrada: ' + palavras + '</div>'
        + _resumo('<strong>Resultado: ' + titulo + '</strong> | Estado final: ' + _codigo(r.estado_final)
                  + ' | RegEx: ' + _codigo(regex) + ' | ' + consistencia, avaliacao.coincide and r.aceita)
        + '<div>RegEx equivalente: ' + _codigo(avaliacao.padrao_regex) + '</div>'
    )
    linhas = [(p.posicao, p.origem, repr(p.caractere), p.classe,
               ", ".join(p.esperadas) or "nenhuma", p.destino, p.explicacao)
              for p in r.passos]
    detalhe = _tabela(("Pos.", "Origem", "Caractere", "Classe", "Esperadas", "Destino", "Explicação"),
                      linhas, "Transições consumidas do AFD")
    if not r.passos:
        detalhe += '<p style="font-size:12.5px"><em>Palavra vazia: permanece no estado inicial q0.</em></p>'
    return cabecalho + detalhe + _resumo('<strong>Justificativa:</strong> ' + _esc(r.motivo), r.aceita)


def html_scanner(resultado: ResultadoScanner, limite: int = 120) -> str:
    """Apresenta tokens e erros sem executar comandos nem permitir HTML de entrada."""
    if limite < 1:
        raise ValueError("limite deve ser positivo")
    estado = "✅ ANÁLISE SEM ERROS LÉXICOS" if not resultado.erros else "❌ ERROS LÉXICOS IDENTIFICADOS"
    topo = _resumo('<strong>' + estado + '</strong> — ' + str(len(resultado.tokens))
                   + ' tokens, ' + str(len(resultado.erros)) + ' erros, '
                   + str(resultado.linhas) + ' linha(s) contadas.', resultado.aprovado)
    linhas_tokens = [(t.linha, t.coluna, t.tipo, repr(t.lexema)) for t in resultado.tokens[:limite]]
    linhas_erros = [(e.linha, e.coluna, repr(e.lexema), e.mensagem, e.dica)
                    for e in resultado.erros[:limite]]
    saida = topo + _tabela(("Linha", "Coluna", "Token", "Lexema"), linhas_tokens, "Tokens reconhecidos")
    saida += _tabela(("Linha", "Coluna", "Lexema", "Erro", "Dica de correção"), linhas_erros,
                    "Erros léxicos — a leitura continuou após cada erro")
    if len(resultado.tokens) > limite or len(resultado.erros) > limite:
        saida += '<p><strong>Aviso:</strong> exibição limitada aos primeiros ' + str(limite) + ' itens por tabela.</p>'
    saida += '<p><em>Análise léxica apenas: nenhum comando foi executado nem houve recarga real.</em></p>'
    return saida


def html_catraca(catraca: Catraca, ultimo: Optional[PassoCatraca] = None,
                 fluxo: Optional[ResultadoFluxo] = None) -> str:
    estado = catraca.estado
    permitidos = catraca.permitidos()
    saida = '<h4 style="font-size:15px;margin:5px 0">Estado atual: ' + _codigo(estado) + '</h4>'
    saida += '<p>' + _esc(DESCRICOES_ESTADOS[estado]) + '</p>'
    saida += '<p><strong>Eventos permitidos agora:</strong> ' + ', '.join(_codigo(e) for e in permitidos) + '</p>'
    saida += '<p><strong>Passagens registradas:</strong> ' + str(catraca.passagens_registradas) + '</p>'
    if ultimo is not None:
        status = "✅ ACEITO" if ultimo.aceito else "❌ RECUSADO"
        saida += _resumo('<strong>Último evento: ' + status + '</strong> — ' +
                         _codigo(ultimo.evento) + '<div>' + _esc(ultimo.explicacao) + '</div>', ultimo.aceito)
    if fluxo is not None:
        completo = "✅ VÁLIDO" if fluxo.completo else "❌ INVÁLIDO (houve recusa)"
        saida += _resumo('<strong>Cenário: ' + _esc(fluxo.titulo) + '</strong> — ' + completo
                         + ' | Eventos processados: ' + str(len(fluxo.passos)) + '/'
                         + str(fluxo.eventos_solicitados), fluxo.completo)
    historico = catraca.historico
    linhas = [(p.numero, p.origem, p.evento, p.destino,
               "ACEITO" if p.aceito else "RECUSADO", p.explicacao)
              for p in historico[-30:]]
    saida += _tabela(("#", "Origem", "Evento", "Destino", "Resultado", "Explicação"),
                     linhas, "Histórico da sessão (últimos 30 eventos)")
    if len(historico) > 30:
        saida += '<p>Mostrando os últimos 30 dos ' + str(len(historico)) + ' eventos.</p>'
    return saida


class LaboratorioR6:
    """Constrói e vincula os controles nativos do ipywidgets.

    Usar no notebook:
        from src.r6_interface import LaboratorioR6
        laboratorio = LaboratorioR6()
        display(laboratorio.widget)

    O estado da catraca é por instância do painel. Executar um cenário
    reinicia apenas a instância exibida, sem modificar as definições do R4.
    """

    def __init__(self):
        try:
            import ipywidgets as w
        except ImportError as erro:
            if erro.name == "ipywidgets":
                raise ModuleNotFoundError(
                    "A interface R6 requer ipywidgets. Instale com: "
                    "python -m pip install -r requirements.txt"
                ) from erro
            raise
        self._w = w
        self.catraca = Catraca()
        self._construir()

    def _construir(self):
        w = self._w
        largura = w.Layout(width="100%")
        corpo = "font-size:13px;line-height:1.45;margin:3px 0 8px"
        subtitulo = "font-size:16px;font-weight:600;line-height:1.35;margin:9px 0 5px"
        def botao(texto, cor="", icone=""):
            return w.Button(description=texto, button_style=cor, icon=icone,
                            layout=w.Layout(width="auto", min_width="115px"))
        def fila(*itens):
            return w.HBox(list(itens), layout=w.Layout(width="100%", flex_flow="row wrap"))
        def bloco(*itens):
            return w.VBox(list(itens), layout=largura)

        # ABA 1: AFDs + rastreamento + RegEx.
        self.seletor_afd = w.Dropdown(options=[("Cartão de transporte", "cartao"),
                                               ("Linha de ônibus", "linha")], value="cartao",
                                      description="Validador:", style={"description_width": "initial"})
        self.campo_palavra = w.Text(value=VALIDADORES["cartao"][2],
                                   description="Palavra:", placeholder="Digite a palavra, ou deixe vazia",
                                   style={"description_width": "initial"}, layout=largura)
        self.botao_validar = botao("Validar e rastrear", "primary", "check")
        self.botao_aceita = botao("Exemplo aceito", "", "check-circle")
        self.botao_rejeita = botao("Exemplo rejeitado", "", "times-circle")
        self.botao_vazia = botao("Palavra vazia", "", "eraser")
        self.saida_afd = w.HTML(value="", layout=largura)
        secao_afds = bloco(
            w.HTML(f'<h3 style="{subtitulo}">1. Validadores AFD</h3>'
                   f'<p style="{corpo}">Selecione o formato, digite uma palavra e veja cada transição da '
                   'função <code>delta</code> e a comparação com <code>re.fullmatch()</code>.</p>'),
            self.seletor_afd, self.campo_palavra,
            fila(self.botao_validar, self.botao_aceita, self.botao_rejeita, self.botao_vazia),
            self.saida_afd,
        )

        # ABA 2: R4 — estado persistente, eventos válidos e inválidos disponíveis.
        self.seletor_evento = w.Dropdown(options=[(nome, nome) for nome in EVENTOS],
                                        value="APROXIMAR_CARTAO", description="Evento:",
                                        style={"description_width": "initial"}, layout=largura)
        self.botao_disparar = botao("Disparar evento", "primary", "play")
        self.botao_reiniciar = botao("Reiniciar catraca", "", "refresh")
        self.seletor_cenario = w.Dropdown(options=[(cenario[0], i) for i, cenario in enumerate(CENARIOS)],
                                         value=0, description="Demonstração:",
                                         style={"description_width": "initial"}, layout=largura)
        self.botao_cenario = botao("Executar cenário", "", "list")
        self.saida_catraca = w.HTML(value=html_catraca(self.catraca), layout=largura)
        secao_catraca = bloco(
            w.HTML(f'<h3 style="{subtitulo}">2. Máquina de estados da catraca — R4</h3>'
                   f'<p style="{corpo}">Escolha qualquer evento, inclusive um proibido no estado atual. '
                   'Em caso de recusa, a catraca informa os eventos permitidos. '
                   'Tudo é simulado, sem conexão com leitores físicos.</p>'),
            self.seletor_evento, fila(self.botao_disparar, self.botao_reiniciar),
            self.seletor_cenario, self.botao_cenario, self.saida_catraca,
        )

        # ABA 3: R5 — scanner de múltiplas linhas com diagnóstico recuperável.
        self.campo_comandos = w.Textarea(value=EXEMPLO_VALIDO, description="Comandos:",
                                        placeholder="Digite comandos de transporte",
                                        style={"description_width": "initial"},
                                        layout=w.Layout(width="100%", height="142px"))
        self.botao_analisar = botao("Analisar tokens", "primary", "search")
        self.botao_exemplo_valido = botao("Exemplo válido", "", "check-circle")
        self.botao_exemplo_erros = botao("Exemplo com erros", "", "exclamation-triangle")
        self.botao_limpar = botao("Limpar texto", "", "eraser")
        self.saida_scanner = w.HTML(value=_resumo(
            'Digite um programa ou selecione um exemplo e clique em <strong>Analisar tokens</strong>.'),
            layout=largura)
        secao_scanner = bloco(
            w.HTML(f'<h3 style="{subtitulo}">3. Scanner da linguagem de transporte — R5</h3>'
                   f'<p style="{corpo}">Digite várias linhas com <code>RECARGA</code>, <code>EMBARQUE</code> '
                   'ou <code>SALDO</code>. O scanner identifica tokens, Maximal Munch, '
                   'e erros com linha, coluna e dica, <strong>continuando após o erro</strong>.</p>'),
            self.campo_comandos,
            fila(self.botao_analisar, self.botao_exemplo_valido,
                 self.botao_exemplo_erros, self.botao_limpar), self.saida_scanner,
        )

        self.abas = w.Tab(children=[secao_afds, secao_catraca, secao_scanner], layout=largura)
        for i, titulo in enumerate(("Validadores AFD", "Catraca", "Scanner")):
            self.abas.set_title(i, titulo)
        self.widget = bloco(
            w.HTML(value=CSS_PAINEL_COMPACTO),
            w.HTML(value='<div style="border-bottom:2px solid #3c7990;padding:3px 0 7px">'
                   '<h2 style="font-size:19px;line-height:1.3;margin:3px 0 5px">🚍 Laboratório interativo — Cartão de Transporte</h2>'
                   '<p style="font-size:13px;line-height:1.4;margin:4px 0">R6 · Teste os AFDs, acompanhe a catraca e analise '
                   'comandos, <strong>sem alterar código</strong>.</p></div>'),
            self.abas,
            w.HTML('<p style="font-size:12px;line-height:1.4;margin:5px 0"><strong>Observação:</strong> códigos e '
                   'movimentações são fictícios. Este painel não valida cartões reais, '
                   'não desconta tarifas e não realiza recargas financeiras.</p>'),
        )

        # Classe CSS so no painel: não diminui o texto de outros notebooks.
        if hasattr(self.widget, "add_class"):
            self.widget.add_class("transporte-painel-compacto")

        # O callback de mudança do AFD preenche automaticamente um exemplo válido.
        self.seletor_afd.observe(self._trocar_afd, names="value")
        self.botao_validar.on_click(self._validar)
        self.botao_aceita.on_click(self._exemplo_aceito)
        self.botao_rejeita.on_click(self._exemplo_rejeitado)
        self.botao_vazia.on_click(self._palavra_vazia)
        self.botao_disparar.on_click(self._disparar)
        self.botao_reiniciar.on_click(self._reiniciar)
        self.botao_cenario.on_click(self._executar_cenario)
        self.botao_analisar.on_click(self._analisar)
        self.botao_exemplo_valido.on_click(self._comandos_validos)
        self.botao_exemplo_erros.on_click(self._comandos_com_erros)
        self.botao_limpar.on_click(self._limpar_comandos)
        self._validar(None)

    def _trocar_afd(self, mudanca):
        if mudanca.get("name") == "value" and mudanca.get("new") in VALIDADORES:
            self.campo_palavra.value = VALIDADORES[mudanca["new"]][2]
            self._validar(None)

    def _validar(self, _):
        self.saida_afd.value = html_validacao(avaliar_entrada(
            self.seletor_afd.value, self.campo_palavra.value))

    def _exemplo_aceito(self, _):
        self.campo_palavra.value = VALIDADORES[self.seletor_afd.value][2]
        self._validar(None)

    def _exemplo_rejeitado(self, _):
        self.campo_palavra.value = VALIDADORES[self.seletor_afd.value][3]
        self._validar(None)

    def _palavra_vazia(self, _):
        self.campo_palavra.value = ""
        self._validar(None)

    def _disparar(self, _):
        passo = self.catraca.disparar(self.seletor_evento.value)
        self.saida_catraca.value = html_catraca(self.catraca, ultimo=passo)

    def _reiniciar(self, _):
        self.catraca.reiniciar()
        self.saida_catraca.value = html_catraca(self.catraca)

    def _executar_cenario(self, _):
        titulo, eventos, _ = CENARIOS[self.seletor_cenario.value]
        self.catraca.reiniciar()
        resultado = self.catraca.executar(eventos, titulo=titulo)
        self.saida_catraca.value = html_catraca(self.catraca, fluxo=resultado)

    def _analisar(self, _):
        self.saida_scanner.value = html_scanner(analisar(self.campo_comandos.value))

    def _comandos_validos(self, _):
        self.campo_comandos.value = EXEMPLO_VALIDO
        self._analisar(None)

    def _comandos_com_erros(self, _):
        self.campo_comandos.value = EXEMPLO_COM_ERROS
        self._analisar(None)

    def _limpar_comandos(self, _):
        self.campo_comandos.value = ""
        self.saida_scanner.value = _resumo("Texto limpo. Digite comandos e clique em Analisar tokens.")


def criar_painel():
    """Ponto de entrada curto da interface, a ser passado a display()."""
    return LaboratorioR6().widget
