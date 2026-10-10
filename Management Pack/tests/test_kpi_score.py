#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the scoring shared by every KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.kpi_score import Metric, score_metric, kpi_score
from metrics.cluster import cluster_performance_metrics, cluster_risk_metrics
from metrics.host import esxi_performance_metrics
from metrics.vm import vm_performance_metrics, guest_os_performance_metrics
from utils import ops_stats
from fakes import FakeSuiteApi

KPI_MODULES = [
    cluster_performance_metrics, vm_performance_metrics, guest_os_performance_metrics,
    cluster_risk_metrics, esxi_performance_metrics,
]

#                    name                 unit   best    green  yellow  orange  zero-at
CPU_READY   = Metric("CPU Ready",         "%",   0.0,    1.0,   2.0,    4.0,    8.0)      # lower is better
FREE_MEMORY = Metric("Guest Free Memory", "MB",  1024.0, 512.0, 256.0,  128.0,  0.0)      # higher is better
CPU_RUN     = Metric("CPU Run",           "%",   60.0,   80.0,  90.0,   95.0,   100.0)    # does not start at 0


# --- Lower is better --------------------------------------------------------

def test_score_at_each_tier_boundary():
    assert score_metric(CPU_READY, 0.0) == (100.0, 1.0)
    assert score_metric(CPU_READY, 1.0) == (75.0, 2.0)
    assert score_metric(CPU_READY, 2.0) == (50.0, 4.0)
    assert score_metric(CPU_READY, 4.0) == (25.0, 8.0)
    assert score_metric(CPU_READY, 8.0) == (0.0, 8.0)


def test_score_drops_in_a_straight_line_inside_a_tier():
    assert score_metric(CPU_READY, 0.5) == (87.5, 1.0)     # halfway through green
    assert score_metric(CPU_READY, 3.0) == (37.5, 4.0)     # halfway through orange
    assert score_metric(CPU_READY, 5.0) == (18.75, 8.0)    # a quarter of the way through red


def test_score_never_goes_below_zero_or_above_100():
    assert score_metric(CPU_READY, 500.0) == (0.0, 8.0)
    assert score_metric(CPU_READY, -1.0) == (100.0, 1.0)


# --- Higher is better -------------------------------------------------------

def test_higher_is_better_at_each_tier_boundary():
    assert score_metric(FREE_MEMORY, 1024.0) == (100.0, 1.0)
    assert score_metric(FREE_MEMORY, 512.0) == (75.0, 2.0)
    assert score_metric(FREE_MEMORY, 256.0) == (50.0, 4.0)
    assert score_metric(FREE_MEMORY, 128.0) == (25.0, 8.0)
    assert score_metric(FREE_MEMORY, 0.0) == (0.0, 8.0)


def test_higher_is_better_inside_a_tier_and_beyond_the_ends():
    assert score_metric(FREE_MEMORY, 768.0) == (87.5, 1.0)     # halfway through green
    assert score_metric(FREE_MEMORY, 192.0) == (37.5, 4.0)     # halfway through orange
    assert score_metric(FREE_MEMORY, 64.0) == (12.5, 8.0)      # halfway through red
    assert score_metric(FREE_MEMORY, 8192.0) == (100.0, 1.0)   # more than "best" is still 100


# --- A sub-metric whose "best" is not 0 -------------------------------------

def test_everything_up_to_best_scores_100():
    assert score_metric(CPU_RUN, 0.0) == (100.0, 1.0)
    assert score_metric(CPU_RUN, 60.0) == (100.0, 1.0)


def test_tiers_of_different_widths():
    assert score_metric(CPU_RUN, 70.0) == (87.5, 1.0)      # green is 20 wide
    assert score_metric(CPU_RUN, 80.0) == (75.0, 2.0)
    assert score_metric(CPU_RUN, 85.0) == (62.5, 2.0)      # yellow is 10 wide
    assert score_metric(CPU_RUN, 92.5) == (37.5, 4.0)      # orange is 5 wide
    assert score_metric(CPU_RUN, 97.5) == (12.5, 8.0)      # red is 5 wide
    assert score_metric(CPU_RUN, 100.0) == (0.0, 8.0)


# --- The KPI ----------------------------------------------------------------

def test_kpi_is_the_weighted_average():
    # CPU Ready = 5 scores 18.75 with weight 8. Free memory of 2 GB scores 100 with weight 1.
    # KPI = (18.75 x 8 + 100 x 1) / (8 + 1) = 250 / 9 = 27.78
    metrics = [CPU_READY, FREE_MEMORY]
    assert kpi_score(metrics, {"CPU Ready": 5.0, "Guest Free Memory": 2048.0}) == 27.78


def test_missing_metric_is_left_out():
    metrics = [CPU_READY, FREE_MEMORY]
    assert kpi_score(metrics, {"CPU Ready": 5.0, "Guest Free Memory": None}) == 18.75
    assert kpi_score(metrics, {"CPU Ready": 5.0}) == 18.75


def test_no_data_at_all_gives_no_kpi():
    assert kpi_score([CPU_READY, FREE_MEMORY], {}) is None


# --- Green as a single value ------------------------------------------------

#                    name           unit  best  green  yellow  orange  zero-at
BAD_PACKETS = Metric("Bad Packets", "%",  0.0,  0.0,   0.2,    0.4,    0.8)


def test_green_as_a_single_value():
    assert score_metric(BAD_PACKETS, 0.0) == (100.0, 1.0)      # only exactly 0 is green
    assert score_metric(BAD_PACKETS, 0.1) == (62.5, 2.0)       # halfway through yellow (0 to 0.2)
    assert score_metric(BAD_PACKETS, 0.2) == (50.0, 4.0)
    assert score_metric(BAD_PACKETS, 0.8) == (0.0, 8.0)


# --- Skip when green --------------------------------------------------------

#                         name             unit  best  green  yellow  orange  zero-at  skip-when-green
RARE_BALLOON  = Metric("Memory Ballooned", "%",  0.0,  1.0,   2.0,    4.0,    8.0,     True)


def test_skipped_while_green_so_no_free_pass():
    # Ballooning at 0.5 is green, so it is left out. Only CPU Ready counts.
    # Without the skip: (18.75 x 8 + 87.5 x 1) / 9 = 26.39. With it: 18.75.
    assert kpi_score([CPU_READY, RARE_BALLOON], {"CPU Ready": 5.0, "Memory Ballooned": 0.5}) == 18.75


def test_counts_once_it_leaves_green():
    # Ballooning at 3 is halfway through orange: 37.5 with weight 4. CPU Ready at 0: 100 with weight 1.
    # KPI = (37.5 x 4 + 100 x 1) / 5 = 50.0
    assert kpi_score([CPU_READY, RARE_BALLOON], {"CPU Ready": 0.0, "Memory Ballooned": 3.0}) == 50.0


def test_only_skipped_green_metrics_means_nothing_is_wrong():
    assert kpi_score([RARE_BALLOON], {"Memory Ballooned": 0.0}) == 100.0
    assert kpi_score([RARE_BALLOON], {"Memory Ballooned": None}) is None    # no data is still no KPI


# --- Every KPI table --------------------------------------------------------

def test_limits_of_every_sub_metric_go_one_way_only():
    for kpi in KPI_MODULES:
        for metric in kpi.METRICS:
            limits = [metric.best, metric.green, metric.yellow, metric.orange, metric.zero_at]
            # best and green may be equal: green is then a single value. The other limits must differ.
            going_up = limits[0] <= limits[1] and all(a < b for a, b in zip(limits[1:], limits[2:]))
            going_down = limits[0] >= limits[1] and all(a > b for a, b in zip(limits[1:], limits[2:]))
            assert going_up or going_down, f"{kpi.KPI_NAME}: {metric.name}"


def test_sub_metric_names_are_unique_and_published_ones_exist():
    for kpi in KPI_MODULES:
        names = [metric.name for metric in kpi.METRICS]
        assert len(names) == len(set(names)), kpi.KPI_NAME
        assert all(metric in kpi.METRICS for metric in kpi.PUBLISHED_METRICS), kpi.KPI_NAME


# --- Reading stats ----------------------------------------------------------

def test_stats_of_many_resources_are_read_in_batches(monkeypatch):
    monkeypatch.setattr(ops_stats, "RESOURCES_PER_REQUEST", 2)
    vm_ids = ["vm-0", "vm-1", "vm-2", "vm-3", "vm-4"]
    api = FakeSuiteApi({vm_id: {"cpu|usage_average": [1.0, float(number)]} for number, vm_id in enumerate(vm_ids)})

    stats = ops_stats.read_latest_stats(api, vm_ids, ["cpu|usage_average"])

    assert api.requests == 3                                # 2 + 2 + 1 VMs
    assert stats["vm-4"] == {"cpu|usage_average": 4.0}      # the newest sample
    assert len(stats) == 5


def test_nothing_to_ask_means_no_request():
    api = FakeSuiteApi({})
    assert ops_stats.read_latest_stats(api, [], ["cpu|usage_average"]) == {}
    assert api.requests == 0
