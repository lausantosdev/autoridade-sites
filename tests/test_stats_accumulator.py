"""Testes do StatsAccumulator."""
import pytest
import threading
from core.stats_accumulator import StatsAccumulator


class TestStatsAccumulator:
    def test_projection_90_pages(self):
        acc = StatsAccumulator()
        proj = acc.get_projection(90, 30)
        assert proj['total_pages'] == 90
        # Tempo: entre 1 e 3 minutos (tolerância ampla)
        assert 60 <= proj['estimated_time_s'] <= 180
        # Custo: entre R$ 0,50 e R$ 1,50
        assert 0.50 <= proj['estimated_cost_brl'] <= 1.50

    def test_record_accumulates_by_provider(self):
        acc = StatsAccumulator()
        acc.record('gemini', 1000, 2000)
        acc.record('gemini', 1100, 2500)
        acc.record('openai', 900, 1800)

        summary = acc.get_summary()
        assert summary['gemini']['pages'] == 2
        assert summary['gemini']['input_tokens'] == 2100
        assert summary['openai']['pages'] == 1
        assert summary['total']['pages'] == 3

    def test_live_cost_increases(self):
        acc = StatsAccumulator()
        cost_0 = acc.get_live_cost()
        acc.record('gemini', 1100, 2450)
        cost_1 = acc.get_live_cost()
        assert cost_1 > cost_0

    def test_thread_safety(self):
        acc = StatsAccumulator()
        def record_many():
            for _ in range(100):
                acc.record('gemini', 1100, 2450)

        threads = [threading.Thread(target=record_many) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        summary = acc.get_summary()
        assert summary['gemini']['pages'] == 1000  # 10 threads × 100 registros

    def test_unknown_provider_ignored(self):
        acc = StatsAccumulator()
        acc.record('provider_invalido', 1000, 2000)  # não deve lançar, apenas logar warning
        summary = acc.get_summary()
        assert summary['total']['pages'] == 0
