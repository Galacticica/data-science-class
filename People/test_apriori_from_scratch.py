"""
===============================================================================
Unit Tests for Apriori Algorithm
-------------------------------------------------------------------------------
Author: Marcus Gubanyi
Date: September 10, 2026

Description:
Unit tests for the Apriori algorithm implementation. These tests verify
the correctness of candidate generation, frequency counting, subset
generation, association rule derivation, and the overall Apriori process.
===============================================================================
"""

import unittest

from apriori_from_scratch import (
    itemset_key,
    count_candidate_frequencies,
    generate_candidates,
    generate_nonempty_proper_subsets,
    generate_association_rules,
    apriori,
)


class TestItemsetKey(unittest.TestCase):

    def test_sorts_items(self):
        result = itemset_key({"B", "A", "C"})
        self.assertEqual(result, ("A", "B", "C"))


class TestCountCandidateFrequencies(unittest.TestCase):

    def test_frequency_counting(self):
        transactions = [
            {"A", "B"},
            {"A"},
            {"A", "C"},
            {"B", "C"},
        ]

        candidates = {
            frozenset({"A"}),
            frozenset({"B"}),
            frozenset({"A", "B"})
        }

        frequencies = count_candidate_frequencies(
            transactions,
            candidates
        )

        self.assertEqual(frequencies[frozenset({"A"})], 3)
        self.assertEqual(frequencies[frozenset({"B"})], 2)
        self.assertEqual(frequencies[frozenset({"A", "B"})], 1)


class TestGenerateCandidates(unittest.TestCase):

    def test_generate_size_two_candidates(self):
        frequent_itemsets = [
            (frozenset({"A"}), 4),
            (frozenset({"B"}), 3),
            (frozenset({"C"}), 2),
        ]

        candidates = generate_candidates(
            frequent_itemsets,
            next_size=2
        )

        expected = {
            frozenset({"A", "B"}),
            frozenset({"A", "C"}),
            frozenset({"B", "C"})
        }

        self.assertEqual(candidates, expected)

    def test_candidate_pruning(self):
        frequent_itemsets = [
            (frozenset({"A", "B"}), 4),
            (frozenset({"A", "C"}), 4),
            (frozenset({"B", "C"}), 4),
        ]

        candidates = generate_candidates(
            frequent_itemsets,
            next_size=3
        )

        self.assertIn(
            frozenset({"A", "B", "C"}),
            candidates
        )


class TestGenerateSubsets(unittest.TestCase):

    def test_nonempty_proper_subsets(self):
        itemset = frozenset({"A", "B", "C"})

        subsets = generate_nonempty_proper_subsets(itemset)

        expected_count = 6

        self.assertEqual(len(subsets), expected_count)

        self.assertIn(frozenset({"A"}), subsets)
        self.assertIn(frozenset({"B"}), subsets)
        self.assertIn(frozenset({"C"}), subsets)

        self.assertIn(frozenset({"A", "B"}), subsets)
        self.assertIn(frozenset({"A", "C"}), subsets)
        self.assertIn(frozenset({"B", "C"}), subsets)


class TestGenerateAssociationRules(unittest.TestCase):

    def test_rule_generation(self):
        frequent_counts = {
            frozenset({"A"}): 4,
            frozenset({"B"}): 3,
            frozenset({"A", "B"}): 2,
        }

        rules = generate_association_rules(
            frequent_counts,
            transaction_count=5
        )

        self.assertEqual(len(rules), 2)

        rule_found = False

        for antecedent, consequent, support, confidence, lift in rules:

            if antecedent == ("A",) and consequent == ("B",):
                rule_found = True

                self.assertAlmostEqual(
                    support,
                    2 / 5
                )

                self.assertAlmostEqual(
                    confidence,
                    2 / 4
                )

        self.assertTrue(rule_found)


class TestApriori(unittest.TestCase):

    def test_apriori_finds_rules(self):

        transactions = [
            {"A", "B"},
            {"A", "B"},
            {"A", "C"},
            {"A", "B", "C"},
            {"B", "C"},
        ]

        rules = apriori(
            transactions,
            min_frequency=2
        )

        self.assertGreater(len(rules), 0)

    def test_empty_transactions(self):

        rules = apriori(
            [],
            min_frequency=2
        )

        self.assertEqual(rules, [])

    def test_contains_expected_rule(self):

        transactions = [
            {"A", "B"},
            {"A", "B"},
            {"A", "B"},
            {"A"},
            {"B"},
        ]

        rules = apriori(
            transactions,
            min_frequency=2
        )

        found = False

        for antecedent, consequent, support, confidence, lift in rules:

            if antecedent == ("A",) and consequent == ("B",):
                found = True

        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
