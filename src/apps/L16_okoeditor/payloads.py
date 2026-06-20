# Deterministic update planning for the L16 okoeditor task.

from __future__ import annotations

from src.apps.L16_okoeditor.models import RecordDetail, TargetSelection, UpdateInstruction


SKOLWIN_INCIDENT_TITLE_REST = "Nietypowa aktywność zwierząt nieopodal miasta Skolwin"
SKOLWIN_INCIDENT_CONTENT = (
    "Czujniki zarejestrowały ślady aktywności zwierząt w pobliżu Skolwina. "
    "Charakter ruchu i ślady przy rzece wskazują na obecność kilku zwierząt, "
    "najprawdopodobniej bobrów. Nie potwierdzono obecności ludzi ani pojazdów, "
    "dlatego zgłoszenie należy traktować jako obserwację zwierząt wymagającą "
    "dalszego monitoringu przy brzegu rzeki."
)
SKOLWIN_TASK_CONTENT = (
    "Nagrania z okolic Skolwina przeanalizowano. Zarejestrowany ruch odpowiada "
    "zwierzętom, prawdopodobnie bobrom, a nie ludziom ani pojazdom. Zadanie "
    "uznaje się za wykonane i przekazane do dalszej obserwacji przyrodniczej."
)
KOMAROWO_TITLE_REST = "Wykryto ruch ludzi w okolicach miasta Komarowo"
KOMAROWO_CONTENT = (
    "Czujniki wykryły ruch ludzi w okolicach miasta Komarowo. Obserwacja "
    "wskazuje na obecność kilku osób poruszających się pieszo przy obrzeżach "
    "miasta. Zdarzenie wymaga dalszego monitoringu i sprawdzenia kierunku "
    "przemieszczania się grupy."
)


# Build the three required update instructions from grounded targets.
def build_update_plan(targets: TargetSelection) -> tuple[UpdateInstruction, ...]:
    skolwin_incident = build_skolwin_incident_update(targets.skolwin_incident)
    skolwin_task = build_skolwin_task_update(targets.skolwin_task)
    komarowo_incident = build_komarowo_incident_update(targets.komarowo_candidate)
    plan = (skolwin_incident, skolwin_task, komarowo_incident)
    validate_update_plan(plan)
    return plan


# Validate one plan before any live update call can happen.
def validate_update_plan(plan: tuple[UpdateInstruction, ...], *, max_writes: int = 3) -> None:
    if len(plan) != 3:
        raise ValueError("The update plan must contain exactly three writes.")
    if len({(instruction.page, instruction.record_id) for instruction in plan}) != len(plan):
        raise ValueError("The update plan must not reuse the same page and record pair twice.")
    if len(plan) > max_writes:
        raise ValueError("The update plan exceeds the configured write limit.")

    for instruction in plan:
        if not instruction.title and not instruction.content:
            raise ValueError(f"Update for {instruction.page}/{instruction.record_id} has no title or content.")
        if instruction.page != "zadania" and instruction.done is not None:
            raise ValueError(f"The done flag is allowed only for zadania, not {instruction.page}.")
        if instruction.page == "zadania" and instruction.done not in {None, "YES", "NO"}:
            raise ValueError(f"Unexpected done flag value for task {instruction.record_id}.")


# Build the Skolwin incident rewrite while preserving its ticket code.
def build_skolwin_incident_update(detail: RecordDetail) -> UpdateInstruction:
    rebuilt_title = build_coded_title("MOVE04", SKOLWIN_INCIDENT_TITLE_REST)
    return UpdateInstruction(
        page="incydenty",
        record_id=detail.record_id,
        title=rebuilt_title,
        content=SKOLWIN_INCIDENT_CONTENT,
        reason="Reclassify the Skolwin incident from people or vehicles to animals.",
        expected_title_substrings=("Skolwin", "zwierząt"),
        expected_body_substrings=("bobr", "zwierząt", "Nie potwierdzono obecności ludzi ani pojazdów"),
    )


# Build the Skolwin task completion update.
def build_skolwin_task_update(detail: RecordDetail) -> UpdateInstruction:
    return UpdateInstruction(
        page="zadania",
        record_id=detail.record_id,
        content=SKOLWIN_TASK_CONTENT,
        done="YES",
        reason="Mark the Skolwin task as done and note that animals such as beavers were seen there.",
        expected_title_substrings=("Skolwin",),
        expected_body_substrings=("bobr", "zwierzęt", "wykonane"),
        expected_done=True,
    )


# Build the replacement incident that redirects operator attention to Komarowo.
def build_komarowo_incident_update(detail: RecordDetail) -> UpdateInstruction:
    rebuilt_title = build_coded_title("MOVE01", KOMAROWO_TITLE_REST)
    return UpdateInstruction(
        page="incydenty",
        record_id=detail.record_id,
        title=rebuilt_title,
        content=KOMAROWO_CONTENT,
        reason="Repurpose one unrelated incident into a Komarowo human-movement report.",
        expected_title_substrings=("Komarowo", "ruch ludzi"),
        expected_body_substrings=("Komarowo", "ruch ludzi", "kilku osób"),
    )


# Build one title with the exact ticket code required by the OKO coding note.
def build_coded_title(code: str, title_without_code: str) -> str:
    return f"{code} {title_without_code}"
