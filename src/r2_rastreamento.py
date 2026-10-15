"""R2 - Rastreamento estruturado, reproduzível e explicável dos AFDs do R1.

Não altera o reconhecimento de palavras: somente consulta a funcao delta.
Sem dependências de terceiros.
"""
from dataclasses import dataclass
from typing import Tuple

from .r1_afds import AFD, classificar


@dataclass(frozen=True)
class Passo:
    posicao: int
    origem: str
    caractere: str
    classe: str
    esperadas: Tuple[str, ...]
    destino: str
    prefixo: str
    restante: str
    explicacao: str


@dataclass(frozen=True)
class Rastreamento:
    afd: str
    palavra: str
    passos: Tuple[Passo, ...]
    estado_final: str
    aceita: bool
    motivo: str


def classes_esperadas(afd: AFD, estado: str) -> Tuple[str, ...]:
    """Retorna as classes com transição que não leva ao erro a partir do estado."""
    if estado not in afd.estados:
        raise ValueError(f"Estado desconhecido: {estado}")
    return tuple(classe for classe in afd.alfabeto if afd.delta[(estado, classe)] != "qerro")


def _classes_legiveis(classes: Tuple[str, ...]) -> str:
    if not classes:
        return "nenhuma (formato completo ou estado de erro)"
    return ", ".join(classes)


def rastrear_detalhado(afd: AFD, palavra: str) -> Rastreamento:
    """Consome TODOS os caracteres, inclusive após entrada em qerro.

    Explica o primeiro erro sem confundir prefixo incompleto com entrada inválida.
    A rastreabilidade é derivada somente de afd.delta, sem RegEx ou regras duplicadas.
    """
    if not isinstance(palavra, str):
        raise TypeError("A palavra deve ser str")
    estado = afd.inicial
    passos = []
    primeiro_erro = None

    for posicao, caractere in enumerate(palavra, 1):
        origem = estado
        classe = classificar(caractere)
        esperadas = classes_esperadas(afd, origem)
        destino = afd.delta[(origem, classe)]
        if origem == "qerro":
            explicacao = "O AFD continua consumindo a entrada em qerro (estado de erro)."
        elif destino == "qerro":
            if origem in afd.finais:
                explicacao = "Caractere excedente: a palavra já estava completa."
            else:
                explicacao = (f"Classe {classe} não permitida em {origem}; "
                              f"esperava: {_classes_legiveis(esperadas)}.")
            if primeiro_erro is None:
                primeiro_erro = (posicao, caractere, classe, explicacao)
        elif destino in afd.finais:
            explicacao = "Transição válida: alcançou um estado de aceitação."
        else:
            explicacao = "Transição válida: ainda é necessário consumir o restante."
        passos.append(Passo(
            posicao, origem, caractere, classe, esperadas, destino,
            palavra[:posicao], palavra[posicao:], explicacao,
        ))
        estado = destino

    aceita = estado in afd.finais
    if aceita:
        motivo = (f"Todos os {len(palavra)} caracteres foram consumidos e "
                  f"{estado} pertence ao conjunto F={{{', '.join(sorted(afd.finais))}}}.")
    elif not palavra:
        motivo = (f"A palavra vazia não realiza transições: permanece em {estado}, "
                  "que não é um estado de aceitação.")
    elif primeiro_erro is not None:
        posicao, caractere, classe, explicacao = primeiro_erro
        motivo = (f"Primeiro erro na posição {posicao} (caractere {caractere!r}, "
                  f"classe {classe}). {explicacao} "
                  f"O AFD terminou em {estado}, fora de F.")
    else:
        esperadas = classes_esperadas(afd, estado)
        motivo = (f"A entrada terminou prematuramente no estado {estado}; "
                  f"faltaram caracteres das classes: {_classes_legiveis(esperadas)}. "
                  f"{estado} não pertence a F.")

    resultado = Rastreamento(afd.nome, palavra, tuple(passos), estado, aceita, motivo)
    if resultado.aceita != afd.aceita(palavra):
        raise AssertionError("Divergencia interna: rastreamento e reconhecedor R1")
    return resultado


def texto_rastreamento(resultado: Rastreamento) -> str:
    """Produz exibicao de console sem dependencia de Jupyter."""
    linhas = [
        f"AFD: {resultado.afd}", f"Palavra: {resultado.palavra!r}",
        "Passo | Origem | Caractere | Classe         | Esperadas                        | Destino",
        "-" * 95,
    ]
    if not resultado.passos:
        linhas.append("(nenhum caractere consumido; permaneceu no estado inicial)")
    for p in resultado.passos:
        linhas.append(
            f"{p.posicao:>5} | {p.origem:<6} | {p.caractere!r:<9} | "
            f"{p.classe:<14} | {_classes_legiveis(p.esperadas):<32} | {p.destino}"
        )
    linhas.extend([
        "-" * 95,
        f"Estado final: {resultado.estado_final}",
        f"Resultado: {'ACEITA' if resultado.aceita else 'REJEITADA'}",
        f"JUSTIFICATIVA: {resultado.motivo}",
    ])
    return "\n".join(linhas)


def rodar_r2(afd: AFD, palavra: str) -> Rastreamento:
    """API complementar a rodar() de R1; imprime e retorna o resultado formal."""
    resultado = rastrear_detalhado(afd, palavra)
    print(texto_rastreamento(resultado))
    return resultado


if __name__ == "__main__":
    from .r1_afds import cartao, linha
    for afd, palavra in (
        (cartao, "12.34.56789012-3"), (cartao, "12.34.56789012-3X"),
        (linha, "8700-10"), (linha, "8700-50"),
    ):
        rodar_r2(afd, palavra)
        print("\n")
