# AI Automation Impact Simulation

### Overview

The APIs enable users to start a multi-agent simulation using an Long Request-Response pattern.
A simulation models workforce impact under automation scenarios, running across multiple **iterations** (independent simulations) and **steps** (time periods within each simulation).

## Base URL

```
http://127.0.0.1:7071
```

## Endpoint

```
/api/etter/simulation/v1
```

---

## Running a Simulation

Send a request with company details, roles, headcount, salaries, and the automation factor.

#### Request (JSON)

```json
{
    "n_iterations": 15,
    "automation_factor": 0.5,
    "roles": [
        {
            "role": "Engineer",
            "count": 300,
            "salary": 80000.0
        },
        {
            "role": "Marketing",
            "count": 100,
            "salary": 70000.0
        }
    ],
    "company": "Google"
}
```

#### Example using cURL

```bash
curl -X POST "http://127.0.0.1:7071/api/etter/simulation/v1" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Google",
    "n_iterations": 15,
    "automation_factor": 0.5,
    "roles": [
        {"role": "Engineer", "count": 300, "salary": 80000},
        {"role": "Marketing", "count": 100, "salary": 70000}
    ]
}'
```

#### Response

```json
{
    "id": "sim-a339f66b-2d41-478b-8597-2d5cd231b9fe",
    "status": "completed",
    "results": [
        {
            "Step": 0,
            "automation_mean": 0.0,
            "automation_min": 0.0,
            "automation_max": 0.0,
            "avg_time_per_employee_mean": 1.0,
            "avg_time_per_employee_min": 1.0,
            "avg_time_per_employee_max": 1.0,
            "employees_mean": 1.0,
            "employees_min": 1.0,
            "employees_max": 1.0,
            "total_salary_of_employees_mean": 1.0,
            "total_salary_of_employees_min": 1.0,
            "total_salary_of_employees_max": 1.0,
            "avg_unused_output_capacity_mean": 0.0,
            "avg_unused_output_capacity_min": 0.0,
            "avg_unused_output_capacity_max": 0.0,
            "Engineer_count_mean": 50.0,
            "Engineer_count_min": 50,
            "Engineer_count_max": 50,
            "Engineer_avg_automation_rate_mean": 0.0,
            "Engineer_avg_automation_rate_min": 0.0,
            "Engineer_avg_automation_rate_max": 0.0,
            "Engineer_avg_time_per_employee_mean": 1.0,
            "Engineer_avg_time_per_employee_min": 1.0,
            "Engineer_avg_time_per_employee_max": 1.0,
            "Engineer_total_salary_of_employee_mean": 4000000.0,
            "Engineer_total_salary_of_employee_min": 4000000.0,
            "Engineer_total_salary_of_employee_max": 4000000.0,
            "Engineer_avg_unused_output_capacity_mean": 0.0,
            "Engineer_avg_unused_output_capacity_min": 0.0,
            "Engineer_avg_unused_output_capacity_max": 0.0,
            "Marketing_count_mean": 100.0,
            "Marketing_count_min": 100,
            "Marketing_count_max": 100,
            "Marketing_avg_automation_rate_mean": 0.0,
            "Marketing_avg_automation_rate_min": 0.0,
            "Marketing_avg_automation_rate_max": 0.0,
            "Marketing_avg_time_per_employee_mean": 1.0,
            "Marketing_avg_time_per_employee_min": 1.0,
            "Marketing_avg_time_per_employee_max": 1.0,
            "Marketing_total_salary_of_employee_mean": 7000000.0,
            "Marketing_total_salary_of_employee_min": 7000000.0,
            "Marketing_total_salary_of_employee_max": 7000000.0,
            "Marketing_avg_unused_output_capacity_mean": 0.0,
            "Marketing_avg_unused_output_capacity_min": 0.0,
            "Marketing_avg_unused_output_capacity_max": 0.0
        },
        {
            "Step": 1,
            "automation_mean": 0.0,
            "automation_min": 0.0,
            "automation_max": 0.0,
            "avg_time_per_employee_mean": 1.0,
            "avg_time_per_employee_min": 1.0,
            "avg_time_per_employee_max": 1.0,
            "employees_mean": 1.0,
            "employees_min": 1.0,
            "employees_max": 1.0,
            "total_salary_of_employees_mean": 1.0,
            "total_salary_of_employees_min": 1.0,
            "total_salary_of_employees_max": 1.0,
            "avg_unused_output_capacity_mean": 0.0,
            "avg_unused_output_capacity_min": 0.0,
            "avg_unused_output_capacity_max": 0.0,
            "Engineer_count_mean": 50.0,
            "Engineer_count_min": 50,
            "Engineer_count_max": 50,
            "Engineer_avg_automation_rate_mean": 0.0,
            "Engineer_avg_automation_rate_min": 0.0,
            "Engineer_avg_automation_rate_max": 0.0,
            "Engineer_avg_time_per_employee_mean": 1.0,
            "Engineer_avg_time_per_employee_min": 1.0,
            "Engineer_avg_time_per_employee_max": 1.0,
            "Engineer_total_salary_of_employee_mean": 4000000.0,
            "Engineer_total_salary_of_employee_min": 4000000.0,
            "Engineer_total_salary_of_employee_max": 4000000.0,
            "Engineer_avg_unused_output_capacity_mean": 0.0,
            "Engineer_avg_unused_output_capacity_min": 0.0,
            "Engineer_avg_unused_output_capacity_max": 0.0,
            "Marketing_count_mean": 100.0,
            "Marketing_count_min": 100,
            "Marketing_count_max": 100,
            "Marketing_avg_automation_rate_mean": 0.0,
            "Marketing_avg_automation_rate_min": 0.0,
            "Marketing_avg_automation_rate_max": 0.0,
            "Marketing_avg_time_per_employee_mean": 1.0,
            "Marketing_avg_time_per_employee_min": 1.0,
            "Marketing_avg_time_per_employee_max": 1.0,
            "Marketing_total_salary_of_employee_mean": 7000000.0,
            "Marketing_total_salary_of_employee_min": 7000000.0,
            "Marketing_total_salary_of_employee_max": 7000000.0,
            "Marketing_avg_unused_output_capacity_mean": 0.0,
            "Marketing_avg_unused_output_capacity_min": 0.0,
            "Marketing_avg_unused_output_capacity_max": 0.0
        },
        ...
{
            "Step": 120,
            "automation_mean": 0.5,
            "automation_min": 0.5,
            "automation_max": 0.5,
            "avg_time_per_employee_mean": 0.7333333333333334,
            "avg_time_per_employee_min": 0.72,
            "avg_time_per_employee_max": 0.7466666666666667,
            "employees_mean": 0.5456349206349211,
            "employees_min": 0.5357142857142864,
            "employees_max": 0.5555555555555559,
            "total_salary_of_employees_mean": 0.7209090909090909,
            "total_salary_of_employees_min": 0.7090909090909091,
            "total_salary_of_employees_max": 0.7327272727272728,
            "avg_unused_output_capacity_mean": 1.0907186948853647,
            "avg_unused_output_capacity_min": 1.08024691358025,
            "avg_unused_output_capacity_max": 1.1011904761904792,
            "Engineer_count_mean": 23.0,
            "Engineer_count_min": 22,
            "Engineer_count_max": 24,
            "Engineer_avg_automation_rate_mean": 0.5,
            "Engineer_avg_automation_rate_min": 0.5,
            "Engineer_avg_automation_rate_max": 0.5,
            "Engineer_avg_time_per_employee_mean": 0.6534090909090908,
            "Engineer_avg_time_per_employee_min": 0.6249999999999999,
            "Engineer_avg_time_per_employee_max": 0.6818181818181819,
            "Engineer_total_salary_of_employee_mean": 1840000.0,
            "Engineer_total_salary_of_employee_min": 1760000.0,
            "Engineer_total_salary_of_employee_max": 1920000.0,
            "Engineer_avg_unused_output_capacity_mean": 1.1553030303030303,
            "Engineer_avg_unused_output_capacity_min": 1.0606060606060603,
            "Engineer_avg_unused_output_capacity_max": 1.25,
            "Marketing_count_mean": 87.0,
            "Marketing_count_min": 84,
            "Marketing_count_max": 90,
            "Marketing_avg_automation_rate_mean": 0.5,
            "Marketing_avg_automation_rate_min": 0.5,
            "Marketing_avg_automation_rate_max": 0.5,
            "Marketing_avg_time_per_employee_mean": 0.5178571428571429,
            "Marketing_avg_time_per_employee_min": 0.5000000000000001,
            "Marketing_avg_time_per_employee_max": 0.5357142857142857,
            "Marketing_total_salary_of_employee_mean": 6090000.0,
            "Marketing_total_salary_of_employee_min": 5880000.0,
            "Marketing_total_salary_of_employee_max": 6300000.0,
            "Marketing_avg_unused_output_capacity_mean": 1.0714285714285716,
            "Marketing_avg_unused_output_capacity_min": 1.031746031746032,
            "Marketing_avg_unused_output_capacity_max": 1.1111111111111112
        }
    ],
    "input_data": {
        "n_iterations": 2,
        "company": "Google",
        "automation_factor": 0.5,
        "roles": [
            {
                "role": "Engineer",
                "count": 50,
                "salary": 80000.0
            },
            {
                "role": "Marketing",
                "count": 100,
                "salary": 70000.0
            }
        ]
    },
    "workloads": [
        {
            "role": "Engineer",
            "workloads": [
                {
                    "Name": "Write code",
                    "Type": "Auto",
                    "Skill": 0.9,
                    "Time": 0.5
                },
                {
                    "Name": "Review code",
                    "Type": "Non-Auto",
                    "Skill": 0.8,
                    "Time": 0.125
                },
                {
                    "Name": "Automated testing",
                    "Type": "Auto",
                    "Skill": 0.7,
                    "Time": 0.2
                },
                {
                    "Name": "Debug production issues",
                    "Type": "Non-Auto",
                    "Skill": 0.85,
                    "Time": 0.175
                }
            ]
        },
        {
            "role": "Marketing",
            "workloads": [
                {
                    "Name": "Content creation",
                    "Type": "Auto",
                    "Skill": 0.85,
                    "Time": 0.4
                },
                {
                    "Name": "SEO optimization",
                    "Type": "Auto",
                    "Skill": 0.7,
                    "Time": 0.15
                },
                {
                    "Name": "Market research",
                    "Type": "Non-Auto",
                    "Skill": 0.75,
                    "Time": 0.2
                },
                {
                    "Name": "Social media campaigns",
                    "Type": "Non-Auto",
                    "Skill": 0.8,
                    "Time": 0.25
                }
            ]
        }
    ]
}
```

## Historic Simulation results

Use the simulation ID to get the results on any simulation

* `created` → `in_progress` → **`completed`**
* `created` → `in_progress` → **`failed`**

#### Request

```http
GET /api/etter/simulation/v1/{simulation_id}
```

#### Example using cURL

```bash
curl -X GET "http://127.0.0.1:7071/api/etter/simulation/v1/0a1e3f53-451a-4842-8356-66e61a4db333" \
  -H "Content-Type: application/json"
```

#### Response (completed)

```json
{
    "id": "sim-a339f66b-2d41-478b-8597-2d5cd231b9fe",
    "status": "completed",
    "results": [
        {
            "Step": 0,
            "automation_mean": 0.0,
            "automation_min": 0.0,
            "automation_max": 0.0,
            "avg_time_per_employee_mean": 1.0,
            "avg_time_per_employee_min": 1.0,
            "avg_time_per_employee_max": 1.0,
            "employees_mean": 1.0,
            "employees_min": 1.0,
            "employees_max": 1.0,
            "total_salary_of_employees_mean": 1.0,
            "total_salary_of_employees_min": 1.0,
            "total_salary_of_employees_max": 1.0,
            "avg_unused_output_capacity_mean": 0.0,
            "avg_unused_output_capacity_min": 0.0,
            "avg_unused_output_capacity_max": 0.0,
            "Engineer_count_mean": 50.0,
            "Engineer_count_min": 50,
            "Engineer_count_max": 50,
            "Engineer_avg_automation_rate_mean": 0.0,
            "Engineer_avg_automation_rate_min": 0.0,
            "Engineer_avg_automation_rate_max": 0.0,
            "Engineer_avg_time_per_employee_mean": 1.0,
            "Engineer_avg_time_per_employee_min": 1.0,
            "Engineer_avg_time_per_employee_max": 1.0,
            "Engineer_total_salary_of_employee_mean": 4000000.0,
            "Engineer_total_salary_of_employee_min": 4000000.0,
            "Engineer_total_salary_of_employee_max": 4000000.0,
            "Engineer_avg_unused_output_capacity_mean": 0.0,
            "Engineer_avg_unused_output_capacity_min": 0.0,
            "Engineer_avg_unused_output_capacity_max": 0.0,
            "Marketing_count_mean": 100.0,
            "Marketing_count_min": 100,
            "Marketing_count_max": 100,
            "Marketing_avg_automation_rate_mean": 0.0,
            "Marketing_avg_automation_rate_min": 0.0,
            "Marketing_avg_automation_rate_max": 0.0,
            "Marketing_avg_time_per_employee_mean": 1.0,
            "Marketing_avg_time_per_employee_min": 1.0,
            "Marketing_avg_time_per_employee_max": 1.0,
            "Marketing_total_salary_of_employee_mean": 7000000.0,
            "Marketing_total_salary_of_employee_min": 7000000.0,
            "Marketing_total_salary_of_employee_max": 7000000.0,
            "Marketing_avg_unused_output_capacity_mean": 0.0,
            "Marketing_avg_unused_output_capacity_min": 0.0,
            "Marketing_avg_unused_output_capacity_max": 0.0
        },
        {
            "Step": 1,
            "automation_mean": 0.0,
            "automation_min": 0.0,
            "automation_max": 0.0,
            "avg_time_per_employee_mean": 1.0,
            "avg_time_per_employee_min": 1.0,
            "avg_time_per_employee_max": 1.0,
            "employees_mean": 1.0,
            "employees_min": 1.0,
            "employees_max": 1.0,
            "total_salary_of_employees_mean": 1.0,
            "total_salary_of_employees_min": 1.0,
            "total_salary_of_employees_max": 1.0,
            "avg_unused_output_capacity_mean": 0.0,
            "avg_unused_output_capacity_min": 0.0,
            "avg_unused_output_capacity_max": 0.0,
            "Engineer_count_mean": 50.0,
            "Engineer_count_min": 50,
            "Engineer_count_max": 50,
            "Engineer_avg_automation_rate_mean": 0.0,
            "Engineer_avg_automation_rate_min": 0.0,
            "Engineer_avg_automation_rate_max": 0.0,
            "Engineer_avg_time_per_employee_mean": 1.0,
            "Engineer_avg_time_per_employee_min": 1.0,
            "Engineer_avg_time_per_employee_max": 1.0,
            "Engineer_total_salary_of_employee_mean": 4000000.0,
            "Engineer_total_salary_of_employee_min": 4000000.0,
            "Engineer_total_salary_of_employee_max": 4000000.0,
            "Engineer_avg_unused_output_capacity_mean": 0.0,
            "Engineer_avg_unused_output_capacity_min": 0.0,
            "Engineer_avg_unused_output_capacity_max": 0.0,
            "Marketing_count_mean": 100.0,
            "Marketing_count_min": 100,
            "Marketing_count_max": 100,
            "Marketing_avg_automation_rate_mean": 0.0,
            "Marketing_avg_automation_rate_min": 0.0,
            "Marketing_avg_automation_rate_max": 0.0,
            "Marketing_avg_time_per_employee_mean": 1.0,
            "Marketing_avg_time_per_employee_min": 1.0,
            "Marketing_avg_time_per_employee_max": 1.0,
            "Marketing_total_salary_of_employee_mean": 7000000.0,
            "Marketing_total_salary_of_employee_min": 7000000.0,
            "Marketing_total_salary_of_employee_max": 7000000.0,
            "Marketing_avg_unused_output_capacity_mean": 0.0,
            "Marketing_avg_unused_output_capacity_min": 0.0,
            "Marketing_avg_unused_output_capacity_max": 0.0
        },
        ...
{
            "Step": 120,
            "automation_mean": 0.5,
            "automation_min": 0.5,
            "automation_max": 0.5,
            "avg_time_per_employee_mean": 0.7333333333333334,
            "avg_time_per_employee_min": 0.72,
            "avg_time_per_employee_max": 0.7466666666666667,
            "employees_mean": 0.5456349206349211,
            "employees_min": 0.5357142857142864,
            "employees_max": 0.5555555555555559,
            "total_salary_of_employees_mean": 0.7209090909090909,
            "total_salary_of_employees_min": 0.7090909090909091,
            "total_salary_of_employees_max": 0.7327272727272728,
            "avg_unused_output_capacity_mean": 1.0907186948853647,
            "avg_unused_output_capacity_min": 1.08024691358025,
            "avg_unused_output_capacity_max": 1.1011904761904792,
            "Engineer_count_mean": 23.0,
            "Engineer_count_min": 22,
            "Engineer_count_max": 24,
            "Engineer_avg_automation_rate_mean": 0.5,
            "Engineer_avg_automation_rate_min": 0.5,
            "Engineer_avg_automation_rate_max": 0.5,
            "Engineer_avg_time_per_employee_mean": 0.6534090909090908,
            "Engineer_avg_time_per_employee_min": 0.6249999999999999,
            "Engineer_avg_time_per_employee_max": 0.6818181818181819,
            "Engineer_total_salary_of_employee_mean": 1840000.0,
            "Engineer_total_salary_of_employee_min": 1760000.0,
            "Engineer_total_salary_of_employee_max": 1920000.0,
            "Engineer_avg_unused_output_capacity_mean": 1.1553030303030303,
            "Engineer_avg_unused_output_capacity_min": 1.0606060606060603,
            "Engineer_avg_unused_output_capacity_max": 1.25,
            "Marketing_count_mean": 87.0,
            "Marketing_count_min": 84,
            "Marketing_count_max": 90,
            "Marketing_avg_automation_rate_mean": 0.5,
            "Marketing_avg_automation_rate_min": 0.5,
            "Marketing_avg_automation_rate_max": 0.5,
            "Marketing_avg_time_per_employee_mean": 0.5178571428571429,
            "Marketing_avg_time_per_employee_min": 0.5000000000000001,
            "Marketing_avg_time_per_employee_max": 0.5357142857142857,
            "Marketing_total_salary_of_employee_mean": 6090000.0,
            "Marketing_total_salary_of_employee_min": 5880000.0,
            "Marketing_total_salary_of_employee_max": 6300000.0,
            "Marketing_avg_unused_output_capacity_mean": 1.0714285714285716,
            "Marketing_avg_unused_output_capacity_min": 1.031746031746032,
            "Marketing_avg_unused_output_capacity_max": 1.1111111111111112
        }
    ],
    "input_data": {
        "n_iterations": 2,
        "company": "Google",
        "automation_factor": 0.5,
        "roles": [
            {
                "role": "Engineer",
                "count": 50,
                "salary": 80000.0
            },
            {
                "role": "Marketing",
                "count": 100,
                "salary": 70000.0
            }
        ]
    },
    "workloads": [
        {
            "role": "Engineer",
            "workloads": [
                {
                    "Name": "Write code",
                    "Type": "Auto",
                    "Skill": 0.9,
                    "Time": 0.5
                },
                {
                    "Name": "Review code",
                    "Type": "Non-Auto",
                    "Skill": 0.8,
                    "Time": 0.125
                },
                {
                    "Name": "Automated testing",
                    "Type": "Auto",
                    "Skill": 0.7,
                    "Time": 0.2
                },
                {
                    "Name": "Debug production issues",
                    "Type": "Non-Auto",
                    "Skill": 0.85,
                    "Time": 0.175
                }
            ]
        },
        {
            "role": "Marketing",
            "workloads": [
                {
                    "Name": "Content creation",
                    "Type": "Auto",
                    "Skill": 0.85,
                    "Time": 0.4
                },
                {
                    "Name": "SEO optimization",
                    "Type": "Auto",
                    "Skill": 0.7,
                    "Time": 0.15
                },
                {
                    "Name": "Market research",
                    "Type": "Non-Auto",
                    "Skill": 0.75,
                    "Time": 0.2
                },
                {
                    "Name": "Social media campaigns",
                    "Type": "Non-Auto",
                    "Skill": 0.8,
                    "Time": 0.25
                }
            ]
        }
    ]
}
```

---

## Field Explanations

| Field                                     | Description                                                              |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| **iteration**                             | The number of independent simulations to run.                            |
| **Step**                                  | Each step represents one month in the simulation timeline.               |
| **total\_time**                           | Total time available to employees in a step.              |
| **avg\_time\_per\_employee**              | Average time available per employee per step.                            |
| **avg\_automation\_rate**                 | Average automation rate applied to roles (0–1).                          |
| **total\_employees**                      | Percentage of the starting employee population still active.             |
| **total\_salary\_of\_employees**          | Total salary of remaining employees (scaled to starting baseline = 1.0). |
| **avg\_unused\_output\_capacity**         | Average unused capacity across employees (Maximum output capacity - Current output).               |
| **{Role}\_count**                         | Current number of employees in the role.                                 |
| **{Role}\_total\_salary\_of\_employee**   | Total salary of employees in that role.                                  |
| **{Role}\_avg\_automation\_rate**         | Average automation applied to that role.                                 |
| **{Role}\_avg\_time\_per\_employee**      | Average time per employee in that role (weekly).                         |
| **{Role}\_avg\_unused\_output\_capacity** | Average unused output capacity per employee in that role.                |

