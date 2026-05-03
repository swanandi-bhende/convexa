"""Convenience wrapper for running the debate orchestrator from the repo root."""

from runpy import run_module


if __name__ == "__main__":
    run_module("agents.orchestrator", run_name="__main__")