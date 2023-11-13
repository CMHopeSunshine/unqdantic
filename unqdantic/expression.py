from dataclasses import dataclass
import operator
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
from typing_extensions import Self

T = TypeVar("T")

from .utils import generate_dict, merge_dicts, recursively_get_item

OperatorFunc = Callable[[Any, Any], Any]


class QueryPath(List[str]):
    def __init__(self, name: str, *args):
        super().__init__(args)
        self.name = name

    def __str__(self) -> str:
        return f"{self.name}." + ".".join(self)

    def __repr__(self) -> str:
        return self.__str__()


class QueryPathProxy:
    def __init__(self, parent_name: str, attr: str) -> None:
        self.parent_name = parent_name
        self.path = QueryPath(parent_name, attr)

    def __repr__(self) -> str:
        return f"{self.parent_name}." + ".".join(self.path)

    def __getattr__(self, name: str) -> Self:
        self.path.append(name)
        return self

    def __getitem__(self, name: str) -> Self:
        self.path.append(name)
        return self

    def startswith(self, other: Any):
        return Query(self.path, _startswith, other)

    def endswith(self, other: Any):
        return Query(self.path, _endswith, other)

    def __len__(self) -> "Query":
        return Query(self.path, _len, None)

    def __eq__(self, other: Any) -> "Query":
        return Query(self.path, operator.eq, other)

    def __ne__(self, other: Any) -> "Query":
        return Query(self.path, operator.ne, other)

    def __lt__(self, other: Any) -> "Query":
        return Query(self.path, operator.lt, other)

    def __le__(self, other: Any) -> "Query":
        return Query(self.path, operator.le, other)

    def __gt__(self, other: Any) -> "Query":
        return Query(self.path, operator.gt, other)

    def __ge__(self, other: Any) -> "Query":
        return Query(self.path, operator.ge, other)

    def __or__(self, other: Any) -> "Query":
        return Query(self.path, operator.or_, other)

    def __xor__(self, other: Any) -> "Query":
        return Query(self.path, operator.xor, other)

    def __add__(self, other: Any) -> "Query":
        return Query(self.path, operator.add, other)

    def __sub__(self, other: Any) -> "Query":
        return Query(self.path, operator.sub, other)

    def __neg__(self) -> "Query":
        return Query(self.path, _neg, None)

    def __pos__(self) -> "Query":
        return Query(self.path, _not, None)

    def __truediv__(self, other: Any) -> "Query":
        return Query(self.path, operator.truediv, other)

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class Query:
    left: Any
    operator: OperatorFunc
    right: Any

    def startswith(self, other: Any):
        return Query(self, _startswith, other)

    def endswith(self, other: Any):
        return Query(self, _endswith, other)

    def __len__(self) -> "Query":
        return Query(self, _len, None)

    def __eq__(self, other: Any) -> "Query":
        return Query(self, operator.eq, other)

    def __ne__(self, other: Any) -> "Query":
        return Query(self, operator.ne, other)

    def __lt__(self, other: Any) -> "Query":
        return Query(self, operator.lt, other)

    def __le__(self, other: Any) -> "Query":
        return Query(self, operator.le, other)

    def __gt__(self, other: Any) -> "Query":
        return Query(self, operator.gt, other)

    def __ge__(self, other: Any) -> "Query":
        return Query(self, operator.ge, other)

    def __xor__(self, other: Any) -> "Query":
        return Query(self, operator.xor, other)

    def __add__(self, other: Any) -> "Query":
        return Query(self, operator.add, other)

    def __sub__(self, other: Any) -> "Query":
        return Query(self, operator.sub, other)

    def __neg__(self) -> "Query":
        return Query(self, _neg, None)

    def __pos__(self) -> "Query":
        return Query(self, _not, None)

    def __truediv__(self, other: Any) -> "Query":
        return Query(self, operator.truediv, other)

    def __or__(self, other: Self) -> Self:
        return Query(self, operator.or_, other)

    def __and__(self, other: Self) -> Self:
        return Query(self, operator.and_, other)

    def __str__(self) -> str:
        return f"<{self.left}|{self.operator.__name__.strip('_')}|{self.right}>"

    def __repr__(self) -> str:
        return (
            f"Query({self.left!r}, {self.operator.__name__.strip('_')}, {self.right!r})"
        )

    def __call__(self, record: Dict[str, Any]) -> bool:
        if isinstance(self.left, Query):
            left = self.left(record)
        elif isinstance(self.left, QueryPath):
            left = recursively_get_item(record, self.left)
        else:
            left = self.left

        if isinstance(self.right, Query):
            right = self.right(record)
        elif isinstance(self.right, QueryPath):
            right = recursively_get_item(record, self.right)
        else:
            right = self.right

        return self.operator(left, right)

    @classmethod
    def merge(
        cls,
        expressions: Tuple[Union[Self, bool], ...],
        operator_func: Optional[OperatorFunc] = None,
    ) -> Self:
        if operator_func is None:
            operator_func = operator.and_
        if not isinstance(expressions[0], cls):
            raise TypeError("表达式必须是 Query 对象")
        if len(expressions) == 1:
            return expressions[0]
        e = expressions[0]
        for i in range(1, len(expressions)):
            if not isinstance(expressions[i], cls):
                raise TypeError("表达式必须是 Query 对象")
            e = Query(e, operator_func, expressions[i])
        return e

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        if isinstance(self.left, QueryPath) and isinstance(self.right, object):
            data = generate_dict({".".join(self.left): self.right})

        if isinstance(self.left, Query):
            key_data = self.left.to_dict()
            data = merge_dicts(data, key_data)

        if isinstance(self.right, Query):
            value_data = self.right.to_dict()
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


def _startswith(a: Any, b: Any) -> bool:
    return a.startswith(b)


def _endswith(a: Any, b: Any) -> bool:
    return a.endswith(b)


def _len(a: Any, b: Any):
    return len(a)


def in_(a: Any, b: Any) -> Query:
    return Query(a, _contains, b)


def not_in(a: Any, b: Any) -> Query:
    return Query(a, _not_contains, b)


def is_(a: Any, b: Any) -> Query:
    return Query(a, operator.is_, b)


def is_not(a: Any, b: Any) -> Query:
    return Query(a, operator.is_not, b)


def concat(a: Any, b: Any) -> Query:
    return Query(a, operator.concat, b)


__all__ = [
    "Query",
    "in_",
    "not_in",
    "is_",
    "is_not",
    "concat",
]
