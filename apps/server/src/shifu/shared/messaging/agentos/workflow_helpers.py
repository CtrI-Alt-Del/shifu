from typing import cast


def copy_agent[Component](agent: Component) -> Component:
    """Copy a model-backed Agent when possible, retaining lightweight test doubles."""
    copier = getattr(agent, 'deep_copy', None)
    if not callable(copier):
        return agent
    return cast('Component', copier())
