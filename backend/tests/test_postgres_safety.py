import pytest

from app.scripts.postgres_safety import destructive_test_database_url


TEST = "postgresql+psycopg://ci:fake@localhost:5432/stockflow_test"


@pytest.mark.parametrize("env, message", [
    ({"TEST_POSTGRES_URL": TEST}, "ALLOW_DESTRUCTIVE"),
    ({"ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "true"}, "TEST_POSTGRES_URL"),
    ({"TEST_POSTGRES_URL": TEST, "DATABASE_URL": TEST, "ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "true"}, "must not"),
    ({"TEST_POSTGRES_URL": TEST, "DATABASE_URL": "postgresql://other:other@localhost/stockflow_test",
      "ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "true"}, "must not"),
])
def test_destructive_database_guard_refuses_unsafe_configuration(env, message):
    with pytest.raises(RuntimeError, match=message):
        destructive_test_database_url(env)


def test_destructive_database_guard_allows_separate_database():
    env = {"TEST_POSTGRES_URL": TEST, "DATABASE_URL": "postgresql://app:fake@localhost/stockflow_app",
           "ALLOW_DESTRUCTIVE_POSTGRES_TESTS": "true"}
    assert destructive_test_database_url(env) == TEST
