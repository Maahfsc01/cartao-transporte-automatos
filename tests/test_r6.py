"""Testes R6: logicamente reais + wiring com dublê leve do ipywidgets.

Não simula a renderização de um navegador. O dublê garante que os eventos
on_click/observe atualizam os componentes esperados. Para aceitação visual,
abra o notebook com ipywidgets >= 8 instalado no Jupyter.
"""

import sys
import types
import unittest
from unittest.mock import patch

from src.r1_afds import cartao, linha
from src.r4_catraca import Catraca
from src.r5_scanner import EXEMPLO_COM_ERROS, EXEMPLO_VALIDO, analisar
from src.r6_interface import (CSS_PAINEL_COMPACTO, avaliar_entrada, html_catraca,
                              html_scanner, html_validacao, LaboratorioR6)


class TestR6Resultados(unittest.TestCase):
    def test_tipografia_compacta_e_acessivel(self):
        self.assertIn("font-size:13px", CSS_PAINEL_COMPACTO)
        self.assertIn("font-size:12.5px", html_scanner(analisar(EXEMPLO_VALIDO)))
        self.assertIn('overflow-x:auto', html_validacao(avaliar_entrada('linha', '8700-10')))

    def test_validador_cartao_aceito(self):
        r = avaliar_entrada("cartao", "12.34.56789012-3")
        self.assertTrue(r.rastreamento.aceita)
        self.assertTrue(r.aceito_regex)
        self.assertTrue(r.coincide)
        self.assertEqual(r.rastreamento.estado_final, "q16")
        self.assertIn("Concordância AFD × RegEx", html_validacao(r))
        self.assertEqual(len(r.rastreamento.passos), 16)

    def test_validador_linha_aceita(self):
        r = avaliar_entrada("linha", "8700-10")
        self.assertTrue(r.rastreamento.aceita)
        self.assertTrue(r.coincide)
        self.assertEqual(r.rastreamento.estado_final, "q7")

    def test_validador_rejeita_formato_e_informa_o_erro(self):
        r = avaliar_entrada("linha", "8700-50")
        self.assertFalse(r.rastreamento.aceita)
        self.assertFalse(r.aceito_regex)
        self.assertIn("❌ REJEITADA", html_validacao(r))
        self.assertIn("Classe CINCO_A_NOVE", r.rastreamento.motivo)

    def test_entrada_vazia_visivel_e_rejeitada(self):
        for nome in ("cartao", "linha"):
            r = avaliar_entrada(nome, "")
            saida = html_validacao(r)
            self.assertFalse(r.rastreamento.aceita)
            self.assertFalse(r.aceito_regex)
            self.assertIn("palavra vazia", saida)
            self.assertIn("q0", saida)

    def test_concordancia_e_sem_duplicar_regras(self):
        for chave,afd in (("cartao",cartao),("linha",linha)):
            for palavra in ("", "12.34.56789012-3", "8700-10", "8700-50", "123456", "a"):
                r = avaliar_entrada(chave, palavra)
                self.assertEqual(r.rastreamento.aceita, afd.aceita(palavra))
                self.assertTrue(r.coincide)

    def test_nome_de_validador_invalido(self):
        with self.assertRaises(ValueError):
            avaliar_entrada("inexistente", "abc")

    def test_html_escapa_entrada_maliciosa_no_validador(self):
        html = html_validacao(avaliar_entrada("cartao", "<script>alert(1)</script>"))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_scanner_validacao_e_tabelas(self):
        s = analisar(EXEMPLO_VALIDO)
        self.assertTrue(s.aprovado)
        html = html_scanner(s)
        self.assertIn("ANÁLISE SEM ERROS", html)
        self.assertIn("NUM_CARTAO", html)
        self.assertIn("NUM_LINHA", html)
        self.assertIn("HORARIO", html)

    def test_scanner_recupera_e_exibe_dicas(self):
        s = analisar(EXEMPLO_COM_ERROS)
        self.assertEqual(len(s.erros),3)
        html = html_scanner(s)
        self.assertIn("ERROS LÉXICOS", html)
        self.assertIn("Dica de correção", html)
        self.assertIn("NUM_CARTAO", html) # reconhece o ultimo cartao, apos os erros
        self.assertIn("2", html)

    def test_escapar_html_da_saida_do_scanner(self):
        s = analisar("SALDO < 20.00; @ ")
        html = html_scanner(s)
        self.assertIn("&lt;", html)
        self.assertIn("caractere", html.lower())

    def test_tabela_limite_e_erro_do_limite(self):
        s = analisar("SALDO 10; " * 60)
        self.assertIn("exibição limitada", html_scanner(s, limite=10))
        with self.assertRaises(ValueError):
            html_scanner(s, limite=0)

    def test_recusa_preserva_estado_mostra_permitidos(self):
        c = Catraca()
        p = c.disparar("INICIAR_GIRO")
        html = html_catraca(c,p)
        self.assertFalse(p.aceito)
        self.assertEqual(c.estado, "TRAVADA")
        self.assertIn("APROXIMAR_CARTAO", html)
        self.assertIn("RECUSADO", html)

    def test_cenario_valido_altera_estado_e_historico(self):
        c = Catraca()
        resultado = c.executar(("APROXIMAR_CARTAO","VALIDAR_CARTAO", "SALDO_SUFICIENTE",
                                "INICIAR_GIRO", "CONCLUIR_GIRO", "REARMAR"))
        html = html_catraca(c, fluxo=resultado)
        self.assertEqual(c.estado, "TRAVADA")
        self.assertEqual(c.passagens_registradas, 1)
        self.assertIn("✅ VÁLIDO", html)
        self.assertIn("CONCLUIR_GIRO", html)


class FakeLayout:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeWidget:
    """Interface mínima do widget, só para testar eventos e vínculos."""
    def __init__(self, children=None, **kwargs):
        self.children = list(children or [])
        self.description = kwargs.get("description", "")
        self.options = kwargs.get("options")
        self._value = kwargs.get("value", "")
        self._click_callbacks = []
        self._observers = []
        self.titles = {}
        self.layout = kwargs.get("layout")

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        anterior = self._value
        self._value = value
        if value != anterior:
            for callback in self._observers:
                callback({"name": "value", "old": anterior, "new": value})

    def observe(self, callback, names="value"):
        if names == "value":
            self._observers.append(callback)

    def on_click(self, callback):
        self._click_callbacks.append(callback)

    def click(self):
        for callback in self._click_callbacks:
            callback(self)

    def set_title(self, index, text):
        self.titles[index] = text


def fake_ipywidgets():
    modulo = types.ModuleType("ipywidgets")
    modulo.Layout = FakeLayout
    for tipo in ("Button", "Dropdown", "Text", "Textarea", "HTML", "Tab", "VBox", "HBox"):
        setattr(modulo, tipo, FakeWidget)
    return modulo


class TestR6Interacoes(unittest.TestCase):
    """Smoke test dos callbacks sem depender de uma extensão frontend instalada."""

    def setUp(self):
        self.patcher = patch.dict(sys.modules, {"ipywidgets": fake_ipywidgets()})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.painel = LaboratorioR6()

    def test_estilos_compactos_estao_no_painel(self):
        self.assertIn("transporte-painel-compacto", self.painel.widget.children[0].value)
        self.assertIn("font-size:19px", self.painel.widget.children[1].value)

    def test_painel_tem_3_abas_e_inicio_funcional(self):
        self.assertEqual(len(self.painel.abas.children), 3)
        self.assertEqual(self.painel.abas.titles[0], "Validadores AFD")
        self.assertIn("ACEITA", self.painel.saida_afd.value)
        self.assertEqual(self.painel.catraca.estado,"TRAVADA")

    def test_afd_seletor_e_botoes_reagem(self):
        self.painel.seletor_afd.value = "linha"
        self.assertEqual(self.painel.campo_palavra.value, "8700-10")
        self.assertIn("ACEITA", self.painel.saida_afd.value)
        self.painel.botao_rejeita.click()
        self.assertEqual(self.painel.campo_palavra.value,"8700-50")
        self.assertIn("REJEITADA", self.painel.saida_afd.value)
        self.painel.botao_vazia.click()
        self.assertEqual(self.painel.campo_palavra.value, "")
        self.assertIn("palavra vazia", self.painel.saida_afd.value)
        self.painel.botao_aceita.click()
        self.assertEqual(self.painel.campo_palavra.value, "8700-10")

    def test_afds_manual_entrada(self):
        self.painel.campo_palavra.value = "12.34.56789012-3X"
        self.painel.botao_validar.click()
        self.assertIn("Caractere excedente", self.painel.saida_afd.value)

    def test_catraca_recusa_permitidos_e_reinicia(self):
        self.painel.seletor_evento.value = "INICIAR_GIRO"
        self.painel.botao_disparar.click()
        self.assertEqual(self.painel.catraca.estado, "TRAVADA")
        self.assertIn("RECUSADO", self.painel.saida_catraca.value)
        self.assertIn("APROXIMAR_CARTAO", self.painel.saida_catraca.value)
        self.painel.seletor_evento.value = "APROXIMAR_CARTAO"
        self.painel.botao_disparar.click()
        self.assertEqual(self.painel.catraca.estado, "CARTAO_LIDO")
        self.painel.botao_reiniciar.click()
        self.assertEqual(self.painel.catraca.estado, "TRAVADA")
        self.assertEqual(len(self.painel.catraca.historico), 0)

    def test_cenarios_validos_e_invalidos(self):
        self.painel.seletor_cenario.value=1
        self.painel.botao_cenario.click()
        self.assertEqual(self.painel.catraca.passagens_registradas,1)
        self.assertIn("VÁLIDO",self.painel.saida_catraca.value)
        self.painel.seletor_cenario.value=3
        self.painel.botao_cenario.click()
        self.assertEqual(self.painel.catraca.estado,"SEM_SALDO")
        self.assertEqual(self.painel.catraca.passagens_registradas,0)
        self.assertIn("INVÁLIDO",self.painel.saida_catraca.value)
        self.assertIn("RECUSADO",self.painel.saida_catraca.value)

    def test_scanner_exemplos_e_limpar(self):
        self.painel.botao_exemplo_erros.click()
        self.assertEqual(self.painel.campo_comandos.value,EXEMPLO_COM_ERROS)
        self.assertIn("ERROS LÉXICOS",self.painel.saida_scanner.value)
        self.painel.botao_exemplo_valido.click()
        self.assertIn("ANÁLISE SEM ERROS",self.painel.saida_scanner.value)
        self.painel.botao_limpar.click()
        self.assertEqual(self.painel.campo_comandos.value,"")
        self.assertIn("Texto limpo", self.painel.saida_scanner.value)
        self.painel.campo_comandos.value = "SALDO >= 20.00"
        self.painel.botao_analisar.click()
        self.assertIn("MAIOR_IGUAL",self.painel.saida_scanner.value)


if __name__ == "__main__":
    unittest.main()
