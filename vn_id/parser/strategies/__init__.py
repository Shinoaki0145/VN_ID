"""Card generation strategies."""
from vn_id.parser.strategies.cccd_2021 import CCCD2021Parser, UnknownCardParser
from vn_id.parser.strategies.can_cuoc_2024 import CanCuoc2024Parser

__all__ = ["CCCD2021Parser", "CanCuoc2024Parser", "UnknownCardParser"]
