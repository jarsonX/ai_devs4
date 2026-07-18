# CLI assembly for the guarded dual-agent L25 workflow.

from __future__ import annotations

import argparse
import json
import traceback
from datetime import UTC, datetime
from typing import Any

from src.apps.L25_timetravel.backend_agent import BackendAgent
from src.apps.L25_timetravel.browser_tools import TimetravelBrowser
from src.apps.L25_timetravel.config import (
    RuntimeConfig,
    build_paths,
    load_browser_config,
    load_hub_config,
    load_openai_config,
    prepare_tls_environment,
)
from src.apps.L25_timetravel.coordination import CoordinationStore
from src.apps.L25_timetravel.evaluation import run_model_evaluation
from src.apps.L25_timetravel.frontend_agent import FrontendAgent
from src.apps.L25_timetravel.hub_client import TimetravelHubClient
from src.apps.L25_timetravel.llm_gateway import L25ModelGateway
from src.apps.L25_timetravel.machine_spec import load_pwr_table
from src.apps.L25_timetravel.offline_simulation import run_offline_simulation
from src.apps.L25_timetravel.supervisor import TimetravelSupervisor, write_runtime_json


# Parse explicit live mode while leaving local dependency validation as default.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guarded dual-agent CHRONOS-P1 timetravel workflow."
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--submit",
        action="store_true",
        help="Use OpenAI, Hub, and authenticated Edge to attempt the task.",
    )
    modes.add_argument(
        "--check-models",
        action="store_true",
        help="Test both agent schemas with OpenAI and no Hub or browser access.",
    )
    modes.add_argument(
        "--simulate",
        action="store_true",
        help="Run all three legs against the complete network-free fake machine.",
    )
    return parser.parse_args()


# Return a local readiness report without opening a browser or loading secrets.
def run_dry_run() -> dict[str, Any]:
    paths = build_paths()
    table = load_pwr_table(paths.input_doc)
    return {
        "status": "ready",
        "mode": "dry-run",
        "network_used": False,
        "pwr_years": len(table),
        "live_command": (
            ".\\venv\\Scripts\\python.exe "
            "-m src.apps.L25_timetravel.main --submit"
        ),
    }


# Run four synthetic schema checks without Hub, Easytools, or browser access.
def run_model_check() -> dict[str, Any]:
    paths = build_paths()
    prepare_tls_environment(paths)
    runtime = RuntimeConfig(max_model_requests_per_agent=2)
    openai_config = load_openai_config()
    backend_model = L25ModelGateway(openai_config, runtime)
    frontend_model = L25ModelGateway(openai_config, runtime)
    result = run_model_evaluation(backend_model, frontend_model)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = paths.output_dir / f"model_evaluation_{stamp}.json"
    write_runtime_json(
        report_path,
        {
            "created_at": datetime.now(UTC).isoformat(),
            "result": result,
            "backend_model": backend_model.records(),
            "frontend_model": frontend_model.records(),
        },
    )
    return {**result, "report_path": str(report_path.relative_to(paths.repo_root))}


# Assemble and execute one fresh guarded live run with two independent model guards.
def run_submit() -> dict[str, Any]:
    paths = build_paths()
    prepare_tls_environment(paths)
    runtime = RuntimeConfig()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = paths.runs_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    store = CoordinationStore(run_dir / "coordination.sqlite3")
    hub = TimetravelHubClient(load_hub_config(), runtime)
    browser = TimetravelBrowser(load_browser_config(), runtime)
    openai_config = load_openai_config()
    backend_model = L25ModelGateway(openai_config, runtime)
    frontend_model = L25ModelGateway(openai_config, runtime)
    backend_agent = BackendAgent(hub, backend_model)
    frontend_agent = FrontendAgent(browser, frontend_model, runtime)
    result: dict[str, Any]
    report_path = run_dir / "run_report.json"
    try:
        browser.open()
        supervisor = TimetravelSupervisor(
            store,
            hub,
            browser,
            backend_agent,
            frontend_agent,
            runtime,
            run_dir,
            load_pwr_table(paths.input_doc),
        )
        result = supervisor.run()
    except Exception as error:
        result = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "hub_requests": hub.request_count(),
        }
        write_runtime_json(report_path, _report(result, hub, backend_model, frontend_model))
        raise
    finally:
        browser.close()
        store.close()
    write_runtime_json(report_path, _report(result, hub, backend_model, frontend_model))
    return {**result, "report_path": str(report_path.relative_to(paths.repo_root))}


# Build one secret-safe report while raw activation responses remain separate files.
def _report(
    result: dict[str, Any],
    hub: TimetravelHubClient,
    backend_model: L25ModelGateway,
    frontend_model: L25ModelGateway,
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "result": result,
        "hub_exchanges": hub.exchanges(),
        "backend_model": backend_model.records(),
        "frontend_model": frontend_model.records(),
    }


# Run only the requested mode and print a compact JSON outcome.
def main() -> None:
    args = parse_args()
    if args.submit:
        result = run_submit()
    elif args.check_models:
        result = run_model_check()
    elif args.simulate:
        result = run_offline_simulation(build_paths())
    else:
        result = run_dry_run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
