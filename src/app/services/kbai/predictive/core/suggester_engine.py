from typing import Dict, Any, List, Optional
from datetime import datetime
from src.common.localization import get_message


class SuggesterEngine:
    """
    Engine to generate dynamic monitoring data and suggestions
    based on actual data vs forecast targets.
    """

    def __init__(self, locale: str = None):
        if not locale:
            try:
                from flask import request

                self.locale = request.headers.get("Accept-Language", "en")
            except Exception:
                self.locale = "en"
        else:
            self.locale = locale

    def generate_monitoraggio(
        self, result: Any, trimester_actuals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates the monitoring block for a specific scenario result.

        Args:
            result: ScenarioResult object containing projections and kpis
            trimester_actuals: List of actual monthly/partial balance data

        Returns:
            Dictionary with metrics monitoring and remaining months.
        """
        if not trimester_actuals or not result.projections:
            return {}

        # 1. Target Data (Last projection year)
        target_p = result.projections[-1]
        target_year = target_p.year

        # 2. Latest Actual Data
        latest_actual = trimester_actuals[-1]
        actual_kpis = latest_actual.get("kpi", {})
        target_kpis = result.kpis.get(target_year, {})

        # 3. Months Remaining
        # Target is usually December of the last year
        target_date = datetime(target_year, 12, 31)
        now = datetime.utcnow()
        months_remaining = (target_date.year - now.year) * 12 + (
            target_date.month - now.month
        )
        if months_remaining < 0:
            months_remaining = 0

        # Define metrics to monitor
        # target_p is a YearProjection object, actual is from a dict (trimester_actuals)
        metrics_defs = [
            {
                "id": "ricavi",
                "target": getattr(target_p, "ricavi", 0),
                "actual": latest_actual.get("ricavi", 0),
            },
            {
                "id": "roi",
                "target": target_kpis.get("ROI", 0),
                "actual": actual_kpis.get("ROI", 0),
            },
            {
                "id": "roe",
                "target": target_kpis.get("ROE", 0),
                "actual": actual_kpis.get("ROE", 0),
            },
            {
                "id": "ros",
                "target": target_kpis.get("ROS", 0),
                "actual": actual_kpis.get("ROS", 0),
            },
            {
                "id": "ebitda",
                "target": getattr(target_p, "ebitda", 0),
                "actual": latest_actual.get("ebitda", 0),
            },
            {
                "id": "ebitda_margin",
                "target": target_kpis.get("EBITDA_Margin", 0),
                "actual": actual_kpis.get("EBITDA_Margin", 0),
            },
            {
                "id": "mdc",
                "target": target_kpis.get("MdC", 0),
                "actual": actual_kpis.get("MdC", 0),
            },
        ]

        monitoraggio_data = {}

        for m in metrics_defs:
            m_id = m["id"]
            target_val = float(m["target"]) if m["target"] is not None else 0.0
            actual_val = float(m["actual"]) if m["actual"] is not None else 0.0

            percent = 0.0
            if target_val != 0:
                # Percentage of completion
                percent = round((actual_val / target_val) * 100, 1)

            suggestions = self._generate_suggestions(
                m_id, actual_val, target_val, actual_kpis
            )

            monitoraggio_data[m_id] = {
                "target_valore": round(target_val, 2),
                "raggiunto_valore": round(actual_val, 2),
                "percentuale_completamento": percent,
                "suggerimenti": suggestions,
            }

        monitoraggio_data["mesi_rimanenti"] = months_remaining
        return monitoraggio_data

    def _generate_suggestions(
        self, metric_id: str, actual: float, target: float, kpis: Dict[str, Any]
    ) -> List[str]:
        """
        Internal logic to pick granular, real-world suggestions as a simple list of strings.
        """
        sugs = []

        # Helper to add suggestion
        def add_sug(key: str):
            sugs.append(get_message(key, self.locale))

        gap_percent = 0
        if target != 0:
            gap_percent = (target - actual) / target

        # 1. RICAVI (Revenues)
        if metric_id == "ricavi":
            if actual < target:
                if gap_percent > 0.20:  # Critical
                    add_sug("pred_sug_ricavi_pricing")
                    add_sug("pred_sug_ricavi_digital_marketing")
                    add_sug("pred_sug_ricavi_mercati")
                    add_sug("pred_sug_ricavi_cause")
                else:  # Moderate
                    add_sug("pred_sug_ricavi_partnership")
                    add_sug("pred_sug_ricavi_cross_selling")
                    add_sug("pred_sug_ricavi_incasso")
            else:  # Met/Exceeded
                add_sug("pred_sug_ricavi_fidelizzazione")
                add_sug("pred_sug_gen_scalability")
                add_sug("pred_sug_gen_innovation")

        # 2. ROI
        elif metric_id == "roi":
            if actual < target:
                if gap_percent > 0.20:  # Critical
                    add_sug("pred_sug_roi_efficiency")
                    add_sug("pred_sug_roi_low_performing")
                else:  # Moderate
                    add_sug("pred_sug_roi_turnover")
                    add_sug("pred_sug_roi_working_capital")
            else:  # Met
                add_sug("pred_sug_roi_reinvestment")
                add_sug("pred_sug_gen_consolidation")

        # 3. ROE
        elif metric_id == "roe":
            if actual < target:
                if gap_percent > 0.15:  # Critical
                    add_sug("pred_sug_roe_profitability")
                    add_sug("pred_sug_roe_refinancing")
                else:  # Moderate
                    add_sug("pred_sug_roe_equity_structure")
                    add_sug("pred_sug_roe_profitability")
            else:  # Met
                add_sug("pred_sug_roe_dividend_policy")
                add_sug("pred_sug_gen_scalability")

        # 4. ROS
        elif metric_id == "ros":
            if actual < target:
                add_sug("pred_sug_ros_premium_price")
                add_sug("pred_sug_ros_cost_control")
                add_sug("pred_sug_ros_discount_policy")
                add_sug("pred_sug_ros_mix")
            else:  # Met
                add_sug("pred_sug_ros_margins")
                add_sug("pred_sug_gen_consolidation")

        # 5. EBITDA / EBITDA MARGIN
        elif metric_id in ["ebitda", "ebitda_margin"]:
            if actual < target:
                if gap_percent > 0.15:  # Critical
                    add_sug("pred_sug_ebitda_opex")
                    add_sug("pred_sug_ebitda_energy")
                    add_sug("pred_sug_ebitda_outsourcing")
                else:  # Moderate
                    add_sug("pred_sug_ebitda_productivity")
                    add_sug("pred_sug_ebitda_digitalization")
                    add_sug("pred_sug_ros_mix")
            else:  # Met
                add_sug("pred_sug_ebitda_productivity")
                add_sug("pred_sug_gen_innovation")

        # 6. MdC (Contribution Margin)
        elif metric_id == "mdc":
            if actual < target:
                add_sug("pred_sug_mdc_supplier_nego")
                add_sug("pred_sug_mdc_waste_reduction")
                add_sug("pred_sug_mdc_logistics")
                add_sug("pred_sug_mdc_variable")
            else:  # Met
                add_sug("pred_sug_mdc_volume")
                add_sug("pred_sug_gen_consolidation")

        # General advice if list is short
        if len(sugs) < 2:
            add_sug("pred_sug_gen_consolidation")

        return sugs[:6]
