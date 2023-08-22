from dataclasses import dataclass
import operator
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING, Union
from typing_extensions import Self

from pydantic.fields import ModelField

if TYPE_CHECKING:
    from .models import Document

from .utils import generate_dict, merge_dicts, recursively_get_item

OperatorFunc = Callable[[Any, Any], Any]


class ExpressionField:
    def __init__(
        self,
        field: ModelField,
        parents: List[Tuple[str, "Document"]],
    ) -> None:
        self.field = field
        self.parents = parents

    def __eq__(self, other: Any) -> "Expression":
        return Expression(self, operator.eq, other)

    def __ne__(self, other: Any) -> "Expression":
        return Expression(self, operator.ne, other)

    def __lt__(self, other: Any) -> "Expression":
        return Expression(self, operator.lt, other)

    def __le__(self, other: Any) -> "Expression":
        return Expression(self, operator.le, other)

    def __gt__(self, other: Any) -> "Expression":
        return Expression(self, operator.gt, other)

    def __ge__(self, other: Any) -> "Expression":
        return Expression(self, operator.ge, other)

    def __or__(self, other: Any) -> "Expression":
        return Expression(self, operator.or_, other)

    def __xor__(self, other: Any) -> "Expression":
        return Expression(self, operator.xor, other)

    def __add__(self, other: Any) -> "Expression":
        return Expression(self, operator.add, other)

    def __sub__(self, other: Any) -> "Expression":
        return Expression(self, operator.sub, other)

    def __neg__(self) -> "Expression":
        return Expression(self, _neg, None)

    def __pos__(self) -> "Expression":
        return Expression(self, _not, None)

    def __truediv__(self, other: Any) -> "Expression":
        return Expression(self, operator.truediv, other)

    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        return f"ExpressionField(name={str(self)}, type={self.field.type_.__name__})"

    def __str__(self) -> str:
        names = [p[0] for p in self.parents]
        names.append(
            (
                "__id"
                if self.field.field_info.extra.get("unqlite_pk")
                else self.field.name
            ),
        )
        return ".".join(names)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self.field.outer_type_, name)
        if isinstance(attr, self.__class__):
            new_parent = (self.field.name, self.field.outer_type_)
            if new_parent not in attr.parents:
                attr.parents.append(new_parent)
            if new_parents := list(set(self.parents) - set(attr.parents)):
                attr.parents = new_parents + attr.parents
        return attr


@dataclass
class Expression:
    key: Union[ExpressionField, "Expression"]
    operator: OperatorFunc
    value: Any

    def __or__(self, other: Self) -> Self:
        return Expression(self, operator.or_, other)

    def __and__(self, other: Self) -> Self:
        return Expression(self, operator.and_, other)

    def __repr__(self) -> str:
        return f"Expression({self.key}-{self.operator.__name__}-{self.value})"

    def to_filter_func(self, record: Dict[str, Any]) -> bool:
        if isinstance(self.key, Expression):
            key = self.key.to_filter_func(record)
        else:
            key = recursively_get_item(record, str(self.key).split("."))
        if isinstance(self.value, Expression):
            value = self.value.to_filter_func(record)
        elif isinstance(self.value, ExpressionField):
            value = recursively_get_item(record, str(self.value).split("."))
        else:
            value = self.value
        return self.operator(key, value)

    @classmethod
    def merge(
        cls,
        expressions: Tuple[Union[Self, bool], ...],
        operator_func: Optional[OperatorFunc] = None,
    ) -> Self:
        if operator_func is None:
            operator_func = operator.and_
        if not isinstance(expressions[0], cls):
            raise TypeError("表达式必须是 Expression 对象")
        if len(expressions) == 1:
            return expressions[0]
        e = expressions[0]
        for i in range(1, len(expressions)):
            if not isinstance(expressions[i], cls):
                raise TypeError("表达式必须是 Expression 对象")
            e = Expression(e, operator_func, expressions[i])
        return e

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        if isinstance(self.key, ExpressionField) and isinstance(self.value, object):
            data = generate_dict({str(self.key): self.value})

        if isinstance(self.key, Expression):
            key_data = self.key.to_dict()
            data = merge_dicts(data, key_data)

        if isinstance(self.value, Expression):
            value_data = self.value.to_dict()
            data = merge_dicts(data, value_data)

        return data


def _neg(a: Any, b: Any) -> bool:
    return -a


def _not(a: Any, b: Any) -> bool:
    return not a


def _contains(a: Any, b: Any) -> bool:
    return a in b


def _not_contains(a: Any, b: Any) -> bool:
    return a not in b


def in_(a: Any, b: Any) -> Expression:
    if not isinstance(a, (ExpressionField, Expression)):
        raise TypeError("表达式必须是 ExpressionField 或 Expression 对象")
    return Expression(a, _contains, b)


def not_in(a: Any, b: Any) -> Expression:
    if not isinstance(a, (ExpressionField, Expression)):
        raise TypeError("表达式必须是 ExpressionField 或 Expression 对象")
    return Expression(a, _not_contains, b)


def is_(a: Any, b: Any) -> Expression:
    if not isinstance(a, (ExpressionField, Expression)):
        raise TypeError("表达式必须是 ExpressionField 或 Expression 对象")
    return Expression(a, operator.is_, b)


def is_not(a: Any, b: Any) -> Expression:
    if not isinstance(a, (ExpressionField, Expression)):
        raise TypeError("表达式必须是 ExpressionField 或 Expression 对象")
    return Expression(a, operator.is_not, b)


def concat(a: Any, b: Any) -> Expression:
    if not isinstance(a, (ExpressionField, Expression)):
        raise TypeError("表达式必须是 ExpressionField 或 Expression 对象")
    return Expression(a, operator.concat, b)


__all__ = [
    "ExpressionField",
    "Expression",
    "in_",
    "not_in",
    "is_",
    "is_not",
    "concat",
]
