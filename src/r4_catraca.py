"""R4: máquina de estados determinística de uma catraca fictícia.

Os eventos de saldo/recarga são sinais simulados, não uma consulta real de
saldo, autorização bancária ou validação de credencial física.

Eventos inválidos são recusados com os eventos permitidos no estado atual,
sem alteração do estado. A tabela de transições é a fonte única da verdade.
"""
from dataclasses import dataclass
from typing import Iterable, Tuple

ESTADOS = (
    "TRAVADA", "CARTAO_LIDO", "VERIFICANDO_SALDO", "LIBERADA", "GIRANDO",
    "PASSAGEM_REGISTRADA", "SEM_SALDO",
)
ESTADO_INICIAL = "TRAVADA"
DESCRICOES_ESTADOS = {
    "TRAVADA": "Bloqueada e aguardando cartão.",
    "CARTAO_LIDO": "Cartão aproximado, aguardando validação.",
    "VERIFICANDO_SALDO": "Aguardando resultado da consulta simulada de saldo.",
    "LIBERADA": "Passagem autorizada, pronta para o giro.",
    "GIRANDO": "Passageiro movimentando a catraca.",
    "PASSAGEM_REGISTRADA": "Giro concluído; aguardando rearme.",
    "SEM_SALDO": "Pagamento não autorizado; cancelar ou confirmar recarga.",
}

@dataclass(frozen=True)
class Transicao:
    origem: str
    evento: str
    destino: str
    regra: str

# É daqui que vêm a execução, a tabela, o diagrama e os testes.
TRANSICOES: Tuple[Transicao, ...] = (
    Transicao("TRAVADA", "APROXIMAR_CARTAO", "CARTAO_LIDO", "Uma tentativa de embarque foi iniciada."),
    Transicao("CARTAO_LIDO", "VALIDAR_CARTAO", "VERIFICANDO_SALDO", "Consulta de saldo iniciada."),
    Transicao("CARTAO_LIDO", "CANCELAR", "TRAVADA", "Leitura cancelada."),
    Transicao("VERIFICANDO_SALDO", "SALDO_SUFICIENTE", "LIBERADA", "Saldo aprovado."),
    Transicao("VERIFICANDO_SALDO", "SALDO_INSUFICIENTE", "SEM_SALDO", "Sem saldo para passagem."),
    Transicao("VERIFICANDO_SALDO", "CANCELAR", "TRAVADA", "Validação interrompida."),
    Transicao("LIBERADA", "INICIAR_GIRO", "GIRANDO", "Passagem iniciada."),
    Transicao("LIBERADA", "TEMPO_ESGOTADO", "TRAVADA", "Liberação expirou antes do giro."),
    Transicao("GIRANDO", "CONCLUIR_GIRO", "PASSAGEM_REGISTRADA", "Giro concluído e passagem registrada."),
    Transicao("PASSAGEM_REGISTRADA", "REARMAR", "TRAVADA", "Catraca pronta para próximo usuário."),
    Transicao("SEM_SALDO", "RECARGA_CONFIRMADA", "VERIFICANDO_SALDO", "Recarga informada; saldo deve ser verificado novamente."),
    Transicao("SEM_SALDO", "CANCELAR", "TRAVADA", "Tentativa sem saldo cancelada."),
)
DELTA = {(t.origem, t.evento): t.destino for t in TRANSICOES}
REGRAS = {(t.origem, t.evento): t.regra for t in TRANSICOES}
EVENTOS = tuple(dict.fromkeys(t.evento for t in TRANSICOES))


def verificar_modelo() -> None:
    """Detecta inconsistências, transições ambíguas e estados inalcançáveis."""
    assert len(ESTADOS) >= 5 and len(set(ESTADOS)) == len(ESTADOS)
    assert len(TRANSICOES) >= 6 and len(DELTA) == len(TRANSICOES)
    assert ESTADO_INICIAL in ESTADOS and set(DESCRICOES_ESTADOS) == set(ESTADOS)
    for t in TRANSICOES:
        assert t.origem in ESTADOS and t.destino in ESTADOS
        assert isinstance(t.evento, str) and bool(t.evento)
    alcançados, fronteira = {ESTADO_INICIAL}, [ESTADO_INICIAL]
    while fronteira:
        estado = fronteira.pop()
        for t in TRANSICOES:
            if t.origem == estado and t.destino not in alcançados:
                alcançados.add(t.destino)
                fronteira.append(t.destino)
    assert alcançados == set(ESTADOS), f"Estados inalcançáveis: {set(ESTADOS) - alcançados}"


@dataclass(frozen=True)
class PassoCatraca:
    numero: int
    origem: str
    evento: str
    destino: str
    aceito: bool
    permitidos: Tuple[str, ...]
    explicacao: str


@dataclass(frozen=True)
class ResultadoFluxo:
    titulo: str
    passos: Tuple[PassoCatraca, ...]
    estado_final: str
    eventos_solicitados: int
    passagens_registradas: int

    @property
    def completo(self) -> bool:
        """Nenhuma recusa e todos os eventos solicitados foram processados."""
        return len(self.passos) == self.eventos_solicitados and all(p.aceito for p in self.passos)

    @property
    def contem_recusa(self) -> bool:
        return any(not p.aceito for p in self.passos)

    @property
    def viagem_concluida(self) -> bool:
        """Passagem registrada e máquina novamente preparada para atender."""
        return self.completo and self.estado_final == ESTADO_INICIAL and self.passagens_registradas > 0


class Catraca:
    """Máquina determinística com rejeição explícita de eventos não permitidos."""

    def __init__(self) -> None:
        self.estado = ESTADO_INICIAL
        self.historico = []
        self.passagens_registradas = 0

    def permitidos(self, estado: str = None) -> Tuple[str, ...]:
        atual = self.estado if estado is None else estado
        if atual not in ESTADOS:
            raise ValueError(f"Estado desconhecido: {atual}")
        return tuple(t.evento for t in TRANSICOES if t.origem == atual)

    def disparar(self, evento: str) -> PassoCatraca:
        """Se inválido, estado não muda e mensagem inclui eventos permitidos."""
        if not isinstance(evento, str):
            raise TypeError("Evento deve ser texto (str)")
        origem = self.estado
        permitidos = self.permitidos()
        destino = DELTA.get((origem, evento))
        aceito = destino is not None
        if aceito:
            self.estado = destino
            if evento == "CONCLUIR_GIRO":
                self.passagens_registradas += 1
            explicacao = REGRAS[(origem, evento)]
        else:
            destino = origem
            causa = (f"Evento {evento!r} não permitido em {origem}." if evento in EVENTOS
                     else f"Evento desconhecido: {evento!r}.")
            explicacao = causa + " Permitidos agora: " + ", ".join(permitidos) + "."
        passo = PassoCatraca(len(self.historico) + 1, origem, evento, destino,
                            aceito, permitidos, explicacao)
        self.historico.append(passo)
        return passo

    def executar(self, eventos: Iterable[str], titulo: str = "Fluxo",
                 parar_ao_recusar: bool = True) -> ResultadoFluxo:
        if isinstance(eventos, (str, bytes)):
            raise TypeError("Passe uma sequência de eventos, não uma string isolada")
        eventos = tuple(eventos)
        if any(not isinstance(e, str) for e in eventos):
            raise TypeError("Todos os eventos devem ser strings")
        passos = []
        for evento in eventos:
            passo = self.disparar(evento)
            passos.append(passo)
            if not passo.aceito and parar_ao_recusar:
                break
        return ResultadoFluxo(titulo, tuple(passos), self.estado,
                              len(eventos), self.passagens_registradas)

    def reiniciar(self) -> None:
        self.estado = ESTADO_INICIAL
        self.historico.clear()
        self.passagens_registradas = 0

    def tabela(self) -> Tuple[Transicao, ...]:
        """Imprime e retorna as 12 transições usadas pela máquina."""
        print("TABELA DE TRANSIÇÕES DA CATRACA")
        print(f"{'Origem':<22} {'Evento':<22} Destino")
        print("-" * 74)
        for t in TRANSICOES:
            print(f"{t.origem:<22} {t.evento:<22} {t.destino}")
        return TRANSICOES


def texto_fluxo(resultado: ResultadoFluxo) -> str:
    linhas = [
        f"CENÁRIO: {resultado.titulo}",
        f"{'#':<3} {'Origem':<22} {'Evento':<22} {'Destino':<22} Status",
        "-" * 94,
    ]
    for p in resultado.passos:
        linhas.append(f"{p.numero:<3} {p.origem:<22} {p.evento:<22} {p.destino:<22} "
                      + ("ACEITO" if p.aceito else "RECUSADO"))
        if not p.aceito:
            linhas.append(f"    MOTIVO: {p.explicacao}")
            linhas.append("    EVENTOS PERMITIDOS: " + ", ".join(p.permitidos))
    linhas.extend((
        f"Estado final: {resultado.estado_final}",
        f"Eventos processados: {len(resultado.passos)}/{resultado.eventos_solicitados}",
        f"Passagens registradas: {resultado.passagens_registradas}",
        f"Resultado: {'FLUXO VÁLIDO' if resultado.completo else 'FLUXO INVÁLIDO'}",
    ))
    return "\n".join(linhas)


# Dois fluxos completos de embarque e dois com tentativa de evento proibido.
CENARIOS = (
    ("Válido 1 — embarque autorizado", (
        "APROXIMAR_CARTAO", "VALIDAR_CARTAO", "SALDO_SUFICIENTE",
        "INICIAR_GIRO", "CONCLUIR_GIRO", "REARMAR",
    ), True),
    ("Válido 2 — recarga e embarque", (
        "APROXIMAR_CARTAO", "VALIDAR_CARTAO", "SALDO_INSUFICIENTE",
        "RECARGA_CONFIRMADA", "SALDO_SUFICIENTE", "INICIAR_GIRO",
        "CONCLUIR_GIRO", "REARMAR",
    ), True),
    ("Inválido 1 — girar antes da validação", (
        "APROXIMAR_CARTAO", "INICIAR_GIRO",
    ), False),
    ("Inválido 2 — girar sem saldo", (
        "APROXIMAR_CARTAO", "VALIDAR_CARTAO", "SALDO_INSUFICIENTE", "INICIAR_GIRO",
    ), False),
)


def executar_cenarios(mostrar: bool = True) -> Tuple[ResultadoFluxo, ...]:
    """Cada cenário usa uma instância própria, evitando compartilhar o estado."""
    resultados = []
    for titulo, eventos, esperado in CENARIOS:
        resultado = Catraca().executar(eventos, titulo=titulo)
        assert resultado.completo == esperado, f"Resultado inesperado: {titulo}"
        assert (resultado.viagem_concluida if esperado else resultado.contem_recusa)
        resultados.append(resultado)
        if mostrar:
            print(texto_fluxo(resultado), "\n")
    return tuple(resultados)


verificar_modelo()

if __name__ == "__main__":
    print(f"Catraca: {len(ESTADOS)} estados, {len(TRANSICOES)} transições")
    Catraca().tabela()
    print()
    executar_cenarios()
