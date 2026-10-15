"""R5 — Scanner lexico deterministico para comandos ficticios de transporte.

Maximal Munch: maior lexema vence; em empate, primeira regra declarada.
Recuperacao: acumula erros com posicao e dica e prossegue ate o fim.
Nao executa comandos nem integra a catraca (isso seria uma fase posterior).
"""
from dataclasses import dataclass
import re
from typing import Pattern, Tuple

from .r1_afds import cartao, linha
from .r3_equivalencia import REGEX_CARTAO, REGEX_LINHA

RESERVADAS = {palavra: palavra for palavra in (
    "RECARGA", "CARTAO", "EMBARQUE", "SALDO", "EVENTO")}

TIPOS_DE_TOKEN = {
    "RECARGA": ("Comando de recarga simulada", "RECARGA"),
    "CARTAO": ("Reservada para cartao", "CARTAO"),
    "EMBARQUE": ("Comando de embarque", "EMBARQUE"),
    "SALDO": ("Reservada para saldo", "SALDO"),
    "EVENTO": ("Reservada para evento", "EVENTO"),
    "NUM_CARTAO": ("Codigo sintatico aceito pelo AFD R1", "12.34.56789012-3"),
    "NUM_LINHA": ("Codigo sintatico aceito pelo AFD R1", "8700-10"),
    "HORARIO": ("Hora 24h: 00:00 a 23:59", "07:42"),
    "REAL": ("Numero decimal com ponto", "20.00"),
    "INTEIRO": ("Numero inteiro ASCII", "20"),
    "IDENTIFICADOR": ("Nome de evento ou parametro", "APROXIMAR_CARTAO"),
    "MAIOR_IGUAL": ("Operador relacional", ">="),
    "MENOR_IGUAL": ("Operador relacional", "<="),
    "IGUAL_IGUAL": ("Igualdade", "=="),
    "MAIOR": ("Operador relacional", ">"),
    "MENOR": ("Operador relacional", "<"),
    "ATRIBUICAO": ("Atribuicao", "="),
    "ABRE_PAREN": ("Abre parenteses", "("),
    "FECHA_PAREN": ("Fecha parenteses", ")"),
    "VIRGULA": ("Separador de argumentos", ","),
    "PONTO_VIRGULA": ("Terminador de comando", ";"),
}
RE_HORARIO = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    linha: int
    coluna: int
    offset: int


@dataclass(frozen=True)
class ErroLexico:
    linha: int
    coluna: int
    lexema: str
    mensagem: str
    dica: str
    offset: int


@dataclass(frozen=True)
class ResultadoScanner:
    tokens: Tuple[Token, ...]
    erros: Tuple[ErroLexico, ...]
    caracteres: int
    linhas: int

    @property
    def aprovado(self) -> bool:
        return not self.erros


@dataclass(frozen=True)
class Regra:
    nome: str
    padrao: Pattern[str]


# CANDIDATO_* permite capturar uma unidade malformada para explicar o erro,
# evitando quebrar um cartao incorreto em varios numeros sem diagnostico.
# As regras de reservadas empatam com IDENTIFICADOR e vencem pela prioridade.
REGRAS: Tuple[Regra, ...] = tuple(
    Regra(nome, re.compile(expressao)) for nome, expressao in (
        ("COMENTARIO", r"\#[^\r\n]*|//[^\r\n]*"),
        ("ESPACO", r"[ \t\f\v\r\n]+"),
        ("CANDIDATO_CARTAO", r"[0-9]+(?:\.[A-Za-z0-9]+){2,}(?:-[A-Za-z0-9]*)?"),
        ("CANDIDATO_LINHA", r"[0-9]{4}-[A-Za-z0-9]*"),
        ("CANDIDATO_HORARIO", r"[0-9]{1,2}:[A-Za-z0-9]*"),
        ("REAL", r"[0-9]+\.[0-9]+"),
        ("INTEIRO", r"[0-9]+"),
        *[(res, res + r"(?![A-Za-z0-9_])") for res in RESERVADAS],
        ("IDENTIFICADOR", r"[A-Za-z_][A-Za-z_0-9]*"),
        ("MAIOR_IGUAL", r">="), ("MENOR_IGUAL", r"<="),
        ("IGUAL_IGUAL", r"=="), ("MAIOR", r">"),
        ("MENOR", r"<"), ("ATRIBUICAO", r"="),
        ("ABRE_PAREN", r"\("), ("FECHA_PAREN", r"\)"),
        ("VIRGULA", r","), ("PONTO_VIRGULA", r";"),
    )
)

DICAS_DOMINIO = {
    "CANDIDATO_CARTAO": (
        "Formato invalido do cartao de transporte.",
        "Use NN.NN.NNNNNNNN-N, por exemplo 12.34.56789012-3 (somente digitos ASCII)."),
    "CANDIDATO_LINHA": (
        "Formato invalido da linha de onibus.",
        "Use ABCD-EF, com A entre 1 e 9 e sufixo EF entre 10 e 49; exemplo 8700-10."),
    "CANDIDATO_HORARIO": (
        "Horario invalido.",
        "Use HH:MM entre 00:00 e 23:59, por exemplo 07:42."),
}


def _posicao_apos(texto: str, linha: int, coluna: int) -> Tuple[int, int]:
    """Linha/coluna iniciam em 1; CRLF conta como uma quebra; tab = 1 coluna."""
    i = 0
    while i < len(texto):
        if texto[i] == "\r":
            linha, coluna = linha + 1, 1
            if i + 1 < len(texto) and texto[i + 1] == "\n":
                i += 1
        elif texto[i] == "\n":
            linha, coluna = linha + 1, 1
        else:
            coluna += 1
        i += 1
    return linha, coluna


def _selecionar_maior(texto: str, offset: int) -> Tuple[str, str] | None:
    """Busca TODAS as regras; em empate, preserva prioridade declarada."""
    melhor = None
    melhor_tamanho = 0
    for regra in REGRAS:
        achado = regra.padrao.match(texto, offset)
        if achado:
            tamanho = achado.end() - offset
            if tamanho > melhor_tamanho:
                melhor, melhor_tamanho = (regra.nome, achado.group(0)), tamanho
    return melhor


def _erro_generico(simbolo: str) -> Tuple[str, str]:
    if simbolo == ":":
        return "Dois-pontos fora de horario valido.", "Use horario HH:MM, exemplo 07:42."
    if simbolo == ".":
        return "Ponto isolado ou numero incompleto.", "Use reais como 20.00 ou cartoes como 12.34.56789012-3."
    if simbolo in ("-", "–", "—"):
        return "Hifen incorreto ou isolado.", "Use '-' ASCII dentro dos codigos de cartao e linha."
    if simbolo == "/":
        return "Barra isolada nao faz parte da linguagem.", "Comentarios devem comecar por # ou // ."
    return "Caractere nao reconhecido no dominio.", "Confira a tabela de tokens e substitua o caractere indicado."


def analisar(fonte: str) -> ResultadoScanner:
    """Tokeniza todo o texto e se recupera de erros sem executar comandos."""
    if not isinstance(fonte, str):
        raise TypeError("A entrada deve ser texto (str)")
    tokens, erros = [], []
    indice, numero_linha, numero_coluna = 0, 1, 1
    while indice < len(fonte):
        achado = _selecionar_maior(fonte, indice)
        if achado is None:
            lexema = fonte[indice]
            mensagem, dica = _erro_generico(lexema)
            erros.append(ErroLexico(numero_linha, numero_coluna, lexema, mensagem, dica, indice))
        else:
            tipo, lexema = achado
            if tipo in DICAS_DOMINIO:
                validadores = {
                    "CANDIDATO_CARTAO": ("NUM_CARTAO", REGEX_CARTAO, cartao),
                    "CANDIDATO_LINHA": ("NUM_LINHA", REGEX_LINHA, linha),
                    "CANDIDATO_HORARIO": ("HORARIO", RE_HORARIO, None),
                }
                tipo_final, regex, afd = validadores[tipo]
                valido = bool(regex.fullmatch(lexema)) and (afd is None or afd.aceita(lexema))
                if valido:
                    tokens.append(Token(tipo_final, lexema, numero_linha, numero_coluna, indice))
                else:
                    mensagem, dica = DICAS_DOMINIO[tipo]
                    erros.append(ErroLexico(numero_linha, numero_coluna, lexema, mensagem, dica, indice))
            elif tipo not in ("COMENTARIO", "ESPACO"):
                tokens.append(Token(tipo, lexema, numero_linha, numero_coluna, indice))
        indice += len(lexema)
        numero_linha, numero_coluna = _posicao_apos(lexema, numero_linha, numero_coluna)
    return ResultadoScanner(tuple(tokens), tuple(erros), len(fonte), numero_linha)


def tabela_tokens():
    """Imprime e retorna as categorias de tokens do scanner."""
    print(f"TABELA DE TOKENS — {len(TIPOS_DE_TOKEN)} tipos")
    print(f"{'TIPO':<19} {'EXEMPLO':<27} DESCRICAO")
    print("-" * 100)
    for tipo, (descricao, exemplo) in TIPOS_DE_TOKEN.items():
        print(f"{tipo:<19} {exemplo:<27} {descricao}")
    return tuple((tipo, descricao, exemplo) for tipo, (descricao, exemplo) in TIPOS_DE_TOKEN.items())


def imprimir_resultado(resultado: ResultadoScanner) -> None:
    print(f"TOKENS: {len(resultado.tokens)} | ERROS: {len(resultado.erros)}")
    print(f"{'LINHA':>5} {'COL':>4} {'TIPO':<20} LEXEMA")
    for token in resultado.tokens:
        print(f"{token.linha:>5} {token.coluna:>4} {token.tipo:<20} {token.lexema!r}")
    if resultado.erros:
        print("ERROS LEXICOS:")
        for erro in resultado.erros:
            print(f" [{erro.linha}:{erro.coluna}] {erro.lexema!r} — {erro.mensagem}")
            print(f"   Dica: {erro.dica}")
    else:
        print("Nenhum erro lexico encontrado.")


EXEMPLO_VALIDO = (
    "# Comandos simulados; nenhuma recarga e efetivada\n"
    "RECARGA 20.00 CARTAO 12.34.56789012-3;\n"
    "EMBARQUE 8700-10 07:42\n"
    "SALDO >= 20.00; SALDO == 20; SALDO <= 30.00\n"
    "EVENTO APROXIMAR_CARTAO // texto, nao dispara catraca\n"
)
EXEMPLO_COM_ERROS = (
    "RECARGA 20.00 CARTAO 12.34.56789012\n"
    "EMBARQUE 8700-50 25:00\n"
    "RECARGA 10.50 CARTAO 12.34.56789012-3\n"
)


if __name__ == "__main__":
    tabela_tokens()
    for titulo, exemplo in (("Exemplo valido", EXEMPLO_VALIDO),
                            ("Exemplo com recuperacao", EXEMPLO_COM_ERROS)):
        print("\n" + titulo + "\n" + "=" * 76)
        imprimir_resultado(analisar(exemplo))
