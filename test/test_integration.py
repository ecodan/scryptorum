"""
Integration tests for scryptorum framework.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from scryptorum import (
    experiment,
    metric,
    timer,
    llm_call,
    Experiment,
    RunType,
    set_default_run_type,
)
from scryptorum.execution.runner import Runner, BaseRunnable
from scryptorum.core.decorators import run_context
from test.conftest import verify_jsonl_file, verify_json_file


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    def test_decorator_based_experiment_trial(self, test_project_root: Path):
        """Test complete decorator-based experiment in trial mode."""
        set_default_run_type(RunType.TRIAL)

        @experiment(name="sentiment_analysis")
        def run_sentiment_analysis():
            """Complete sentiment analysis experiment."""

            # Load and process data
            reviews = load_test_reviews()
            processed_reviews = preprocess_reviews(reviews)

            # Run inference
            predictions = []
            for review in processed_reviews:
                sentiment = analyze_sentiment(review)
                predictions.append(sentiment)

            # Evaluate results
            accuracy = calculate_accuracy(predictions)
            f1 = calculate_f1_score(predictions)

            return {"accuracy": accuracy, "f1": f1}

        @timer("data_loading")
        def load_test_reviews():
            """Load test review data."""
            time.sleep(0.01)  # Simulate loading
            return [
                "Great product, love it!",
                "Terrible service, very disappointed",
                "Average quality, nothing special",
                "Excellent customer support",
                "Poor value for money",
            ]

        @timer("preprocessing")
        def preprocess_reviews(reviews):
            """Preprocess review text."""
            time.sleep(0.005)  # Simulate preprocessing
            return [review.lower().strip() for review in reviews]

        @llm_call(model="gpt-4")
        def analyze_sentiment(review):
            """Analyze sentiment using LLM."""
            time.sleep(0.02)  # Simulate API call
            # Mock sentiment analysis
            positive_words = ["great", "love", "excellent"]
            if any(word in review for word in positive_words):
                return "positive"
            elif "terrible" in review or "poor" in review:
                return "negative"
            else:
                return "neutral"

        @metric(name="accuracy", metric_type="accuracy")
        def calculate_accuracy(predictions):
            """Calculate accuracy metric."""
            # Mock ground truth
            ground_truth = ["positive", "negative", "neutral", "positive", "negative"]
            correct = sum(1 for p, gt in zip(predictions, ground_truth) if p == gt)
            return correct / len(ground_truth)

        @metric(name="f1_score", metric_type="f1")
        def calculate_f1_score(predictions):
            """Calculate F1 score."""
            # Simplified F1 calculation
            return 0.82

        # Run the experiment
        result = run_sentiment_analysis(project_root=test_project_root)

        # Verify results
        assert "accuracy" in result
        assert "f1" in result
        assert 0 <= result["accuracy"] <= 1

        # Verify experiment structure
        exp_path = test_project_root / "experiments" / "sentiment_analysis"
        trial_run_path = exp_path / "runs" / "trial_run"
        assert trial_run_path.exists()

        # Verify all logs were created
        log_entries = verify_jsonl_file(trial_run_path / "run.jsonl")
        metric_entries = verify_jsonl_file(trial_run_path / "metrics.jsonl")
        timing_entries = verify_jsonl_file(trial_run_path / "timings.jsonl")

        # Check for expected events
        event_types = {e["event_type"] for e in log_entries}
        assert "run_started" in event_types
        assert "run_finished" in event_types
        assert "llm_call" in event_types

        # Check metrics
        metric_names = {e["name"] for e in metric_entries}
        assert {"accuracy", "f1_score"} == metric_names

        # Check timings
        timing_ops = {e["operation"] for e in timing_entries}
        assert {"data_loading", "preprocessing", "analyze_sentiment"} == timing_ops

        # Verify LLM calls
        llm_events = [e for e in log_entries if e["event_type"] == "llm_call"]
        assert len(llm_events) == 5  # One for each review

    def test_class_based_experiment_milestone(self, test_project_root: Path):
        """Test complete class-based experiment in milestone mode."""

        class TextClassificationRunnable(BaseRunnable):
            """Complete text classification experiment."""

            def prepare(self):
                """Setup experiment resources."""
                self.model_name = self.config.get("model", "bert-base")
                self.batch_size = self.config.get("batch_size", 16)

                self.run.log_event(
                    "experiment_config",
                    {"model": self.model_name, "batch_size": self.batch_size},
                )

                # Simulate model loading
                time.sleep(0.01)
                self.run.log_timing("model_loading", 100.0)

            def execute(self):
                """Execute the classification experiment."""
                # Load dataset
                dataset = self._load_dataset()

                # Process in batches
                all_predictions = []
                for i in range(0, len(dataset), self.batch_size):
                    batch = dataset[i : i + self.batch_size]
                    predictions = self._process_batch(batch, i // self.batch_size)
                    all_predictions.extend(predictions)

                # Store predictions for scoring
                self.predictions = all_predictions

                # Create intermediate artifacts
                self.run.preserve_artifacts(
                    {
                        "predictions": all_predictions,
                        "dataset_info": {
                            "total_samples": len(dataset),
                            "num_batches": (len(dataset) + self.batch_size - 1)
                            // self.batch_size,
                        },
                    }
                )

            def score(self):
                """Evaluate experiment results."""
                # Calculate metrics
                accuracy = self._calculate_accuracy()
                precision = self._calculate_precision()
                recall = self._calculate_recall()
                f1 = 2 * (precision * recall) / (precision + recall)

                # Log all metrics
                self.run.log_metric("accuracy", accuracy, "accuracy")
                self.run.log_metric("precision", precision, "precision")
                self.run.log_metric("recall", recall, "recall")
                self.run.log_metric("f1_score", f1, "f1")

                # Create evaluation artifacts
                evaluation_results = {
                    "metrics": {
                        "accuracy": accuracy,
                        "precision": precision,
                        "recall": recall,
                        "f1_score": f1,
                    },
                    "confusion_matrix": [[45, 5], [8, 42]],
                    "classification_report": "detailed_report_here",
                }

                self.run.preserve_artifacts({"evaluation": evaluation_results})

            def cleanup(self):
                """Clean up resources."""
                self.run.log_event("cleanup_started", {})
                # Simulate cleanup
                time.sleep(0.005)
                self.run.log_event("cleanup_completed", {})

            def _load_dataset(self):
                """Load classification dataset."""
                time.sleep(0.02)  # Simulate loading
                self.run.log_timing("dataset_loading", 200.0)

                # Mock dataset
                return [
                    ("positive text example", "positive"),
                    ("negative text example", "negative"),
                    ("neutral text example", "neutral"),
                ] * 30  # 90 samples total

            def _process_batch(self, batch, batch_num):
                """Process a batch of samples."""
                time.sleep(0.01)  # Simulate processing

                predictions = []
                for text, _ in batch:
                    # Mock LLM call
                    self.run.log_llm_call(
                        model=self.model_name,
                        input_data=f"Classify: {text[:30]}...",
                        output_data="positive",
                        duration_ms=50.0,
                    )
                    predictions.append("positive")

                self.run.log_timing(f"batch_{batch_num}_processing", len(batch) * 50.0)
                return predictions

            def _calculate_accuracy(self):
                """Calculate classification accuracy."""
                # Mock accuracy calculation
                return 0.87

            def _calculate_precision(self):
                """Calculate precision."""
                return 0.85

            def _calculate_recall(self):
                """Calculate recall."""
                return 0.89

        # Run the experiment
        runner = Runner(test_project_root)
        config = {"model": "bert-large-uncased", "batch_size": 8}

        run = runner.run_experiment(
            "text_classification",
            runnable_class=TextClassificationRunnable,
            run_type=RunType.MILESTONE,
            run_id="classification_v2",
            config=config,
        )

        # Verify experiment structure
        exp_path = test_project_root / "experiments" / "text_classification"
        run_path = exp_path / "runs" / "classification_v2"
        assert run_path.exists()
        assert (run_path / "artifacts").exists()
        assert (run_path / "code_snapshot").exists()

        # Verify all lifecycle stages were executed
        log_entries = verify_jsonl_file(run.log_file)
        event_types = {e["event_type"] for e in log_entries}

        expected_events = {
            "run_started",
            "experiment_config",
            "cleanup_started",
            "cleanup_completed",
            "run_finished",
        }
        assert expected_events.issubset(event_types)

        # Verify metrics
        metric_entries = verify_jsonl_file(run.metrics_file)
        metric_names = {e["name"] for e in metric_entries}
        expected_metrics = {"accuracy", "precision", "recall", "f1_score"}
        assert expected_metrics == metric_names

        # Verify artifacts were saved
        predictions_file = run.artifacts_dir / "predictions.json"
        evaluation_file = run.artifacts_dir / "evaluation.json"

        assert predictions_file.exists()
        assert evaluation_file.exists()

        # Verify artifact contents
        predictions_data = verify_json_file(predictions_file)
        assert len(predictions_data) == 90  # 90 predictions

        evaluation_data = verify_json_file(evaluation_file)
        assert "metrics" in evaluation_data
        assert "confusion_matrix" in evaluation_data

    def test_mixed_decorator_and_manual_logging(self, test_project_root: Path):
        """Test experiment mixing decorators with manual logging."""

        @experiment(name="mixed_experiment")
        def run_mixed_experiment():
            """Experiment mixing decorators and manual logging."""

            # Get the current run for manual logging
            from scryptorum.core.decorators import get_current_run

            run = get_current_run()

            # Manual event logging
            run.log_event("experiment_phase", {"phase": "data_preparation"})

            # Use decorators for some operations
            data = load_data_with_timer()

            # Manual timing
            with run.TimerContext(run, "manual_processing"):
                processed_data = [x * 2 for x in data]
                time.sleep(0.01)

            # Use decorator for metrics
            accuracy = calculate_metric_with_decorator(processed_data)

            # Manual metric logging
            run.log_metric(
                "manual_metric", 0.75, "custom", dataset_size=len(processed_data)
            )

            # Manual LLM call logging
            run.log_llm_call(
                model="manual-model",
                input_data="manual input",
                output_data="manual output",
                duration_ms=123.45,
            )

            return accuracy

        @timer("data_loading")
        def load_data_with_timer():
            """Load data with automatic timing."""
            time.sleep(0.005)
            return [1, 2, 3, 4, 5]

        @metric(name="calculated_accuracy", metric_type="accuracy")
        def calculate_metric_with_decorator(data):
            """Calculate metric with automatic logging."""
            return len(data) / 10.0  # Mock accuracy

        set_default_run_type(RunType.TRIAL)
        result = run_mixed_experiment(project_root=test_project_root)

        # Verify mixed logging worked correctly
        exp_path = test_project_root / "experiments" / "mixed_experiment"
        trial_run_path = exp_path / "runs" / "trial_run"

        # Check main log
        log_entries = verify_jsonl_file(trial_run_path / "run.jsonl")
        event_types = {e["event_type"] for e in log_entries}

        assert "experiment_phase" in event_types
        assert "llm_call" in event_types

        # Check metrics
        metric_entries = verify_jsonl_file(trial_run_path / "metrics.jsonl")
        metric_names = {e["name"] for e in metric_entries}
        assert {"calculated_accuracy", "manual_metric"} == metric_names

        # Verify manual metric has additional metadata
        manual_metrics = [e for e in metric_entries if e["name"] == "manual_metric"]
        assert len(manual_metrics) == 1
        assert manual_metrics[0]["dataset_size"] == 5

        # Check timings
        timing_entries = verify_jsonl_file(trial_run_path / "timings.jsonl")
        timing_ops = {e["operation"] for e in timing_entries}
        assert {"data_loading", "manual_processing"} == timing_ops


class TestConcurrencyAndPerformance:
    """Test framework behavior under concurrent usage."""

    def test_concurrent_experiments(self, test_project_root: Path):
        """Test running multiple experiments concurrently."""
        import threading
        import queue

        results = queue.Queue()

        def run_concurrent_experiment(exp_id):
            """Run a single experiment."""
            try:

                @experiment(name=f"concurrent_exp_{exp_id}")
                def concurrent_experiment():
                    # Simulate work
                    time.sleep(0.01)
                    return f"result_{exp_id}"

                set_default_run_type(RunType.TRIAL)
                result = concurrent_experiment(project_root=test_project_root)
                results.put((exp_id, result, None))
            except Exception as e:
                results.put((exp_id, None, e))

        # Run 5 concurrent experiments
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_concurrent_experiment, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Collect results
        experiment_results = {}
        while not results.empty():
            exp_id, result, error = results.get()
            if error:
                pytest.fail(f"Experiment {exp_id} failed: {error}")
            experiment_results[exp_id] = result

        assert len(experiment_results) == 5

        # Verify all experiments were created
        for i in range(5):
            exp_path = test_project_root / "experiments" / f"concurrent_exp_{i}"
            assert exp_path.exists()

            trial_run_path = exp_path / "runs" / "trial_run"
            assert trial_run_path.exists()


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""

    def test_experiment_with_partial_failures(self, test_project_root: Path):
        """Test experiment that has some failures but continues."""

        class PartiallyFailingRunnable(BaseRunnable):
            def prepare(self):
                self.run.log_event("prepare_success", {})

            def execute(self):
                # Simulate partial failures
                for i in range(5):
                    try:
                        if i == 2:  # Fail on iteration 2
                            raise ConnectionError(f"Simulated failure {i}")

                        self.run.log_llm_call(
                            model="test-model",
                            input_data=f"input_{i}",
                            output_data=f"output_{i}",
                            duration_ms=100.0,
                        )
                        self.run.log_metric(f"iteration_{i}", 0.1 * i, "progress")

                    except ConnectionError as e:
                        # Log the error but continue
                        self.run.log_event(
                            "iteration_error", {"iteration": i, "error": str(e)}
                        )

                self.run.log_event("run_completed_with_errors", {"total_errors": 1})

            def score(self):
                # Calculate metrics based on successful iterations
                success_rate = 4 / 5  # 4 out of 5 succeeded
                self.run.log_metric("success_rate", success_rate, "rate")

            def cleanup(self):
                self.run.log_event("cleanup_success", {})

        runner = Runner(test_project_root)

        # Should complete successfully despite partial failures
        run = runner.run_experiment(
            "partial_failure_test", runnable_class=PartiallyFailingRunnable
        )

        # Verify experiment completed
        log_entries = verify_jsonl_file(run.log_file)
        event_types = {e["event_type"] for e in log_entries}

        assert "prepare_success" in event_types
        assert "iteration_error" in event_types
        assert "run_completed_with_errors" in event_types
        assert "cleanup_success" in event_types
        assert "run_finished" in event_types

        # Verify partial metrics were logged
        metric_entries = verify_jsonl_file(run.metrics_file)
        metric_names = {e["name"] for e in metric_entries}

        # Should have metrics for successful iterations plus success_rate
        expected_metrics = {
            "iteration_0",
            "iteration_1",
            "iteration_3",
            "iteration_4",
            "success_rate",
        }
        assert expected_metrics == metric_names

        # Should not have metric for failed iteration
        assert "iteration_2" not in metric_names

    def test_corrupted_log_recovery(self, test_project_root: Path):
        """Test behavior with corrupted log files."""
        # Create experiment with some valid logs
        experiment = Experiment(test_project_root, "corrupted_test")
        run = experiment.create_run(RunType.TRIAL)

        # Add some valid entries
        run.log_metric("valid_metric", 0.5)
        run.finish()

        # Corrupt the metrics file by adding invalid JSON
        with open(run.metrics_file, "a") as f:
            f.write("this is not valid json\n")
            f.write('{"valid": "entry", "name": "after_corruption", "value": 0.8}\n')

        # Reading should handle corruption gracefully
        experiment = Experiment(test_project_root, "corrupted_test")
        runs = experiment.list_runs()

        # Should still find the run despite corruption
        assert len(runs) == 1
        assert runs[0]["run_id"] == "trial_run"
