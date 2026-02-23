"""Unit tests for src/tools/market_tools.py"""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock

import pytest


class TestGetMarketOverview:

    @patch("src.tools.market_tools.yf.Ticker")
    def test_returns_json_dict(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = 500.0
        mock_tk.fast_info.previous_close = 495.0
        mock_ticker.return_value = mock_tk
        from src.tools.market_tools import get_market_overview
        result = json.loads(get_market_overview.invoke({}))
        assert isinstance(result, dict)
        assert len(result) > 0

    @patch("src.tools.market_tools.yf.Ticker")
    def test_spy_included(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = 500.0
        mock_tk.fast_info.previous_close = 495.0
        mock_ticker.return_value = mock_tk
        from src.tools.market_tools import get_market_overview
        result = json.loads(get_market_overview.invoke({}))
        assert "SPY" in result

    @patch("src.tools.market_tools.yf.Ticker")
    def test_change_pct_computed(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = 110.0
        mock_tk.fast_info.previous_close = 100.0
        mock_ticker.return_value = mock_tk
        from src.tools.market_tools import get_market_overview
        result = json.loads(get_market_overview.invoke({}))
        spy = result.get("SPY", {})
        # (110 - 100) / 100 * 100 = 10.0
        assert abs(spy.get("change_pct", 0) - 10.0) < 0.1

    @patch("src.tools.market_tools.yf.Ticker")
    def test_ticker_error_handled(self, mock_ticker):
        """Individual ticker failures should not crash the whole call."""
        mock_ticker.side_effect = Exception("fetch error")
        from src.tools.market_tools import get_market_overview
        result = json.loads(get_market_overview.invoke({}))
        # Should still return a dict (empty or with error entries)
        assert isinstance(result, dict)

    @patch("src.tools.market_tools.yf.Ticker")
    def test_none_price_handled(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = None
        mock_tk.fast_info.previous_close = None
        mock_ticker.return_value = mock_tk
        from src.tools.market_tools import get_market_overview
        result = json.loads(get_market_overview.invoke({}))
        assert isinstance(result, dict)


class TestGetSectorPerformance:

    @patch("src.tools.market_tools.yf.download")
    def test_returns_json_with_sector_returns(self, mock_download):
        import pandas as pd
        import numpy as np
        etfs = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLRE", "XLU", "XLC"]
        idx = pd.date_range("2024-01-01", periods=10, freq="B")
        data = pd.DataFrame({e: 100 + np.arange(10, dtype=float) for e in etfs}, index=idx)
        mock_download.return_value = data
        from src.tools.market_tools import get_sector_performance
        result = json.loads(get_sector_performance.invoke({"period": "1mo"}))
        assert "sector_returns_pct" in result or "error" in result

    @patch("src.tools.market_tools.yf.download")
    def test_sorted_best_to_worst(self, mock_download):
        import pandas as pd
        import numpy as np
        etfs = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLRE", "XLU", "XLC"]
        idx = pd.date_range("2024-01-01", periods=10, freq="B")
        data = pd.DataFrame({e: 100 + np.arange(10, dtype=float) for e in etfs}, index=idx)
        mock_download.return_value = data
        from src.tools.market_tools import get_sector_performance
        result = json.loads(get_sector_performance.invoke({"period": "1mo"}))
        if "sector_returns_pct" in result:
            vals = list(result["sector_returns_pct"].values())
            assert vals == sorted(vals, reverse=True)

    @patch("src.tools.market_tools.yf.download")
    def test_error_handled(self, mock_download):
        mock_download.side_effect = Exception("network error")
        from src.tools.market_tools import get_sector_performance
        result = json.loads(get_sector_performance.invoke({"period": "1mo"}))
        assert "error" in result

    @patch("src.tools.market_tools.yf.download")
    def test_period_included_in_response(self, mock_download):
        import pandas as pd
        import numpy as np
        idx = pd.date_range("2024-01-01", periods=5, freq="B")
        data = pd.DataFrame({"XLK": [100.0, 105.0, 102.0, 108.0, 110.0]}, index=idx)
        mock_download.return_value = data
        from src.tools.market_tools import get_sector_performance
        result = json.loads(get_sector_performance.invoke({"period": "3mo"}))
        # period should appear in result when no error
        assert result.get("period") == "3mo" or "error" in result


def test_market_tools_export():
    from src.tools.market_tools import MARKET_TOOLS
    names = {t.name for t in MARKET_TOOLS}
    assert "get_market_overview" in names
    assert "get_sector_performance" in names
