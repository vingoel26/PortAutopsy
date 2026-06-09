"""
causal_engine
~~~~~~~~~~~~~
Causal intelligence layer: DAG builder, failure detection, counterfactual replay.
"""

from .dag_builder import build_dag, export_graph_json
from .failure_detector import detect_failures, DetectedFailure
from .counterfactual import run_counterfactual

__all__ = [
    "build_dag",
    "export_graph_json",
    "detect_failures",
    "DetectedFailure",
    "run_counterfactual",
]
