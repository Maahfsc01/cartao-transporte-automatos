"""Testes iniciais exclusivos do R1. R3 (AFD × RegEx) será feito depois."""
import unittest
from src.r1_afds import cartao, linha, classificar, CLASSES


class TestR1(unittest.TestCase):
    def test_cartao_aceitos(self):
        for palavra in ("12.34.56789012-3", "00.00.00000000-0", "99.99.99999999-9"):
            with self.subTest(palavra=palavra):
                self.assertTrue(cartao.aceita(palavra))

    def test_cartao_rejeitados(self):
        for palavra in ("", "12.34.56789012", "12.34.56789012-", "12-34-56789012-3", "12.34.56789012-3X", " 12.34.56789012-3", "12.34.5678901A-3"):
            with self.subTest(palavra=palavra):
                self.assertFalse(cartao.aceita(palavra))

    def test_linha_aceitas(self):
        for palavra in ("8700-10", "1234-49", "9000-21", "4321-30"):
            with self.subTest(palavra=palavra):
                self.assertTrue(linha.aceita(palavra))

    def test_linha_rejeitadas(self):
        for palavra in ("", "0700-10", "8700-00", "8700-50", "8700-1", "8700-10X", "870010", "87A0-10", "8700-99"):
            with self.subTest(palavra=palavra):
                self.assertFalse(linha.aceita(palavra))

    def test_delta_total_e_deterministica(self):
        for afd in (cartao, linha):
            self.assertGreaterEqual(len(afd.estados), 5)
            self.assertEqual(len(afd.delta), len(afd.estados) * len(CLASSES))
            for q in afd.estados:
                for c in CLASSES:
                    self.assertIn(afd.delta[(q, c)], afd.estados)

    def test_classes_disjuntas(self):
        exemplos = "0123456789.-abc_ \t\n"
        for c in exemplos:
            self.assertIn(classificar(c), CLASSES)
        self.assertEqual(classificar("0"), "ZERO")
        self.assertEqual(classificar("1"), "UM_A_QUATRO")
        self.assertEqual(classificar("5"), "CINCO_A_NOVE")
        self.assertEqual(classificar("."), "PONTO")
        self.assertEqual(classificar("-"), "HIFEN")
        self.assertEqual(classificar("A"), "OUTRO")

    def test_palavra_vazia_e_sufixo(self):
        self.assertFalse(cartao.aceita(""))
        self.assertFalse(linha.aceita(""))
        self.assertFalse(cartao.aceita("12.34.56789012-3 LIXO"))
        self.assertFalse(linha.aceita("8700-10 LIXO"))


if __name__ == "__main__":
    unittest.main()
