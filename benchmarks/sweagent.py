import asyncio
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from benchmarks.benchmark import BaseBenchmark
from scripts.logs import logger


class SWEAgentBenchmark(BaseBenchmark):
    HARNESS_DATASET_NAME = "SWE-bench/SWE-bench_Lite"
    DEFAULT_MODEL_NAME = "AFlow-SWEAgent"

    def __init__(self, name: str, file_path: str, log_path: str):
        super().__init__(name, file_path, log_path)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception), reraise=True)
    async def _generate_output(self, agent: Callable, prompt: str) -> Tuple[str, float]:
        return await asyncio.wait_for(agent(prompt), timeout=300)

    def _infer_split(self) -> str:
        path = self.file_path.lower()
        if path.endswith("_validate.jsonl"):
            return "dev"
        if path.endswith("_test.jsonl"):
            return "test"
        return "test"

    def _extract_patch(self, prediction: str) -> str:
        if not prediction:
            return ""

        text = prediction.strip()

        xml_match = re.search(r"<patch>(.*?)</patch>", text, re.DOTALL | re.IGNORECASE)
        if xml_match:
            text = xml_match.group(1).strip()

        fenced_match = re.search(r"```(?:diff|patch)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            text = fenced_match.group(1).strip()

        diff_index = text.find("diff --git")
        if diff_index != -1:
            return text[diff_index:].strip()

        patch_header = re.search(r"(^--- .*\n\+\+\+ .*)", text, re.MULTILINE)
        if patch_header:
            return text[patch_header.start() :].strip()

        return text

    async def evaluate_problem(self, problem: dict, agent: Callable) -> Dict[str, Any]:
        prompt = problem["prompt"]
        try:
            prediction, cost = await self._generate_output(agent, prompt)
            model_patch = self._extract_patch(prediction)
            return {
                "instance_id": problem["instance_id"],
                "repo": problem["repo"],
                "prompt": prompt,
                "problem_statement": problem["problem_statement"],
                "prediction": prediction,
                "model_patch": model_patch,
                "cost": cost,
            }
        except Exception as e:
            logger.info(f"Maximum retries reached for {problem['instance_id']}. Error: {e}")
            return {
                "instance_id": problem["instance_id"],
                "repo": problem["repo"],
                "prompt": prompt,
                "problem_statement": problem["problem_statement"],
                "prediction": str(e),
                "model_patch": "",
                "cost": 0.0,
            }

    def calculate_score(self, expected_output: Any, prediction: Any) -> Tuple[float, Any]:
        return 0.0, prediction

    def get_result_columns(self) -> List[str]:
        return [
            "instance_id",
            "repo",
            "prediction",
            "model_patch",
            "score",
            "resolved",
            "patch_applied",
            "cost",
            "evaluation_details",
        ]

    def _write_predictions(self, predictions: List[Dict[str, Any]]) -> Path:
        output_dir = Path(self.log_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        predictions_path = output_dir / "predictions.jsonl"

        with predictions_path.open("w", encoding="utf-8") as fout:
            for pred in predictions:
                payload = {
                    "instance_id": pred["instance_id"],
                    "model_name_or_path": self.DEFAULT_MODEL_NAME,
                    "model_patch": pred["model_patch"],
                }
                fout.write(json.dumps(payload, ensure_ascii=False) + "\n")

        logger.info(f"SWE-Agent predictions written to {predictions_path}")
        return predictions_path

    def _ensure_eval_environment(self) -> None:
        missing = []
        if importlib.util.find_spec("swebench") is None:
            missing.append("python package `swebench`")

        docker_path = shutil.which("docker")
        if docker_path is None:
            missing.append("a working Docker installation")
        else:
            try:
                probe = subprocess.run(
                    [docker_path, "version"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if probe.returncode != 0:
                    missing.append("a working Docker installation")
            except Exception:
                missing.append("a working Docker installation")

        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(
                "SWE-Agent predictions were generated successfully, "
                f"but official SWE-bench evaluation requires {joined}. "
                "Install the missing dependency/dependencies and rerun the benchmark."
            )

    def _load_instance_results(self, report_root: Path, run_id: str) -> Dict[str, Dict[str, Any]]:
        candidates = sorted(
            [path for path in report_root.rglob("instance_results.jsonl") if run_id in str(path)],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            candidates = sorted(
                list(report_root.rglob("instance_results.jsonl")),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )

        if not candidates:
            raise FileNotFoundError(
                f"Could not find instance_results.jsonl under {report_root} after SWE-bench evaluation."
            )

        results_by_id: Dict[str, Dict[str, Any]] = {}
        with candidates[0].open("r", encoding="utf-8") as fin:
            for line in fin:
                if not line.strip():
                    continue
                payload = json.loads(line)
                instance_id = payload.get("instance_id")
                if instance_id:
                    results_by_id[instance_id] = payload
        return results_by_id

    def _run_harness(self, predictions_path: Path, split: str) -> Dict[str, Dict[str, Any]]:
        self._ensure_eval_environment()

        run_id = f"aflow_{self.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_root = Path(self.log_path) / "evaluation_results"
        report_root.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "swebench.harness.run_evaluation",
            "--dataset_name",
            self.HARNESS_DATASET_NAME,
            "--split",
            split,
            "--predictions_path",
            str(predictions_path),
            "--max_workers",
            "1",
            "--run_id",
            run_id,
            "--report_dir",
            str(report_root),
        ]

        logger.info("Running official SWE-bench harness for SWE-Agent benchmark")
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                "SWE-bench harness execution failed.\n"
                f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
            )

        return self._load_instance_results(report_root=report_root, run_id=run_id)

    def _build_rows(
        self,
        predictions: List[Dict[str, Any]],
        instance_results: Dict[str, Dict[str, Any]],
    ) -> List[Tuple[Any, ...]]:
        rows = []
        for pred in predictions:
            result = instance_results.get(pred["instance_id"], {})
            resolved = bool(result.get("resolved", False))
            patch_applied = result.get("patch_applied")
            if patch_applied is None:
                patch_applied = result.get("patch_successfully_applied", False)

            rows.append(
                (
                    pred["instance_id"],
                    pred["repo"],
                    pred["prediction"],
                    pred["model_patch"],
                    1.0 if resolved else 0.0,
                    resolved,
                    bool(patch_applied),
                    pred["cost"],
                    json.dumps(result, ensure_ascii=False),
                )
            )
        return rows

    async def run_evaluation(self, agent: Callable, va_list: List[int], max_concurrent_tasks: int = 50):
        data = await self.load_data(va_list)
        predictions = await self.evaluate_all_problems(data, agent, max_concurrent_tasks)
        predictions_path = self._write_predictions(predictions)
        split = self._infer_split()
        instance_results = self._run_harness(predictions_path=predictions_path, split=split)
        rows = self._build_rows(predictions, instance_results)
        average_score, average_cost, total_cost = self.save_results_to_csv(rows, self.get_result_columns())
        logger.info(f"Average score on {self.name} dataset: {average_score:.5f}")
        logger.info(f"Total Cost: {total_cost:.5f}")
        return average_score, average_cost, total_cost

    async def run_baseline(self, agent: Callable, max_concurrent_tasks: int = 50):
        return await self.run_evaluation(agent, None, max_concurrent_tasks)
