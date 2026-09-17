import types
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast, get_args, get_origin, get_type_hints


class Serialization:
    @staticmethod
    def serialize_value(value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if is_dataclass(value):
            return {
                field.name: Serialization.serialize_value(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, tuple | list):
            items = cast('tuple[object, ...] | list[object]', value)
            return [Serialization.serialize_value(item) for item in items]
        if isinstance(value, dict):
            items = cast('dict[object, object]', value)
            return {
                str(key): Serialization.serialize_value(item)
                for key, item in items.items()
            }
        return value

    @staticmethod
    def deserialize_value(value: object, target_type: object) -> object:  # noqa: C901
        if value is None:
            return None

        if target_type is Any or target_type is object:
            return value

        origin = get_origin(target_type)
        arguments = get_args(target_type)

        if origin in (types.UnionType,):
            errors: list[Exception] = []
            for argument in arguments:
                if argument is type(None):
                    continue
                try:
                    return Serialization.deserialize_value(value, argument)
                except (KeyError, TypeError, ValueError) as error:
                    errors.append(error)
            raise TypeError(
                f'Unable to deserialize {value!r} as {target_type!r}'
            ) from (errors[-1] if errors else None)

        if origin is tuple:
            item_type = arguments[0] if arguments else Any
            return tuple(
                Serialization.deserialize_value(item, item_type)
                for item in cast('list[object]', value)
            )

        if origin is list:
            item_type = arguments[0] if arguments else Any
            return [
                Serialization.deserialize_value(item, item_type)
                for item in cast('list[object]', value)
            ]

        if origin is dict:
            key_type = arguments[0] if arguments else Any
            value_type = arguments[1] if len(arguments) > 1 else Any
            return {
                Serialization.deserialize_value(
                    key, key_type
                ): Serialization.deserialize_value(item, value_type)
                for key, item in cast('dict[object, object]', value).items()
            }

        if target_type is datetime:
            return datetime.fromisoformat(cast('str', value))

        if target_type is Decimal:
            return Decimal(cast('str', value))

        if isinstance(target_type, type) and issubclass(target_type, Enum):
            return target_type(value)

        if isinstance(target_type, type) and is_dataclass(target_type):
            type_hints = get_type_hints(target_type)
            data = cast('dict[str, object]', value)
            return target_type(
                **{
                    field.name: Serialization.deserialize_value(
                        data[field.name], type_hints[field.name]
                    )
                    for field in fields(target_type)
                }
            )

        if isinstance(target_type, type):
            return target_type(value)

        return value
