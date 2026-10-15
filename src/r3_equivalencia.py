"""R3 — Bateria de equivalência: os AFDs e expressões regulares independentes.

Usa a tabela delta dos AFDs do R1 e a biblioteca padrão re. A RegEx NÃO
é gerada a partir do delta; isso permite comparar duas implementações.

Importante: concordância em testes não é uma prova formal de equivalência
para toda palavra possível. A bateria e o estresse complementam a
justificativa estruturada por posições documentada no README.
"""

from dataclasses import dataclass
from random import Random
import re
from typing import Pattern, Sequence, Tuple

from .r1_afds import AFD, cartao, linha

# [0-9] é INTENCIONAL: o AFD considera os algarismos ASCII 0..9.
# Não usar \d, pois em Python \d também abrange dígitos Unicode.
# A correspondência completa é aplicada com re.fullmatch, sem ^ ou $.
REGEX_CARTAO: Pattern[str] = re.compile(r"[0-9]{2}\.[0-9]{2}\.[0-9]{8}-[0-9]")
REGEX_LINHA: Pattern[str] = re.compile(r"[1-9][0-9]{3}-[1-4][0-9]")


@dataclass(frozen=True)
class CasoTeste:
    palavra: str
    esperado: bool
    justificativa: str


@dataclass(frozen=True)
class ResultadoCaso:
    entrada: str
    esperado: bool
    aceita_afd: bool
    aceita_regex: bool
    justificativa: str

    @property
    def divergencia(self) -> bool:
        return self.aceita_afd != self.aceita_regex

    @property
    def falha_de_expectativa(self) -> bool:
        return self.aceita_afd != self.esperado or self.aceita_regex != self.esperado


@dataclass(frozen=True)
class ResultadoBateria:
    nome: str
    expressao: str
    resultados: Tuple[ResultadoCaso, ...]

    @property
    def total(self) -> int:
        return len(self.resultados)

    @property
    def total_aceitas(self) -> int:
        return sum(r.esperado for r in self.resultados)

    @property
    def total_rejeitadas(self) -> int:
        return sum(not r.esperado for r in self.resultados)

    @property
    def divergencias(self) -> int:
        return sum(r.divergencia for r in self.resultados)

    @property
    def falhas_de_expectativa(self) -> int:
        return sum(r.falha_de_expectativa for r in self.resultados)

    @property
    def aprovado(self) -> bool:
        return self.divergencias == 0 and self.falhas_de_expectativa == 0


@dataclass(frozen=True)
class ResultadoEstresse:
    nome: str
    entradas_testadas: int
    divergencias: int
    aceitas_afd: int
    exemplos_divergentes: Tuple[str, ...]


def aceita_regex(padrao: Pattern[str], palavra: str) -> bool:
    """Exige match de TODA a palavra; inválidas não são normalizadas."""
    if not isinstance(palavra, str):
        raise TypeError("A palavra deve ser texto (str)")
    return padrao.fullmatch(palavra) is not None


CASOS_CARTAO: Tuple[CasoTeste, ...] = (
    CasoTeste("12.34.56789012-3", True, "Formato canônico completo"),
    CasoTeste("00.00.00000000-0", True, "Zeros ASCII permitidos"),
    CasoTeste("99.99.99999999-9", True, "Noves ASCII permitidos"),
    CasoTeste("01.00.00000000-0", True, "Zeros à esquerda permitidos"),
    CasoTeste("10.29.87654321-4", True, "Mistura de dígitos"),
    CasoTeste("42.07.31415926-5", True, "Separadores nas posições exatas"),
    CasoTeste("98.76.54321098-7", True, "Outra sequência válida"),
    CasoTeste("70.40.12345678-0", True, "Dígito final zero"),
    CasoTeste("", False, "Palavra vazia: não alcança estado final"),
    CasoTeste("12.34.56789012-3X", False, "Caractere excedente"),
    CasoTeste("12.34.56789012", False, "Faltam hífen e dígito final"),
    CasoTeste("12.34.56789012-", False, "Dígito final ausente"),
    CasoTeste("12-34-56789012-3", False, "Hífen em lugar de pontos"),
    CasoTeste("1234.56789012-3", False, "Primeiro ponto ausente"),
    CasoTeste("12.34.5678901A-3", False, "Letra no bloco numérico"),
    CasoTeste(" 12.34.56789012-3", False, "Espaço inicial"),
    CasoTeste("12.34.56789012-3\n", False, "Quebra de linha final"),
    CasoTeste("１２.34.56789012-3", False, "Dígito Unicode não é ASCII"),
    CasoTeste("12.34.56789012_3", False, "Sublinhado em vez de hífen"),
    CasoTeste("12.34.56789012-30", False, "Dígito excedente"),
)

CASOS_LINHA: Tuple[CasoTeste, ...] = (
    CasoTeste("8700-10", True, "Linha e variante do exemplo"),
    CasoTeste("1234-49", True, "Variante no limite superior"),
    CasoTeste("9000-21", True, "Prefixo máximo permitido"),
    CasoTeste("4321-30", True, "Variante da terceira dezena"),
    CasoTeste("1000-40", True, "Menor prefixo e variante 40"),
    CasoTeste("9999-19", True, "Maior prefixo e variante 19"),
    CasoTeste("7001-33", True, "Outra linha e variante"),
    CasoTeste("8010-20", True, "Variante 20"),
    CasoTeste("", False, "Palavra vazia: não alcança estado final"),
    CasoTeste("0700-10", False, "Primeiro dígito zero"),
    CasoTeste("8700-00", False, "Variante abaixo de 10"),
    CasoTeste("8700-50", False, "Variante acima de 49"),
    CasoTeste("8700-1", False, "Variante incompleta"),
    CasoTeste("8700-10X", False, "Caractere excedente"),
    CasoTeste("870010", False, "Hífen ausente"),
    CasoTeste("87A0-10", False, "Letra entre dígitos"),
    CasoTeste("8700-99", False, "Variante fora da faixa"),
    CasoTeste("8700-10\n", False, "Quebra de linha final"),
    CasoTeste("8７00-10", False, "Dígito Unicode não é ASCII"),
    CasoTeste("8700–10", False, "Travessão em lugar de hífen ASCII"),
    CasoTeste("8700-10 ", False, "Espaço final"),
)


def executar_bateria(
    afd: AFD, padrao: Pattern[str], casos: Sequence[CasoTeste]
) -> ResultadoBateria:
    """Verifica os 3 oráculos: resultado do AFD, RegEx e esperado explícito."""
    entradas = [c.palavra for c in casos]
    if len(entradas) != len(set(entradas)):
        raise ValueError("A bateria contém palavras repetidas")
    if sum(c.esperado for c in casos) < 5:
        raise ValueError("A bateria deve conter pelo menos cinco palavras aceitas")
    if sum(not c.esperado for c in casos) < 5:
        raise ValueError("A bateria deve conter pelo menos cinco palavras rejeitadas")
    if "" not in entradas or next(c for c in casos if c.palavra == "").esperado:
        raise ValueError("A palavra vazia deve estar presente entre as rejeitadas")

    resultados = tuple(
        ResultadoCaso(
            entrada=c.palavra,
            esperado=c.esperado,
            aceita_afd=afd.aceita(c.palavra),
            aceita_regex=aceita_regex(padrao, c.palavra),
            justificativa=c.justificativa,
        )
        for c in casos
    )
    return ResultadoBateria(afd.nome, padrao.pattern, resultados)


def imprimir_bateria(resultado: ResultadoBateria) -> None:
    print(f"AFD: {resultado.nome} | RegEx: {resultado.expressao}")
    print("Entrada                  | Esperado  | AFD       | RegEx     | Igual? | Coerente?")
    print("-" * 82)
    for r in resultado.resultados:
        esperado = "ACEITA" if r.esperado else "REJEITA"
        a = "ACEITA" if r.aceita_afd else "REJEITA"
        b = "ACEITA" if r.aceita_regex else "REJEITA"
        print(f"{repr(r.entrada):<24} | {esperado:<9} | {a:<9} | {b:<9} | "
              f"{'SIM' if not r.divergencia else 'NÃO':<6} | "
              f"{'SIM' if not r.falha_de_expectativa else 'NÃO'}")
    print(f"TOTAL: {resultado.total} ({resultado.total_aceitas} aceitas, "
          f"{resultado.total_rejeitadas} rejeitadas) | "
          f"""DIVERGÊNCIAS: {resultado.divergencias} | """
          f"ERROS DE EXPECTATIVA: {resultado.falhas_de_expectativa}")


def _gerar_valido_cartao(rng: Random) -> str:
    digitos = "0123456789"
    bloco = lambda n: "".join(rng.choices(digitos, k=n))
    return f"{bloco(2)}.{bloco(2)}.{bloco(8)}-{bloco(1)}"


def _gerar_valido_linha(rng: Random) -> str:
    digitos = "0123456789"
    bloco = lambda n: "".join(rng.choices(digitos, k=n))
    return f"{rng.choice('123456789')}{bloco(3)}-{rng.choice('1234')}{bloco(1)}"


def _mutar(rng: Random, palavra: str) -> str:
    """Gera perturbacoes do formato sem presumir que toda mutacao sera invalida."""
    simbolos = "0123456789.-AX_ á\t\n１–"
    posicao = rng.randrange(len(palavra) + 1)
    acao = rng.choice(("inserir", "remover", "substituir", "repetir"))
    if acao == "inserir":
        return palavra[:posicao] + rng.choice(simbolos) + palavra[posicao:]
    if acao == "remover":
        posicao = min(posicao, len(palavra) - 1)
        return palavra[:posicao] + palavra[posicao + 1:]
    if acao == "substituir":
        posicao = min(posicao, len(palavra) - 1)
        return palavra[:posicao] + rng.choice(simbolos) + palavra[posicao + 1:]
    return palavra + palavra[-1]


def testar_estresse(quantidade_por_tipo: int = 1000, semente: int = 20261013
                   ) -> Tuple[ResultadoEstresse, ResultadoEstresse]:
    """Reproduzível: N validos, N perturbacoes, N textos aleatorios POR AFD.

    Stress complementar à bateria obrigatória; verifica concordancia, não
    declara prova matemática de equivalência universal.
    """
    if quantidade_por_tipo <= 0:
        raise ValueError("quantidade_por_tipo deve ser positiva")
    rng = Random(semente)
    resultados = []
    for afd, regex, gerador in (
        (cartao, REGEX_CARTAO, _gerar_valido_cartao),
        (linha, REGEX_LINHA, _gerar_valido_linha),
    ):
        divergencias = 0
        aceitas = 0
        exemplos = []
        total = 0
        for tipo in ("valido", "mutado", "aleatorio"):
            for _ in range(quantidade_por_tipo):
                if tipo == "valido":
                    palavra = gerador(rng)
                elif tipo == "mutado":
                    palavra = _mutar(rng, gerador(rng))
                else:
                    simbolos = "0123456789.-AX_ á\t\n１–"
                    palavra = "".join(rng.choices(simbolos, k=rng.randrange(0, 22)))
                a = afd.aceita(palavra)
                b = aceita_regex(regex, palavra)
                total += 1
                aceitas += a
                if a != b:
                    divergencias += 1
                    if len(exemplos) < 5:
                        exemplos.append(repr(palavra))
        resultados.append(ResultadoEstresse(afd.nome, total, divergencias,
                                            aceitas, tuple(exemplos)))
    return tuple(resultados)


def executar_tudo() -> Tuple[ResultadoBateria, ResultadoBateria]:
    return (
        executar_bateria(cartao, REGEX_CARTAO, CASOS_CARTAO),
        executar_bateria(linha, REGEX_LINHA, CASOS_LINHA),
    )


if __name__ == "__main__":
    for resumo in executar_tudo():
        imprimir_bateria(resumo)
        if not resumo.aprovado:
            raise SystemExit(f"Falha na equivalência: {resumo.nome}")
        print()
    for estresse in testar_estresse():
        print(f"ESTRESSE {estresse.nome}: {estresse.entradas_testadas} entradas, "
              f"{estresse.divergencias} divergências")
        if estresse.divergencias:
            raise SystemExit("Falha no estresse")
