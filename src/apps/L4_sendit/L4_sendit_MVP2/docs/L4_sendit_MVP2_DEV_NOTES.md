# Issues

## Table Of Contents

- [Issues Summary](#issues-summary)
- [Issue 1: declaration_builder](#issue-1-declaration_builder)
- [Issue 2: WDP](#issue-2-wdp)
- [Thoughts After Stage 5 Implementation](#thoughts-after-stage-5-implementation)

## Issues Summary

| Issue | Status |
|---|---|
| `declaration_builder` | <span style="color: #b45309;"><strong>Not resolved</strong></span> |
| `WDP` | <span style="color: #b45309;"><strong>Not resolved</strong></span> |

## Issue 1: declaration_builder
***Status:*** <span style="color: #b45309;"><strong>Not resolved</strong></span>

During a manual review of AI-generated code, the following approach was found in `.\src\apps\L4_sendit\L4_sendit_MVP2\declaration_builder.py`:

```
def _resolve_known_task_category(
    contents: str,
    route_status: str,
    disabled_route_exception: str,
) -> tuple[str, str]:
    normalized_contents = contents.lower()
    normalized_route_status = route_status.lower()
    normalized_exception = disabled_route_exception.lower()

    # === KNOWN_TASK: spk_transport_declaration ===============================
    # The currently supported course task uses reactor fuel cassettes. MVP1 and
    # local validation established category A as the accepted interpretation.
    # Keep this course-specific rule explicit so future tasks can replace it
    # with their own documented executor logic.
    # =========================================================================
    if (
        "reaktor" in normalized_contents
        and "paliw" in normalized_contents
        and "wy" in normalized_route_status
    ):
        return (
            "A",
            (
                "Known task executor treats reactor fuel cassettes as category A to satisfy "
                "the disabled-route exception documented for Żarnowiec routes."
            ),
        )

    raise ValueError("Known declaration executor cannot resolve the shipment category from current evidence.")
```

This is a poor design because the category is assigned based on the keywords `"reaktor"`, `"paliw"`, and `"wy"`. As a result, any package that does not contain those keywords would not be assigned to category A, even if it should in fact be treated that way.

### Cause
- The code was proposed by an AI agent (AI responsibility).
- The documentation in `.\src\apps\L4_sendit\L4_sendit_MVP2\docs` does not define clearly enough how this should be handled (human responsibility).

### Supporting documentation
Based on `.\data\L4_sendit\references\index.md` (section `"4. KLASYFIKACJA PRZESYŁEK"`, subsection `"4.1. Kategorie przesyłek"`), the categories are described as follows:

```
4. KLASYFIKACJA PRZESYŁEK

4.1. Kategorie przesyłek

Każda przesyłka przyjmowana do SPK musi zostać zaklasyfikowana do jednej z następujących kategorii:

**Kategoria A - Strategiczna**  
Przesyłki o znaczeniu krytycznym dla funkcjonowania Systemu i infrastruktury. Obejmuje: podzespoły elektroniczne, części zamienne do automatów kontrolnych, moduły komunikacyjne, ogniwa paliwowe, materiały do naprawy torów.  
Uprawnienia do nadawania: wyłącznie jednostki autoryzowane przez System  
Priorytet transportu: najwyższy  
Czas dostawy: maksymalnie 24 godziny w obrębie jednego regionu  

**Kategoria B - Medyczna**  
Przesyłki związane ze zdrowiem i bezpieczeństwem sanitarnym ludności. Obejmuje: leki, szczepionki, sprzęt medyczny, próbki laboratoryjne, środki dezynfekcyjne.  
Uprawnienia do nadawania: placówki medyczne z aktualną autoryzacją  
Priorytet transportu: bardzo wysoki  
Czas dostawy: maksymalnie 36 godzin w obrębie jednego regionu  

**Kategoria C - Żywnościowa**  
Transport żywności między osadami, z farm do centrów dystrybucyjnych, z magazynów do punktów wydawania. Obejmuje: produkty spożywcze, nasiona, nawozy, pasze.  
Uprawnienia do nadawania: farmy kolektywne, magazyny centralne, autoryzowani producenci  
Priorytet transportu: wysoki  
Czas dostawy: maksymalnie 48 godzin w obrębie jednego regionu  

**Kategoria D - Gospodarcza**  
Przesyłki związane z codziennym funkcjonowaniem osad. Obejmuje: narzędzia, materiały budowlane, odzież, środki higieny, opał.  
Uprawnienia do nadawania: jednostki administracyjne osad, autoryzowani rzemieślnicy  
Priorytet transportu: standardowy  
Czas dostawy: maksymalnie 7 dni w obrębie jednego regionu  

**Kategoria E - Osobista**  
Przesyłki nadawane przez osoby fizyczne do innych osób fizycznych. Obejmuje: listy, drobne przedmioty osobiste, pamiątki.  
Uprawnienia do nadawania: każdy obywatel z aktualnym identyfikatorem Systemu  
Priorytet transportu: najniższy  
Czas dostawy: bez gwarancji - zależny od dostępności miejsca w wagonach  

**Kategoria X - Zakazana**  
Kategoria obejmująca przedmioty, których przesyłanie jest bezwzględnie zakazane. Obejmuje: broń i amunicja (z wyjątkiem autoryzowanych transferów między garnizonami), materiały wybuchowe, substancje radioaktywne, nośniki danych niezatwierdzone przez System, urządzenia nadawcze nieautoryzowane, organizmy żywe (z wyjątkiem nasion i kultur bakteryjnych kat. B), alkohol powyżej 1 litra na przesyłkę, książki i publikacje bez stempla cenzury Systemu.
```

### Solution to be implemented
- The application should assign a category based on `.\data\L4_sendit\references\index.md` (section `"4. KLASYFIKACJA PRZESYŁEK"`, subsection `"4.1. Kategorie przesyłek"`). This should be handled by an LLM, and we need a confidence measure.
- Design note: in a real production application, we would need additional safeguards and verification checks. For example, when the LLM assigns category A, that decision should be approved by a human.

## Issue 2: WDP
***Status:*** <span style="color: #b45309;"><strong>Not resolved</strong></span>

According to `.\data\L4_sendit\output\task_result.json`: "Explicit WDP terminology evidence is not yet extracted in Stage 4".

WDP seems to be calculated correctly. However, it should be verified how the model handles the `WDP` abbreviation, which according to `zalacznik-G.md` stands for `Wagony Dodatkowe Płatne`. At this point, I am not sure whether this causes any real issues.

## Thoughts After Stage 5 Implementation

Stage 5 works for the current task, but it leaves two uncertainties:
- Category A is currently an explicit interpretation inside the known task executor.
- WDP still uses the physical number of additional wagons, without a separate terminological fact extracted in Stage 4 (see WDP above).

This means the pipeline already works through Stage 5, but these two areas are exactly the points worth refining before Stage 6.
