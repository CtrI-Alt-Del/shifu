from typing import Final

# The pages the web app can report, keyed by its route name. The Mentor only ever
# receives these fixed labels, never text sent by the browser.
MENTOR_PAGE_LABELS: Final[dict[str, str]] = {
    'dashboard': 'Início, com os seus Objetivos',
    'root': 'Início, com os seus Objetivos',
    'curriculum': 'Currículo',
    'learning': 'Aprendizado',
    'learningGoalsNew': 'Criação de um novo Objetivo',
    'learningGoal': 'Página de um Objetivo',
    'learningSkill': 'Página de uma Habilidade',
    'learningGoalSkillsAdd': 'Adição de Habilidades a um Objetivo',
    'learningCompetency': 'Página de uma Competência',
    'learningActivity': 'Atividade',
    'learningAttempt': 'Resultado de uma tentativa de Atividade',
    'learningDiagnosticResult': 'Resultado do diagnóstico de uma Habilidade',
    'gamification': 'Progresso',
    'gamificationOverview': 'Progresso, visão geral',
    'gamificationCalendar': 'Progresso, calendário da sequência',
    'gamificationAchievements': 'Progresso, conquistas',
    'gamificationXpHistory': 'Progresso, histórico de XP',
    'intelligence': 'Mentor',
    'intelligenceMemories': 'Memórias do Mentor',
    'intelligencePlanner': 'Planejamento de Objetivo com IA',
    'account': 'Sua conta',
    'accountProfile': 'Conta, perfil',
    'accountSecurity': 'Conta, segurança',
    'accountAiUsage': 'Conta, uso de IA',
    'accountDelete': 'Conta, exclusão da conta',
}


def mentor_page_label(page: str | None) -> str | None:
    return MENTOR_PAGE_LABELS.get(page) if page is not None else None
