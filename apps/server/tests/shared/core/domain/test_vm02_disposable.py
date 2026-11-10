# Disposable test for the SHIFU-87 VM-02 check. It covers only part of the code.
from shifu.shared.core.vm02_disposable import vm02_clamp, vm02_sign


def test_vm02_clamp_keeps_value_inside_range() -> None:
    assert vm02_clamp(5, 0, 10) == 5
    assert vm02_clamp(-1, 0, 10) == 0


def test_vm02_sign_returns_positive_sign() -> None:
    assert vm02_sign(3) == 1
