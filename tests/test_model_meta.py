from tests.database import database
from tests.models import User
from unqdantic.meta import MetaConfig


def test_meta():
    assert User.__fields__.keys() == {"id", "name", "age", "info"}
    assert issubclass(User.meta, MetaConfig)
    assert User.meta.db is database
    assert User.meta.name == "user"
