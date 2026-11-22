"""English words and their Portuguese translations shared by the pair fakers."""

WORDS = ('dog', 'house', 'water', 'book', 'tree', 'sun', 'moon', 'star')
TRANSLATIONS = (
    'cachorro',
    'casa',
    'agua',
    'livro',
    'arvore',
    'sol',
    'lua',
    'estrela',
)
MAX_FAKE_PAIRS = len(WORDS)


def rotated_order(size: int) -> tuple[int, ...]:
    """A display order that never mirrors the answer key by position."""
    return tuple((index + 1) % size for index in range(size))
