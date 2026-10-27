#!/usr/bin/env python3
"""Pytest discovery helper for Kubeflow components and pipelines.

This script discovers `tests/` directories under the provided component or
pipeline paths and runs pytest with a two-minute timeout per test.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
import warnings
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Sequence

import docker
import pytest
import yaml
from docker.types import Mount

from scripts.lib.discovery import get_repo_root, normalize_targets

REPO_ROOT = get_repo_root()
TIMEOUT_SECONDS = 120


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Discover tests/ directories for the specified components or pipelines "
            "and execute pytest with a two-minute timeout per test."
        )
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        help=(
            "Component or pipeline directories (or files within them) to test. "
            "If omitted, all components and pipelines are scanned."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help="Per-test timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass the -vv flag to pytest for more detailed output.",
    )
    return parser.parse_args()


def discover_test_dirs(targets: Sequence[Path]) -> list[Path]:
    """Discover tests/ directories under the given targets.

    Args:
        targets: Sequence of component or pipeline paths to search.

    Returns:
        List of discovered tests/ directory paths relative to REPO_ROOT.
    """
    discovered: list[Path] = []

    for target in targets:
        search_root = target if target.is_dir() else target.parent
        if not search_root.exists():
            continue

        # Direct tests/ folder
        direct = search_root / "tests"
        if direct.is_dir() and _is_member_of_pipeline_or_component(direct):
            if direct not in discovered:
                discovered.append(direct.relative_to(REPO_ROOT))
        else:
            # Broader target (category, subcategory, or repo root) –
            # recurse to find all nested tests/ directories.
            for tests_dir in sorted(search_root.rglob("tests")):
                if tests_dir.is_dir() and _is_member_of_pipeline_or_component(tests_dir):
                    if tests_dir not in discovered:
                        discovered.append(tests_dir.relative_to(REPO_ROOT))

    return discovered


def _is_member_of_pipeline_or_component(candidate: Path) -> bool:
    """Check if a path is within components/ or pipelines/ directory.

    Args:
        candidate: Path to check.

    Returns:
        True if the path is within components/ or pipelines/, False otherwise.
    """
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError:
        warnings.warn(
            f"Unable to determine relative path for {candidate} relative to repo root {REPO_ROOT}. Skipping.",
        )
        return False

    return relative.parts and relative.parts[0] in {"components", "pipelines"}


def build_pytest_args(
    test_dirs: Sequence[Path], timeout_seconds: int, verbose: bool, junixt_xml_report_file: str = "report.xml"
) -> tuple[list[str], str]:
    """Build pytest command-line arguments.

    Args:
        test_dirs: Directories containing tests to run.
        timeout_seconds: Per-test timeout in seconds.
        verbose: Whether to enable verbose pytest output.
        junixt_xml_report_file: name for the JUnit XML report produced by pytest.

    Returns:
        List of pytest command-line arguments.
    """
    pytest_run_id = datetime.now().strftime("%Y-%m-%d_%H_%M")
    args: list[str] = [
        f"--timeout={timeout_seconds}",
        "--timeout-method=signal",
        f"--junit-xml=.pytest_cache/v/{pytest_run_id}/{junixt_xml_report_file}",
    ]
    if verbose:
        args.append("-vv")

    args.extend(str(directory) for directory in test_dirs)
    return args, f".pytest_cache/v/{pytest_run_id}/{junixt_xml_report_file}"


def merge_pytest_reports(test_reports: list[str]) -> tuple[bool, str]:
    """Merges multiple JunitXML reports into a unified pytest-style CLI report.

    Arguments:
    test_reports: list of file paths to Junit reports.

    Returns:
    a tuple consisting of a flag whether any errors occurred and a string containing a unified CLI report.
    """
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    total_time = 0.0

    failure_details = []
    results_by_file = OrderedDict()

    for xml_report in test_reports:
        try:
            tree = ET.parse(xml_report)
            root = tree.getroot()

            suites = tuple()
            if root.tag == "testsuites":
                # `testsuites` wrapper for nested `testsuite` tags
                suites = root.iter("testsuite")
            elif root.tag == "testsuite":
                # either single `testsuite` or nested `testsuite` tags.
                # In the latter case we want to collect suite summary only from the root tag
                suites = [root]

            test_classes_patt = re.compile(r"(?<=\.)([A-Z]{1}\w+)")
            for suite in suites:
                total_tests += int(suite.get("tests", 0))
                total_failures += int(suite.get("failures", 0))
                total_errors += int(suite.get("errors", 0))
                total_skipped += int(suite.get("skipped", 0))
                total_time += float(suite.get("time", 0.0))

                for testcase in suite.iter("testcase"):
                    # pytest reports should ALWAYS have these two attributes
                    classname = testcase.get("classname", None)
                    name = testcase.get("name", None)

                    # parts = classname.split(".")
                    # file_end = len(parts)
                    classname_split = classname.split(".")
                    test_classes = re.findall(test_classes_patt, classname)
                    if test_classes:
                        module_path = "/".join(classname_split[: -len(test_classes)])
                        test_classes_path = ".".join(classname_split[-len(test_classes) :])
                        node_id = f"{module_path}.py::{test_classes_path}::{name}"

                    else:
                        module_path = "/".join(classname_split)
                        node_id = f"{module_path}.py::{name}"

                    # for i in range(len(parts) - 1, -1, -1):
                    #     if parts[i] and (parts[i][0].islower() or parts[i][0] == "_"):
                    #         file_end = i + 1
                    #         break

                    # file_path = testcase.get("file") or "/".join(parts[:file_end]) + ".py"
                    # class_name = ".".join(parts[file_end:])

                    # if class_name:
                    #     nodeid = f"{file_path}::{class_name}::{name}"
                    # else:
                    #     nodeid = f"{file_path}::{name}"

                    if module_path not in results_by_file:
                        results_by_file[module_path] = []

                    testcase_progress_reported = False
                    for elem in testcase.iter():
                        if not testcase_progress_reported and elem.tag in {"failure", "error", "skipped"}:
                            letter = {"failure": "F", "error": "E", "skipped": "s"}[elem.tag]
                            results_by_file[module_path].append(letter)
                            testcase_progress_reported = True

                        if elem.tag == "failure":
                            failure_details.append((node_id, elem.text or "Unknown Failure"))
                        elif elem.tag == "error":
                            failure_details.append((f"{node_id} (ERROR)", elem.text or "Unknown Error"))

                    if not testcase_progress_reported:
                        results_by_file[module_path].append(".")

        except Exception as e:
            print(f"Could not parse {xml_report}: {e}", file=sys.stderr)

    total_passed = total_tests - total_failures - total_errors - total_skipped

    lines = [
        "============================= test session starts =============================",
        "This is a unified report merged from multiple pytest invocations across docker workers and a host machine.\n"
        f"collected {total_tests} items",
        "",
    ]

    tests_so_far = 0
    for file_path, chars in results_by_file.items():
        tests_so_far += len(chars)
        pct = int(tests_so_far / total_tests * 100) if total_tests else 0
        progress = "".join(chars)
        pct_str = f"[{pct:3d}%]"
        line = f"{file_path} {progress}"
        padding = max(1, 80 - len(line) - len(pct_str))
        lines.append(f"{line}{' ' * padding}{pct_str}")

    if failure_details:
        lines.append("")
        lines.append("=================================== FAILURES ===================================")
        failed_modules = []
        for nodeid, traceback_text in failure_details:
            parts = nodeid.split("::")
            heading = f"{parts[-2]}.{parts[-1]}" if len(parts) >= 3 else parts[-1]
            lines.append(f" {heading} ".center(80, "_"))
            lines.append(traceback_text.strip())
            lines.append("")
            failed_modules.append(f"FAILED {nodeid}")
        lines.append("=========================== short test summary info ============================")
        lines.extend(failed_modules)

    summary_parts = []
    if total_failures:
        summary_parts.append(f"{total_failures} failed")
    if total_errors:
        summary_parts.append(f"{total_errors} errors")
    if total_passed:
        summary_parts.append(f"{total_passed} passed")
    if total_skipped:
        summary_parts.append(f"{total_skipped} skipped")

    summary_str = ", ".join(summary_parts) if summary_parts else "no tests run"
    lines.append(f"==================== {summary_str} in {total_time:.2f}s ====================")

    return bool(failure_details), "\n".join(lines)


def execute_tests_in_container(image_to_test_dirs: tuple[str, list]) -> tuple[str, str]:
    """Executes `pytest` command in a container for specified directories."""
    report_file = f"report_thread_{threading.get_native_id()}.xml"

    docker_client = docker.from_env()
    image, test_dirs = image_to_test_dirs
    pytest_args, report_path = build_pytest_args(
        test_dirs=test_dirs,
        timeout_seconds=TIMEOUT_SECONDS,
        verbose=False,
        junixt_xml_report_file=report_file,
    )

    print(f"running tests ({test_dirs}) in thread: {threading.get_native_id()}")
    # custom logic for pulling the image -- if the requested image is one being built as part of the PR
    # in future this should be made by incorporating this shit into .tekton builds  --> midstream required (30min check every 6 minutes)

    from threading import Semaphore

    # pulling images safely restricted to 2 at once in order not to throttle network (images might be quite large)
    image_pulling_semaphore = Semaphore(2)

    # quay_image_pattern = re.compile(r"^quay\.io/\w+\/[-\w]+(?:@sha256:|:)[-\w]+")
    image_pulling_semaphore.acquire()

    print(f"pulling image: {image}")

    _ = docker_client.images.pull(image)

    image_pulling_semaphore.release()

    # assumptions:
    # internet access (but should be true as the CI/CD pipelines do have it)
    # installing test-necessary packages will not destroy in-image python env

    # installing only pytest and pytest-cov so that not to change the existing python environment
    # ENTRYPOINT installing kfp-components[test] (same as .tekton pipeline does)
    # TODO additional packages needed for running tests
    ENTRYPOINT = f"""
    pip install -i https://pypi.org/simple pytest pytest-cov pytest-timeout || exit 1
    pytest {" ".join(pytest_args)}
    #pytest -q --junit-xml='.pytest_cache/v/test_debug/report1.xml' components/data_processing/sdg/tests/test_component_local.py
    """

    pipelines_components_mount = Mount(target="/mnt/pipelines-components", source=str(get_repo_root()), type="bind")

    run_output = ""
    try:
        run_output = docker_client.containers.run(
            image,
            # "8ec9b25dbea5",
            entrypoint=["/bin/bash", "-c", ENTRYPOINT],
            # command=CMD,
            mounts=[pipelines_components_mount],
            working_dir="/mnt/pipelines-components",
            stderr=True,
            remove=True,
            stdout=True,
        )
    except docker.errors.ContainerError as e:  # TODO must re-raise the error when pytest crashes -- what about when pytest fails partially? What RC is returned then?
        print(
            f"running tests for folders ({test_dirs}) returned non-zero status code"
        )  ## what does pytest return on failures?
        # print(e.container.logs())  # na debugu najlepiej
        # raise e.stderr # czy coś na debugu

    if isinstance(run_output, bytes):
        run_output = run_output.decode("utf-8")

    return run_output, report_path


def main() -> int:
    """Main entry point for running component/pipeline tests.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    targets = normalize_targets(args.paths)
    test_dirs = discover_test_dirs(targets)

    if not test_dirs:
        print("No tests/ directories found under the supplied paths. Nothing to do.")
        return 0
    print(test_dirs)

    print(f"Running pytest for: {test_dirs}")

    image_to_test_dirs = defaultdict(list)
    test_dirs_for_local_execution = []
    for dir in test_dirs:
        # file always exists as required by provided skeletons for components and pipelines folders
        with (dir.parent / "metadata.yaml").open("r", encoding="utf-8") as metadata_file:
            metadata = yaml.safe_load(metadata_file)
        if tests_image := metadata.get("tests", {}).get("image", None):
            image_to_test_dirs[tests_image].append(dir)
        else:
            test_dirs_for_local_execution.append(dir)

    failure = False

    test_reports = []
    if image_to_test_dirs:
        thread_executor = ThreadPoolExecutor(max_workers=6)

        # Does it collect threads -- NO???  --> would async loop not block here????
        for output, report_path in thread_executor.map(execute_tests_in_container, image_to_test_dirs.items()):
            print(f"Container returned:\n{output}")
            test_reports.append(report_path)

    # run pytest
    report_file = f"report_thread_{threading.get_native_id()}.xml"
    pytest_args, report_path = build_pytest_args(
        test_dirs=test_dirs_for_local_execution,
        timeout_seconds=TIMEOUT_SECONDS,
        verbose=False,
        junixt_xml_report_file=report_file,
    )

    print(f"running tests ({test_dirs_for_local_execution}) in main thread: {threading.get_native_id()}")

    # TODO show output when nothing is executed in docker
    with open(os.devnull) as devnull:
        with redirect_stdout(devnull):
            _ = pytest.main(pytest_args)
    test_reports.append(report_path)

    failure, report = merge_pytest_reports(test_reports)

    print(report)

    if failure:
        print("❌ Pytest reported failures. See log above for details.")
        return 1
    print("✅ Pytest completed successfully.")


if __name__ == "__main__":
    sys.exit(main())
