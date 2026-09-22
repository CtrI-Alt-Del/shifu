def require_positive_curriculum_position(position: int) -> None:
    if position < 1:
        raise ValueError('Curriculum positions must be positive.')
