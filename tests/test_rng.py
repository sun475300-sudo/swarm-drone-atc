"""src.utils.rng 전역 RNG 모듈 테스트"""
import numpy as np
import pytest

from src.utils.rng import get_current_seed, get_rng, reset_for_test, set_global_seed

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_rng_state():
    """각 테스트 전후로 RNG 상태를 초기화한다."""
    reset_for_test()
    yield
    reset_for_test()


class TestSetGlobalSeed:
    def test_basic_seed(self):
        set_global_seed(42)
        rng = get_rng()
        assert isinstance(rng, np.random.Generator)

    def test_seed_zero(self):
        set_global_seed(0)
        assert get_current_seed() == 0

    def test_negative_seed_raises(self):
        with pytest.raises(ValueError, match="seed must be >= 0"):
            set_global_seed(-1)

    def test_determinism(self):
        set_global_seed(99)
        v1 = get_rng().random()
        set_global_seed(99)
        v2 = get_rng().random()
        assert v1 == pytest.approx(v2)

    def test_different_seeds_different_values(self):
        set_global_seed(1)
        v1 = get_rng().random()
        set_global_seed(2)
        v2 = get_rng().random()
        assert v1 != v2


class TestGetRng:
    def test_raises_before_seed(self):
        with pytest.raises(RuntimeError, match="set_global_seed"):
            get_rng()

    def test_returns_generator_after_seed(self):
        set_global_seed(10)
        assert isinstance(get_rng(), np.random.Generator)

    def test_same_instance_each_call(self):
        set_global_seed(5)
        assert get_rng() is get_rng()


class TestGetCurrentSeed:
    def test_raises_before_seed(self):
        with pytest.raises(RuntimeError, match="set_global_seed"):
            get_current_seed()

    def test_returns_correct_seed(self):
        set_global_seed(123)
        assert get_current_seed() == 123

    def test_updates_on_re_seed(self):
        set_global_seed(1)
        set_global_seed(7)
        assert get_current_seed() == 7


class TestResetForTest:
    def test_clears_rng(self):
        set_global_seed(42)
        reset_for_test()
        with pytest.raises(RuntimeError):
            get_rng()

    def test_clears_seed(self):
        set_global_seed(42)
        reset_for_test()
        with pytest.raises(RuntimeError):
            get_current_seed()

    def test_idempotent(self):
        reset_for_test()
        reset_for_test()
        with pytest.raises(RuntimeError):
            get_rng()
