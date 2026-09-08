"""comparative_analytics.py — Week-over-week comparisons across health domains."""

from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request
from api.blueprints import state
from api.blueprints.helpers import require_user_and_auth, coerce_int, parse_iso_datetime

comparative_bp = Blueprint('comparative_analytics', __name__)


def calculate_weekly_stats(data_points, date_key, value_keys, cutoff_date):
    """
    Calculate weekly statistics from data points.
    
    Args:
        data_points: List of dicts with date and value data
        date_key: Key containing the date/timestamp
        value_keys: List of keys containing numeric values to aggregate
        cutoff_date: Only include data after this date
    """
    weekly_data = {}
    
    for point in data_points:
        try:
            if date_key in point:
                dt = parse_iso_datetime(point[date_key])
            else:
                continue
                
            if dt < cutoff_date:
                continue
                
            # Calculate week number (ISO week)
            week_key = dt.strftime("%Y-W%W")
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "week_start": (dt - timedelta(days=dt.weekday())).date().isoformat(),
                    "week_end": (dt + timedelta(days=6 - dt.weekday())).date().isoformat(),
                    "count": 0,
                    "values": {key: [] for key in value_keys}
                }
            
            weekly_data[week_key]["count"] += 1
            for key in value_keys:
                if key in point and point[key] is not None:
                    try:
                        weekly_data[week_key]["values"][key].append(float(point[key]))
                    except (ValueError, TypeError):
                        pass
                        
        except Exception:
            continue
    
    results = []
    for week_key, data in sorted(weekly_data.items()):
        week_result = {
            "week": week_key,
            "week_start": data["week_start"],
            "week_end": data["week_end"],
            "count": data["count"]
        }
        
        for key in value_keys:
            values = data["values"][key]
            if values:
                week_result[f"{key}_avg"] = round(sum(values) / len(values), 2)
                week_result[f"{key}_total"] = round(sum(values), 2)
                week_result[f"{key}_min"] = round(min(values), 2)
                week_result[f"{key}_max"] = round(max(values), 2)
            else:
                week_result[f"{key}_avg"] = 0
                week_result[f"{key}_total"] = 0
                week_result[f"{key}_min"] = 0
                week_result[f"{key}_max"] = 0
        
        results.append(week_result)
    
    return results


def calculate_week_over_week_change(current_week, previous_week, metric_key):
    """Calculate percentage change between weeks for a specific metric."""
    current_val = current_week.get(f"{metric_key}_avg", 0)
    previous_val = previous_week.get(f"{metric_key}_avg", 0)
    
    if previous_val == 0:
        if current_val > 0:
            return "increased_from_zero", 100.0
        return "no_change", 0.0
    
    change_pct = ((current_val - previous_val) / previous_val) * 100
    
    if change_pct > 5:
        return "increased", round(change_pct, 1)
    elif change_pct < -5:
        return "decreased", round(abs(change_pct), 1)
    else:
        return "stable", round(change_pct, 1)


def generate_explanation(domain, metric, direction, change_pct, context=None):
    """Generate human-readable explanation for trend changes."""
    if direction == "stable":
        return f"{metric} remained stable with minimal change ({change_pct}%)."
    
    direction_word = "increased" if direction == "increased" else "decreased"
    
    explanations = {
        "activity": {
            "duration_minutes": f"Activity duration {direction_word} by {change_pct}% compared to last week.",
            "energy_after": f"Post-activity energy levels {direction_word} by {change_pct}%.",
        },
        "sleep": {
            "duration_hours": f"Sleep duration {direction_word} by {change_pct}% compared to last week.",
            "quality_score": f"Sleep quality {direction_word} by {change_pct}%.",
        },
        "nutrition": {
            "calories": f"Daily calorie intake {direction_word} by {change_pct}% compared to last week.",
            "protein_g": f"Protein intake {direction_word} by {change_pct}% compared to last week.",
        },
        "productivity": {
            "focus_score": f"Focus scores {direction_word} by {change_pct}% compared to last week.",
            "effectiveness": f"Session effectiveness {direction_word} by {change_pct}%.",
        }
    }
    
    domain_explanations = explanations.get(domain, {})
    return domain_explanations.get(metric, f"{metric} {direction_word} by {change_pct}%.")


def calculate_confidence(data_points_count, week_count):
    """Calculate confidence score based on data availability."""
    if week_count < 2:
        return "low", "Insufficient weekly data for comparison"
    
    if data_points_count < 5:
        return "low", "Limited data points - trends may not be representative"
    
    if data_points_count < 15:
        return "medium", "Moderate data availability - trends are reasonably reliable"
    
    return "high", "Strong data availability - trends are highly reliable"


def analyze_domain(data_points, date_key, metrics, domain_name, cutoff_date):
    """
    Generic domain analysis to reduce code duplication.
    
    Args:
        data_points: List of data points for the domain
        date_key: Key containing the date/timestamp
        metrics: List of metric keys to analyze
        domain_name: Name of the domain for explanations
        cutoff_date: Only include data after this date
    
    Returns:
        Dict with weekly_data, week_over_week_trends, and confidence
    """
    weekly_data = calculate_weekly_stats(data_points, date_key, metrics, cutoff_date)
    
    trends = []
    for i in range(1, len(weekly_data)):
        current = weekly_data[i]
        previous = weekly_data[i-1]
        
        week_trend = {
            "week": current["week"],
            "metrics": {}
        }
        
        for metric in metrics:
            direction, change_pct = calculate_week_over_week_change(current, previous, metric)
            explanation = generate_explanation(domain_name, metric, direction, change_pct)
            
            week_trend["metrics"][metric] = {
                "current_avg": current[f"{metric}_avg"],
                "previous_avg": previous[f"{metric}_avg"],
                "change_pct": change_pct,
                "direction": direction,
                "explanation": explanation
            }
        
        trends.append(week_trend)
    
    confidence_level, confidence_reason = calculate_confidence(len(data_points), len(weekly_data))
    
    return {
        "weekly_data": weekly_data,
        "week_over_week_trends": trends,
        "confidence": {
            "level": confidence_level,
            "reason": confidence_reason,
            "data_points": len(data_points),
            "weeks_with_data": len(weekly_data)
        }
    }


@comparative_bp.route('/api/comparative-analytics/<user_id>', methods=['GET'])
def get_comparative_analytics(user_id):
    """
    Return week-over-week comparative analytics across all health domains.
    
    Query params:
        weeks : int  — number of weeks to analyze (default 4, max 12)
        domains : str — comma-separated list of domains (activity,sleep,nutrition,productivity)
    """
    user, err = require_user_and_auth(user_id)
    if err:
        return err

    weeks, weeks_err = coerce_int(request.args.get('weeks', 4), 4, minimum=2, maximum=12)
    if weeks_err:
        return weeks_err

    domains_param = request.args.get('domains', 'activity,sleep,nutrition,productivity')
    domains = [d.strip() for d in domains_param.split(',') if d.strip()]
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    
    results = {
        "user_id": user_id,
        "analysis_period": {
            "weeks_analyzed": weeks,
            "start_date": cutoff_date.date().isoformat(),
            "end_date": datetime.now(timezone.utc).date().isoformat()
        },
        "domains": {}
    }
    
    # Activity analytics
    if "activity" in domains:
        activity_logs = state.activity_logs.get(user_id, [])
        results["domains"]["activity"] = analyze_domain(
            activity_logs, 
            "timestamp", 
            ["duration_minutes", "energy_after"],
            "activity",
            cutoff_date
        )
    
    # Sleep analytics
    if "sleep" in domains:
        sleep_logs = state.sleep_logs.get(user_id, [])
        results["domains"]["sleep"] = analyze_domain(
            sleep_logs,
            "timestamp",
            ["duration_hours", "quality_score"],
            "sleep",
            cutoff_date
        )
    
    # Nutrition analytics
    if "nutrition" in domains:
        daily_logs = state.daily_logs.get(user_id, {})
        nutrition_data = []
        
        for date_str, daily_log in daily_logs.items():
            try:
                dt = datetime.fromisoformat(date_str)
                if dt >= cutoff_date:
                    total = daily_log.get_total_nutrition()
                    nutrition_data.append({
                        "date": date_str,
                        "calories": total.calories,
                        "protein_g": total.protein_g,
                        "carbs_g": total.carbs_g,
                        "fat_g": total.fat_g
                    })
            except Exception:
                continue
        
        results["domains"]["nutrition"] = analyze_domain(
            nutrition_data,
            "date",
            ["calories", "protein_g"],
            "nutrition",
            cutoff_date
        )
    
    # Productivity analytics
    if "productivity" in domains:
        productivity_sessions = state.productivity_sessions.get(user_id, [])
        results["domains"]["productivity"] = analyze_domain(
            productivity_sessions,
            "timestamp",
            ["predicted_focus_score", "effectiveness"],
            "productivity",
            cutoff_date
        )
    
    return jsonify(results), 200