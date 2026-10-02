-- 1. SELECT com filtro: tentativas com nota igual ou superior a 80.
SELECT event_id, learner_id, resource_id, score, occurred_at
FROM learning_events
WHERE event_type = 'activity_submitted'
  AND score >= 80
ORDER BY occurred_at;

-- 2. JOIN: eventos com o nome e a turma do aprendiz.
SELECT l.display_name, l.cohort, e.event_type, e.resource_id, e.score
FROM learners AS l
JOIN learning_events AS e ON e.learner_id = l.learner_id
WHERE e.event_type = 'activity_submitted'
ORDER BY l.display_name, e.occurred_at;

-- 3. GROUP BY: total de eventos e média de notas por tipo.
SELECT event_type, COUNT(*) AS event_count, ROUND(AVG(score), 2) AS average_score
FROM learning_events
GROUP BY event_type
ORDER BY event_count DESC, event_type;
