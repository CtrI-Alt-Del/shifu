class AppError(Exception):
    message: str = 'Erro interno da aplicação.'
    title: str = 'Erro interno da aplicação'

    def __init__(self, message: str | None = None, title: str | None = None) -> None:
        self.message = message or type(self).message
        self.title = title or type(self).title
        super().__init__(self.message)
