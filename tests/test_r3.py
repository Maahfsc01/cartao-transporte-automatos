"""R3 - Bateria de testes AFD x RegEx e estresse de regressao."""
import unittest
import re

from src.r1_afds import cartao, linha
from src.r3_equivalencia import (
    REGEX_CARTAO, REGEX_LINHA, CASOS_CARTAO, CASOS_LINHA,
    CasoTeste, aceita_regex, executar_bateria, executar_tudo, testar_estresse,
    imprimir_bateria,
)
from io import StringIO
from contextlib import redirect_stdout


class TestR3(unittest.TestCase):
    def test_regex_do_cartao(self):
        self.assertEqual(REGEX_CARTAO.pattern, r"[0-9]{2}\.[0-9]{2}\.[0-9]{8}-[0-9]")
        self.assertTrue(aceita_regex(REGEX_CARTAO, "12.34.56789012-3"))
        self.assertFalse(aceita_regex(REGEX_CARTAO, "12.34.56789012-3X"))

    def test_regex_da_linha(self):
        self.assertEqual(REGEX_LINHA.pattern, r"[1-9][0-9]{3}-[1-4][0-9]")
        self.assertTrue(aceita_regex(REGEX_LINHA, "8700-10"))
        self.assertFalse(aceita_regex(REGEX_LINHA, "8700-50"))

    def test_cobertura_minima_e_palavra_vazia(self):
        for casos in (CASOS_CARTAO, CASOS_LINHA):
            with self.subTest(casos=len(casos)):
                self.assertGreaterEqual(sum(c.esperado for c in casos), 5)
                self.assertGreaterEqual(sum(not c.esperado for c in casos), 5)
                self.assertIn("", [c.palavra for c in casos if not c.esperado])
                self.assertEqual(len(casos), len(set(c.palavra for c in casos)))

    def test_zero_divergencias_e_zero_falhas_esperadas(self):
        for resultado in executar_tudo():
            with self.subTest(validador=resultado.nome):
                self.assertEqual(resultado.divergencias, 0)
                self.assertEqual(resultado.falhas_de_expectativa, 0)
                self.assertTrue(resultado.aprovado)
                self.assertEqual(resultado.total, resultado.total_aceitas + resultado.total_rejeitadas)

    def test_fullmatch_rejeita_sufixo_e_quebra_de_linha(self):
        for afd, regex, base in (
            (cartao, REGEX_CARTAO, "12.34.56789012-3"),
            (linha, REGEX_LINHA, "8700-10"),
        ):
            for palavra in (base + "X", base + "\n", base + " ", " " + base):
                with self.subTest(afd=afd.nome, texto=repr(palavra)):
                    self.assertFalse(aceita_regex(regex, palavra))
                    self.assertFalse(afd.aceita(palavra))

    def test_unicode_nao_e_digito_ascii(self):
        self.assertFalse(aceita_regex(REGEX_CARTAO, "１２.34.56789012-3"))
        self.assertFalse(aceita_regex(REGEX_LINHA, "8７00-10"))
        self.assertFalse(cartao.aceita("１２.34.56789012-3"))
        self.assertFalse(linha.aceita("8７00-10"))

    def test_regras_especiais_da_linha(self):
        for p, esperado in (("1000-10", True), ("9999-49", True),
                             ("0000-10", False), ("9999-09", False),
                             ("9999-50", False), ("9999-99", False)):
            with self.subTest(palavra=p):
                self.assertEqual(linha.aceita(p), esperado)
                self.assertEqual(aceita_regex(REGEX_LINHA, p), esperado)

    def test_entradas_nao_textuais_rejeitadas_por_tipo(self):
        for entrada in (None, 1234, b"8700-10", []):
            with self.subTest(entrada=repr(entrada)):
                with self.assertRaises(TypeError):
                    aceita_regex(REGEX_LINHA, entrada)

    def test_validacao_de_bateria_com_regressao(self):
        with self.assertRaises(ValueError):
            executar_bateria(cartao, REGEX_CARTAO, [CasoTeste("", False, "vazia")])
        with self.assertRaises(ValueError):
            executar_bateria(cartao, REGEX_CARTAO,
                             CASOS_CARTAO + (CASOS_CARTAO[0],))
        bug_regex = re.compile(r"[0-9]+")
        resumo = executar_bateria(cartao, bug_regex, CASOS_CARTAO)
        self.assertFalse(resumo.aprovado)
        self.assertGreater(resumo.divergencias, 0)
        self.assertGreater(resumo.falhas_de_expectativa, 0)

    def test_tabela_console_e_justificativas(self):
        r = executar_tudo()[0]
        buf = StringIO()
        with redirect_stdout(buf):
            imprimir_bateria(r)
        saida = buf.getvalue()
        self.assertIn("DIVERGÊNCIAS: 0", saida)
        self.assertIn("ERROS DE EXPECTATIVA: 0", saida)
        self.assertIn("'12.34.56789012-3'", saida)
        self.assertTrue(all(x.justificativa for x in r.resultados))

    def test_estresse_reprodutivel(self):
        resultados = testar_estresse(quantidade_por_tipo=1000, semente=20261013)
        self.assertEqual(len(resultados), 2)
        for r in resultados:
            with self.subTest(validador=r.nome):
                self.assertEqual(r.entradas_testadas, 3000)
                self.assertEqual(r.divergencias, 0)
                self.assertGreaterEqual(r.aceitas_afd, 1000)
                self.assertEqual(r.exemplos_divergentes, ())
        self.assertEqual(resultados, testar_estresse(quantidade_por_tipo=1000, semente=20261013))


if __name__ == "__main__":
    unittest.main()
