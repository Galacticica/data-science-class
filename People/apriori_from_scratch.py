"""
===============================================================================
Apriori Algorithm
-------------------------------------------------------------------------------
Author: Marcus Gubanyi
Date: September 10, 2026

Description:
This program implements the Apriori algorithm for discovering frequent
itemsets and generating association rules from a collection of transactions.
The implementation is written from scratch using only native Python data
structures such as sets, lists, dictionaries, and tuples.

The algorithm proceeds by:
1. Generating candidate itemsets of increasing size.
2. Counting their frequencies within the transaction database.
3. Identifying frequent itemsets that satisfy a minimum frequency threshold.
4. Applying the Apriori principle to prune invalid candidates.
5. Generating association rules from the discovered frequent itemsets.
6. Computing support, confidence, and lift for each rule.

Input:
    - A list of transactions, where each transaction is represented as a set.
    - A minimum frequency threshold.

Output:
    - A list of association rules represented as:
      (antecedent, consequent, support, confidence, lift)
===============================================================================
"""

def itemset_key(itemset):
    """Return a consistently ordered tuple for an itemset."""
    return tuple(sorted(itemset, key=lambda item: str(item)))


def count_candidate_frequencies(transactions, candidates):
    """
    Count how many transactions contain each candidate itemset.

    Returns:
        Dictionary mapping candidate frozensets to frequency counts.
    """
    frequencies = {candidate: 0 for candidate in candidates}

    for transaction in transactions:
        for candidate in candidates:
            if candidate.issubset(transaction):
                frequencies[candidate] += 1

    return frequencies


def generate_candidates(frequent_itemsets, next_size):
    """
    Generate candidate itemsets of size next_size.

    Two frequent itemsets of size next_size - 1 are joined when their
    first next_size - 2 items match. A candidate is retained only when
    all of its subsets of size next_size - 1 are frequent.
    """
    frequent_sets = [itemset for itemset, frequency in frequent_itemsets]
    frequent_lookup = set(frequent_sets)
    ordered_sets = [itemset_key(itemset) for itemset in frequent_sets]

    candidates = set()

    for i in range(len(ordered_sets)):
        for j in range(i + 1, len(ordered_sets)):
            left = ordered_sets[i]
            right = ordered_sets[j]

            # Join step: the first next_size - 2 items must match.
            if left[:next_size - 2] != right[:next_size - 2]:
                continue

            candidate = frozenset(left) | frozenset(right)

            if len(candidate) != next_size:
                continue

            # Prune step: every subset of size next_size - 1
            # must already be frequent.
            keep_candidate = True

            for item in candidate:
                subset = candidate - {item}

                if subset not in frequent_lookup:
                    keep_candidate = False
                    break

            if keep_candidate:
                candidates.add(candidate)

    return candidates


def generate_nonempty_proper_subsets(itemset):
    """
    Generate every nonempty proper subset.
    """
    items = list(itemset)
    subsets = []

    # Binary masks enumerate all possible subsets.
    # Skip 0, the empty set, and 2^n - 1, the full set.
    for mask in range(1, (2 ** len(items)) - 1):
        subset = set()

        for position in range(len(items)):
            if mask & (1 << position):
                subset.add(items[position])

        subsets.append(frozenset(subset))

    return subsets


def generate_association_rules(frequent_counts, transaction_count):
    """
    Generate all possible association rules from the frequent itemsets.

    Each returned rule is:
        (
            antecedent,
            consequent,
            support,
            confidence,
            lift
        )

    Antecedents and consequents are returned as ordered tuples.
    """
    association_rules = []

    for itemset, itemset_frequency in frequent_counts.items():
        if len(itemset) < 2:
            continue

        antecedents = generate_nonempty_proper_subsets(itemset)

        for antecedent in antecedents:
            consequent = itemset - antecedent

            antecedent_frequency = frequent_counts[antecedent]
            consequent_frequency = frequent_counts[consequent]

            support = itemset_frequency / transaction_count
            confidence = itemset_frequency / antecedent_frequency
            consequent_support = consequent_frequency / transaction_count
            lift = confidence / consequent_support

            rule = (
                itemset_key(antecedent),
                itemset_key(consequent),
                support,
                confidence,
                lift
            )

            association_rules.append(rule)

    return association_rules


def apriori(transactions, min_frequency):
    """
    Run the Apriori algorithm.

    Parameters:
        transactions:
            A list of sets. Each set contains the items in one transaction.

        min_frequency:
            The minimum number of transactions in which an itemset
            must appear to be considered frequent.

    Returns:
        A list of association rules. Each rule has the form:

        (
            antecedent,
            consequent,
            support,
            confidence,
            lift
        )
    """
    if not transactions:
        return []

    transactions = [set(transaction) for transaction in transactions]

    # Collect all individual items.
    all_items = set()

    for transaction in transactions:
        all_items.update(transaction)

    # Initial candidates are all itemsets of size 1.
    candidates = {frozenset({item}) for item in all_items}

    itemset_size = 1

    # Stores every frequent itemset and its frequency.
    frequent_counts = {}

    while candidates:
        candidate_frequencies = count_candidate_frequencies(
            transactions,
            candidates
        )

        frequent_itemsets = []

        for candidate, frequency in candidate_frequencies.items():
            if frequency >= min_frequency:
                frequent_itemsets.append((candidate, frequency))
                frequent_counts[candidate] = frequency

        if not frequent_itemsets:
            break

        itemset_size += 1

        candidates = generate_candidates(
            frequent_itemsets,
            itemset_size
        )

    return generate_association_rules(
        frequent_counts,
        len(transactions)
    )

if __name__ == "__main__":
    transactions = [
        {"Athletics", "Scholars", "Choir"},
        {"Esports", "Scholars"},
        {"Athletics", "Band"},
        {"Esports", "Scholars", "Forensics"},
        {"Athletics", "Scholars"},
        {"Choir", "Band", "Theater"},
        {"Athletics", "Scholars", "Forensics"},
        {"Esports", "Theater"},
        {"Scholars", "Forensics"},
        {"Athletics", "Choir"}
    ]

    rules = apriori(transactions, min_frequency=2)

    for antecedent, consequent, support, confidence, lift in rules:
        print(
            f"{antecedent} -> {consequent}: "
            f"support={support:.2f}, "
            f"confidence={confidence:.2f}, "
            f"lift={lift:.2f}"
        )
