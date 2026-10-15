"""R5 — Testes de tokenizacao, Maximal Munch e recuperacao lexico."""
import unittest
from contextlib import redirect_stdout
from io import StringIO

from src.r5_scanner import (
    EXEMPLO_COM_ERROS, EXEMPLO_VALIDO, RESERVADAS, REGRAS,
    TIPOS_DE_TOKEN, analisar, imprimir_resultado, tabela_tokens,
)
from src.r1_afds import cartao, linha


class TestR5Scanner(unittest.TestCase):
    def tipos(self, fonte):
        return [t.tipo for t in analisar(fonte).tokens]

    def test_numero_de_tipos_e_reservadas(self):
        self.assertGreaterEqual(len(TIPOS_DE_TOKEN), 8)
        self.assertGreaterEqual(len(RESERVADAS), 3)
        self.assertEqual(len(RESERVADAS), len(set(RESERVADAS)))
        self.assertTrue(set(RESERVADAS) <= set(TIPOS_DE_TOKEN))

    def test_regras_sao_compiladas_sem_duplicar_nomes(self):
        nomes = [regra.nome for regra in REGRAS]
        self.assertEqual(len(nomes), len(set(nomes)))
        self.assertGreaterEqual(len(nomes), len(TIPOS_DE_TOKEN))

    def test_exemplo_valido_sem_erros(self):
        resultado = analisar(EXEMPLO_VALIDO)
        self.assertTrue(resultado.aprovado)
        self.assertEqual(len(resultado.erros), 0)
        self.assertIn("NUM_CARTAO", [x.tipo for x in resultado.tokens])
        self.assertIn("NUM_LINHA", [x.tipo for x in resultado.tokens])
        self.assertIn("HORARIO", [x.tipo for x in resultado.tokens])

    def test_comando_recarga_com_id_e_decimal(self):
        tokens = analisar("RECARGA 20.00 CARTAO 12.34.56789012-3;").tokens
        self.assertEqual([(t.tipo, t.lexema) for t in tokens], [
            ("RECARGA", "RECARGA"), ("REAL", "20.00"),
            ("CARTAO", "CARTAO"), ("NUM_CARTAO", "12.34.56789012-3"),
            ("PONTO_VIRGULA", ";")])
        self.assertEqual((tokens[3].linha, tokens[3].coluna), (1, 22))

    def test_comando_embarque_linha_hora(self):
        self.assertEqual(self.tipos("EMBARQUE 8700-10 07:42"),
                         ["EMBARQUE", "NUM_LINHA", "HORARIO"])

    def test_reservadas_cinco_e_identificador(self):
        self.assertEqual(self.tipos("RECARGA CARTAO EMBARQUE SALDO EVENTO APROXIMAR_CARTAO"),
                         ["RECARGA", "CARTAO", "EMBARQUE", "SALDO", "EVENTO", "IDENTIFICADOR"])

    def test_palavra_reservada_nao_e_prefixo(self):
        self.assertEqual(self.tipos("RECARGA2026 RECARGA_EXTRA EMBARQUE_2 SALDO_"),
                         ["IDENTIFICADOR"] * 4)

    def test_reservadas_sao_sensiveis_a_caixa(self):
        self.assertEqual(self.tipos("recarga Recarga RECARGA"),
                         ["IDENTIFICADOR", "IDENTIFICADOR", "RECARGA"])

    def test_operadores_compostos_maximal_munch(self):
        self.assertEqual(self.tipos("SALDO >= 20 SALDO > 20 SALDO <= 30 SALDO < 30 SALDO == 20 SALDO = 20"),
                         ["SALDO", "MAIOR_IGUAL", "INTEIRO", "SALDO", "MAIOR", "INTEIRO",
                          "SALDO", "MENOR_IGUAL", "INTEIRO", "SALDO", "MENOR", "INTEIRO",
                          "SALDO", "IGUAL_IGUAL", "INTEIRO", "SALDO", "ATRIBUICAO", "INTEIRO"])

    def test_numero_real_mais_longo_que_inteiro(self):
        self.assertEqual(self.tipos("20.00 20 0.5"), ["REAL", "INTEIRO", "REAL"])

    def test_token_grande_cartao_nao_e_quebrado_em_reais(self):
        self.assertEqual(self.tipos("12.34.56789012-3"), ["NUM_CARTAO"])

    def test_token_grande_linha_nao_e_quebrado_em_inteiros(self):
        self.assertEqual(self.tipos("8700-10"), ["NUM_LINHA"])

    def test_cartoes_validos_do_r1_sao_tokens(self):
        for entrada in ("12.34.56789012-3", "00.00.00000000-0", "99.99.99999999-9"):
            self.assertTrue(cartao.aceita(entrada))
            result = analisar(entrada)
            self.assertTrue(result.aprovado)
            self.assertEqual([t.tipo for t in result.tokens], ["NUM_CARTAO"])

    def test_linhas_validas_do_r1_sao_tokens(self):
        for entrada in ("8700-10", "1234-49", "9999-19"):
            self.assertTrue(linha.aceita(entrada))
            result = analisar(entrada)
            self.assertTrue(result.aprovado)
            self.assertEqual([t.tipo for t in result.tokens], ["NUM_LINHA"])

    def test_cartao_malformado_erro_unico_com_dica(self):
        for entrada in ("12.34.56789012", "12.34.56789012-", "12.34.56789012-3X", "12.34.5678901A-3"):
            resultado = analisar(entrada)
            self.assertFalse(resultado.aprovado)
            self.assertEqual(len(resultado.erros), 1, entrada)
            self.assertEqual(resultado.erros[0].lexema, entrada)
            self.assertIn("NN.NN.NNNNNNNN-N", resultado.erros[0].dica)
            self.assertFalse(resultado.tokens)

    def test_linha_malformada_erro_unico_com_dica(self):
        for entrada in ("8700-50", "8700-00", "0700-10", "8700-10X", "8700-"):
            resultado = analisar(entrada)
            self.assertFalse(resultado.aprovado)
            self.assertEqual(len(resultado.erros), 1, entrada)
            self.assertEqual(resultado.erros[0].lexema, entrada)
            self.assertIn("ABCD-EF", resultado.erros[0].dica)

    def test_horarios_bordas_validos(self):
        for entrada in ("00:00", "07:42", "23:59", "19:00"):
            self.assertEqual(self.tipos(entrada), ["HORARIO"])
            self.assertTrue(analisar(entrada).aprovado)

    def test_horarios_invalidos_com_dica(self):
        for entrada in ("25:00", "18:75", "07:4", "07:42Z", "07:"):
            resultado = analisar(entrada)
            self.assertEqual(len(resultado.erros), 1, entrada)
            self.assertEqual(resultado.erros[0].lexema, entrada)
            self.assertIn("HH:MM", resultado.erros[0].dica)

    def test_exemplo_erros_preserva_linhas_e_recupera(self):
        resultado = analisar(EXEMPLO_COM_ERROS)
        self.assertEqual([(e.linha, e.coluna) for e in resultado.erros],
                         [(1, 22), (2, 10), (2, 18)])
        self.assertEqual([e.lexema for e in resultado.erros],
                         ["12.34.56789012", "8700-50", "25:00"])
        self.assertEqual([t.tipo for t in resultado.tokens[-4:]],
                         ["RECARGA", "REAL", "CARTAO", "NUM_CARTAO"])
        self.assertEqual(resultado.tokens[-1].linha, 3)

    def test_erro_simbolo_nao_interrompe_mesma_linha(self):
        r = analisar("RECARGA @ 20.00 CARTAO 12.34.56789012-3")
        self.assertEqual([(e.linha, e.coluna, e.lexema) for e in r.erros], [(1, 9, "@")])
        self.assertEqual([t.tipo for t in r.tokens[-3:]], ["REAL", "CARTAO", "NUM_CARTAO"])
        self.assertTrue(r.erros[0].dica)

    def test_dois_erros_genericos_que_nao_interrompem(self):
        r = analisar("$ # ignorado\nEMBARQUE 8700-10 07:42 %")
        self.assertEqual([e.lexema for e in r.erros], ["$", "%"])
        self.assertEqual((r.erros[1].linha, r.erros[1].coluna), (2, 24))
        self.assertEqual([t.tipo for t in r.tokens], ["EMBARQUE", "NUM_LINHA", "HORARIO"])

    def test_comentarios_e_espacos_ignorados(self):
        entrada = " \t# comentário <= == 123\nRECARGA 20.00 // SALDO >= 10\nEMBARQUE 8700-10 07:42"
        self.assertEqual(self.tipos(entrada), ["RECARGA", "REAL", "EMBARQUE", "NUM_LINHA", "HORARIO"])
        self.assertFalse(analisar(entrada).erros)

    def test_quebras_crlf_cr_e_tab_com_posicoes(self):
        r = analisar("RECARGA\r\n\tEMBARQUE\rSALDO\n  CARTAO")
        self.assertEqual([(t.linha, t.coluna) for t in r.tokens],
                         [(1, 1), (2, 2), (3, 1), (4, 3)])
        self.assertEqual(r.linhas, 4)

    def test_lista_vazia_e_apenas_comentarios(self):
        for fonte in ("", "\n", "# comentario", "// comentario\n# outro\n"):
            r = analisar(fonte)
            self.assertEqual(r.tokens, ())
            self.assertEqual(r.erros, ())
            self.assertTrue(r.aprovado)

    def test_nao_aceita_tipos_de_entrada_errados(self):
        for entrada in (None, 42, b"RECARGA", ["RECARGA"]):
            with self.assertRaises(TypeError):
                analisar(entrada)

    def test_simbolos_hifen_barra_e_ponto_tem_dicas(self):
        r = analisar("- / . :")
        self.assertEqual(len(r.erros), 4)
        self.assertTrue(all(e.dica and e.mensagem for e in r.erros))

    def test_delimitadores_nao_emitem_erro(self):
        self.assertEqual(self.tipos("(20,30);"), ["ABRE_PAREN", "INTEIRO", "VIRGULA", "INTEIRO", "FECHA_PAREN", "PONTO_VIRGULA"])

    def test_rejeicao_de_linha_nao_descarta_horario_mesmo_com_erros(self):
        r = analisar("EMBARQUE 8700-50 07:42 SALDO >= 10")
        self.assertEqual(len(r.erros), 1)
        self.assertEqual(r.erros[0].lexema, "8700-50")
        self.assertEqual([t.tipo for t in r.tokens],
                         ["EMBARQUE", "HORARIO", "SALDO", "MAIOR_IGUAL", "INTEIRO"])

    def test_entradas_aleatorias_nao_quebram_invariantes_lexicas(self):
        from random import Random
        aleatorio = Random(20261013)
        caracteres = "0123456789ABCxyz_#;><=:/-.@ $\\\n\t"
        for _ in range(250):
            texto = "".join(aleatorio.choices(caracteres, k=aleatorio.randrange(0, 65)))
            resultado = analisar(texto)
            self.assertEqual(resultado.caracteres, len(texto))
            self.assertTrue(all(0 <= x.offset < len(texto) for x in (*resultado.tokens, *resultado.erros)))
            self.assertTrue(all(x.tipo in TIPOS_DE_TOKEN for x in resultado.tokens))
            for token in resultado.tokens:
                if token.tipo == "NUM_CARTAO":
                    self.assertTrue(cartao.aceita(token.lexema))
                if token.tipo == "NUM_LINHA":
                    self.assertTrue(linha.aceita(token.lexema))

    def test_relatorio_e_tabela_expoem_todos_os_tokens_e_erros(self):
        with redirect_stdout(StringIO()) as saida:
            linhas = tabela_tokens()
            imprimir_resultado(analisar(EXEMPLO_COM_ERROS))
        texto = saida.getvalue()
        self.assertEqual(len(linhas), len(TIPOS_DE_TOKEN))
        self.assertIn("Dica:", texto)
        self.assertIn("[1:22]", texto)
        self.assertIn("NUM_CARTAO", texto)


if __name__ == "__main__":
    unittest.main()
