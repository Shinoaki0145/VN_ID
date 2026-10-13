"""Version-specific card parsers and backward-compatible extraction facades."""
from vn_id.parser.base import BaseCardParser
from vn_id.parser.factory import CardParserFactory
from vn_id.parser.strategies import CCCD2021Parser, CanCuoc2024Parser
from vn_id.parser.front import FrontRuleExtractor
from vn_id.parser.back import BackRuleExtractor

__all__ = [
    "BaseCardParser", "CardParserFactory", "CCCD2021Parser", "CanCuoc2024Parser",
    "FrontRuleExtractor", "BackRuleExtractor",
]
