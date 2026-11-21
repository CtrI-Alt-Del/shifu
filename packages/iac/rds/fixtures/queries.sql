\set ON_ERROR_STOP on

-- Counts for the fictitious batch loaded by E02.
SELECT 'identity_accounts' AS tabela, COUNT(*) AS registros
FROM :"schema_name".identity_accounts
WHERE id LIKE 'RDSLAB2026%'
UNION ALL
SELECT 'learning_goals', COUNT(*)
FROM :"schema_name".learning_goals
WHERE id LIKE 'RDSLAB2026%'
UNION ALL
SELECT 'gamification_xp_grants', COUNT(*)
FROM :"schema_name".gamification_xp_grants
WHERE id LIKE 'RDSLAB2026%'
ORDER BY tabela;

-- E03: filtro de metas com SQL no título.
SELECT id, title, created_at
FROM :"schema_name".learning_goals
WHERE title ILIKE '%SQL%'
ORDER BY created_at, id;

-- E03: JOIN de contas com histórico fictício de XP.
SELECT a.display_name, x.amount, x.origin->>'label' AS origem
FROM :"schema_name".identity_accounts AS a
JOIN :"schema_name".gamification_xp_grants AS x ON x.account_id = a.id
ORDER BY a.display_name, x.occurred_at, x.id;

-- E03: agregação de concessões e XP por conta.
SELECT a.display_name, COUNT(*) AS concessoes, SUM(x.amount) AS total_xp
FROM :"schema_name".identity_accounts AS a
JOIN :"schema_name".gamification_xp_grants AS x ON x.account_id = a.id
GROUP BY a.id, a.display_name
ORDER BY total_xp DESC, a.display_name;
