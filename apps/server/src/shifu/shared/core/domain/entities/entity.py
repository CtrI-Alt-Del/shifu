from dataclasses import dataclass
from typing import dataclass_transform


def _entity_equal(self: object, other: object) -> bool:
    return type(self) is type(other) and object.__getattribute__(
        self, 'id'
    ) == object.__getattribute__(other, 'id')


def _entity_hash(self: object) -> int:
    return hash((type(self), object.__getattribute__(self, 'id')))


def _set_entity_attribute(self: object, name: str, value: object) -> None:
    if name == 'id':
        try:
            object.__getattribute__(self, name)
        except AttributeError:
            pass
        else:
            raise AttributeError("Entity attribute 'id' is immutable")

    object.__setattr__(self, name, value)


def _delete_entity_attribute(self: object, name: str) -> None:
    if name == 'id':
        raise AttributeError("Entity attribute 'id' is immutable")

    object.__delattr__(self, name)


@dataclass_transform(eq_default=False, kw_only_default=True)
def entity[EntityType](cls: type[EntityType]) -> type[EntityType]:
    entity_class = dataclass(cls, eq=False, kw_only=True, slots=True)
    entity_class.__eq__ = _entity_equal  # type: ignore[method-assign]
    entity_class.__hash__ = _entity_hash  # type: ignore[method-assign]
    entity_class.__setattr__ = _set_entity_attribute  # type: ignore[method-assign]
    entity_class.__delattr__ = _delete_entity_attribute  # type: ignore[method-assign]
    return entity_class
