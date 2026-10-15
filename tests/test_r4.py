"""Testes formais do R4, sem dependências de terceiros."""
import unittest
from contextlib import redirect_stdout
from io import StringIO

from src.r4_catraca import (
    Catraca, CENARIOS, DELTA, DESCRICOES_ESTADOS, ESTADOS, ESTADO_INICIAL,
    EVENTOS, TRANSICOES, executar_cenarios, texto_fluxo, verificar_modelo,
)


class TestR4Catraca(unittest.TestCase):
    def test_requisitos_estruturais_e_alcancabilidade(self):
        verificar_modelo()
        self.assertGreaterEqual(len(ESTADOS), 5)
        self.assertGreaterEqual(len(TRANSICOES), 6)
        self.assertEqual(len(DELTA), len(TRANSICOES))
        self.assertEqual(len(DESCRICOES_ESTADOS), len(ESTADOS))
        self.assertEqual(ESTADO_INICIAL, "TRAVADA")

    def test_transicoes_exatamente_como_tabela_delta(self):
        for t in TRANSICOES:
            with self.subTest(origem=t.origem, evento=t.evento):
                maquina = Catraca()
                maquina.estado = t.origem  # Inspeciona cada transição de maneira isolada.
                passo = maquina.disparar(t.evento)
                self.assertTrue(passo.aceito)
                self.assertEqual(passo.destino, t.destino)
                self.assertEqual(maquina.estado, t.destino)
                self.assertEqual(DELTA[(t.origem, t.evento)], t.destino)

    def test_tabela_e_eventos_permitidos_vem_das_transicoes(self):
        catraca = Catraca()
        with redirect_stdout(StringIO()) as resultado:
            tabela = catraca.tabela()
        self.assertEqual(tuple(tabela), TRANSICOES)
        self.assertIn("SALDO_INSUFICIENTE", resultado.getvalue())
        for estado in ESTADOS:
            esperados = tuple(t.evento for t in TRANSICOES if t.origem == estado)
            self.assertEqual(catraca.permitidos(estado), esperados)
        self.assertTrue(set(EVENTOS) >= {"CANCELAR", "APROXIMAR_CARTAO"})
        with self.assertRaises(ValueError):
            catraca.permitidos("NAO_EXISTE")

    def test_dois_fluxos_validos_com_rearme_e_passagem(self):
        resultados = executar_cenarios(mostrar=False)
        self.assertEqual(len(resultados), 4)
        for fluxo in resultados[:2]:
            self.assertTrue(fluxo.completo)
            self.assertFalse(fluxo.contem_recusa)
            self.assertTrue(fluxo.viagem_concluida)
            self.assertEqual(fluxo.estado_final, "TRAVADA")
            self.assertEqual(fluxo.passagens_registradas, 1)
            self.assertTrue(all(p.aceito for p in fluxo.passos))

    def test_dois_fluxos_invalidos_com_lista_de_eventos(self):
        fluxos = executar_cenarios(mostrar=False)[2:]
        self.assertEqual(len(fluxos), 2)
        for fluxo in fluxos:
            self.assertFalse(fluxo.completo)
            self.assertTrue(fluxo.contem_recusa)
            self.assertEqual(fluxo.passagens_registradas, 0)
            recusas = [p for p in fluxo.passos if not p.aceito]
            self.assertEqual(len(recusas), 1)
            recusa = recusas[0]
            self.assertEqual(recusa.origem, recusa.destino)
            self.assertTrue(recusa.permitidos)
            self.assertIn("Permitidos agora", recusa.explicacao)
            for evento in recusa.permitidos:
                self.assertIn(evento, texto_fluxo(fluxo))
        self.assertEqual(fluxos[0].estado_final, "CARTAO_LIDO")
        self.assertEqual(fluxos[0].passos[-1].permitidos, ("VALIDAR_CARTAO", "CANCELAR"))
        self.assertEqual(fluxos[1].estado_final, "SEM_SALDO")
        self.assertEqual(fluxos[1].passos[-1].permitidos, ("RECARGA_CONFIRMADA", "CANCELAR"))

    def test_evento_recusado_nao_altera_estado_nem_contador(self):
        catraca = Catraca()
        r = catraca.disparar("INICIAR_GIRO")
        self.assertFalse(r.aceito)
        self.assertEqual(r.origem, r.destino)
        self.assertEqual(catraca.estado, "TRAVADA")
        self.assertEqual(catraca.passagens_registradas, 0)
        self.assertEqual(r.permitidos, ("APROXIMAR_CARTAO",))

    def test_evento_desconhecido_recusado_com_dica(self):
        catraca = Catraca()
        passo = catraca.disparar("PULAR_CATRACA")
        self.assertFalse(passo.aceito)
        self.assertIn("desconhecido", passo.explicacao)
        self.assertIn("APROXIMAR_CARTAO", passo.explicacao)
        self.assertEqual(catraca.estado, ESTADO_INICIAL)
        vazio = catraca.disparar("")
        self.assertFalse(vazio.aceito)
        self.assertTrue(vazio.permitidos)

    def test_recusa_e_recuperacao_sem_reiniciar(self):
        catraca = Catraca()
        catraca.disparar("APROXIMAR_CARTAO")
        erro = catraca.disparar("INICIAR_GIRO")
        self.assertFalse(erro.aceito)
        self.assertEqual(catraca.estado, "CARTAO_LIDO")
        novo_passo = catraca.disparar("VALIDAR_CARTAO")
        self.assertTrue(novo_passo.aceito)
        self.assertEqual(catraca.estado, "VERIFICANDO_SALDO")

    def test_recarga_exige_revalidacao_de_saldo(self):
        catraca = Catraca()
        for evento in ("APROXIMAR_CARTAO", "VALIDAR_CARTAO", "SALDO_INSUFICIENTE", "RECARGA_CONFIRMADA"):
            self.assertTrue(catraca.disparar(evento).aceito)
        self.assertEqual(catraca.estado, "VERIFICANDO_SALDO")
        erro = catraca.disparar("INICIAR_GIRO")
        self.assertFalse(erro.aceito)
        self.assertIn("SALDO_SUFICIENTE", erro.permitidos)
        self.assertEqual(catraca.estado, "VERIFICANDO_SALDO")

    def test_expiracao_e_cancelamentos(self):
        maquina = Catraca()
        for evento in ("APROXIMAR_CARTAO", "VALIDAR_CARTAO", "SALDO_SUFICIENTE", "TEMPO_ESGOTADO"):
            self.assertTrue(maquina.disparar(evento).aceito)
        self.assertEqual(maquina.estado, "TRAVADA")
        self.assertEqual(maquina.passagens_registradas, 0)
        for origem_em_eventos in (
            ("APROXIMAR_CARTAO", "CANCELAR"),
            ("APROXIMAR_CARTAO", "VALIDAR_CARTAO", "CANCELAR"),
            ("APROXIMAR_CARTAO", "VALIDAR_CARTAO", "SALDO_INSUFICIENTE", "CANCELAR"),
        ):
            catraca = Catraca()
            self.assertTrue(catraca.executar(origem_em_eventos).completo)
            self.assertEqual(catraca.estado, "TRAVADA")
            self.assertEqual(catraca.passagens_registradas, 0)

    def test_fluxo_parcial_nao_equivale_a_viagem(self):
        catraca = Catraca()
        fluxo = catraca.executar(("APROXIMAR_CARTAO",))
        self.assertTrue(fluxo.completo)
        self.assertFalse(fluxo.viagem_concluida)
        self.assertEqual(fluxo.estado_final, "CARTAO_LIDO")

    def test_parada_apos_erro_configuravel(self):
        seq = ("INICIAR_GIRO", "APROXIMAR_CARTAO")
        interrompido = Catraca().executar(seq)
        self.assertEqual(len(interrompido.passos), 1)
        self.assertFalse(interrompido.completo)
        self.assertEqual(interrompido.estado_final, "TRAVADA")
        continua = Catraca().executar(seq, parar_ao_recusar=False)
        self.assertEqual(len(continua.passos), 2)
        self.assertFalse(continua.completo)
        self.assertEqual(continua.estado_final, "CARTAO_LIDO")

    def test_dois_embarques_sucessivos(self):
        catraca = Catraca()
        seq = CENARIOS[0][1]
        catraca.executar(seq)
        resultado = catraca.executar(seq)
        self.assertEqual(resultado.passagens_registradas, 2)
        self.assertEqual(catraca.estado, "TRAVADA")

    def test_reiniciar_redefine_tudo(self):
        catraca = Catraca()
        catraca.executar(CENARIOS[0][1])
        catraca.reiniciar()
        self.assertEqual(catraca.estado, ESTADO_INICIAL)
        self.assertEqual(catraca.passagens_registradas, 0)
        self.assertEqual(catraca.historico, [])

    def test_entrada_de_tipo_incorreto_rejeitada_sem_efeito(self):
        catraca = Catraca()
        with self.assertRaises(TypeError):
            catraca.disparar(123)
        for invalido in ("APROXIMAR_CARTAO", b"APROXIMAR_CARTAO", ["APROXIMAR_CARTAO", 123]):
            with self.assertRaises(TypeError):
                catraca.executar(invalido)
        self.assertEqual(catraca.estado, ESTADO_INICIAL)
        self.assertEqual(len(catraca.historico), 0)

    def test_todos_os_cenarios_podem_ser_impressos(self):
        with redirect_stdout(StringIO()) as saida:
            resultados = executar_cenarios(mostrar=True)
        texto = saida.getvalue()
        self.assertEqual(len(resultados), 4)
        self.assertEqual(texto.count("CENÁRIO:"), 4)
        self.assertEqual(texto.count("EVENTOS PERMITIDOS:"), 2)
        self.assertEqual(texto.count("FLUXO VÁLIDO"), 2)
        self.assertEqual(texto.count("FLUXO INVÁLIDO"), 2)


if __name__ == "__main__":
    unittest.main()
