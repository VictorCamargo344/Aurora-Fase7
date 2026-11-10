-- =====================================================================
-- SIFSM - Sistema Integrado de Futuro Sustentável em Marte
-- Aurora Siger - Fase 7 - Gestão energética sustentável da colônia
--
-- Script de criação do banco de dados (SQLite).
-- Pode ser executado várias vezes: as tabelas são apagadas e recriadas.
-- Uso manual:  sqlite3 aurora_siger.db < script_banco.sql
-- (o gerar_base.py executa este script automaticamente)
-- =====================================================================

PRAGMA foreign_keys = ON;

-- Remove as tabelas na ordem inversa das dependências (filhas primeiro)
DROP TABLE IF EXISTS alertas;
DROP TABLE IF EXISTS manutencoes;
DROP TABLE IF EXISTS leituras;
DROP TABLE IF EXISTS baterias;
DROP TABLE IF EXISTS modulos;

-- ---------------------------------------------------------------------
-- Módulos da colônia (habitação, médico, energia, laboratório...)
-- prioridade: 1 = mais essencial ... 5 = menos essencial
-- consumo_base_kwh_dia: consumo nominal diário do módulo, sem
--                       aquecimento e iluminação extras
-- ---------------------------------------------------------------------
CREATE TABLE modulos (
    id_modulo            INTEGER PRIMARY KEY,
    nome                 TEXT    NOT NULL UNIQUE,
    tipo                 TEXT    NOT NULL,
    codigo_sensor        TEXT    UNIQUE,
    prioridade           INTEGER NOT NULL CHECK (prioridade BETWEEN 1 AND 5),
    status               TEXT    NOT NULL CHECK (status IN ('ativo', 'manutencao', 'alerta')),
    consumo_base_kwh_dia REAL    NOT NULL CHECK (consumo_base_kwh_dia > 0)
);

-- ---------------------------------------------------------------------
-- Banco de baterias da colônia (armazenamento de energia)
-- eficiencia: fração da energia excedente que de fato é armazenada
-- ---------------------------------------------------------------------
CREATE TABLE baterias (
    id_bateria        INTEGER PRIMARY KEY,
    nome              TEXT NOT NULL,
    capacidade_kwh    REAL NOT NULL CHECK (capacidade_kwh > 0),
    carga_inicial_pct REAL NOT NULL CHECK (carga_inicial_pct BETWEEN 0 AND 100),
    carga_minima_pct  REAL NOT NULL CHECK (carga_minima_pct BETWEEN 0 AND 100),
    eficiencia        REAL NOT NULL CHECK (eficiencia > 0 AND eficiencia <= 1)
);

-- ---------------------------------------------------------------------
-- Leituras horárias dos sensores de cada módulo
-- ciclo: hora sequencial da missão (1, 2, 3...)
-- dia / hora: derivados do ciclo (ciclo 1 = dia 1, hora 0)
-- carga_bateria_pct: estado de carga do banco de baterias da colônia
--                    ao final daquele ciclo (mesmo valor para todos
--                    os módulos no mesmo ciclo)
-- ---------------------------------------------------------------------
CREATE TABLE leituras (
    id_leitura          INTEGER PRIMARY KEY,
    id_modulo           INTEGER NOT NULL,
    ciclo               INTEGER NOT NULL CHECK (ciclo >= 1),
    dia                 INTEGER NOT NULL CHECK (dia >= 1),
    hora                INTEGER NOT NULL CHECK (hora BETWEEN 0 AND 23),
    consumo_kwh         REAL    NOT NULL CHECK (consumo_kwh >= 0),
    geracao_kwh         REAL    NOT NULL CHECK (geracao_kwh >= 0),
    temperatura_c       REAL    NOT NULL CHECK (temperatura_c BETWEEN -150 AND 50),
    luminosidade_lux    REAL    NOT NULL CHECK (luminosidade_lux >= 0),
    umidade_interna_pct REAL    NOT NULL CHECK (umidade_interna_pct BETWEEN 0 AND 100),
    carga_bateria_pct   REAL    NOT NULL CHECK (carga_bateria_pct BETWEEN 0 AND 100),
    UNIQUE (id_modulo, ciclo),
    FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Alertas gerados pela regra booleana
-- gravidade: 1 = crítico, 2 = alto, 3 = moderado
-- ---------------------------------------------------------------------
CREATE TABLE alertas (
    id_alerta INTEGER PRIMARY KEY,
    id_modulo INTEGER NOT NULL,
    ciclo     INTEGER NOT NULL,
    tipo      TEXT    NOT NULL CHECK (tipo IN ('energia', 'consumo', 'energia_consumo')),
    gravidade INTEGER NOT NULL CHECK (gravidade BETWEEN 1 AND 3),
    mensagem  TEXT    NOT NULL,
    resolvido INTEGER NOT NULL DEFAULT 0 CHECK (resolvido IN (0, 1)),
    FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Registro de manutenções dos módulos
-- dia: dia da missão em que a manutenção foi registrada
-- ---------------------------------------------------------------------
CREATE TABLE manutencoes (
    id_manutencao INTEGER PRIMARY KEY,
    id_modulo     INTEGER NOT NULL,
    dia           INTEGER NOT NULL CHECK (dia >= 1),
    descricao     TEXT    NOT NULL,
    status        TEXT    NOT NULL CHECK (status IN ('pendente', 'concluida')),
    FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo) ON DELETE CASCADE
);

-- Índice para acelerar consultas por ciclo (usadas na análise energética)
CREATE INDEX idx_leituras_ciclo ON leituras (ciclo);
