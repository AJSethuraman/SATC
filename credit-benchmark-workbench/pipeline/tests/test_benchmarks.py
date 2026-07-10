"""Stage 2: percentiles, suppression, coverage gaps, size buckets."""

import math

from ccbw.benchmarks import MIN_N, THIN_N, dist_stats, percentile
from ccbw.segments import size_bucket_for_ebitda


class TestPercentile:
    def test_median_odd(self):
        assert percentile([1, 2, 3, 4, 5], 50) == 3

    def test_median_even_interpolates(self):
        assert percentile([1, 2, 3, 4], 50) == 2.5

    def test_p90_interpolation(self):
        vals = list(range(1, 11))  # 1..10
        assert math.isclose(percentile(vals, 90), 9.1)

    def test_endpoints(self):
        vals = [5.0, 7.0, 9.0]
        assert percentile(vals, 0) == 5.0
        assert percentile(vals, 100) == 9.0


class TestDistStats:
    def test_below_min_n_suppressed(self):
        assert dist_stats([1.0] * (MIN_N - 1)) is None

    def test_nan_values_excluded(self):
        vals = [1.0, 2.0, 3.0, float("nan"), float("nan")]
        s = dist_stats(vals)
        assert s["n"] == 3

    def test_ordered_output(self):
        s = dist_stats([float(x) for x in range(1, 21)])
        assert s["p10"] <= s["p25"] <= s["p50"] <= s["p75"] <= s["p90"]
        assert s["n"] == 20


class TestSizeBuckets:
    def test_band_edges(self):
        assert size_bucket_for_ebitda(4.9e6) is None      # below modeled range
        assert size_bucket_for_ebitda(5e6) == "lmm"
        assert size_bucket_for_ebitda(24.9e6) == "lmm"
        assert size_bucket_for_ebitda(25e6) == "cmm"
        assert size_bucket_for_ebitda(100e6) == "umm"
        assert size_bucket_for_ebitda(300e6) == "large"

    def test_thin_threshold_sane(self):
        assert MIN_N < THIN_N
