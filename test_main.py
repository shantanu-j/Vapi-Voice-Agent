import pytest

if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [
                "tests/unit",
                "tests/integration",
                "-v",
            ]
        )
    )