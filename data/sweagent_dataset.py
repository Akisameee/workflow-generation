import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests

from scripts.logs import logger


HF_DATASET_NAME = "SWE-bench/SWE-bench_Lite"
HF_CONFIG_NAME = "default"
HF_ROWS_API = "https://datasets-server.huggingface.co/rows"
PAGE_SIZE = 100

SPLIT_TO_OUTPUT = {
    "dev": Path("data/datasets/sweagent_validate.jsonl"),
    "test": Path("data/datasets/sweagent_test.jsonl"),
}


def _parse_json_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        return [stripped]
    return []


def _format_test_names(title: str, tests: Iterable[str]) -> str:
    tests = list(tests)
    if not tests:
        return f"{title}: none"
    lines = [f"{title}:"]
    lines.extend(f"- {test_name}" for test_name in tests)
    return "\n".join(lines)


def _build_prompt(row: Dict[str, Any]) -> str:
    hints_text = (row.get("hints_text") or "").strip()
    hints_block = hints_text if hints_text else "No additional hints."

    fail_to_pass = _parse_json_list(row.get("FAIL_TO_PASS"))
    pass_to_pass = _parse_json_list(row.get("PASS_TO_PASS"))

    sections = [
        "You are resolving a real-world software issue.",
        "Generate a single unified diff patch that can be applied with `git apply`.",
        "Return only the patch text. Do not add explanations or markdown fences.",
        "",
        f"Repository: {row['repo']}",
        f"Base commit: {row['base_commit']}",
        f"Environment setup commit: {row.get('environment_setup_commit', '')}",
        f"Version: {row.get('version', '')}",
        "",
        "Issue statement:",
        row["problem_statement"].strip(),
        "",
        "Hints:",
        hints_block,
        "",
        _format_test_names("Tests that should fail before your fix and pass after it", fail_to_pass),
        "",
        _format_test_names("Tests that must keep passing", pass_to_pass),
        "",
        "Respond with the patch only.",
    ]
    return "\n".join(sections).strip() + "\n"


def _normalize_row(row: Dict[str, Any], split: str) -> Dict[str, Any]:
    normalized = dict(row)
    normalized["split"] = split
    normalized["dataset_name"] = HF_DATASET_NAME
    normalized["FAIL_TO_PASS"] = _parse_json_list(row.get("FAIL_TO_PASS"))
    normalized["PASS_TO_PASS"] = _parse_json_list(row.get("PASS_TO_PASS"))
    normalized["prompt"] = _build_prompt(normalized)
    return normalized


def _fetch_rows(split: str, offset: int, length: int) -> Dict[str, Any]:
    params = {
        "dataset": HF_DATASET_NAME,
        "config": HF_CONFIG_NAME,
        "split": split,
        "offset": offset,
        "length": length,
    }
    response = requests.get(HF_ROWS_API, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def _download_split(split: str, output_path: Path, force_download: bool = False) -> None:
    if output_path.exists() and not force_download:
        logger.info(f"{output_path} already exists. Skipping SWE-Agent dataset download for split '{split}'.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    first_page = _fetch_rows(split=split, offset=0, length=1)
    total_rows = int(first_page["num_rows_total"])
    logger.info(f"Downloading {HF_DATASET_NAME} split '{split}' with {total_rows} rows to {output_path}")

    with output_path.open("w", encoding="utf-8") as fout:
        for offset in range(0, total_rows, PAGE_SIZE):
            page = _fetch_rows(split=split, offset=offset, length=PAGE_SIZE)
            for item in page["rows"]:
                normalized = _normalize_row(item["row"], split=split)
                fout.write(json.dumps(normalized, ensure_ascii=False) + "\n")

    logger.info(f"Saved SWE-Agent formatted data to {output_path}")


def download_swebench_lite(force_download: bool = False) -> None:
    for split, output_path in SPLIT_TO_OUTPUT.items():
        _download_split(split=split, output_path=output_path, force_download=force_download)


if __name__ == "__main__":
    download_swebench_lite(force_download=False)
