PRAGMA foreign_keys = ON;

CREATE TABLE modulos (
    id_modulo INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo TEXT,
    codigo_sensor TEXT,
    prioridade INTEGER,
    status TEXT CHECK (status IN ('ativo', 'manutencao', 'alerta'))
);

CREATE TABLE leituras (
    id_leitura INTEGER PRIMARY KEY,
    id_modulo INTEGER NOT NULL,
    ciclo INTEGER NOT NULL,
    consumo_kwh REAL,
    geracao_kwh	REAL,
    temperatura_c REAL,
    luminosidade_lux REAL,
    umidade_pct	REAL,
    FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo)
);

CREATE TABLE alertas (
    id_alerta INTEGER PRIMARY KEY,
    id_modulo INTEGER NOT NULL,
    ciclo INTEGER,
    tipo TEXT,
    mensagem TEXT,
    resolvido INTEGER,
    FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo)
);

CREATE TABLE manutencoes (
    id_manutencao INTEGER PRIMARY KEY,
    id_modulo INTEGER NOT NULL,
    data TEXT,
    descricao TEXT,
    status TEXT CHECK (status IN ('pendente', 'concluida')),
    FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo)
);