import copy
import json
from pathlib import Path
import unittest

from phiage.evidence import EvidenceError, audit, digest, validate
from phiage.simulation import simulate

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "synthetic-evidence.json"

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_valid(self):
        self.assertEqual(len(validate(self.bundle)["hypotheses"]), 2)

    def test_fixture_does_not_count_as_empirical(self):
        report = audit(self.bundle)
        self.assertEqual(len(report["hypotheses"]), 2)
        for result in report["hypotheses"]:
            self.assertEqual(result["stage"], "no-empirical-evidence")
            self.assertEqual(result["independence_groups"], 0)

    def test_duplicate_id_rejected(self):
        self.bundle["evidence"].append(copy.deepcopy(self.bundle["evidence"][0]))
        with self.assertRaises(EvidenceError):
            validate(self.bundle)

    def test_non_synthetic_requires_source(self):
        self.bundle["evidence"][0]["synthetic"] = False
        with self.assertRaises(EvidenceError):
            validate(self.bundle)

    def test_repeat_publications_same_group_count_once(self):
        e = self.bundle["evidence"][0]
        e.update(synthetic=False, source_url="https://example.org/study-a")
        duplicate = copy.deepcopy(e)
        duplicate.update(id="REAL-A2", source_url="https://example.org/study-a-secondary")
        self.bundle["evidence"] = [e, duplicate]
        result = audit(self.bundle)["hypotheses"][0]
        self.assertEqual(result["independence_groups"], 1)
        self.assertEqual(result["supporting_groups"], 1)
        self.assertEqual(result["stage"], "needs-independent-replication")

    def test_conflict_is_visible(self):
        a = self.bundle["evidence"][0]
        b = self.bundle["evidence"][2]
        for x in (a, b):
            x["synthetic"] = False
            x["source_url"] = "https://example.org/" + x["id"]
        self.bundle["evidence"] = [a, b]
        result = audit(self.bundle)["hypotheses"][0]
        self.assertEqual(result["stage"], "contested")
        self.assertEqual(result["contradicting_groups"], 1)

    def test_deterministic_digest(self):
        shuffled = dict(reversed(list(self.bundle.items())))
        self.assertEqual(digest(self.bundle), digest(shuffled))

class ToyModelTests(unittest.TestCase):
    def test_deterministic_bounded(self):
        result = simulate(steps=20)
        self.assertEqual(result, simulate(steps=20))
        self.assertEqual(len(result["series"]), 21)
        for row in result["series"]:
            for key in ("damage", "inflammation", "senescence", "repair_capacity"):
                self.assertGreaterEqual(row[key], 0)
                self.assertLessEqual(row[key], 1)

    def test_stronger_repair_reduces_toy_damage(self):
        low = simulate(steps=50, boost=0)["series"][-1]["damage"]
        high = simulate(steps=50, boost=0.5)["series"][-1]["damage"]
        self.assertLessEqual(high, low)

    def test_invalid_params(self):
        for kwargs in ({"steps": 0}, {"generation": float("nan")}, {"boost": -0.1}):
            with self.assertRaises(ValueError):
                simulate(**kwargs)

if __name__ == "__main__":
    unittest.main()
