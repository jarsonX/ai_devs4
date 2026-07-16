# Bounded semantic evaluation for the L24 radio classifier.

from __future__ import annotations

from dataclasses import dataclass

from src.apps.L24_goingthere.llm_gateway import RadioHintClassifier
from src.apps.L24_goingthere.models import RockDirection


# Store one synthetic hint whose meaning is clear without copying course phrases.
@dataclass(frozen=True)
class EvaluationCase:
    name: str
    hint: str
    expected: RockDirection


EVALUATION_CASES = (
    EvaluationCase(
        name="larboard_reference",
        hint=(
            "A jagged boulder lurks off the larboard quarter; the view through "
            "the windshield is clear."
        ),
        expected=RockDirection.LEFT,
    ),
    EvaluationCase(
        name="windshield_reference",
        hint=(
            "Both side passages are open, but the obstacle fills the view "
            "through the windshield."
        ),
        expected=RockDirection.FRONT,
    ),
    EvaluationCase(
        name="right_wing_contrast",
        hint=(
            "Straight ahead remains open. Keep away from the wing on your "
            "right; that is where the boulder waits."
        ),
        expected=RockDirection.RIGHT,
    ),
    EvaluationCase(
        name="opposite_of_safe_port",
        hint=(
            "Nothing threatens the bow, and the port side is safe. The only "
            "obstruction sits across the hull from that safe side."
        ),
        expected=RockDirection.RIGHT,
    ),
    EvaluationCase(
        name="negated_starboard",
        hint=(
            "The starboard alarm reports no obstruction there. The collision "
            "risk lies dead ahead."
        ),
        expected=RockDirection.FRONT,
    ),
    EvaluationCase(
        name="remaining_flank",
        hint=(
            "The rock is not ahead and not to starboard; it shadows the "
            "remaining flank."
        ),
        expected=RockDirection.LEFT,
    ),
    EvaluationCase(
        name="mirrored_hazard",
        hint=(
            "The passage along the port rail is safe. The hazard mirrors it "
            "across the hull."
        ),
        expected=RockDirection.RIGHT,
    ),
    EvaluationCase(
        name="elimination",
        hint=(
            "You could continue forward or edge right without impact. Do not "
            "choose the remaining lateral route."
        ),
        expected=RockDirection.LEFT,
    ),
    EvaluationCase(
        name="both_flanks_clear",
        hint=(
            "Both flanks are unobstructed; the dangerous mass lies on the "
            "craft's present line of travel."
        ),
        expected=RockDirection.FRONT,
    ),
)


# Run a small real-model check and return a JSON-safe result.
def run_classifier_evaluation(
    classifier: RadioHintClassifier,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for case in EVALUATION_CASES:
        actual = classifier.classify(case.hint)
        results.append(
            {
                "name": case.name,
                "hint": case.hint,
                "expected": case.expected.value,
                "actual": actual.value,
                "passed": actual is case.expected,
            }
        )

    passed = sum(bool(result["passed"]) for result in results)
    return {
        "status": "passed" if passed == len(results) else "failed",
        "passed_cases": passed,
        "total_cases": len(results),
        "model_requests": classifier.request_count(),
        "cases": results,
        "classifications": classifier.records(),
    }
