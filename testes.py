"""
SIFSM - Aurora Siger - Fase 7
Testes automáticos das partes centrais do sistema (unittest, biblioteca padrão).

Execução:  python testes.py
(se o banco data/aurora_siger.db não existir, ele é gerado antes dos testes)
"""

import math
import sqlite3
import unittest

import numpy as np
import sympy as sp

import simulacao_computacional as sim
from src import gerar_base
from src import regra_booleana as rb
from src.alertas import gerar_alertas
from src.config import ARQUIVO_BANCO, ARQUIVO_SQL
from src.estruturas import FilaAlertas, media_movel
from src.regressao import treinar_regressao
from src.terminal import configurar_saida_utf8


class TestRegraBooleana(unittest.TestCase):
    def test_tabela_verdade_tem_16_linhas(self):
        self.assertEqual(len(rb.tabela_verdade()), 16)

    def test_casos_principais(self):
        # bateria baixa e sem sol, módulo não essencial -> risco e corte
        self.assertEqual(rb.avaliar_regra(True, False, False, False), (True, True))
        # mesma situação, módulo essencial -> risco, mas sem corte
        self.assertEqual(rb.avaliar_regra(True, False, False, True), (True, False))
        # bateria baixa, mas o sol cobre o consumo -> sem risco
        self.assertEqual(rb.avaliar_regra(True, True, False, False), (False, False))
        # consumo excessivo sozinho já gera risco
        self.assertEqual(rb.avaliar_regra(False, True, True, False), (True, True))

    def test_corte_nunca_atinge_modulo_essencial(self):
        for a, g, e, p, _, corte in rb.tabela_verdade():
            if p:
                self.assertFalse(corte)

    def test_montar_variaveis_limiares(self):
        a, g, e, p = rb.montar_variaveis(29.9, 10, 20, 3.0, 2.0, 2)
        self.assertEqual((a, g, e, p), (True, False, True, True))
        a, g, e, p = rb.montar_variaveis(30.0, 20, 20, 2.8, 2.0, 3)
        self.assertEqual((a, g, e, p), (False, True, False, False))

    def test_modulo_sem_perfil_nao_gera_consumo_excessivo(self):
        self.assertFalse(rb.montar_variaveis(50, 0, 10, 99.0, None, 3)[2])


class TestBateria(unittest.TestCase):
    def test_limites_fisicos(self):
        self.assertEqual(sim.atualizar_carga(490, 50, 500, 0.95), 500)
        self.assertEqual(sim.atualizar_carga(10, -50, 500, 0.95), 0)

    def test_eficiencia_so_na_carga(self):
        self.assertAlmostEqual(sim.atualizar_carga(100, 10, 500, 0.95), 109.5)
        self.assertAlmostEqual(sim.atualizar_carga(100, -10, 500, 0.95), 90)


class TestEstruturasDeDados(unittest.TestCase):
    def test_fila_respeita_gravidade_prioridade_e_ciclo(self):
        fila = FilaAlertas()
        fila.inserir({"gravidade": 3, "prioridade": 1, "ciclo": 10, "id": "moderado"})
        fila.inserir({"gravidade": 1, "prioridade": 5, "ciclo": 5, "id": "critico"})
        fila.inserir({"gravidade": 2, "prioridade": 4, "ciclo": 7, "id": "alto_p4"})
        fila.inserir({"gravidade": 2, "prioridade": 1, "ciclo": 3, "id": "alto_p1_antigo"})
        fila.inserir({"gravidade": 2, "prioridade": 1, "ciclo": 9, "id": "alto_p1_recente"})
        ordem = [fila.atender()["id"] for _ in range(len(fila))]
        self.assertEqual(ordem, ["critico", "alto_p1_recente", "alto_p1_antigo", "alto_p4", "moderado"])
        self.assertIsNone(fila.atender())

    def test_media_movel_com_deque(self):
        medias = media_movel([1, 2, 3, 4, 5], janela=2)
        self.assertEqual(medias, [1.0, 1.5, 2.5, 3.5, 4.5])


class TestBancoDeDados(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(ARQUIVO_SQL.read_text(encoding="utf-8"))
        self.con.execute("INSERT INTO modulos VALUES (1, 'Teste', 'outro', NULL, 3, 'ativo', 10)")

    def tearDown(self):
        self.con.close()

    def _inserir_leitura(self, consumo=1.0, carga=50.0, ciclo=1):
        self.con.execute(
            "INSERT INTO leituras (id_modulo, ciclo, dia, hora, consumo_kwh, geracao_kwh, temperatura_c, "
            "luminosidade_lux, umidade_interna_pct, carga_bateria_pct) VALUES (1, ?, 1, 0, ?, 0, -50, 0, 40, ?)",
            (ciclo, consumo, carga))

    def test_constraints_rejeitam_valores_impossiveis(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self._inserir_leitura(consumo=-1)
        with self.assertRaises(sqlite3.IntegrityError):
            self._inserir_leitura(carga=120)
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO modulos VALUES (2, 'X', 'outro', NULL, 9, 'ativo', 10)")

    def test_leitura_duplicada_e_rejeitada(self):
        self._inserir_leitura()
        with self.assertRaises(sqlite3.IntegrityError):
            self._inserir_leitura()

    def test_exclusao_em_cascata(self):
        self._inserir_leitura()
        self.con.execute("DELETE FROM modulos WHERE id_modulo = 1")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM leituras").fetchone()[0], 0)


class TestComDadosReais(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARQUIVO_BANCO.exists():
            gerar_base.gerar_base()
        cls.bateria, cls.modulos, cls.leituras = sim.carregar_dados()
        cls.series = sim.montar_series(cls.modulos, cls.leituras)

    def test_base_sem_nulos_e_completa(self):
        self.assertEqual(len(self.leituras), 6 * 168)
        self.assertFalse(self.leituras.isna().any().any())

    def test_modelo_reproduz_carga_registrada(self):
        r = sim.simular_bateria(self.series, self.bateria)
        self.assertLess(np.abs(r["carga_pct"] - self.series["carga_registrada"]).max(), 1e-6)

    def test_corte_de_carga_reduz_apagao(self):
        sem = sim.simular_bateria(self.series, self.bateria)
        com = sim.simular_bateria(self.series, self.bateria, corte_ativo=True)
        self.assertLess(com["energia_nao_atendida_kwh"], sem["energia_nao_atendida_kwh"])

    def test_carga_sempre_entre_0_e_100(self):
        for r in sim.executar_cenarios(self.series, self.bateria).values():
            self.assertTrue(((r["carga_pct"] >= 0) & (r["carga_pct"] <= 100)).all())

    def test_integral_simbolica(self):
        t, pp = sp.symbols("t P_p", positive=True)
        integral = sp.integrate(pp * sp.sin(sp.pi * (t - 6) / 12), (t, 6, 18))
        self.assertEqual(sp.simplify(integral - 24 * pp / sp.pi), 0)
        simb = sim.analise_simbolica(self.series)
        self.assertAlmostEqual(simb["energia_teorica"], 24 * simb["pico_estimado"] / math.pi)
        # a soma das leituras deve ficar a menos de 2% da integral
        self.assertLess(abs(simb["energia_teorica"] - simb["energia_medida"]) / simb["energia_teorica"], 0.02)

    def test_regressao_coerente(self):
        reg = treinar_regressao(self.leituras)
        self.assertLess(reg["b"], 0)          # mais frio -> mais consumo
        self.assertGreater(reg["r2_teste"], 0.6)

    def test_deteccao_das_anomalias_injetadas(self):
        perfil = rb.calcular_perfil_esperado(self.leituras)
        modulos = {int(m.id_modulo): m._asdict() for m in self.modulos.itertuples()}
        alertas = gerar_alertas(self.leituras, modulos)
        detectados = {(a["id_modulo"], a["dia"], a["hora"]) for a in alertas if a["E"]}
        for id_modulo, dia, horas, _ in gerar_base.ANOMALIAS:
            for hora in horas:
                self.assertIn((id_modulo, dia, hora), detectados)
        self.assertTrue(perfil)


if __name__ == "__main__":
    configurar_saida_utf8()
    unittest.main(verbosity=2)
