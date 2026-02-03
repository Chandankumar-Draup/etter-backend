import traceback
import json
from os import environ
from typing import List, Dict, Tuple
from pandas import DataFrame, Series, concat

from ml_models.simulation import SimulationEngine
from ml_models.simulation import SimulationRequestData
from services.simulation.role_provider import EtterConsoleDataProvider


def get_simulation_engine() -> SimulationEngine:
    """
    Getting the simulation engine based on the provider type
    """

    provider_type = environ.get("SIMULATION_PROVIDER_TYPE", "local")
    if not hasattr(get_simulation_engine, "_engine"):
        if provider_type == "local":
            print("Using LocalSimulationEngine", flush=True)
            get_simulation_engine._engine = SimulationEngine(number_of_months=48)
        else:
            print("Using EtterConsoleDataProvider", flush=True)
            provider = EtterConsoleDataProvider()
            get_simulation_engine._engine = SimulationEngine(
                role_provider=provider, number_of_months=48
            )
    return get_simulation_engine._engine


def transform_simulation_results(
    role_groups: List[Dict], simulation_data: DataFrame
) -> Tuple[List[Dict], List[Dict]]:
    simulation_data.drop(
        columns=["role_groups", "role_provider", "automation_factor"], inplace=True
    )
    total_employee = sum([group["count"] for group in role_groups])
    total_salary = sum([group["salary"] * group["count"] for group in role_groups])

    simulation_data["total_employees"] = (
        simulation_data["total_employees"] * total_employee
    )
    simulation_data["total_salary_of_employees"] = (
        simulation_data["total_salary_of_employees"] * total_salary
    )
    simulation_data["cost_savings"] = (
        simulation_data["total_salary_of_employees"].iloc[0]
        - simulation_data["total_salary_of_employees"]
    )
    simulation_data["headcount_savings"] = (
        simulation_data["total_employees"].iloc[0] - simulation_data["total_employees"]
    )
    for group in role_groups:
        simulation_data[f"{group['role']}_cost_savings"] = (
            simulation_data[f"{group['role']}_total_salary_of_employee"].iloc[0]
            - simulation_data[f"{group['role']}_total_salary_of_employee"]
        )

    agg = {
        "avg_automation_rate": ["mean", "min", "max"],
        "total_employees": ["mean", "min", "max"],
        "avg_time_per_employee": ["mean", "min", "max"],
        "total_salary_of_employees": ["mean", "min", "max"],
        "cost_savings": ["mean", "min", "max"],
        "avg_unused_output_capacity": ["mean", "min", "max"],
        "headcount_savings": ["mean", "min", "max"],
    }

    for group in role_groups:
        for field in [
            "count",
            "cost_savings",
            "avg_automation_rate",
            "avg_time_per_employee",
            "total_salary_of_employee",
            "avg_unused_output_capacity",
        ]:
            agg[f"{group['role']}_{field}"] = ["mean", "min", "max"]
    grouped = simulation_data.groupby("Step").agg(agg).reset_index()

    columns = [
        "Step",
        "automation_mean",
        "automation_min",
        "automation_max",
        "employees_mean",
        "employees_min",
        "employees_max",
        "avg_time_per_employee_mean",
        "avg_time_per_employee_min",
        "avg_time_per_employee_max",
        "total_salary_of_employees_mean",
        "total_salary_of_employees_min",
        "total_salary_of_employees_max",
        "cost_savings_mean",
        "cost_savings_min",
        "cost_savings_max",
        "avg_unused_output_capacity_mean",
        "avg_unused_output_capacity_min",
        "avg_unused_output_capacity_max",
        "headcount_savings_mean",
        "headcount_savings_min",
        "headcount_savings_max",
    ]
    for group in role_groups:
        for field in [
            "count",
            "cost_savings",
            "avg_automation_rate",
            "avg_time_per_employee",
            "total_salary_of_employee",
            "avg_unused_output_capacity",
        ]:
            columns.append(f"{group['role']}_{field}_{'mean'}")
            columns.append(f"{group['role']}_{field}_{'min'}")
            columns.append(f"{group['role']}_{field}_{'max'}")

    grouped.columns = columns
    results = grouped.to_dict(orient="records")

    agg_res = compute_yearly_metrics(grouped).to_dict(orient="records")
    return results, agg_res


def compute_yearly_metrics(simulation_data: DataFrame) -> DataFrame:
    step_interval = 12
    yearly_diffs = DataFrame()
    simulation_data.set_index("Step", inplace=True)

    all_diffs = []
    for col in simulation_data.columns:
        # Calculate the difference for each 'year'
        initial_values = simulation_data[col].iloc[::step_interval].values
        subsequent_values = (
            simulation_data[col].iloc[step_interval::step_interval].values
        )

        # Ensure the lengths match by truncating the longer one
        min_length = min(len(initial_values), len(subsequent_values))
        diffs = subsequent_values[:min_length] - initial_values[:min_length]
        all_diffs.append(Series(diffs, name=col))

    yearly_diffs = concat(all_diffs, axis=1)

    yearly_diffs.index = [f"Year {i + 1}" for i in range(len(yearly_diffs))]
    yearly_diffs["Year"] = [i + 1 for i in range(len(yearly_diffs))]

    return yearly_diffs

def explain_results(role_groups: List[Dict], role_workload_map: List[Dict], yearly_metrics: List[Dict]) -> List[Dict]:
    """
    Generate comprehensive explanations for simulation results.
    
    Analyzes workload characteristics, automation patterns, cost savings,
    and key factors affecting each role's simulation outcomes. Note that
    yearly_metrics contains year-to-year deltas (changes from year n-1 to year n),
    not cumulative values.
    
    Args:
        role_groups: List of role dictionaries with 'role', 'count', 'salary'
        role_workload_map: List of dictionaries mapping roles to their workloads
        yearly_metrics: List of dictionaries containing yearly aggregated metrics.
            Each metric represents the year-to-year change (delta), not cumulative values.
            For example, headcount_saving_mean: 2.2 means 2.2 headcount saved from year n-1 to n.
        
    Returns:
        List of explanation dictionaries, each containing role name and detailed explanation
    """
    explanations = []
    # Create lookup maps for easier access
    workload_map = {item["role"]: item["workloads"] for item in role_workload_map}

    role = role_groups[0]["role"]
    metrics_names = []
    metrics = yearly_metrics[0]
    for keys in metrics.keys():
        if keys.endswith("_mean") and keys.startswith(role):
            metrics_names.append(keys.replace(role + "_", "").replace("_mean", ""))
    yearly_metrics_by_role = sorted(yearly_metrics, key=lambda x: x["Year"])

    for role_group in role_groups:
        role_name = role_group["role"]
        workloads = workload_map.get(role_name, [])
        
        # Initialize variables for use across sections
        auto_workloads = []
        non_auto_workloads = []
        auto_avg_skill = 0
        non_auto_avg_skill = 0
        total_time = 0
        auto_time = 0
        non_auto_time = 0
        
        explanation_parts = []
        
        # 1. Role Overview
        explanation_parts.append(f"## {role_name} Analysis")
        explanation_parts.append(
            f"This role has {role_group['count']} employees with an average salary of "
            f"${role_group['salary']:,.0f} per employee."
        )
        
        # 2. Workload Characteristics
        if workloads:

            workload_list_md = ["\n### Workloads"] + [f"- {workload.get('Name', 'Unnamed')}" for workload in workloads]
            explanation_parts.extend(workload_list_md)

            explanation_parts.append("\n### Workload Characteristics")
            auto_workloads = [
                w for w in workloads
                if w.get("Type", "").lower() in ["auto", "automated"]
            ]
            non_auto_workloads = [
                w for w in workloads
                if w.get("Type", "").lower() in ["non-auto", "non-automated"]
            ]
            
            total_time = sum(w.get("Time", 0) for w in workloads)
            auto_time = sum(w.get("Time", 0) for w in auto_workloads)
            non_auto_time = sum(w.get("Time", 0) for w in non_auto_workloads)
            

            explanation_parts.append(
                f"- **Total Workloads**: {len(workloads)} distinct responsibilities"
            )
            if total_time > 0:
                explanation_parts.append(
                    f"- **Time Distribution**: {auto_time/total_time*100:.1f}% automated, "
                    f"{non_auto_time/total_time*100:.1f}% non-automated"
                )

            # Average skill level
            if auto_workloads:
                auto_avg_skill = (
                    sum(w.get("Skill", 0) for w in auto_workloads) / len(auto_workloads)
                )
            if non_auto_workloads:
                non_auto_avg_skill = (
                    sum(w.get("Skill", 0) for w in non_auto_workloads) / len(non_auto_workloads)
                )
            explanation_parts.append(
                f"- **Average Auto Skill Level**: {auto_avg_skill:.2f} (on a 0-1 scale)"
            )
            explanation_parts.append(
                f"- **Average Non-Auto Skill Level**: {non_auto_avg_skill:.2f} (on a 0-1 scale)"
            )

        

        key = f"{role_name}_count_mean"
        if key in metrics:
            count_change_by_year = [year.get(key)for year in yearly_metrics]
            total_headcount_change = sum(count_change_by_year) if count_change_by_year else 0
            avg_headcount_change = (
                total_headcount_change / len(count_change_by_year)
                if count_change_by_year
                else 0
            )
            
            explanation_parts.append("\n### Workforce Changes")
            explanation_parts.append(
                f"- **Average Year-to-Year Headcount Change**: {avg_headcount_change:.1f} employees "
                f"(average reduction per year)"
            )
            explanation_parts.append(
                f"- **Total Cumulative Headcount Reduction**: {abs(total_headcount_change):.1f} employees "
                f"(sum of all year-to-year reductions)"
            )
            
            # Analyze headcount reduction distribution
            if abs(total_headcount_change) < 0.1:
                # Zero or near-zero reduction
                explanation_parts.append(
                    "  - **No Significant Reduction**: The workload requires too much skill or is "
                    "human-centric, making automation unable to have a meaningful impact on this role. "
                    "The complexity and skill requirements of the responsibilities prevent automation "
                    "from reducing headcount."
                )
            elif count_change_by_year:
                # Sort by year and analyze first half vs second half
                total_years = len(count_change_by_year)
                midpoint = total_years // 2
                
                # First half: years 1 to midpoint
                first_half_reductions = sum(abs(count_change) for count_change in count_change_by_year[:midpoint])
                # Second half: years midpoint+1 to total years
                second_half_reductions = sum(abs(count_change) for count_change in count_change_by_year[midpoint:])
                
                total_reductions = first_half_reductions + second_half_reductions

                if total_reductions > 0:
                    first_half_pct = (first_half_reductions / total_reductions * 100)
                    second_half_pct = (second_half_reductions / total_reductions * 100)
                    
                    if first_half_pct > 60:
                        explanation_parts.append(
                            f"- **Early Reduction Pattern**: {first_half_pct:.1f}% of headcount reduction "
                            f"occurs in the first half of the simulation period (Years 1-{midpoint}). "
                            f"This indicates that automated workloads are relatively easy to automate "
                            f"and require less skill, allowing employees and the firm to quickly benefit "
                            f"from automation."
                        )
                    elif second_half_pct > 60:
                        explanation_parts.append(
                            f"- **Late Reduction Pattern**: {second_half_pct:.1f}% of headcount reduction "
                            f"occurs in the second half of the simulation period (Years {midpoint+1}+). "
                            f"This indicates that automated workloads are more complex and require higher "
                            f"skill levels, meaning employees and the firm slowly benefit from automation "
                            f"as skills are developed over time."
                        )
                    else:
                        explanation_parts.append(
                            f"- **Balanced Reduction Pattern**: Headcount reduction is distributed relatively "
                            f"evenly across the simulation period ({first_half_pct:.1f}% in first half, "
                            f"{second_half_pct:.1f}% in second half), indicating a mix of automation "
                            f"complexities and skill requirements."
                        )
        
        # 6. Time Efficiency
        if "avg_time_per_employee" in metrics:
            time_changes = metrics["avg_time_per_employee"]
            avg_time_change = (
                sum(time_changes) / len(time_changes) if time_changes else 0
            )
            
            explanation_parts.append("\n### Time Efficiency")
            explanation_parts.append(
                f"- **Average Year-to-Year Time Change**: {avg_time_change*100:.2f}% "
                f"(average change per year)"
            )
            if avg_time_change < -0.01:
                explanation_parts.append(
                    f"  - **Improved Efficiency**: Average time per employee decreased by "
                    f"{abs(avg_time_change)*100:.2f}% per year on average, indicating better "
                    f"workload distribution as automation progresses."
                )
            elif avg_time_change > 0.01:
                explanation_parts.append(
                    f"  - **Increased Time**: Average time per employee increased by "
                    f"{avg_time_change*100:.2f}% per year on average, suggesting remaining workloads "
                    f"require more attention as automation reduces headcount."
                )
            else:
                explanation_parts.append(
                    "  - **Stable Time Allocation**: Time per employee remained relatively constant "
                    "year-to-year."
                )
        
        
        # 8. Key Factors Affecting Results
        explanation_parts.append("\n### Key Factors")
        factors = []
        
        if workloads:
            if len(auto_workloads) > len(non_auto_workloads):
                factors.append("A high proportion of workloads are suitable for automation.")
            if auto_avg_skill > 0.7:
                factors.append(
                    "Automated workloads require advanced skills, which slows the pace of automation."
                )
            elif 0 < auto_avg_skill < 0.5:
                factors.append(
                    "Automated workloads require relatively low skill levels, enabling a faster automation process."
                )
            if total_time > 0 and (non_auto_time / total_time) > 0.5:
                factors.append(
                    "A significant portion of employee time is devoted to non-automatable tasks, which limits both the speed and overall benefits of automation."
                )
        
        if "avg_automation_rate" in metrics:
            automation_rates = metrics["avg_automation_rate"]
            if automation_rates and max(automation_rates) > 0.15:
                factors.append("Rapid automation adoption in early years")
        
        if not factors:
            factors.append("Balanced workload characteristics")
        
        for i, factor in enumerate(factors, 1):
            explanation_parts.append(f"{i}. {factor}")

        explanation = "\n".join(explanation_parts)
        
        explanations.append({
            "role": role_name,
            "explanation": explanation,
        })
    
    return explanations

async def run_and_store_simulation(
    data: SimulationRequestData,
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    Background task to run the simulation and update its results.
    """
    engine: SimulationEngine = get_simulation_engine()
    
    results = []
    workloads = []
    yearly_metrics = []
    try:
        if data["n_iterations"] > 0:
            workloads = await engine.get_role_workload_map_async(data["roles"], data["company"])
            results = engine.run_multiple_simulations(
                role_groups=data["roles"],
                company=data["company"],
                automation_factor=data["automation_factor"],
                n_simulations=data["n_iterations"],
            )
            results, yearly_metrics = transform_simulation_results(
                data["roles"], simulation_data=results
            )
            explanations = explain_results(data["roles"], workloads, yearly_metrics)


#         # 9. Limitations and Assumptions
#         limitations_and_assumptions_text = """### Limitations and Assumptions
# - **Linear Automation**: Automation adoption follows a simplified model and may not capture all real-world complexities. For example, the automation factor is fixed for the entire simulation period, and determines the speed of automation adoptions.
# - **Static Workload Model**: Assumes workload characteristics remain constant throughout the simulation period.
# - **Skill Homogeneity**: Assumes uniform skill levels across employees within the same role.
# - **Automation Factor**: The automation factor is fixed for the entire simulation period, and determines the speed of automation adoptions.
# """

        return results, yearly_metrics, workloads, explanations
    except Exception as e:
        print("Error during simulation:", e)
        traceback.print_exc()
        return results, yearly_metrics, workloads, []
