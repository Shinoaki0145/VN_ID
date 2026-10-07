"""Validator and fusion package for VN_ID."""
from vn_id.validator.cccd_rules import CCCDValidator
from vn_id.validator.fuzzy_address import AddressFuzzyMatcher
from vn_id.validator.fusion import DataFusion

__all__ = ["CCCDValidator", "AddressFuzzyMatcher", "DataFusion"]

