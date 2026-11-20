\set ON_ERROR_STOP on

BEGIN;

INSERT INTO :"schema_name".identity_accounts (
    id, display_name, email, password_hash, status, access_version,
    retained_session_id, retained_session_access_version, time_zone,
    created_at, updated_at, confirmed_at
)
VALUES
    ('RDSLAB2026' || lpad('1', 16, '0'), 'Conta fictícia 01', 'rds-lab-01@example.invalid', 'LAB-SEM-CREDENCIAL-NAO-VALIDA', 'pending-confirmation', 1, NULL, NULL, 'America/Sao_Paulo', '2026-11-18T12:00:00Z', '2026-11-18T12:00:00Z', NULL),
    ('RDSLAB2026' || lpad('2', 16, '0'), 'Conta fictícia 02', 'rds-lab-02@example.invalid', 'LAB-SEM-CREDENCIAL-NAO-VALIDA', 'pending-confirmation', 1, NULL, NULL, 'America/Sao_Paulo', '2026-11-18T12:01:00Z', '2026-11-18T12:01:00Z', NULL),
    ('RDSLAB2026' || lpad('3', 16, '0'), 'Conta fictícia 03', 'rds-lab-03@example.invalid', 'LAB-SEM-CREDENCIAL-NAO-VALIDA', 'pending-confirmation', 1, NULL, NULL, 'America/Sao_Paulo', '2026-11-18T12:02:00Z', '2026-11-18T12:02:00Z', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO :"schema_name".learning_goals (
    id, account_id, title, description, created_at, updated_at
)
VALUES
    ('RDSLAB2026' || lpad('101', 16, '0'), 'RDSLAB2026' || lpad('1', 16, '0'), 'SQL básico', 'Meta fictícia para consultar e filtrar dados relacionais.', '2026-11-18T12:10:00Z', '2026-11-18T12:10:00Z'),
    ('RDSLAB2026' || lpad('102', 16, '0'), 'RDSLAB2026' || lpad('1', 16, '0'), 'Consultas SQL', 'Meta fictícia para praticar operadores e condições SQL.', '2026-11-18T12:11:00Z', '2026-11-18T12:11:00Z'),
    ('RDSLAB2026' || lpad('103', 16, '0'), 'RDSLAB2026' || lpad('2', 16, '0'), 'JOIN em SQL', 'Meta fictícia para relacionar linhas de tabelas SQL.', '2026-11-18T12:12:00Z', '2026-11-18T12:12:00Z'),
    ('RDSLAB2026' || lpad('104', 16, '0'), 'RDSLAB2026' || lpad('2', 16, '0'), 'PostgreSQL inicial', 'Meta fictícia para explorar os recursos do PostgreSQL.', '2026-11-18T12:13:00Z', '2026-11-18T12:13:00Z'),
    ('RDSLAB2026' || lpad('105', 16, '0'), 'RDSLAB2026' || lpad('3', 16, '0'), 'GROUP BY SQL', 'Meta fictícia para agrupar e somar resultados SQL.', '2026-11-18T12:14:00Z', '2026-11-18T12:14:00Z')
ON CONFLICT (id) DO NOTHING;

INSERT INTO :"schema_name".gamification_xp_grants (
    id, account_id, fact_id, amount, origin, occurred_at, granted_at
)
VALUES
    ('RDSLAB2026' || lpad('201', 16, '0'), 'RDSLAB2026' || lpad('1', 16, '0'), 'RDSLAB2026' || lpad('301', 16, '0'), 25, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('401', 16, '0'), 'label', 'Atividade SQL 01', 'goal_id', 'RDSLAB2026' || lpad('101', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('501', 16, '0')), '2026-11-18T13:00:00Z', '2026-11-18T13:00:01Z'),
    ('RDSLAB2026' || lpad('202', 16, '0'), 'RDSLAB2026' || lpad('1', 16, '0'), 'RDSLAB2026' || lpad('302', 16, '0'), 40, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('402', 16, '0'), 'label', 'Atividade SQL 02', 'goal_id', 'RDSLAB2026' || lpad('102', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('502', 16, '0')), '2026-11-18T13:01:00Z', '2026-11-18T13:01:01Z'),
    ('RDSLAB2026' || lpad('203', 16, '0'), 'RDSLAB2026' || lpad('1', 16, '0'), 'RDSLAB2026' || lpad('303', 16, '0'), 35, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('403', 16, '0'), 'label', 'Atividade PostgreSQL 01', 'goal_id', 'RDSLAB2026' || lpad('101', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('503', 16, '0')), '2026-11-18T13:02:00Z', '2026-11-18T13:02:01Z'),
    ('RDSLAB2026' || lpad('204', 16, '0'), 'RDSLAB2026' || lpad('1', 16, '0'), 'RDSLAB2026' || lpad('304', 16, '0'), 50, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('404', 16, '0'), 'label', 'Atividade SQL 03', 'goal_id', 'RDSLAB2026' || lpad('102', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('504', 16, '0')), '2026-11-18T13:03:00Z', '2026-11-18T13:03:01Z'),
    ('RDSLAB2026' || lpad('205', 16, '0'), 'RDSLAB2026' || lpad('2', 16, '0'), 'RDSLAB2026' || lpad('305', 16, '0'), 20, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('405', 16, '0'), 'label', 'Atividade JOIN 01', 'goal_id', 'RDSLAB2026' || lpad('103', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('505', 16, '0')), '2026-11-18T13:04:00Z', '2026-11-18T13:04:01Z'),
    ('RDSLAB2026' || lpad('206', 16, '0'), 'RDSLAB2026' || lpad('2', 16, '0'), 'RDSLAB2026' || lpad('306', 16, '0'), 60, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('406', 16, '0'), 'label', 'Atividade PostgreSQL 02', 'goal_id', 'RDSLAB2026' || lpad('104', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('506', 16, '0')), '2026-11-18T13:05:00Z', '2026-11-18T13:05:01Z'),
    ('RDSLAB2026' || lpad('207', 16, '0'), 'RDSLAB2026' || lpad('2', 16, '0'), 'RDSLAB2026' || lpad('307', 16, '0'), 45, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('407', 16, '0'), 'label', 'Atividade JOIN 02', 'goal_id', 'RDSLAB2026' || lpad('103', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('507', 16, '0')), '2026-11-18T13:06:00Z', '2026-11-18T13:06:01Z'),
    ('RDSLAB2026' || lpad('208', 16, '0'), 'RDSLAB2026' || lpad('2', 16, '0'), 'RDSLAB2026' || lpad('308', 16, '0'), 15, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('408', 16, '0'), 'label', 'Atividade SQL 04', 'goal_id', 'RDSLAB2026' || lpad('104', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('508', 16, '0')), '2026-11-18T13:07:00Z', '2026-11-18T13:07:01Z'),
    ('RDSLAB2026' || lpad('209', 16, '0'), 'RDSLAB2026' || lpad('3', 16, '0'), 'RDSLAB2026' || lpad('309', 16, '0'), 30, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('409', 16, '0'), 'label', 'Atividade GROUP BY 01', 'goal_id', 'RDSLAB2026' || lpad('105', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('509', 16, '0')), '2026-11-18T13:08:00Z', '2026-11-18T13:08:01Z'),
    ('RDSLAB2026' || lpad('210', 16, '0'), 'RDSLAB2026' || lpad('3', 16, '0'), 'RDSLAB2026' || lpad('310', 16, '0'), 55, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('410', 16, '0'), 'label', 'Atividade PostgreSQL 03', 'goal_id', 'RDSLAB2026' || lpad('105', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('510', 16, '0')), '2026-11-18T13:09:00Z', '2026-11-18T13:09:01Z'),
    ('RDSLAB2026' || lpad('211', 16, '0'), 'RDSLAB2026' || lpad('3', 16, '0'), 'RDSLAB2026' || lpad('311', 16, '0'), 25, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('411', 16, '0'), 'label', 'Atividade SQL 05', 'goal_id', 'RDSLAB2026' || lpad('105', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('511', 16, '0')), '2026-11-18T13:10:00Z', '2026-11-18T13:10:01Z'),
    ('RDSLAB2026' || lpad('212', 16, '0'), 'RDSLAB2026' || lpad('3', 16, '0'), 'RDSLAB2026' || lpad('312', 16, '0'), 75, json_build_object('source', 'activity', 'reference_id', 'RDSLAB2026' || lpad('412', 16, '0'), 'label', 'Atividade GROUP BY 02', 'goal_id', 'RDSLAB2026' || lpad('105', 16, '0'), 'skill_experience_id', 'RDSLAB2026' || lpad('512', 16, '0')), '2026-11-18T13:11:00Z', '2026-11-18T13:11:01Z')
ON CONFLICT (id) DO NOTHING;

COMMIT;
