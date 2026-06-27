"""Divisional (varga) chart computation.

A varga maps an ecliptic longitude to a *new* sign according to a divisor D and
classical placement rules. Only the resulting sign matters for varga judgement
(the inner longitude is conventionally set to the mid-point of the mapped sign
so house allocation by whole-sign still works downstream).

Implemented vargas: D1, D7, D9, D10, D12, D60 - the ones used during
rectification (Navamsa for marriage, Saptamsa for children, Dasamsa for career,
Dwadasamsa for parents, Shashtiamsa as the finest karmic check).
"""
from __future__ import annotations

from ..core.constants import DEG_PER_SIGN, SIGN_QUALITY
from ..core.ephemeris import Position, norm360


def _sign_and_offset(longitude: float) -> tuple[int, float]:
    sign = int(longitude // DEG_PER_SIGN)
    offset = longitude % DEG_PER_SIGN
    return sign, offset


def _sign_to_longitude(sign_index: int) -> float:
    """Return the mid-degree (15°) of a sign so downstream math is stable."""
    return norm360(sign_index * DEG_PER_SIGN + 15.0)


def navamsa_sign(longitude: float) -> int:
    """D9 sign index (0=Aries). Each sign splits into 9 parts of 3°20'.

    The starting sign of the navamsa sequence depends on the element of the
    rasi: fire signs start from Aries, earth from Capricorn, air from Libra,
    water from Cancer (the classic movable-element rule).
    """
    sign, offset = _sign_and_offset(longitude)
    part = int(offset // (DEG_PER_SIGN / 9.0))  # 0..8
    start_by_element = {0: 0, 1: 9, 2: 6, 3: 3}  # fire, earth, air, water
    element = sign % 4
    start = start_by_element[element]
    return (start + part) % 12


def saptamsa_sign(longitude: float) -> int:
    """D7 sign index. Each sign into 7 parts of ~4°17'.

    Odd signs start from the same sign; even signs start from the 7th sign.
    """
    sign, offset = _sign_and_offset(longitude)
    part = int(offset // (DEG_PER_SIGN / 7.0))  # 0..6
    start = sign if sign % 2 == 0 else (sign + 6) % 12
    return (start + part) % 12


def dasamsa_sign(longitude: float) -> int:
    """D10 sign index. Each sign into 10 parts of 3°.

    Odd signs count from the same sign; even signs from the 9th sign.
    """
    sign, offset = _sign_and_offset(longitude)
    part = int(offset // (DEG_PER_SIGN / 10.0))  # 0..9
    start = sign if sign % 2 == 0 else (sign + 8) % 12
    return (start + part) % 12


def dwadasamsa_sign(longitude: float) -> int:
    """D12 sign index. Each sign into 12 parts of 2°30', counting from itself."""
    sign, offset = _sign_and_offset(longitude)
    part = int(offset // (DEG_PER_SIGN / 12.0))  # 0..11
    return (sign + part) % 12


def shashtiamsa_sign(longitude: float) -> int:
    """D60 sign index. Each sign into 60 parts of 0°30'.

    For odd signs count the parts forward from Aries; for even signs reverse.
    This is the standard Parashari D60 sign-derivation (deity assignment is
    omitted as only the sign is needed for rectification scoring).
    """
    sign, offset = _sign_and_offset(longitude)
    part = int(offset // (DEG_PER_SIGN / 60.0))  # 0..59
    if sign % 2 == 0:
        base = part % 12
    else:
        base = (11 - (part % 12))
    return (sign + base) % 12


def rasi_sign(longitude: float) -> int:
    return int(longitude // DEG_PER_SIGN)


_VARGA_FUNCS = {
    "D1": rasi_sign,
    "D7": saptamsa_sign,
    "D9": navamsa_sign,
    "D10": dasamsa_sign,
    "D12": dwadasamsa_sign,
    "D60": shashtiamsa_sign,
}


def varga_position(longitude: float, varga: str) -> Position:
    """Map a longitude into the requested varga, returned as a Position."""
    if varga not in _VARGA_FUNCS:
        raise ValueError(f"unsupported varga: {varga!r}")
    sign = _VARGA_FUNCS[varga](longitude)
    return Position(_sign_to_longitude(sign), 0.0)


def varga_sign_index(longitude: float, varga: str) -> int:
    if varga not in _VARGA_FUNCS:
        raise ValueError(f"unsupported varga: {varga!r}")
    return _VARGA_FUNCS[varga](longitude)
