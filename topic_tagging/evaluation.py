import csv
import json
from dataclasses import dataclass, field
from typing import List
from sefaria.model import *
import django
django.setup()

@dataclass
class LabelledRef:
    ref: str
    slugs: List[str]

    def __repr__(self):
        return f"LabelledRef(ref='{self.ref}', slugs={self.slugs})"

class Evaluator:
    def __init__(self, golden_standard: List[LabelledRef], predicted: List[LabelledRef], considered_labels: List[str]):
        self.golden_standard = golden_standard
        self.predicted = predicted
        self.considered_labels = considered_labels

        self.golden_standard_projection = self.get_projection_of_labelled_refs(self.golden_standard)
        self.golden_standard_projection = self.filter_out_refs_not_in_predicted(self.golden_standard_projection)
        self.add_implied_toc_slugs(self.golden_standard_projection)

        self.predicted_projection = self.get_projection_of_labelled_refs(self.predicted)
        self.predicted_projection = self.filter_out_refs_not_in_gold(self.predicted_projection)
        self.predicted_projection = self.sort_list1_based_on_list2_and_ref_field(self.predicted_projection, self.golden_standard_projection)
        self.add_implied_toc_slugs(self.predicted_projection)

        self.gold_prediction_pairs = zip(self.golden_standard_projection, self.predicted_projection)

    def get_projection_of_labelled_refs(self, lrs :List[LabelledRef]) -> List[LabelledRef]:
        # Remove irrelevant slugs from the slugs list
        projected = []
        for ref in lrs:
            projected.append(LabelledRef(ref.ref, [slug for slug in ref.slugs if slug in self.considered_labels]))
        return projected



    def filter_out_refs_not_in_predicted(self, lrs :List[LabelledRef]) -> List[LabelledRef]:
        predicted_refs = [labelled_ref.ref for labelled_ref in self.predicted]
        projected = [labelled_ref for labelled_ref in lrs if labelled_ref.ref in predicted_refs]
        return projected

    def filter_out_refs_not_in_gold(self, lrs :List[LabelledRef]) -> List[LabelledRef]:
        gold_refs = [labelled_ref.ref for labelled_ref in self.golden_standard]
        projected = [labelled_ref for labelled_ref in lrs if labelled_ref.ref in gold_refs]
        return projected

    def sort_list1_based_on_list2_and_ref_field(self, list1, list2):
        field_index_map = {labelledRef.ref: index for index, labelledRef in enumerate(list2)}

        def custom_sort_key(labelledRef):
            return field_index_map.get(labelledRef.ref, float('inf'))

        # Sort list1 using the custom sorting key
        sorted_list1 = sorted(list1, key=custom_sort_key)

        return sorted_list1

    def add_implied_toc_slugs(self, labelled_refs: List[LabelledRef]):

        def _find_parent_slug(data_structure, target_slug):
            # Access the 'children' list
            children = data_structure['children']

            # Iterate through each category dictionary
            for category in children:
                # If the target slug matches the current category's slug
                if category['slug'] == target_slug:
                    # Return the parent slug
                    return data_structure['slug']
                # If the current category has children, recursively search within them
                if 'children' in category:
                    result = _find_parent_slug(category, target_slug)
                    # If the parent slug is found in any of the children, return it
                    if result:
                        return result
            # If the target slug is not found in any children, return None
            return None

        toc = library.get_topic_toc_json_recursive()
        for lr in labelled_refs:
            for slug in lr.slugs:
                parent = (_find_parent_slug({"children": toc, "slug": None}, slug))
                if parent and parent not in lr.slugs and parent in self.considered_labels:
                    # print(f"{parent} missing parent of {slug}")
                    lr.slugs.append(parent)

    def find_childless_slugs(self, labelled_refs: List[LabelledRef]):

        def _find_children_by_slug(data_structure, target_slug):
            # Access the 'children' list
            children = data_structure.get('children', [])

            # Initialize a list to store the children
            found_children = []

            # Iterate through each category dictionary
            for category in children:
                # If the target slug matches the current category's slug
                if category['slug'] == target_slug:
                    # If the current category has children, add them to the list
                    if 'children' in category:
                        found_children.extend(category['children'])
                    # Return the list of children or an empty list if no children found
                    return found_children or None

                # If the current category has children, recursively search within them
                if 'children' in category:
                    result = _find_children_by_slug(category, target_slug)
                    # If children are found in any of the children, extend the list
                    if result:
                        found_children.extend(result)

        toc = library.get_topic_toc_json_recursive()
        for lr in labelled_refs:
            for slug in lr.slugs:
                if slug == 'laws':
                    continue
                children = (_find_children_by_slug({"children": toc, "slug": None}, slug))

                if children and all(child['slug'] not in lr.slugs for child in children):
                    print(lr.ref)
                    print(f"{slug}'s children are not included")

    def compute_accuracy(self) -> float:
        correct_predictions = 0
        total_predictions = 0

        for golden_ref, evaluated_ref in zip(self.golden_standard_projection, self.predicted_projection):
            total_predictions += 1
            if set(golden_ref.slugs) == set(evaluated_ref.slugs):
                correct_predictions += 1

        if total_predictions == 0:
            return 0.0

        accuracy = correct_predictions / total_predictions
        return accuracy

    def compute_metrics_for_refs_pair(self, golden_standard_ref: LabelledRef, predicted_ref: LabelledRef):
        golden_standard = golden_standard_ref.slugs
        predicted = predicted_ref.slugs

        true_positives = 0
        false_positives = 0
        false_negatives = 0

        for item in predicted:
            if item in golden_standard:
                true_positives += 1
            else:
                false_positives += 1

        for item in golden_standard:
            if item not in predicted:
                false_negatives += 1

        return true_positives, false_positives, false_negatives

    def get_slug_differences(self, golden_standard_ref: LabelledRef, predicted_ref: LabelledRef):
        golden_standard = golden_standard_ref.slugs
        predicted = predicted_ref.slugs

        true_positives = []
        false_positives = []
        false_negatives = []

        for item in predicted:
            if item in golden_standard:
                true_positives.append(item)
            else:
                false_positives.append(item)

        for item in golden_standard:
            if item not in predicted:
                false_negatives.append(item)

        return true_positives, false_positives, false_negatives

    def compute_total_precision(self):
        total_true_positives = 0
        total_false_positives = 0
        total_false_negatives = 0

        for golden_standard_ref, predicted_ref in zip(self.golden_standard_projection, self.predicted_projection):
            true_positives, false_positives, false_negatives = self.compute_metrics_for_refs_pair(golden_standard_ref, predicted_ref)
            total_true_positives += true_positives
            total_false_positives += false_positives
            total_false_negatives += false_negatives

        total_precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 0
        return total_precision

    def compute_total_recall(self):
        total_true_positives = 0
        total_false_negatives = 0

        for golden_standard_ref, predicted_ref in zip(self.golden_standard_projection, self.predicted_projection):
            true_positives, _, false_negatives = self.compute_metrics_for_refs_pair(golden_standard_ref, predicted_ref)
            # if false_negatives != 0:
            #     print("oh!")
            total_true_positives += true_positives
            total_false_negatives += false_negatives

        total_recall = total_true_positives / (total_true_positives + total_false_negatives) if (total_true_positives + total_false_negatives) > 0 else 0
        return total_recall

    def compute_f1_score(self):
        precision = self.compute_total_precision()
        recall = self.compute_total_recall()

        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        return f1_score

    def compute_slug_stats(self):
        slug_stats = {}
        for slug in self.considered_labels:
            slug_stats[slug] = {"false_positives": 0,
                                "false_negatives": 0,
                                "true_positives": 0}
        for gold_lr, pred_lr in self.gold_prediction_pairs:
            true_positives, false_positives, false_negatives = self.get_slug_differences(gold_lr, pred_lr)
            for slug in true_positives:
                slug_stats[slug]['true_positives'] += 1
            for slug in false_positives:
                slug_stats[slug]['false_positives'] += 1
            for slug in false_negatives:
                slug_stats[slug]['false_negatives'] += 1
        return slug_stats




class DataHandler:
    def __init__(self, golden_standard_filename, predicted_filename, considered_slugs_filename):
        self.golden_standard_filename = golden_standard_filename
        self.predicted_filename = predicted_filename
        self.considered_slugs_filename = considered_slugs_filename

    def _jsonl_to_labelled_refs(self, jsonl_filename) -> List[LabelledRef]:
        lrs = []
        with open(jsonl_filename, 'r') as file:
            for line in file:
                data = json.loads(line)
                ref = data['ref']
                slugs = data['slugs']
                lrs.append(LabelledRef(ref, slugs))
        return lrs

    def _read_first_column_or_array(self, file_path):
        file_extension = file_path.split('.')[-1]
        if file_extension == 'csv':
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                first_column = [row[0] for row in reader]
                return first_column
        elif file_extension == 'json':
            with open(file_path, 'r') as file:
                data = json.load(file)
                if isinstance(data, dict):
                    first_array = next(iter(data.values()))
                    if isinstance(first_array, list):
                        return first_array
                    else:
                        raise ValueError("Invalid JSON format. Expecting an array as a value for the first key.")
                else:
                    raise ValueError("Invalid JSON format. Expecting a dictionary.")
        elif file_extension == 'jsonl':
            with open(file_path, 'r') as file:
                first_line = file.readline()
                data = json.loads(first_line)
                if isinstance(data, dict):
                    first_array = next(iter(data.values()))
                    if isinstance(first_array, list):
                        return first_array
                    else:
                        raise ValueError("Invalid JSONL format. Expecting an array as a value for the first key.")
                else:
                    raise ValueError("Invalid JSONL format. Expecting a dictionary.")
        else:
            raise ValueError("Unsupported file format. Only CSV, JSON, and JSONL are supported.")

    def get_golden_standard(self) -> List[LabelledRef]:
        return self._jsonl_to_labelled_refs(self.golden_standard_filename)

    def get_predicted(self) -> List[LabelledRef]:
        return self._jsonl_to_labelled_refs(self.predicted_filename)

    def get_considered_slugs(self) -> List[LabelledRef]:
        return self._read_first_column_or_array(self.considered_slugs_filename)


def write_slugs_stats_to_csv(data, filename):
    # Extracting column names
    columns = set()
    for row_data in data.values():
        columns.update(row_data.keys())

    # Writing to CSV
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[''] + list(columns))
        writer.writeheader()
        for row_key, row_data in data.items():
            row = {key: row_data.get(key, '') for key in columns}
            row[''] = row_key
            writer.writerow(row)

def evaluate_results(results_jsonl_filename):
    handler = DataHandler("evaluation_data/gold.jsonl", results_jsonl_filename, 'evaluation_data/all_slugs_and_titles_for_prodigy.csv')
    evaluator = Evaluator(handler.get_golden_standard(), handler.get_predicted(), handler.get_considered_slugs())
    stats = evaluator.compute_slug_stats()
    write_slugs_stats_to_csv(stats, 'evaluation_data/slugs_stats.csv')
    # sort_slugs_by_false_positives = sorted(stats.items(), key=lambda x: x[1]['false_positives'], reverse=True)

    print("Recall: ", evaluator.compute_total_recall())
    print("Precision: ", evaluator.compute_total_precision())
    print("F1 :", evaluator.compute_f1_score())

if __name__ == "__main__":
    # Create some sample data
    golden_standard = [
        LabelledRef("ref1", ["a", "b", "c"]),
        LabelledRef("ref2", ["b", "c", "d"]),
        LabelledRef("ref3", ["c", "d", "e"])
    ]

    evaluated = [
        LabelledRef("ref1", ["a", "c", "e"]),
        LabelledRef("ref2", ["b", "d"]),
        LabelledRef("ref3", ["c", "d", "e"])
    ]

    considered_labels = ["a", "b", "c"]

    # Initialize Evaluator
    evaluator = Evaluator(golden_standard, evaluated, considered_labels)

    # Test accessing the projections
    print("Golden Standard Projection:")
    for ref in evaluator.golden_standard_projection:
        print(ref)

    print("\nEvaluated Projection:")
    for ref in evaluator.predicted_projection:
        print(ref)

    handler = DataHandler("evaluation_data/gold.jsonl", "evaluation_data/gold.jsonl", 'evaluation_data/all_slugs_and_titles_for_prodigy.csv')
    evaluator = Evaluator(handler.get_golden_standard(), handler.get_predicted(), handler.get_considered_slugs())
    print(evaluator.compute_f1_score())


