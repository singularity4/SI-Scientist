"""Tests for the promotion rule and for FolderState.promote_champion."""

import tempfile
import unittest
from pathlib import Path

from scorer.run_algorithm import DatasetResult, promotes
from system.helper import FolderState


def result_with(improvements):
    """A result that satisfies every criterion, with the given improvement per dataset."""
    results = {
        dataset: DatasetResult(
            dataset=dataset, sigma=1.0, accuracy_mean=80.0, accuracy_sd=1.0, n_restarts=8,
            n_iter_mean=10.0, checks={"finite": 8, "nonneg": 8, "monotone": 8},
            paired={"champion_mean": 80.0 - delta, "delta_mean": delta, "delta_sd": 1.0})
        for dataset, delta in improvements.items()
    }
    return {"_results": results}


class PromotionRule(unittest.TestCase):
    def test_average_improvement_decides(self):
        self.assertTrue(promotes(result_with({"synthetic": 4.0, "moons": -1.0}))[0])
        self.assertTrue(promotes(result_with({"synthetic": 2.0, "moons": 1.0}))[0])
        self.assertFalse(promotes(result_with({"synthetic": 1.0, "moons": -2.0}))[0])
        self.assertFalse(promotes(result_with({"synthetic": 1.0, "moons": -1.0}))[0])

    def test_a_failed_criterion_rejects_despite_improvement(self):
        result = result_with({"synthetic": 4.0, "moons": 4.0})
        result["_results"]["moons"].checks["monotone"] = 7
        promoted, reason = promotes(result)
        self.assertFalse(promoted)
        self.assertIn("monotone", reason)


class ChampionPromotion(unittest.TestCase):
    def test_writes_code_and_record(self):
        with tempfile.TemporaryDirectory() as directory:
            state = FolderState(Path(directory))
            record = {"name": "candidate", "module": "champion/algorithm.py",
                      "objective": "measured objective", "derivation": {}}
            source = "UPDATE = None\nOBJECTIVE = None\nPARAMS = {}\n"
            state.promote_champion(record, source)
            self.assertEqual(state.read_champion(), record)
            self.assertEqual((Path(directory) / "champion/algorithm.py").read_text(), source)

    def test_invalid_code_leaves_champion_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            state = FolderState(Path(directory))
            record = {"name": "good", "module": "champion/algorithm.py"}
            source = "UPDATE = None\n"
            state.promote_champion(record, source)
            with self.assertRaises(SyntaxError):
                state.promote_champion({"name": "bad", "module": "champion/algorithm.py"},
                                       "def broken(\n")
            self.assertEqual(state.read_champion(), record)
            self.assertEqual((Path(directory) / "champion/algorithm.py").read_text(), source)

    def test_rejects_accuracy_in_record(self):
        with tempfile.TemporaryDirectory() as directory:
            state = FolderState(Path(directory))
            with self.assertRaises(ValueError):
                state.promote_champion(
                    {"module": "champion/algorithm.py", "accuracy": {}},
                    "UPDATE = None\n")


if __name__ == "__main__":
    unittest.main()
