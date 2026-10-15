"""Testes de regressao e de rastreabilidade dos AFDs."""
import unittest

from src.r1_afds import cartao, linha
from src.r2_rastreamento import (
    classes_esperadas, rastrear_detalhado, rodar_r2, texto_rastreamento,
)
from contextlib import redirect_stdout
from io import StringIO


class TestR2(unittest.TestCase):
    def test_cartao_aceito(self):
        r = rastrear_detalhado(cartao, "12.34.56789012-3")
        self.assertTrue(r.aceita)
        self.assertEqual(r.estado_final, "q16")
        self.assertEqual(len(r.passos), 16)
        self.assertEqual(r.passos[0].origem, "q0")
        self.assertEqual(r.passos[-1].destino, "q16")
        self.assertIn("pertence", r.motivo)

    def test_cartao_rejeitado_extra(self):
        r = rastrear_detalhado(cartao, "12.34.56789012-3X")
        self.assertFalse(r.aceita)
        self.assertEqual(r.estado_final, "qerro")
        self.assertIn("posição 17", r.motivo)
        self.assertIn("excedente", r.motivo)
        self.assertEqual(r.passos[-1].origem, "q16")

    def test_linha_aceita(self):
        r = rastrear_detalhado(linha, "8700-10")
        self.assertTrue(r.aceita)
        self.assertEqual(len(r.passos), 7)
        self.assertEqual(r.estado_final, "q7")

    def test_linha_rejeita_dezena_nao_permitida(self):
        r = rastrear_detalhado(linha, "8700-50")
        self.assertFalse(r.aceita)
        self.assertEqual(r.estado_final, "qerro")
        self.assertIn("posição 6", r.motivo)
        self.assertIn("UM_A_QUATRO", r.motivo)

    def test_cartao_incompleto(self):
        r = rastrear_detalhado(cartao, "12.34.56789012")
        self.assertFalse(r.aceita)
        self.assertEqual(r.estado_final, "q14")
        self.assertIn("prematuramente", r.motivo)
        self.assertIn("HIFEN", r.motivo)

    def test_linha_incompleta(self):
        r = rastrear_detalhado(linha, "8700-1")
        self.assertFalse(r.aceita)
        self.assertEqual(r.estado_final, "q6")
        self.assertIn("prematuramente", r.motivo)

    def test_palavra_vazia(self):
        for afd in (cartao, linha):
            with self.subTest(afd=afd.nome):
                r = rastrear_detalhado(afd, "")
                self.assertFalse(r.aceita)
                self.assertEqual(r.estado_final, "q0")
                self.assertEqual(r.passos, ())
                self.assertIn("vazia", r.motivo)

    def test_erro_permanente_consumo_total(self):
        palavra = "8700-50XX"
        r = rastrear_detalhado(linha, palavra)
        self.assertEqual(len(r.passos), len(palavra))
        self.assertEqual(r.passos[5].destino, "qerro")
        self.assertTrue(all(p.destino == "qerro" for p in r.passos[5:]))
        self.assertIn("posição 6", r.motivo)

    def test_prefixo_restante_e_delta(self):
        for afd, palavra in ((cartao, "12.34.56789012-3X"), (linha, "0700-10")):
            r = rastrear_detalhado(afd, palavra)
            for p in r.passos:
                self.assertEqual(p.prefixo + p.restante, palavra)
                self.assertEqual(afd.delta[(p.origem, p.classe)], p.destino)
                self.assertEqual(p.posicao, len(p.prefixo))

    def test_classes_esperadas(self):
        self.assertEqual(classes_esperadas(linha, "q0"), ("UM_A_QUATRO", "CINCO_A_NOVE"))
        self.assertEqual(classes_esperadas(linha, "q5"), ("UM_A_QUATRO",))
        self.assertEqual(classes_esperadas(cartao, "q16"), ())
        with self.assertRaises(ValueError):
            classes_esperadas(cartao, "inexistente")

    def test_entradas_invalidas_type(self):
        for valor in (None, 8700, [], b"8700-10"):
            with self.subTest(valor=valor):
                with self.assertRaises(TypeError):
                    rastrear_detalhado(linha, valor)

    def test_r1_e_r2_concordam(self):
        exemplos = ["", "8700-10", "8700-49", "8700-50", "0000-10", "8700-1", "8700-10X", "ø"]
        exemplos += ["12.34.56789012-3", "12.34.56789012", "12.34.56789012-3X", "00.00.00000000-0", "123"]
        for afd in (cartao, linha):
            for palavra in exemplos:
                with self.subTest(afd=afd.nome, palavra=palavra):
                    self.assertEqual(rastrear_detalhado(afd, palavra).aceita, afd.aceita(palavra))

    def test_saida_texto_e_rodar(self):
        f = StringIO()
        with redirect_stdout(f):
            r = rodar_r2(linha, "8700-50")
        txt = texto_rastreamento(r)
        self.assertEqual(txt + "\n", f.getvalue())
        self.assertIn("REJEITADA", txt)
        self.assertIn("JUSTIFICATIVA", txt)


if __name__ == "__main__":
    unittest.main()
