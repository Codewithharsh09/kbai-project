# kpi_analysis_helper.py

from typing import Dict, List, Any
from collections import defaultdict
from src.extensions import db
from src.app.database.models.kbai_balance.analysis_kpi_info import AnalysisKpiInfo

# KPI_META removed as it is now localized dynamically
from flask import request
from src.common.localization import get_message

def pct_change(old_val, new_val):
    if old_val == 0:
        return 0
    return ((new_val - old_val) / abs(old_val)) * 100

def format_pct(value: float) -> str:
    if value is None:
        return ""
    sign = "+" if value > 0 else ""
    return f"{sign}{round(value, 1)}%"

def evaluate_kpi_status(values: List[float], kpi_name: str) -> str:
    valid = [v for v in values if isinstance(v, (int, float)) and v is not None]

    # Hard overrides
    if kpi_name in ["EBITDA", "EBIT_Reddito_Operativo"] and valid and valid[-1] < 0:
        return "ALARMING"

    if kpi_name == "Patrimonio_Netto" and valid and valid[-1] < 0:
        return "ALARMING"

    if len(valid) == 3:
        v1, v2, v3 = valid
        score = 0

        trend = pct_change(v1, v3)
        momentum = pct_change(v2, v3)

        score += 2 if trend > 15 else 1 if trend > 0 else -1 if trend >= -15 else -2
        score += 2 if momentum > 10 else 1 if momentum > 0 else -1 if momentum >= -10 else -2

        if v2 > v1 and v3 > v2:
            score += 1
        elif v2 < v1 and v3 < v2:
            score -= 1

        if score <= -3:
            return "ALARMING"
        elif score <= -1:
            return "RISKY"
        elif score <= 1:
            return "AVERAGE"
        else:
            return "GOOD"

    if len(valid) == 2:
        change = pct_change(valid[0], valid[1])
        if change > 10:
            return "GOOD"
        elif change >= -10:
            return "AVERAGE"
        elif change >= -25:
            return "RISKY"
        else:
            return "ALARMING"

    return "AVERAGE"

def build_time_based_synthesis(year_values: list, locale: str = 'en') -> str:
    """
    year_values: [(year, value), ...] sorted by year
    """

    if len(year_values) < 2:
        return get_message("insufficient_historical_data", locale)

    (y1, v1), (y2, v2) = year_values[-2], year_values[-1]
    yoy = pct_change(v1, v2)

    direction = "increase" if yoy > 0 else "decrease"

    if len(year_values) == 2:
        return get_message(
            "synthesis_2_years", 
            locale, 
            direction=direction, 
            yoy=format_pct(yoy)
        )

    # 3 years
    (y0, v0) = year_values[0]
    trend = pct_change(v0, v2)

    long_dir = "increase" if trend > 0 else "decrease"
    short_dir = "increase" if yoy > 0 else "decrease"

    return get_message(
        "synthesis_3_years",
        locale,
        long_dir=long_dir,
        trend=format_pct(trend),
        y0=y0,
        short_dir=short_dir,
        yoy=format_pct(yoy)
    )

def calculate_kpi_statuses(kpi_years: Dict[str, list]) -> Dict[str, str]:
    statuses = {}

    for kpi_name, year_values in kpi_years.items():
        sorted_values = sorted(year_values, key=lambda x: x[0])
        values = [v for _, v in sorted_values]
        statuses[kpi_name] = evaluate_kpi_status(values, kpi_name)

    return statuses

def build_kpi_insight(kpi_name: str, status: str, year_values: list) -> Dict[str, str]:
    locale = request.headers.get('Accept-Language', 'en')
    
    dynamic_synthesis = build_time_based_synthesis(year_values, locale)

    # Dynamic suggestion retrieval
    # Key format: kpi_{kpi_name}_{status}_suggestion
    suggestion_key = f"kpi_{kpi_name}_{status}_suggestion"
    suggestion = get_message(suggestion_key, locale)
    
    # Fallback if key not found (can happen for new KPIs not yet in localization)
    if suggestion == suggestion_key:
        suggestion = ""

    return {
        "synthesis": dynamic_synthesis,
        "suggestion": suggestion,
        "note": status
    }

def store_analysis_kpi_info(analysis_id, kpi_values, kpi_statuses, balances):

    kpi_year_map = defaultdict(list)
    kpi_name_to_kv = {}

    balance_year_map = {
        b.id_balance: b.year
        for b in balances
    }

    for kv in kpi_values:
        year = balance_year_map.get(kv.id_balance)
        if year is None:
            continue

        value = float(kv.value) if kv.value is not None else None
        kpi_year_map[kv.kpi_name].append((year, value))

        if kv.kpi_name not in kpi_name_to_kv:
            kpi_name_to_kv[kv.kpi_name] = kv

    for kpi_name, status in kpi_statuses.items():
        kv = kpi_name_to_kv.get(kpi_name)
        if not kv:
            continue

        year_values = sorted(kpi_year_map.get(kpi_name, []))

        insight = build_kpi_insight(kpi_name, status, year_values)

        record = AnalysisKpiInfo(
            id_analysis=analysis_id,
            id_kpi=kv.id_kpi,
            synthesis=insight["synthesis"],
            suggestion=insight["suggestion"],
            note=None
        )

        db.session.merge(record)

    db.session.commit()

def calculate_goal_percentage(year_values: list) -> float:
    """
    Calculate relative performance percentage for a KPI.

    year_values: [(year, value), ...]
    Formula:
        Goal % = (Current − Worst) / (Best − Worst) × 100
    """

    if not year_values:
        return 0.0

    # Sort by year to get latest value
    sorted_values = sorted(year_values, key=lambda x: x[0])
    values = [v for _, v in sorted_values if v is not None]

    if len(values) < 2:
        return 0.0

    current = values[-1]
    worst = min(values)
    best = max(values)

    if best == worst:
        return 100.0

    goal = ((current - worst) / (best - worst)) * 100
    return round(goal, 1)


# =============================================================================
# COMPETITOR-SPECIFIC FUNCTIONS
# =============================================================================

def evaluate_competitor_status(competitor_value: float, benchmark_baseline: float, kpi_name: str) -> str:
    """
    Calculate competitor KPI status by comparing against benchmark baseline.
    
    Args:
        competitor_value: Competitor's KPI value
        benchmark_baseline: Average of 3 benchmark balance values
        kpi_name: Name of the KPI
    
    Returns:
        Status: ALARMING, RISKY, AVERAGE, or GOOD
    """
    if competitor_value is None or benchmark_baseline is None:
        return "AVERAGE"
    
    # Hard overrides (same as benchmark logic)
    if kpi_name in ["EBITDA", "EBIT_Reddito_Operativo"] and competitor_value < 0:
        return "ALARMING"
    
    if kpi_name == "Patrimonio_Netto" and competitor_value < 0:
        return "ALARMING"
    
    # Avoid division by zero
    if benchmark_baseline == 0:
        return "AVERAGE"
    
    # Calculate percentage difference
    pct_diff = ((competitor_value - benchmark_baseline) / abs(benchmark_baseline)) * 100
    
    # Status mapping based on competitor performance vs benchmark
    # For positive KPIs (higher is better): EBITDA, Ricavi_Totali, etc.
    positive_kpis = ["EBITDA", "EBIT_Reddito_Operativo", "Patrimonio_Netto", 
                     "Ricavi_Totali", "MOL_RICAVI_%", "EBITDA_Margin_%", 
                     "Margine_Contribuzione_%", "Mark_Up"]
    
    # For negative KPIs (lower is better): Costi_Variabili, Spese_Generali_Ratio, Fatturato_Equilibrio_BEP
    negative_kpis = ["Costi_Variabili", "Spese_Generali_Ratio", "Fatturato_Equilibrio_BEP"]
    
    if kpi_name in positive_kpis:
        # Higher is better
        if pct_diff > 20:  # Competitor is 20%+ better
            return "GOOD"
        elif pct_diff > 5:  # Competitor is 5-20% better
            return "AVERAGE"
        elif pct_diff >= -10:  # Competitor is within -10% to +5%
            return "AVERAGE"
        elif pct_diff >= -25:  # Competitor is 10-25% worse
            return "RISKY"
        else:  # Competitor is >25% worse
            return "ALARMING"
    
    elif kpi_name in negative_kpis:
        # Lower is better (inverse logic)
        if pct_diff < -20:  # Competitor is 20%+ lower (better)
            return "GOOD"
        elif pct_diff < -5:  # Competitor is 5-20% lower (better)
            return "AVERAGE"
        elif pct_diff <= 10:  # Competitor is within -5% to +10%
            return "AVERAGE"
        elif pct_diff <= 25:  # Competitor is 10-25% higher (worse)
            return "RISKY"
        else:  # Competitor is >25% higher (worse)
            return "ALARMING"
    
    # Default for unknown KPIs
    return "AVERAGE"


def calculate_competitor_goal_percentage(
    competitor_value: float,
    benchmark_baseline: float,
    kpi_name: str
) -> float:
    """
    Calculate goal percentage showing competitive position.
    
    Formula: Goal % = (Competitor / Benchmark_Baseline) × 100
    
    Interpretation:
    - 100% = Equal performance (competitor aur company same level)
    - >100% = Competitor AAGE hai (e.g., 120% = competitor 20% better)
    - <100% = Company AAGE hai (e.g., 80% = company 20% better, competitor pichhe)
    
    For negative KPIs (lower is better), formula is inverted:
    Goal % = (Benchmark_Baseline / Competitor) × 100
    
    Args:
        competitor_value: Competitor ka KPI value
        benchmark_baseline: Company ka average (3 benchmark balances se)
        kpi_name: KPI ka naam
    
    Returns:
        Goal percentage (100 = equal, >100 = competitor aage, <100 = company aage)
    """
    if competitor_value is None or benchmark_baseline is None:
        return 0.0
    
    if benchmark_baseline == 0:
        return 0.0
    
    # Positive KPIs (higher is better): EBITDA, Ricavi, etc.
    positive_kpis = ["EBITDA", "EBIT_Reddito_Operativo", "Patrimonio_Netto", 
                     "Ricavi_Totali", "MOL_RICAVI_%", "EBITDA_Margin_%", 
                     "Margine_Contribuzione_%", "Mark_Up"]
    
    # Negative KPIs (lower is better): Costi, Spese, BEP
    negative_kpis = ["Costi_Variabili", "Spese_Generali_Ratio", "Fatturato_Equilibrio_BEP"]
    
    if kpi_name in positive_kpis:
        # Higher is better: (Competitor / Company) × 100
        goal = (competitor_value / benchmark_baseline) * 100
    elif kpi_name in negative_kpis:
        # Lower is better: (Company / Competitor) × 100
        if competitor_value == 0:
            return 0.0
        goal = (benchmark_baseline / competitor_value) * 100
    else:
        # Default: positive KPI logic
        goal = (competitor_value / benchmark_baseline) * 100
    
    return round(goal, 1)


def build_competitor_synthesis(
    kpi_name: str,
    competitor_value: float,
    benchmark_baseline: float,
    benchmark_years: list,
    goal_percentage: float
) -> str:
    """
    Generate synthesis text showing clear competitive position.
    Shows: Competitor kitna aage/pichhe hai, Company kitna aage/pichhe hai.
    """
    locale = request.headers.get('Accept-Language', 'en')

    if competitor_value is None or benchmark_baseline is None:
        return get_message("competitor_insufficient_data", locale)
    
    pct_diff = ((competitor_value - benchmark_baseline) / abs(benchmark_baseline)) * 100
    years_str = ", ".join(str(y) for y in sorted(set(benchmark_years)))
    
    # Format values
    comp_val_str = f"{competitor_value:,.2f}"
    company_val_str = f"{benchmark_baseline:,.2f}"
    
    # Determine who is ahead
    if abs(pct_diff) < 1:  # Essentially equal (< 1% difference)
        return get_message(
            "competitor_levels_similar",
            locale,
            kpi_name=kpi_name,
            comp_val_str=comp_val_str,
            company_val_str=company_val_str,
            years_str=years_str,
            gap=abs(round(pct_diff, 1))
        )
    
    if pct_diff > 0:
        # Competitor is ahead (better)
        ahead_by = abs(round(pct_diff, 1))
        return get_message(
            "competitor_ahead",
            locale,
            ahead_by=ahead_by,
            kpi_name=kpi_name,
            comp_val_str=comp_val_str,
            company_val_str=company_val_str,
            years_str=years_str,
            goal_percentage=goal_percentage
        )
    else:
        # Company is ahead (better)
        ahead_by = abs(round(pct_diff, 1))
        return get_message(
            "company_ahead",
            locale,
            ahead_by=ahead_by,
            kpi_name=kpi_name,
            company_val_str=company_val_str,
            years_str=years_str,
            comp_val_str=comp_val_str,
            goal_percentage=goal_percentage
        )


def build_competitor_suggestion(
    kpi_name: str,
    status: str,
    competitor_value: float,
    benchmark_baseline: float,
    goal_percentage: float,
    pct_diff: float
) -> str:
    """
    Generate suggestions based on competitive position.
    """
    locale = request.headers.get('Accept-Language', 'en')
    
    # Base suggestion from KPI meta (now dynamic)
    suggestion_key = f"kpi_{kpi_name}_{status}_suggestion"
    base_suggestion = get_message(suggestion_key, locale)
    if base_suggestion == suggestion_key:
        base_suggestion = ""
    
    # Competitive positioning context
    if abs(pct_diff) < 5:
        competitive_advice = get_message("competitor_advice_closely_matched", locale)
    elif pct_diff > 20:
        competitive_advice = get_message(
            "competitor_advice_significantly_ahead",
            locale,
            diff=abs(round(pct_diff, 1))
        )
    elif pct_diff > 5:
        competitive_advice = get_message(
            "competitor_advice_advantage",
            locale,
            diff=abs(round(pct_diff, 1))
        )
    elif pct_diff > -5:
        competitive_advice = get_message(
            "competitor_advice_balanced",
            locale,
            goal_percentage=goal_percentage
        )
    elif pct_diff > -20:
        competitive_advice = get_message(
            "competitor_advice_company_ahead",
            locale,
            diff=abs(round(pct_diff, 1))
        )
    else:
        competitive_advice = get_message(
            "competitor_advice_strong_advantage",
            locale,
            diff=abs(round(pct_diff, 1))
        )
    
    return base_suggestion + competitive_advice


def calculate_competitor_kpi_statuses(
    competitor_kpi_data: Dict[str, float],
    benchmark_kpi_data: Dict[str, list]
) -> Dict[str, str]:
    """
    Calculate statuses for all competitor KPIs.
    
    Args:
        competitor_kpi_data: {kpi_name: value} - Single competitor values
        benchmark_kpi_data: {kpi_name: [(year, value), ...]} - Benchmark values
    
    Returns:
        {kpi_name: status} dictionary
    """
    statuses = {}
    
    for kpi_name, comp_value in competitor_kpi_data.items():
        benchmark_values = benchmark_kpi_data.get(kpi_name, [])
        
        if not benchmark_values:
            statuses[kpi_name] = "AVERAGE"
            continue
        
        # Calculate benchmark baseline (average)
        values = [v for _, v in sorted(benchmark_values)]
        benchmark_baseline = sum(values) / len(values) if values else 0
        
        statuses[kpi_name] = evaluate_competitor_status(
            comp_value, benchmark_baseline, kpi_name
        )
    
    return statuses


def build_competitor_kpi_insight(
    kpi_name: str,
    competitor_value: float,
    benchmark_baseline: float,
    benchmark_min: float,
    benchmark_max: float,
    benchmark_years: list,
    status: str
) -> Dict[str, Any]:
    """
    Build complete KPI insight for competitor with revised goal and text.
    """
    # Calculate goal percentage (shows competitor vs benchmark baseline)
    goal_percentage = calculate_competitor_goal_percentage(
        competitor_value, benchmark_baseline, kpi_name
    )
    
    # Calculate percentage difference
    pct_diff = ((competitor_value - benchmark_baseline) / abs(benchmark_baseline)) * 100 if benchmark_baseline != 0 else 0
    
    # Build competitor-specific synthesis
    synthesis = build_competitor_synthesis(
        kpi_name, competitor_value, benchmark_baseline, 
        benchmark_years, goal_percentage
    )
    
    # Build competitor-specific suggestion
    suggestion = build_competitor_suggestion(
        kpi_name, status, competitor_value, 
        benchmark_baseline, goal_percentage, pct_diff
    )
    
    return {
        "synthesis": synthesis,
        "suggestion": suggestion,
        "goal": goal_percentage,  # 100 = equal, >100 = competitor aage, <100 = company aage
        "status": status
    }