"""The test-database guard: integration tests must never touch real data."""

import pytest

from tests.db.harness import UnsafeTestDatabaseError, check_test_database_url


SERVER = "postgresql+psycopg2://postgres:postgres@localhost:5434"
APP_URL = f"{SERVER}/exam_engine_db"


def test_accepts_a_dedicated_test_database():
    url = check_test_database_url(f"{SERVER}/exam_engine_test", APP_URL)
    assert url.database == "exam_engine_test"
    assert url.port == 5434


@pytest.mark.parametrize(
    "name",
    [
        "exam_engine_db",  # the app's database
        "postgres",  # the server's maintenance database
        "exam_engine_testing",  # suffix must be exactly _test
        "test_exam_engine",  # prefix doesn't count
        "Exam_Engine_test",  # uppercase would need quoting
        'x_test"; DROP DATABASE exam_engine_db; --',
    ],
)
def test_rejects_names_without_the_test_suffix(name):
    with pytest.raises(UnsafeTestDatabaseError):
        check_test_database_url(f"{SERVER}/{name}", APP_URL)


def test_rejects_a_url_without_a_database():
    with pytest.raises(UnsafeTestDatabaseError):
        check_test_database_url(SERVER, APP_URL)


def test_rejects_the_apps_own_database_even_if_it_ends_in_test():
    with pytest.raises(UnsafeTestDatabaseError, match="DATABASE_URL"):
        check_test_database_url(
            f"{SERVER}/exam_engine_test", f"{SERVER}/exam_engine_test"
        )
