"""
Flask API Blueprint for the Digital Twin UI.

Exposes REST endpoints that wrap the simulation engine, graph validator,
and scope selector. All endpoints return JSON.

Routes:
    GET  /api/dt/readiness           - Graph readiness score
    GET  /api/dt/taxonomy            - Full taxonomy tree
    GET  /api/dt/hierarchy           - Full hierarchy with entity counts at every level
    GET  /api/dt/functions           - List functions for scope dropdowns
    GET  /api/dt/scope/<type>/<name> - Scoped entity data
    GET  /api/dt/technologies        - Available technology profiles
    POST /api/dt/simulate            - Run a simulation (v1 or v2 engine)
    GET  /api/dt/scenarios           - List scenarios
    GET  /api/dt/scenarios/<id>      - Get scenario detail
    DELETE /api/dt/scenarios/<id>    - Delete a scenario
    POST /api/dt/compare             - Compare scenarios
    POST /api/dt/chat                - Chat with the graph (SSE streaming)

Simulation types:
    role_redesign      - Automate tasks by factor, assess role impact
    tech_adoption      - Deploy a specific technology, assess impact
    multi_tech_adoption - Deploy multiple technologies simultaneously
    task_distribution  - Set target automation distribution across tasks
"""

import logging
import traceback
from typing import Optional

from flask import Blueprint, Response, jsonify, request, stream_with_context

logger = logging.getLogger(__name__)

dt_api = Blueprint("dt_api", __name__, url_prefix="/api/dt")

# Module-level state: set by init_api() when the app starts.
_neo4j_conn = None
_scenario_manager = None
_chat_engine = None


def init_api(neo4j_conn):
    """Initialize API with a Neo4j connection. Called once at app startup."""
    global _neo4j_conn, _scenario_manager, _chat_engine
    _neo4j_conn = neo4j_conn

    from draup_world_model.digital_twin.simulation.scenario_manager import (
        ScenarioManager,
    )
    _scenario_manager = ScenarioManager(neo4j_conn)

    # Initialize chat engine — load schema once at startup
    try:
        from draup_world_model.digital_twin.chat.schema import schema_context
        from draup_world_model.digital_twin.chat.engine import ChatEngine

        schema_context.load(neo4j_conn)
        _chat_engine = ChatEngine(neo4j_conn, schema_context.context)
        logger.info("Chat engine initialized with schema context")
    except Exception as e:
        logger.warning("Chat engine initialization failed: %s", e)
    logger.info("Digital Twin API initialized")


def _get_conn():
    if _neo4j_conn is None:
        raise RuntimeError("API not initialized - call init_api() first")
    return _neo4j_conn


def _get_manager():
    if _scenario_manager is None:
        raise RuntimeError("API not initialized - call init_api() first")
    return _scenario_manager


# ── Readiness & Validation ──────────────────────────────────────────


@dt_api.route("/readiness")
def get_readiness():
    """Get graph readiness score with dimension breakdown."""
    try:
        from draup_world_model.digital_twin.graph.validator import GraphValidator
        validator = GraphValidator(_get_conn())
        readiness = validator.compute_readiness_score()
        validation = validator.validate()
        return jsonify({
            "readiness": readiness,
            "validation": validation,
        })
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Taxonomy ────────────────────────────────────────────────────────


@dt_api.route("/taxonomy")
def get_taxonomy():
    """Get full taxonomy tree for navigation."""
    try:
        conn = _get_conn()
        query = """
        MATCH (o:DTOrganization)-[:DT_CONTAINS]->(f:DTFunction)
        OPTIONAL MATCH (f)-[:DT_CONTAINS]->(sf:DTSubFunction)
        OPTIONAL MATCH (sf)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
        OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(jf:DTJobFamily)
        RETURN o.name AS org, o.id AS org_id,
               f.name AS func_name, f.id AS func_id,
               f.headcount AS func_hc,
               collect(DISTINCT {
                   name: sf.name, id: sf.id,
                   groups: collect(DISTINCT {name: jfg.name, id: jfg.id})
               }) AS sub_functions
        ORDER BY f.name
        """
        # Use a simpler query that builds the tree in Python
        func_query = """
        MATCH (f:DTFunction)
        OPTIONAL MATCH (f)<-[:DT_CONTAINS]-(o:DTOrganization)
        RETURN f.id AS id, f.name AS name,
               COALESCE(f.computed_headcount, 0) AS headcount,
               o.name AS org_name, o.id AS org_id
        ORDER BY f.name
        """
        functions = conn.execute_read_query(func_query)

        sf_query = """
        MATCH (f:DTFunction)-[:DT_CONTAINS]->(sf:DTSubFunction)
        RETURN f.id AS func_id, sf.id AS id, sf.name AS name,
               COALESCE(sf.total_headcount, 0) AS headcount
        ORDER BY sf.name
        """
        sub_functions = conn.execute_read_query(sf_query)

        jfg_query = """
        MATCH (sf:DTSubFunction)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
        RETURN sf.id AS sf_id, jfg.id AS id, jfg.name AS name,
               COALESCE(jfg.total_headcount, 0) AS headcount
        ORDER BY jfg.name
        """
        job_family_groups = conn.execute_read_query(jfg_query)

        jf_query = """
        MATCH (jfg:DTJobFamilyGroup)-[:DT_CONTAINS]->(jf:DTJobFamily)
        RETURN jfg.id AS jfg_id, jf.id AS id, jf.name AS name,
               COALESCE(jf.total_headcount, 0) AS headcount
        ORDER BY jf.name
        """
        job_families = conn.execute_read_query(jf_query)

        # Build tree
        org_name = functions[0]["org_name"] if functions else "Acme Corporation"
        org_id = functions[0]["org_id"] if functions else "org_acme"

        # Index children by parent
        sf_by_func = {}
        for sf in sub_functions:
            sf_by_func.setdefault(sf["func_id"], []).append(
                {"id": sf["id"], "name": sf["name"], "type": "sub_function",
                 "headcount": sf.get("headcount") or 0, "children": []}
            )

        jfg_by_sf = {}
        for jfg in job_family_groups:
            jfg_by_sf.setdefault(jfg["sf_id"], []).append(
                {"id": jfg["id"], "name": jfg["name"], "type": "job_family_group",
                 "headcount": jfg.get("headcount") or 0, "children": []}
            )

        jf_by_jfg = {}
        for jf in job_families:
            jf_by_jfg.setdefault(jf["jfg_id"], []).append(
                {"id": jf["id"], "name": jf["name"], "type": "job_family",
                 "headcount": jf.get("headcount") or 0}
            )

        # Assemble tree
        func_nodes = []
        for f in functions:
            sfs = sf_by_func.get(f["id"], [])
            for sf_node in sfs:
                jfgs = jfg_by_sf.get(sf_node["id"], [])
                for jfg_node in jfgs:
                    jfg_node["children"] = jf_by_jfg.get(jfg_node["id"], [])
                sf_node["children"] = jfgs
            func_nodes.append({
                "id": f["id"],
                "name": f["name"],
                "type": "function",
                "headcount": f.get("headcount", 0),
                "children": sfs,
            })

        total_hc = sum(f.get("headcount", 0) for f in func_nodes)
        tree = {
            "id": org_id,
            "name": org_name,
            "type": "organization",
            "headcount": total_hc,
            "children": func_nodes,
        }

        return jsonify({"taxonomy": tree})

    except Exception as e:
        logger.error(f"Taxonomy fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Hierarchy (full expandable tree with counts) ───────────────────


@dt_api.route("/hierarchy")
def get_hierarchy():
    """
    Get full organizational hierarchy with entity counts at every level.

    Returns a tree: Organization → Functions → SubFunctions → JobFamilyGroups
    → JobFamilies → Roles, with headcount/task/skill counts aggregated.
    """
    try:
        conn = _get_conn()

        # Fetch all taxonomy levels
        func_query = """
        MATCH (f:DTFunction)
        OPTIONAL MATCH (f)<-[:DT_CONTAINS]-(o:DTOrganization)
        OPTIONAL MATCH (f)-[:DT_CONTAINS]->(:DTSubFunction)-[:DT_CONTAINS]->
                        (:DTJobFamilyGroup)-[:DT_CONTAINS]->(:DTJobFamily)
                        -[:DT_HAS_ROLE]->(r:DTRole)
        OPTIONAL MATCH (r)-[:DT_HAS_WORKLOAD]->(:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
        RETURN f.id AS id, f.name AS name,
               COALESCE(f.computed_headcount, 0) AS headcount,
               o.name AS org_name, o.id AS org_id,
               count(DISTINCT r) AS role_count,
               count(DISTINCT t) AS task_count
        ORDER BY f.name
        """
        functions = conn.execute_read_query(func_query)

        sf_query = """
        MATCH (f:DTFunction)-[:DT_CONTAINS]->(sf:DTSubFunction)
        OPTIONAL MATCH (sf)-[:DT_CONTAINS]->(:DTJobFamilyGroup)-[:DT_CONTAINS]->
                        (:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
        RETURN f.id AS func_id, sf.id AS id, sf.name AS name,
               count(DISTINCT r) AS role_count
        ORDER BY sf.name
        """
        sub_functions = conn.execute_read_query(sf_query)

        jfg_query = """
        MATCH (sf:DTSubFunction)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
        OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
        RETURN sf.id AS sf_id, jfg.id AS id, jfg.name AS name,
               count(DISTINCT r) AS role_count
        ORDER BY jfg.name
        """
        job_family_groups = conn.execute_read_query(jfg_query)

        jf_query = """
        MATCH (jfg:DTJobFamilyGroup)-[:DT_CONTAINS]->(jf:DTJobFamily)
        OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(r:DTRole)
        RETURN jfg.id AS jfg_id, jf.id AS id, jf.name AS name,
               count(DISTINCT r) AS role_count
        ORDER BY jf.name
        """
        job_families = conn.execute_read_query(jf_query)

        role_query = """
        MATCH (jf:DTJobFamily)-[:DT_HAS_ROLE]->(r:DTRole)
        OPTIONAL MATCH (r)-[:DT_HAS_WORKLOAD]->(w:DTWorkload)-[:DT_CONTAINS_TASK]->(t:DTTask)
        RETURN jf.id AS jf_id, r.id AS id, r.name AS name,
               COALESCE(r.computed_headcount, 0) AS headcount,
               COALESCE(r.computed_automation_score, r.automation_score, 0) AS automation_score,
               count(DISTINCT t) AS task_count
        ORDER BY r.name
        """
        roles = conn.execute_read_query(role_query)

        # Build tree bottom-up
        org_name = functions[0]["org_name"] if functions else "Acme Corporation"
        org_id = functions[0]["org_id"] if functions else "org_acme"

        roles_by_jf = {}
        for r in roles:
            roles_by_jf.setdefault(r["jf_id"], []).append({
                "id": r["id"], "name": r["name"], "type": "role",
                "headcount": r.get("headcount") or 0,
                "task_count": r.get("task_count") or 0,
                "automation_score": r.get("automation_score") or 0,
            })

        from draup_world_model.digital_twin.automation import weighted_automation_score
        _weighted_auto = weighted_automation_score

        jf_by_jfg = {}
        for jf in job_families:
            children = roles_by_jf.get(jf["id"], [])
            hc = sum(c.get("headcount", 0) for c in children)
            jf_by_jfg.setdefault(jf["jfg_id"], []).append({
                "id": jf["id"], "name": jf["name"], "type": "job_family",
                "role_count": jf.get("role_count") or 0,
                "headcount": hc,
                "automation_score": _weighted_auto(children),
                "children": children,
            })

        jfg_by_sf = {}
        for jfg in job_family_groups:
            children = jf_by_jfg.get(jfg["id"], [])
            hc = sum(c.get("headcount", 0) for c in children)
            jfg_by_sf.setdefault(jfg["sf_id"], []).append({
                "id": jfg["id"], "name": jfg["name"], "type": "job_family_group",
                "role_count": jfg.get("role_count") or 0,
                "headcount": hc,
                "automation_score": _weighted_auto(children),
                "children": children,
            })

        sf_by_func = {}
        for sf in sub_functions:
            children = jfg_by_sf.get(sf["id"], [])
            hc = sum(c.get("headcount", 0) for c in children)
            sf_by_func.setdefault(sf["func_id"], []).append({
                "id": sf["id"], "name": sf["name"], "type": "sub_function",
                "role_count": sf.get("role_count") or 0,
                "headcount": hc,
                "automation_score": _weighted_auto(children),
                "children": children,
            })

        func_nodes = []
        total_hc = 0
        total_roles = 0
        total_tasks = 0
        for f in functions:
            children = sf_by_func.get(f["id"], [])
            hc = f.get("headcount") or sum(c.get("headcount", 0) for c in children)
            total_hc += hc
            total_roles += f.get("role_count") or 0
            total_tasks += f.get("task_count") or 0
            func_nodes.append({
                "id": f["id"], "name": f["name"], "type": "function",
                "headcount": hc,
                "role_count": f.get("role_count") or 0,
                "task_count": f.get("task_count") or 0,
                "automation_score": _weighted_auto(children),
                "children": children,
            })

        tree = {
            "id": org_id,
            "name": org_name,
            "type": "organization",
            "headcount": total_hc,
            "role_count": total_roles,
            "task_count": total_tasks,
            "automation_score": _weighted_auto(func_nodes),
            "children": func_nodes,
        }

        return jsonify({"hierarchy": tree})

    except Exception as e:
        logger.error(f"Hierarchy fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Scope ───────────────────────────────────────────────────────────


@dt_api.route("/scope/<scope_type>/<scope_name>")
def get_scope(scope_type: str, scope_name: str):
    """Get all entities within an organizational scope."""
    try:
        from draup_world_model.digital_twin.simulation.scope_selector import ScopeSelector
        selector = ScopeSelector(_get_conn())
        data = selector.select(scope_type, scope_name)
        return jsonify({"scope": data})
    except Exception as e:
        logger.error(f"Scope selection failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Technologies ────────────────────────────────────────────────────


@dt_api.route("/technologies")
def list_technologies():
    """List available technology profiles for tech adoption simulation."""
    from draup_world_model.digital_twin.simulation.simulations.tech_adoption import (
        TechAdoptionSimulation,
        TECHNOLOGY_PROFILES,
    )
    techs = []
    for name, profile in TECHNOLOGY_PROFILES.items():
        techs.append({
            "name": name,
            "vendor": profile["vendor"],
            "license_tier": profile["license_tier"],
            "capabilities": profile["capabilities"],
            "adoption_speed": profile["adoption_speed"],
        })
    return jsonify({"technologies": techs})


# ── Simulation ──────────────────────────────────────────────────────


@dt_api.route("/simulate", methods=["POST"])
def run_simulation():
    """
    Run a simulation scenario.

    Request body:
        {
            "type": "role_redesign" | "tech_adoption" | "multi_tech_adoption" | "task_distribution",
            "scope_name": "Claims Management",
            "scope_type": "function",              # optional, default "function"
            "name": "My Scenario",                 # optional
            "engine": "v2",                        # optional, "v1" or "v2" (default: "v2")
            "parameters": {                        # optional overrides
                "automation_factor": 0.5,           # role_redesign
                "technology_name": "Microsoft Copilot",  # tech_adoption
                "technology_names": [...],          # multi_tech_adoption
                "adoption_months": 12,
                "distribution_target": {...}        # task_distribution
            },
            "config": {                            # optional advanced settings
                "j_curve_enabled": true,
                "organization": {
                    "initial_resistance": 0.6,
                    "initial_morale": 0.7
                },
                "redeployability_pct": 60.0
            },
            "timeline_months": 36                  # optional
        }
    """
    try:
        body = request.get_json(force=True)
        sim_type = body.get("type", "role_redesign")
        scope_name = body.get("scope_name", "Claims Management")
        scope_type = body.get("scope_type", "function")
        params = body.get("parameters", {})
        timeline = body.get("timeline_months", 36)
        engine = body.get("engine", "v2")
        name = body.get("name", f"{sim_type} - {scope_name}")

        from draup_world_model.digital_twin.simulation.scenario_manager import ScenarioConfig

        # Build a descriptive default name based on simulation type
        if sim_type == "tech_adoption" and "name" not in body:
            tech_name = params.get("technology_name", "Microsoft Copilot")
            name = f"{tech_name} - {scope_name}"
        elif sim_type == "multi_tech_adoption" and "name" not in body:
            tech_names = params.get("technology_names", [])
            name = f"{' + '.join(tech_names)} - {scope_name}"

        config = ScenarioConfig(
            name=name,
            simulation_type=sim_type,
            scope_type=scope_type,
            scope_name=scope_name,
            parameters=params,
            constraints=body.get("constraints", {}),
            timeline_months=timeline,
        )

        # Build SimulationConfig from advanced settings if provided
        adv = body.get("config", {})
        sim_config = _build_sim_config(adv) if adv else None

        manager = _get_manager()
        if sim_config:
            # Create a manager with custom simulation config for this run
            from draup_world_model.digital_twin.simulation.scenario_manager import (
                ScenarioManager,
            )
            manager = ScenarioManager(
                _get_conn(), simulation_config=sim_config
            )

        scenario_id = manager.create_scenario(config)

        if engine == "v2":
            result = manager.run_scenario_v2(scenario_id)
        else:
            result = manager.run_scenario(scenario_id)

        return jsonify({
            "scenario_id": scenario_id,
            "engine": engine,
            "config": {
                "name": name,
                "type": sim_type,
                "scope_type": scope_type,
                "scope_name": scope_name,
                "parameters": params,
                "timeline_months": timeline,
            },
            "result": result,
        })

    except Exception as e:
        logger.error(f"Simulation failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


def _build_sim_config(adv: dict):
    """Build a SimulationConfig from the 'config' dict in the request body."""
    from draup_world_model.digital_twin.config import (
        CascadeConfig,
        FinancialConfig,
        OrganizationProfile,
        SimulationConfig,
    )

    kwargs = {}

    # Financial overrides
    fin_keys = {
        "j_curve_enabled", "j_curve_dip_pct", "j_curve_duration_months",
        "severance_months", "change_management_pct",
        "reskilling_cost_per_skill_per_person",
        "include_tech_cost_in_role_redesign",
        "default_tech_cost_per_user_month",
    }
    fin_overrides = {k: v for k, v in adv.items() if k in fin_keys}
    if fin_overrides:
        kwargs["financial"] = FinancialConfig(**fin_overrides)

    # Organization overrides
    org_data = adv.get("organization", {})
    org_keys = {
        "initial_resistance", "initial_morale", "initial_ai_proficiency",
        "initial_culture_readiness", "culture_time_constant_months",
        "base_annual_attrition_pct",
    }
    org_overrides = {k: v for k, v in org_data.items() if k in org_keys}
    if org_overrides:
        kwargs["organization"] = OrganizationProfile(**org_overrides)

    # Cascade overrides
    cascade_keys = {"redeployability_pct"}
    cascade_overrides = {k: v for k, v in adv.items() if k in cascade_keys}
    if cascade_overrides:
        kwargs["cascade"] = CascadeConfig(**cascade_overrides)

    return SimulationConfig(**kwargs) if kwargs else None


# ── Scenarios ───────────────────────────────────────────────────────


@dt_api.route("/scenarios")
def list_scenarios():
    """List all scenarios."""
    try:
        manager = _get_manager()
        return jsonify({"scenarios": manager.list_scenarios()})
    except Exception as e:
        logger.error("Scenarios list failed: %s", e)
        return jsonify({"scenarios": [], "error": str(e)}), 200


@dt_api.route("/scenarios/<scenario_id>")
def get_scenario(scenario_id: str):
    """Get a specific scenario with results."""
    try:
        manager = _get_manager()
        scenario = manager.get_scenario(scenario_id)
        if not scenario:
            return jsonify({"error": "Scenario not found"}), 404
        return jsonify({"scenario": scenario})
    except Exception as e:
        logger.error("Scenario fetch failed: %s", e)
        return jsonify({"error": str(e)}), 500


@dt_api.route("/scenarios/<scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id: str):
    """Delete a scenario."""
    try:
        manager = _get_manager()
        if manager.delete_scenario(scenario_id):
            return jsonify({"deleted": True})
        return jsonify({"error": "Scenario not found"}), 404
    except Exception as e:
        logger.error("Scenario delete failed: %s", e)
        return jsonify({"error": str(e)}), 500


# ── Comparison ──────────────────────────────────────────────────────


@dt_api.route("/compare", methods=["POST"])
def compare_scenarios():
    """
    Compare multiple scenarios side-by-side.

    Request body:
        {"scenario_ids": ["scenario_1", "scenario_2"]}
    """
    try:
        body = request.get_json(force=True)
        scenario_ids = body.get("scenario_ids", [])
        if len(scenario_ids) < 2:
            return jsonify({"error": "Need at least 2 scenario IDs"}), 400

        manager = _get_manager()
        comparison = manager.compare_scenarios(scenario_ids)
        return jsonify({"comparison": comparison})

    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Functions (for scope dropdowns) ─────────────────────────────────


@dt_api.route("/functions")
def list_functions():
    """List all DTFunction nodes for scope selection dropdowns."""
    try:
        conn = _get_conn()
        query = """
        MATCH (f:DTFunction)
        RETURN f.id AS id, f.name AS name, f.headcount AS headcount
        ORDER BY f.name
        """
        functions = conn.execute_read_query(query)
        return jsonify({"functions": functions})
    except Exception as e:
        logger.error(f"Functions fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


@dt_api.route("/scope_entities")
def list_scope_entities():
    """List all entities available for each scope type (for Graph Explorer scope selector)."""
    try:
        conn = _get_conn()
        scope_queries = {
            "function": "MATCH (n:DTFunction) RETURN n.name AS name ORDER BY n.name",
            "sub_function": "MATCH (n:DTSubFunction) RETURN n.name AS name ORDER BY n.name",
            "job_family_group": "MATCH (n:DTJobFamilyGroup) RETURN n.name AS name ORDER BY n.name",
            "job_family": "MATCH (n:DTJobFamily) RETURN n.name AS name ORDER BY n.name",
            "role": "MATCH (n:DTRole) RETURN n.name AS name ORDER BY n.name",
        }
        result = {}
        for scope_type, q in scope_queries.items():
            rows = conn.execute_read_query(q)
            result[scope_type] = [r["name"] for r in rows if r.get("name")]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Scope entities fetch failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Graph Visualization ────────────────────────────────────────────


@dt_api.route("/graph")
def get_graph():
    """
    Get graph nodes and edges for interactive visualization.

    Query params:
        scope_type  - function|sub_function|organization (default: organization)
        scope_name  - Name of the scope entity (default: all)
        node_types  - Comma-separated node type filter (e.g. DTRole,DTSkill)
        limit       - Max nodes to return (default: 300)
    """
    try:
        conn = _get_conn()
        scope_type = request.args.get("scope_type", "organization")
        scope_name = request.args.get("scope_name", "")
        node_types_param = request.args.get("node_types", "")
        limit = min(int(request.args.get("limit", "300")), 500)

        allowed_types = node_types_param.split(",") if node_types_param else []

        # Common tail for all scope queries: collect nodes, find edges, return
        _graph_tail = """
            UNWIND all_nodes AS n
            WITH DISTINCT n
            WHERE n IS NOT NULL
            WITH collect(n) AS nodes
            UNWIND nodes AS a
            UNWIND nodes AS b
            WITH nodes, a, b
            WHERE id(a) < id(b)
            OPTIONAL MATCH (a)-[r]->(b) WHERE type(r) STARTS WITH 'DT_'
            WITH nodes, collect({src: a.id, tgt: b.id, rel: type(r)}) AS rels_raw
            UNWIND nodes AS n
            WITH collect(DISTINCT {
                id: n.id,
                label: [l IN labels(n) WHERE l STARTS WITH 'DT'][0],
                name: n.name,
                headcount: COALESCE(n.computed_headcount, 0),
                automation: COALESCE(n.automation_potential, n.automation_score),
                description: n.description
            }) AS node_list,
            [r IN rels_raw WHERE r.rel IS NOT NULL] AS edge_list
            RETURN node_list, edge_list
        """

        # Build the scope-specific query to collect nodes and relationships
        if scope_type == "role" and scope_name:
            query = """
            MATCH (role:DTRole {name: $scope_name})
            OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
            OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
            OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
            OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
            WITH collect(DISTINCT role) + collect(DISTINCT wl) +
                 collect(DISTINCT task) + collect(DISTINCT skill) + collect(DISTINCT tech) AS all_nodes
            """ + _graph_tail
            params = {"scope_name": scope_name}
        elif scope_type == "sub_function" and scope_name:
            query = """
            MATCH (sf:DTSubFunction {name: $scope_name})
            OPTIONAL MATCH (sf)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
            OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(jf:DTJobFamily)
            OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(role:DTRole)
            OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
            OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
            OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
            OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
            WITH collect(DISTINCT sf) + collect(DISTINCT jfg) +
                 collect(DISTINCT jf) + collect(DISTINCT role) + collect(DISTINCT wl) +
                 collect(DISTINCT task) + collect(DISTINCT skill) + collect(DISTINCT tech) AS all_nodes
            """ + _graph_tail
            params = {"scope_name": scope_name}
        elif scope_type == "job_family_group" and scope_name:
            query = """
            MATCH (jfg:DTJobFamilyGroup {name: $scope_name})
            OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(jf:DTJobFamily)
            OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(role:DTRole)
            OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
            OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
            OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
            OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
            WITH collect(DISTINCT jfg) + collect(DISTINCT jf) + collect(DISTINCT role) +
                 collect(DISTINCT wl) + collect(DISTINCT task) +
                 collect(DISTINCT skill) + collect(DISTINCT tech) AS all_nodes
            """ + _graph_tail
            params = {"scope_name": scope_name}
        elif scope_type == "job_family" and scope_name:
            query = """
            MATCH (jf:DTJobFamily {name: $scope_name})
            OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(role:DTRole)
            OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
            OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
            OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
            OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
            WITH collect(DISTINCT jf) + collect(DISTINCT role) + collect(DISTINCT wl) +
                 collect(DISTINCT task) + collect(DISTINCT skill) + collect(DISTINCT tech) AS all_nodes
            """ + _graph_tail
            params = {"scope_name": scope_name}
        elif scope_type == "function" and scope_name:
            query = """
            MATCH (f:DTFunction {name: $scope_name})
            OPTIONAL MATCH (f)-[:DT_CONTAINS]->(sf:DTSubFunction)
            OPTIONAL MATCH (sf)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
            OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(jf:DTJobFamily)
            OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(role:DTRole)
            OPTIONAL MATCH (role)-[:DT_HAS_WORKLOAD]->(wl:DTWorkload)
            OPTIONAL MATCH (wl)-[:DT_CONTAINS_TASK]->(task:DTTask)
            OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
            OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
            WITH collect(DISTINCT f) + collect(DISTINCT sf) + collect(DISTINCT jfg) +
                 collect(DISTINCT jf) + collect(DISTINCT role) + collect(DISTINCT wl) +
                 collect(DISTINCT task) + collect(DISTINCT skill) + collect(DISTINCT tech) AS all_nodes
            """ + _graph_tail
            params = {"scope_name": scope_name}
        else:
            # Organization-wide: taxonomy + roles + skills + technologies (no tasks/workloads for perf)
            query = """
            MATCH (o:DTOrganization)-[:DT_CONTAINS]->(f:DTFunction)
            OPTIONAL MATCH (f)-[:DT_CONTAINS]->(sf:DTSubFunction)
            OPTIONAL MATCH (sf)-[:DT_CONTAINS]->(jfg:DTJobFamilyGroup)
            OPTIONAL MATCH (jfg)-[:DT_CONTAINS]->(jf:DTJobFamily)
            OPTIONAL MATCH (jf)-[:DT_HAS_ROLE]->(role:DTRole)
            OPTIONAL MATCH (role)-[:DT_REQUIRES_SKILL]->(skill:DTSkill)
            OPTIONAL MATCH (role)-[:DT_USES_TECHNOLOGY]->(tech:DTTechnology)
            WITH collect(DISTINCT o) + collect(DISTINCT f) + collect(DISTINCT sf) +
                 collect(DISTINCT jfg) + collect(DISTINCT jf) + collect(DISTINCT role) +
                 collect(DISTINCT skill) + collect(DISTINCT tech) AS all_nodes
            """ + _graph_tail
            params = {}

        result = conn.execute_read_query(query, params)

        if not result:
            return jsonify({"nodes": [], "edges": [], "node_types": [], "edge_types": []})

        row = result[0]
        raw_nodes = row.get("node_list", [])
        raw_edges = row.get("edge_list", [])

        # Apply node_types filter and limit
        nodes = []
        node_ids = set()
        for n in raw_nodes:
            if not n.get("id"):
                continue
            if allowed_types and n.get("label") not in allowed_types:
                continue
            if len(nodes) >= limit:
                break
            nodes.append(n)
            node_ids.add(n["id"])

        # Filter edges to only include visible nodes
        edges = []
        for e in raw_edges:
            if e.get("src") in node_ids and e.get("tgt") in node_ids:
                edges.append({
                    "source": e["src"],
                    "target": e["tgt"],
                    "type": e["rel"],
                })

        node_types = sorted(set(n["label"] for n in nodes if n.get("label")))
        edge_types = sorted(set(e["type"] for e in edges if e.get("type")))

        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "node_types": node_types,
            "edge_types": edge_types,
        })

    except Exception as e:
        logger.error(f"Graph fetch failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# ── Node Detail ────────────────────────────────────────────────────


@dt_api.route("/node/<node_id>")
def get_node_detail(node_id: str):
    """
    Get a single node with all properties and its direct relationships.

    Returns the node plus all neighbors grouped by relationship type.
    """
    try:
        conn = _get_conn()

        query = """
        MATCH (n {id: $node_id})
        WHERE any(l IN labels(n) WHERE l STARTS WITH 'DT')
        OPTIONAL MATCH (n)-[r_out]->(m_out)
        WHERE type(r_out) STARTS WITH 'DT_'
        OPTIONAL MATCH (n)<-[r_in]-(m_in)
        WHERE type(r_in) STARTS WITH 'DT_'
        WITH n,
             collect(DISTINCT {
                 direction: 'outgoing',
                 type: type(r_out),
                 node_id: m_out.id,
                 node_label: [l IN labels(m_out) WHERE l STARTS WITH 'DT'][0],
                 node_name: m_out.name
             }) AS out_rels,
             collect(DISTINCT {
                 direction: 'incoming',
                 type: type(r_in),
                 node_id: m_in.id,
                 node_label: [l IN labels(m_in) WHERE l STARTS WITH 'DT'][0],
                 node_name: m_in.name
             }) AS in_rels
        RETURN n,
               [l IN labels(n) WHERE l STARTS WITH 'DT'][0] AS node_label,
               [r IN out_rels WHERE r.type IS NOT NULL] AS outgoing,
               [r IN in_rels WHERE r.type IS NOT NULL] AS incoming
        """
        result = conn.execute_read_query(query, {"node_id": node_id})

        if not result:
            return jsonify({"error": "Node not found"}), 404

        row = result[0]
        node_props = dict(row["n"])
        node_label = row["node_label"]

        # Resolve automation_score: prefer computed (bottom-up) over static
        if "computed_automation_score" in node_props:
            node_props["automation_score"] = node_props.pop("computed_automation_score")
        elif "automation_score" not in node_props and "automation_potential" in node_props:
            node_props["automation_score"] = node_props["automation_potential"]

        # Build relationships list
        relationships = []
        for rel in row.get("outgoing", []):
            relationships.append({
                "direction": "outgoing",
                "type": rel["type"],
                "target": {
                    "id": rel["node_id"],
                    "label": rel["node_label"],
                    "name": rel["node_name"],
                },
            })
        for rel in row.get("incoming", []):
            relationships.append({
                "direction": "incoming",
                "type": rel["type"],
                "source": {
                    "id": rel["node_id"],
                    "label": rel["node_label"],
                    "name": rel["node_name"],
                },
            })

        return jsonify({
            "node": {
                "id": node_id,
                "label": node_label,
                "name": node_props.get("name", node_id),
                "properties": node_props,
            },
            "relationships": relationships,
        })

    except Exception as e:
        logger.error(f"Node detail failed: {e}")
        return jsonify({"error": str(e)}), 500


# ── Chat (SSE streaming) ────────────────────────────────────────────


@dt_api.route("/chat", methods=["POST"])
def chat():
    """
    Stream a chat response via Server-Sent Events.

    Request body:
        { "message": str, "history": [...] }

    Each SSE event is a JSON object with a "type" field:
        status, cypher, data, insight, suggest, error, done
    """
    import json as _json

    if _chat_engine is None:
        return jsonify({"error": "Chat engine not available. Check ANTHROPIC_API_KEY."}), 503

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    history = body.get("history") or []

    def generate():
        try:
            for event in _chat_engine.stream(message, history):
                yield f"data: {_json.dumps(event, default=str)}\n\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"data: {_json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {_json.dumps({'type': 'done', 'time_ms': 0})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
