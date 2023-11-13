from tests.models import User, UserInfo


def test_meta():
    user1 = User(name="Ax", age=15, info=UserInfo()).insert()
    assert user1.id == 0
    assert user1.age == 15
    assert user1.info.money == 200
    user2 = User(name="Axy", age=18, info=UserInfo(money=300)).insert()
    assert user2.id == 1
    assert user2.info.money == 300

    user3 = User(name="Az", age=20, info=UserInfo()).insert()
    assert user3.id == 2

    user4 = User(name="By", age=40, info=UserInfo(money=300)).insert()
    assert user4.id == 3


def test_query():
    assert (user1 := User.find_one(User.name == "Ax")) and user1.id == 0
    assert (user2 := User.find_one(User.name == "Axy")) and user2.id == 1

    assert len(User.find_all(User.name.startswith("Ax"))) == 2
    assert len(User.find_all(User.name.endswith("y"))) == 2

    assert len(User.find_all(User.age >= 18)) == 3
    assert len(User.find_all(User.age < 18)) == 1

    assert len(User.find_all(User.info.money == 300)) == 2
    assert len(User.find_all(User.info.money > 100)) == 4

    assert len(User.all()) == 4
    user2.delete()
    assert not User.find_one(User.name == "Axy")

    User.delete_by_id(3)
    assert len(User.all()) == 2

    user1.name = "qwe"
    user1.save()
    assert User.find_one(User.name == "qwe")
