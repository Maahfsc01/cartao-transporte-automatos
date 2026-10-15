"""R1 - AFDs completos e determinísticos para um cartão de transporte fictício.

Dependências do módulo: somente a biblioteca padrão do Python.
"""
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Tuple

CLASSES = ("ZERO", "UM_A_QUATRO", "CINCO_A_NOVE", "PONTO", "HIFEN", "OUTRO")
DIGITOS = frozenset(("ZERO", "UM_A_QUATRO", "CINCO_A_NOVE"))
NAO_ZERO = frozenset(("UM_A_QUATRO", "CINCO_A_NOVE"))


def classificar(caractere: str) -> str:
    """Classifica um caractere em uma única classe, sem sobreposição."""
    if len(caractere) != 1:
        raise ValueError("A classificação exige exatamente um caractere")
    if caractere == "0":
        return "ZERO"
    if caractere in "1234":
        return "UM_A_QUATRO"
    if caractere in "56789":
        return "CINCO_A_NOVE"
    if caractere == ".":
        return "PONTO"
    if caractere == "-":
        return "HIFEN"
    return "OUTRO"


@dataclass
class AFD:
    nome: str
    significado: str
    estados: Tuple[str, ...]
    alfabeto: Tuple[str, ...]
    delta: Dict[Tuple[str, str], str]
    inicial: str
    finais: FrozenSet[str]
    padrao: Tuple[str, ...]
    descricao_regras: str

    def __post_init__(self):
        """Verifica completude, determinismo e integridade da tabela de transição."""
        q = set(self.estados)
        sigma = set(self.alfabeto)
        if self.inicial not in q or not set(self.finais) <= q:
            raise ValueError("Estado inicial ou final fora de Q")
        esperado = {(estado, classe) for estado in q for classe in sigma}
        if set(self.delta) != esperado:
            raise ValueError("A transição não está definida exatamente uma vez para cada par (estado, classe)")
        if any(destino not in q for destino in self.delta.values()):
            raise ValueError("Uma transição aponta para estado inexistente")
        if "qerro" not in q or any(self.delta[("qerro", c)] != "qerro" for c in sigma):
            raise ValueError("O estado de erro deve manter a rejeição até o final da entrada")

    def transitar(self, estado: str, caractere: str) -> str:
        return self.delta[(estado, classificar(caractere))]

    def aceita(self, palavra: str) -> bool:
        """Consome TODA a palavra e aceita somente se terminar em F."""
        if not isinstance(palavra, str):
            raise TypeError("A entrada deve ser texto (str)")
        estado = self.inicial
        for caractere in palavra:
            estado = self.transitar(estado, caractere)
        return estado in self.finais

    def rastrear(self, palavra: str) -> List[Tuple[int, str, str, str, str]]:
        """Retorna (posição, estado origem, caractere, classe, estado destino)."""
        estado = self.inicial
        passos = []
        for posicao, caractere in enumerate(palavra, start=1):
            classe = classificar(caractere)
            destino = self.delta[(estado, classe)]
            passos.append((posicao, estado, caractere, classe, destino))
            estado = destino
        return passos

    def rodar(self, palavra: str) -> bool:
        """Demonstra o processamento, inclusive a palavra vazia."""
        print(f"AFD: {self.nome}")
        print(f"Entrada: {palavra!r}")
        if palavra == "":
            print("Nenhum caractere consumido (palavra vazia).")
        for pos, origem, caractere, classe, destino in self.rastrear(palavra):
            print(f"  {pos:02d}. {origem:>5} -- {caractere!r} [{classe}] --> {destino}")
        estado_final = self.inicial if palavra == "" else self.rastrear(palavra)[-1][4]
        aceitou = estado_final in self.finais
        print(f"Estado final: {estado_final} | Resultado: {'ACEITA' if aceitou else 'REJEITADA'}")
        if not aceitou:
            if estado_final == "qerro":
                print("Motivo: algum caractere não correspondia ao esperado naquela posição, ou houve caracteres excedentes.")
            else:
                print("Motivo: a palavra terminou antes de chegar ao estado de aceitação.")
        return aceitou

    def tabela(self) -> List[Dict[str, str]]:
        """Mostra a tabela de transição integral, incluindo o estado de erro.

        Retorna também uma lista de dicionários para uso no notebook.
        """
        colunas = ("Estado",) + self.alfabeto
        linhas = []
        for estado in self.estados:
            rotulo = ("→" if estado == self.inicial else "") + ("*" if estado in self.finais else "") + estado
            linha = {"Estado": rotulo}
            for classe in self.alfabeto:
                linha[classe] = self.delta[(estado, classe)]
            linhas.append(linha)
        larguras = {c: max(len(c), *(len(l[c]) for l in linhas)) for c in colunas}
        def formatar(linha):
            return " | ".join(str(linha[c]).ljust(larguras[c]) for c in colunas)
        print(f"TABELA DE TRANSIÇÕES — {self.nome}")
        print("Legenda: → inicial; * aceitação; qerro = estado de erro")
        print(formatar({c: c for c in colunas}))
        print("-+-".join("-" * larguras[c] for c in colunas))
        for linha in linhas:
            print(formatar(linha))
        return linhas


def _construir_afd(nome: str, significado: str, padrao: Tuple[str, ...], descricao: str) -> AFD:
    """Cria δ total para o formato e inclui um estado de erro."""
    estados = tuple(f"q{i}" for i in range(len(padrao) + 1)) + ("qerro",)
    delta = {(estado, classe): "qerro" for estado in estados for classe in CLASSES}
    for classe in CLASSES:
        delta[("qerro", classe)] = "qerro"
    grupos = {
        "D": DIGITOS,
        "N": NAO_ZERO,
        "T": frozenset(("UM_A_QUATRO",)),
        "P": frozenset(("PONTO",)),
        "H": frozenset(("HIFEN",)),
    }
    for indice, simbolo in enumerate(padrao):
        for classe in grupos[simbolo]:
            delta[(f"q{indice}", classe)] = f"q{indice + 1}"
    return AFD(nome, significado, estados, CLASSES, delta, "q0", frozenset((f"q{len(padrao)}",)), padrao, descricao)


cartao = _construir_afd(
    "Cartão de transporte",
    "Código didático do cartão: 2 dígitos, ponto, 2 dígitos, ponto, 8 dígitos, hífen, 1 dígito.",
    tuple("DDPDDP" + "D" * 8 + "HD"),
    "NN.NN.NNNNNNNN-N; N ∈ 0–9. Os dígitos são sintáticos, sem verificação de dígito calculado.",
)

linha = _construir_afd(
    "Linha de ônibus",
    "Código didático de linha: quatro dígitos, hífen e variante de 10 a 49.",
    tuple("NDDDH" + "TD"),
    "ABCD-EF; A ∈ 1–9, B/C/D/F ∈ 0–9 e E ∈ 1–4 (variante didática de 10 a 49).",
)


if __name__ == "__main__":
    cartao.rodar("12.34.56789012-3")
    linha.rodar("8700-10")
