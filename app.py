import json
import math
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# CAREER VENTURE LAB - PATHWAY MKT-3 (AP CALCULUS | LOCAL-BUSINESS MARKETING AGENCY)
# Full Staged Simulator:
#   Stage 1: Core Engine, AP Calculus Math Panel, Dated Ledger, Save/Load, Tests
#   Stage 2: AI Departmental Handoff Cards, Report Center, Costed Marketing Studio
#   Stage 3: Frozen-Snapshot Practice Assessments & Cross-Course Connections
# ==============================================================================

st.set_page_config(
    page_title="Career Venture Lab | MKT-3 Agency Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DEFAULT MKT-3 BASELINE CONSTANTS (Handbook Pages 40, 70, 98-102) ---
DEFAULT_STATE = {
    "team_id": "TEAM-MKT-01",
    "course": "AP Calculus",
    "pathway_id": "MKT-3",
    "business_name": "Local-Business Marketing Agency",
    "selected_level": "Applied",  # Foundation | Applied | Advanced
    "snapshot_id": "SNAP-0001",
    "state_version": 1,
    "simulation_date": "2027-01-31",
    "base_period": "monthly",
    "working_days": 22,
    "currency": "USD",
    "random_seed": 2027,
    "assumptions": [
        "All figures are fictional teaching defaults from Career Venture Lab MKT-3.",
        "Revenue is recognized only on completed campaign packages, capped by monthly capacity.",
        "Startup equipment ($1,500) is an asset; pre-opening setup ($1,000) is recorded at start.",
        "Client pass-through ad budgets are excluded from agency revenue and profit.",
    ],
    "sources": ["Career Venture Lab Student Handbook (Revised Nov 2026), Pathway MKT-3"],
    "funding": {
        "owner_contribution": 6500.00,
        "equipment_assets": 1500.00,
        "pre_opening_expense": 1000.00,
        "opening_cash": 4000.00,
        "loan_principal": 0.00,
        "interest_rate_monthly": 0.00,
    },
    "inputs": {
        "base_price": 250.00,
        "D0": 12,
        "staff_hours": 80.0,
        "hours_per_unit": 8.0,
        "revision_hours_per_package": 0.0,
        "extra_revision_hourly_cost": 5.00,
        "own_ad_spend": 0.00,
        "client_media_budget": 0.00,
        "refund_amount": 0.00,
        "additional_capex": 0.00,
    },
    "variable_cost_lines": {
        "designer_labor": 40.00,
        "licensed_assets": 10.00,
        "printing_delivery": 20.00,
        "quality_revision_allowance": 10.00,
    },
    "fixed_cost_lines": {
        "software": 250.00,
        "workspace": 300.00,
        "admin": 200.00,
        "hosting": 150.00,
    },
    "cash": 4000.00,
    "debt": 0.00,
    "ledger": [],
    "processed_run_ids": [],
    "processed_campaign_ids": [],
    "ai_recommendations": [],
    "decisions": [],
    "marketing_drafts": [],
    "frozen_assessment": None,
}

MONTHLY_FIXTURE = pd.DataFrame([
    {"month": "2027-01", "requested": 12, "capacity_override": 10, "ad_cost": 0.00},
    {"month": "2027-02", "requested": 13, "capacity_override": 10, "ad_cost": 100.00},
    {"month": "2027-03", "requested": 11, "capacity_override": 7, "ad_cost": 0.00},
])


def init_state():
    if "biz_state" not in st.session_state:
        st.session_state.biz_state = json.loads(json.dumps(DEFAULT_STATE))
    else:
        for k, v in DEFAULT_STATE.items():
            if k not in st.session_state.biz_state:
                st.session_state.biz_state[k] = json.loads(json.dumps(v))


def reset_state():
    team_id = st.session_state.biz_state.get("team_id", "TEAM-MKT-01")
    level = st.session_state.biz_state.get("selected_level", "Applied")
    st.session_state.biz_state = json.loads(json.dumps(DEFAULT_STATE))
    st.session_state.biz_state["team_id"] = team_id
    st.session_state.biz_state["selected_level"] = level


def compute_metrics(state, requested_override=None, capacity_override=None, ad_override=None):
    inp = state["inputs"]
    vlines = state["variable_cost_lines"]
    flines = state["fixed_cost_lines"]

    price = float(inp["base_price"])
    requested = int(inp["D0"] if requested_override is None else requested_override)
    staff_hours = float(inp["staff_hours"])
    hours_per_unit = float(inp["hours_per_unit"])
    rev_hours = float(inp["revision_hours_per_package"])
    extra_rev_cost = float(inp["extra_revision_hourly_cost"])

    total_hours_per_unit = hours_per_unit + rev_hours
    derived_capacity = int(math.floor(staff_hours / total_hours_per_unit)) if total_hours_per_unit > 0 else 0
    capacity = int(capacity_override) if capacity_override is not None else derived_capacity

    sold = min(max(0, requested), max(0, capacity))
    unserved_demand = max(0, requested - sold)

    base_var_unit = sum(float(x) for x in vlines.values())
    variable_per_unit = round(base_var_unit + (rev_hours * extra_rev_cost), 2)
    fixed_total = round(sum(float(x) for x in flines.values()), 2)
    marketing = round(float(inp["own_ad_spend"] if ad_override is None else ad_override), 2)
    refunds = round(float(inp["refund_amount"]), 2)
    capex = round(float(inp["additional_capex"]), 2)

    gross_revenue = round(price * sold, 2)
    net_revenue = round(gross_revenue - refunds, 2)
    variable_expense = round(sold * variable_per_unit, 2)
    operating_profit = round(net_revenue - variable_expense - fixed_total - marketing, 2)
    net_cash_change = round(operating_profit - capex, 2)

    return {
        "price": price,
        "requested": requested,
        "derived_capacity": derived_capacity,
        "capacity": capacity,
        "sold": sold,
        "unserved_demand": unserved_demand,
        "variable_per_unit": variable_per_unit,
        "fixed_total": fixed_total,
        "marketing": marketing,
        "refunds": refunds,
        "capex": capex,
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "variable_expense": variable_expense,
        "total_operating_expense": round(variable_expense + fixed_total + marketing, 2),
        "operating_profit": operating_profit,
        "net_cash_change": net_cash_change,
    }


def record_simulation_step(state, run_id, sim_date, metrics, mode="Normal", campaign_id=None):
    """Idempotent ledger writer: blocks duplicate runs and duplicate campaign charges."""
    if not run_id:
        return False, "Run ID is required."
    if run_id in state["processed_run_ids"]:
        return False, f"Duplicate run_id '{run_id}' rejected. No transactions created."

    if campaign_id and metrics["marketing"] > 0:
        if campaign_id in state["processed_campaign_ids"]:
            return False, f"Duplicate campaign_id '{campaign_id}' rejected. Campaign already charged."
        state["processed_campaign_ids"].append(campaign_id)

    v = state["state_version"]
    tx_base = f"TX-v{v}-{len(state['ledger']) + 1:04d}"

    entries = [
        {
            "transaction_id": f"{tx_base}-REV",
            "run_id": run_id,
            "date": sim_date,
            "mode": mode,
            "event_type": "sales_revenue",
            "category": "Campaign Packages",
            "quantity": metrics["sold"],
            "unit_price": metrics["price"],
            "amount": metrics["net_revenue"],
            "state_version": v,
        },
        {
            "transaction_id": f"{tx_base}-VAR",
            "run_id": run_id,
            "date": sim_date,
            "mode": mode,
            "event_type": "variable_expense",
            "category": "Package Delivery Costs",
            "quantity": metrics["sold"],
            "unit_price": metrics["variable_per_unit"],
            "amount": -metrics["variable_expense"],
            "state_version": v,
        },
        {
            "transaction_id": f"{tx_base}-FIX",
            "run_id": run_id,
            "date": sim_date,
            "mode": mode,
            "event_type": "fixed_expense",
            "category": "Monthly Overhead",
            "quantity": 1,
            "unit_price": metrics["fixed_total"],
            "amount": -metrics["fixed_total"],
            "state_version": v,
        },
    ]

    if metrics["marketing"] > 0:
        entries.append({
            "transaction_id": f"{tx_base}-MKT",
            "run_id": run_id,
            "date": sim_date,
            "mode": mode,
            "event_type": "marketing_expense",
            "category": campaign_id or "Agency Promotion",
            "quantity": 1,
            "unit_price": metrics["marketing"],
            "amount": -metrics["marketing"],
            "state_version": v,
        })

    if metrics["capex"] > 0:
        entries.append({
            "transaction_id": f"{tx_base}-CAPEX",
            "run_id": run_id,
            "date": sim_date,
            "mode": mode,
            "event_type": "capital_expenditure",
            "category": "Equipment Purchase",
            "quantity": 1,
            "unit_price": metrics["capex"],
            "amount": -metrics["capex"],
            "state_version": v,
        })

    state["ledger"].extend(entries)
    state["cash"] = round(state["cash"] + metrics["net_cash_change"], 2)
    state["processed_run_ids"].append(run_id)
    state["state_version"] += 1
    state["snapshot_id"] = f"SNAP-{state['state_version']:04d}"
    state["simulation_date"] = sim_date
    return True, f"Recorded run '{run_id}' -> Advanced to state v{state['state_version']}."


init_state()
state = st.session_state.biz_state

# ==============================================================================
# SIDEBAR: IDENTITY, SNAPSHOT EXPORT/IMPORT, & LEVEL CONTROL
# ==============================================================================
with st.sidebar:
    st.title("Career Venture Lab")
    st.caption(f"**{state['pathway_id']}** | {state['course']}")

    state["team_id"] = st.text_input("Team ID", value=state["team_id"])
    state["selected_level"] = st.selectbox(
        "Teacher-Approved Math Level",
        ["Foundation", "Applied", "Advanced"],
        index=["Foundation", "Applied", "Advanced"].index(state["selected_level"]),
    )

    st.divider()
    st.markdown(f"**Snapshot ID:** `{state['snapshot_id']}`")
    st.markdown(f"**State Version:** `v{state['state_version']}`")
    st.markdown(f"**Cash on Hand:** `${state['cash']:,.2f}`")
    if state["cash"] < 800:
        st.warning("Finance Flag: Cash reserve is below $800!")

    st.divider()
    st.subheader("Save / Restore State (JSON)")
    snapshot_json = json.dumps(state, indent=2)
    st.download_button(
        label="Export Snapshot JSON",
        data=snapshot_json,
        file_name=f"{state['team_id']}_{state['pathway_id']}_v{state['state_version']}.json",
        mime="application/json",
    )

    uploaded_file = st.file_uploader("Import Snapshot JSON", type=["json"])
    if uploaded_file is not None:
        try:
            imported = json.load(uploaded_file)
            if imported.get("team_id") != state["team_id"]:
                st.error(
                    f"Rejected Import: Team ID mismatch (expected '{state['team_id']}', got '{imported.get('team_id')}')."
                )
            elif imported.get("pathway_id") != "MKT-3":
                st.error("Rejected Import: Pathway must be MKT-3.")
            elif int(imported.get("state_version", 0)) < int(state["state_version"]):
                st.error(
                    f"Rejected Stale Snapshot: Imported v{imported.get('state_version')} is older than current v{state['state_version']}."
                )
            else:
                st.session_state.biz_state = imported
                st.success(f"Restored {imported.get('snapshot_id')} (v{imported.get('state_version')}).")
                st.rerun()
        except Exception as exc:
            st.error(f"Invalid JSON file: {exc}")

    if st.button("Reset to Opening Baseline"):
        reset_state()
        st.rerun()

# ==============================================================================
# MAIN TABS (ALL MODULES WITH PLAIN-LANGUAGE EXPLANATIONS)
# ==============================================================================
st.title("Local-Business Marketing Agency (MKT-3)")
st.caption(
    "AP Calculus Business Simulator | Simulated educational data only — human review required before committing changes."
)

tabs = st.tabs([
    "1. Overview & Inputs",
    "2. AP Calculus Math",
    "3. Ledger & Run",
    "4. AI Departmental Handoff",
    "5. Report Center & Memos",
    "6. Marketing Studio",
    "7. Assessments & Cross-Course",
    "8. Acceptance Tests",
])

# ------------------------------------------------------------------------------
# TAB 1: OVERVIEW & EDITABLE BUSINESS INPUTS
# ------------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Overview & Inputs Module")
    st.info(
        "**Plain-Language Explanation:** This is your agency's control panel. Adjust prices, client demand, "
        "staff hours, or monthly bills below to preview what happens. Changing numbers here only tests a scenario—"
        "it does **not** touch your official cash or ledger until you approve a monthly run in **Tab 3**."
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**Pricing & Demand Inputs**")
        state["inputs"]["base_price"] = st.number_input(
            "Package Price ($)", min_value=1.0, max_value=1000.0, value=float(state["inputs"]["base_price"]), step=10.0
        )
        state["inputs"]["D0"] = st.number_input(
            "Requested Packages / Month", min_value=0, max_value=200, value=int(state["inputs"]["D0"]), step=1
        )
        state["inputs"]["own_ad_spend"] = st.number_input(
            "Own-Agency Advertising ($)", min_value=0.0, max_value=5000.0, value=float(state["inputs"]["own_ad_spend"]), step=25.0
        )

    with col_b:
        st.markdown("**Staffing & Revision Inputs**")
        state["inputs"]["staff_hours"] = st.number_input(
            "Productive Staff Hours / Month", min_value=0.0, max_value=500.0, value=float(state["inputs"]["staff_hours"]), step=8.0
        )
        state["inputs"]["hours_per_unit"] = st.number_input(
            "Base Hours per Package", min_value=1.0, max_value=40.0, value=float(state["inputs"]["hours_per_unit"]), step=1.0
        )
        state["inputs"]["revision_hours_per_package"] = st.number_input(
            "Extra Revision Hours / Package", min_value=0.0, max_value=20.0, value=float(state["inputs"]["revision_hours_per_package"]), step=0.5
        )
        state["inputs"]["extra_revision_hourly_cost"] = st.number_input(
            "Extra Revision Cost ($/hr)", min_value=0.0, max_value=100.0, value=float(state["inputs"]["extra_revision_hourly_cost"]), step=1.0
        )

    with col_c:
        st.markdown("**Unit & Monthly Cost Lines**")
        with st.expander("Variable Costs ($/package)", expanded=True):
            for k, val in state["variable_cost_lines"].items():
                state["variable_cost_lines"][k] = st.number_input(
                    k.replace("_", " ").title(), min_value=0.0, value=float(val), step=5.0, key=f"var_{k}"
                )
        with st.expander("Fixed Costs ($/month)", expanded=False):
            for k, val in state["fixed_cost_lines"].items():
                state["fixed_cost_lines"][k] = st.number_input(
                    k.replace("_", " ").title(), min_value=0.0, value=float(val), step=25.0, key=f"fix_{k}"
                )
        state["inputs"]["client_media_budget"] = st.number_input(
            "Client Pass-Through Ad Budget ($ - Liability, Not Revenue)",
            min_value=0.0,
            value=float(state["inputs"]["client_media_budget"]),
            step=50.0,
        )

    preview = compute_metrics(state)

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Monthly Capacity", f"{preview['capacity']} pkgs", f"{state['inputs']['staff_hours']:.0f} hrs avail")
    m2.metric("Completed Sales", f"{preview['sold']} pkgs", f"-{preview['unserved_demand']} unserved demand")
    m3.metric("Projected Revenue", f"${preview['net_revenue']:,.2f}")
    m4.metric("Total Monthly Expense", f"${preview['total_operating_expense']:,.2f}", f"${preview['variable_per_unit']:.2f}/pkg var")
    m5.metric("Operating Profit", f"${preview['operating_profit']:,.2f}")

# ------------------------------------------------------------------------------
# TAB 2: PERSISTENT AP CALCULUS MATH PANEL
# ------------------------------------------------------------------------------
with tabs[1]:
    level = state["selected_level"]
    st.subheader(f"AP Calculus Math Module — {level} Mode")
    st.info(
        "**Plain-Language Explanation:** This module uses derivatives ($P'(p)$) to test how changing your package price "
        "affects profit. Because your team can only build a limited number of packages each month, it also marks "
        "the **Capacity Corner**—the exact price where customer demand matches your team's maximum workload."
    )

    p0 = 250.0
    D0 = 12.0
    a = 2 * D0  # 24
    b = D0 / p0  # 0.048
    v = preview["variable_per_unit"]
    F = preview["fixed_total"] + preview["marketing"]
    cap = preview["capacity"]

    p_corner = (a - cap) / b if b > 0 else 0.0
    p_unconstrained_opt = (a + b * v) / (2 * b)
    p_max_domain = 2 * p0  # 500

    st.markdown(
        f"""
        * **Business Question:** What package price $p$ maximizes monthly profit while respecting our capacity ceiling of **{cap} packages**?
        * **Demand Equation:** $q(p) = {a:.0f} - {b:.3f}p$ on domain $0 \le p \le {p_max_domain:.0f}$ (units: packages/month)
        * **Variable Cost ($v$):** `${v:.2f}/package` | **Fixed + Marketing Cost ($F$):** `${F:.2f}/month`
        """
    )

    prices = np.linspace(0, p_max_domain, 501)
    q_unconstrained = np.maximum(0.0, a - b * prices)
    s_constrained = np.minimum(float(cap), q_unconstrained)

    profit_unconstrained = (prices - v) * q_unconstrained - F
    profit_constrained = (prices - v) * s_constrained - F
    d_profit_constrained = np.where(prices < p_corner, float(cap), a + b * v - 2 * b * prices)

    if level == "Foundation":
        st.write(
            f"- **Critical Point ($P'(p) = 0$):** $p = \frac{{{a:.0f} + {b:.3f}({v:.2f})}}{{2({b:.3f})}} = **\${p_unconstrained_opt:.2f}**$"
        )
        st.write(
            f"- **Unconstrained Demand at $p = \${p_unconstrained_opt:.2f}$:** $q = {a - b * p_unconstrained_opt:.2f}$ packages/month"
        )
        st.warning(
            f"Feasibility Check: At $p = \${p_unconstrained_opt:.2f}$, demand is {a - b * p_unconstrained_opt:.2f} packages, "
            f"which is above our capacity of {cap} packages. Switch to **Applied** mode in the sidebar to enforce capacity."
        )

    elif level == "Applied":
        candidates = [
            ("Left Endpoint (p = $0)", 0.0),
            (f"Capacity Corner (q = {cap})", p_corner),
            ("Unconstrained Critical Point", p_unconstrained_opt),
            ("Right Endpoint (p = $500)", p_max_domain),
        ]
        rows = []
        for label, p_val in candidates:
            q_val = max(0.0, a - b * p_val)
            s_val = min(float(cap), q_val)
            prof_cont = (p_val - v) * s_val - F
            s_int = int(math.floor(s_val))
            prof_int = (p_val - v) * s_int - F
            feasible = (
                "Yes (Interior)"
                if p_val > p_corner
                else ("Boundary" if abs(p_val - p_corner) < 1e-6 else "Capped by Capacity")
            )
            rows.append({
                "Candidate Point": label,
                "Price ($)": round(p_val, 2),
                "Raw Demand q(p)": round(q_val, 2),
                "Continuous Sales s(p)": round(s_val, 2),
                "Continuous Profit ($)": round(prof_cont, 2),
                "Whole-Unit Sales": s_int,
                "Whole-Unit Profit ($)": round(prof_int, 2),
                "Status": feasible,
            })
        df_cand = pd.DataFrame(rows)
        st.dataframe(df_cand, use_container_width=True, hide_index=True)

        best_row = df_cand.loc[df_cand["Continuous Profit ($)"].idxmax()]
        st.success(
            f"**Optimal Constrained Price:** **${best_row['Price ($)']:.2f}** "
            f"(Continuous Profit: **${best_row['Continuous Profit ($)']:,.2f}** | "
            f"Whole-Unit Profit: **${best_row['Whole-Unit Profit ($)']:,.2f}** at {int(best_row['Whole-Unit Sales'])} packages)."
        )

    else:  # Advanced
        t_end = st.slider("Integration Horizon T (days)", min_value=1, max_value=10, value=10)
        acc_rev = 100 * t_end + 10 * (t_end ** 2)
        acc_cost = 60 * t_end + 2.5 * (t_end ** 2)
        acc_prof = acc_rev - acc_cost
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Accumulated Revenue ∫r(t)dt [0,{t_end}]", f"${acc_rev:,.2f}")
        c2.metric(f"Accumulated Cost ∫c(t)dt [0,{t_end}]", f"${acc_cost:,.2f}")
        c3.metric(f"Net Accumulated Gain [0,{t_end}]", f"${acc_prof:,.2f}")
        st.caption("Rate model r(t)=100+20t and c(t)=60+5t ($/day) is isolated from the monthly ledger.")

    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=prices, y=profit_unconstrained, name="Unconstrained Profit P(p)", line=dict(dash="dash", color="#7f8c8d")))
    fig_p.add_trace(go.Scatter(x=prices, y=profit_constrained, name="Constrained Profit (Capped)", line=dict(color="#1f77b4", width=3)))
    fig_p.add_hline(y=0, line_dash="dot", line_color="black", annotation_text="Break-Even ($0)")
    if 0 <= p_corner <= p_max_domain:
        fig_p.add_vline(x=p_corner, line_dash="dash", line_color="#d95f02", annotation_text=f"Capacity Corner p=${p_corner:.2f}")
    fig_p.update_layout(
        title=f"Profit Function P(p) | Snapshot {state['snapshot_id']} (v{state['state_version']})",
        xaxis_title="Package Price p (USD)",
        yaxis_title="Monthly Profit (USD)",
        height=340,
    )
    st.plotly_chart(fig_p, use_container_width=True)

    fig_dp = go.Figure()
    fig_dp.add_trace(go.Scatter(x=prices, y=d_profit_constrained, name="Constrained Derivative P'(p)", line=dict(color="#2ca02c", width=2.5)))
    fig_dp.add_hline(y=0, line_dash="dot", line_color="black", annotation_text="P'(p) = 0")
    if 0 <= p_corner <= p_max_domain:
        fig_dp.add_vline(x=p_corner, line_dash="dash", line_color="#d95f02", annotation_text="Corner (P' undefined)")
    fig_dp.update_layout(
        title="Marginal Profit With Respect to Price: P'(p) ($/month per $1 price increase)",
        xaxis_title="Package Price p (USD)",
        yaxis_title="Rate of Change P'(p)",
        height=280,
    )
    st.plotly_chart(fig_dp, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: LEDGER & SIMULATION RUN
# ------------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Ledger & Simulation Run Module")
    st.info(
        "**Plain-Language Explanation:** Think of the Ledger as your agency's official bank register. "
        "When you click **Approve & Record Simulation Month**, your previewed sales and bills become permanent, "
        "your cash balance updates, and your Snapshot Version moves forward by 1. Clicking twice with the same Run ID is blocked."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        run_id_input = st.text_input("Unique Run ID", value=f"RUN-2027-{state['state_version']:02d}")
    with c2:
        sim_date_input = st.text_input("Period End Date (YYYY-MM-DD)", value=state["simulation_date"])
    with c3:
        camp_id_input = st.text_input("Campaign ID (if Ad Spend > $0)", value="CAMP-001")

    if st.button("Approve & Record Simulation Month", type="primary"):
        ok, msg = record_simulation_step(
            state,
            run_id=run_id_input.strip(),
            sim_date=sim_date_input.strip(),
            metrics=preview,
            mode="Normal",
            campaign_id=camp_id_input.strip() if preview["marketing"] > 0 else None,
        )
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()
    if state["ledger"]:
        df_ledger = pd.DataFrame(state["ledger"])
        st.dataframe(df_ledger, use_container_width=True, hide_index=True)
        st.download_button(
            "Export Ledger CSV",
            data=df_ledger.to_csv(index=False),
            file_name=f"{state['team_id']}_ledger_v{state['state_version']}.csv",
            mime="text/csv",
        )
    else:
        st.caption("No transactions recorded yet. Click 'Approve & Record Simulation Month' above to log Round 1.")

# ------------------------------------------------------------------------------
# TAB 4: AI DEPARTMENTAL HANDOFF (MANUAL WORKFLOW + STALE-VERSION CHECK)
# ------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("AI Departmental Handoff Module (Manual Workflow)")
    st.info(
        "**Plain-Language Explanation:** Because this app runs without paid APIs, you test your four AI assistants "
        "(Finance, Operations, Market/Marketing, Independent Reviewer) outside the dashboard in Gemini Skills/Gems, "
        "then log and verify their proposals here. Any recommendation built on an old snapshot version is automatically rejected."
    )

    st.markdown(f"**Current Active Snapshot:** `{state['snapshot_id']}` | **Required Version:** `v{state['state_version']}`")

    with st.form("ai_handoff_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            rec_role = st.selectbox("AI Department Role", ["Finance", "Operations", "Market and Marketing", "Independent Reviewer"])
        with col2:
            rec_version = st.number_input("Snapshot Version Used by AI", min_value=1, value=int(state["state_version"]), step=1)
        with col3:
            rec_checker = st.text_input("Student Checker Name", value="")
        rec_summary = st.text_area("AI Recommendation & Proposed Changes (Summary)")
        submitted_rec = st.form_submit_button("Validate & Import AI Proposal")

        if submitted_rec:
            if int(rec_version) != int(state["state_version"]):
                st.error(
                    f"Rejected Stale Recommendation: Proposal used v{rec_version}, but business is currently at v{state['state_version']}."
                )
            elif not rec_checker.strip() or not rec_summary.strip():
                st.warning("Please enter both a Student Checker Name and the AI Recommendation summary.")
            else:
                state["ai_recommendations"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "role": rec_role,
                    "state_version": int(rec_version),
                    "checker": rec_checker.strip(),
                    "summary": rec_summary.strip(),
                    "approval_status": "Approved by Student",
                })
                st.success(f"Verified and logged {rec_role} recommendation for v{rec_version}.")

    if state["ai_recommendations"]:
        st.dataframe(pd.DataFrame(state["ai_recommendations"]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# TAB 5: REPORT CENTER & DECISION MEMOS
# ------------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Report Center & Decision Memo Module")
    st.info(
        "**Plain-Language Explanation:** Viewing reports here never creates fake transactions or advances time. "
        "**Profit** measures whether your monthly sales beat your monthly expenses, while **Cash Flow** tracks actual "
        "dollars entering and leaving your bank account."
    )

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("### Simplified Income Statement (Current Preview)")
        inc_df = pd.DataFrame([
            {"Line Item": "Net Sales Revenue", "Amount ($)": preview["net_revenue"]},
            {"Line Item": "Variable Delivery Expenses", "Amount ($)": -preview["variable_expense"]},
            {"Line Item": "Fixed Monthly Overhead", "Amount ($)": -preview["fixed_total"]},
            {"Line Item": "Own-Agency Marketing", "Amount ($)": -preview["marketing"]},
            {"Line Item": "Operating Profit / (Loss)", "Amount ($)": preview["operating_profit"]},
        ])
        st.dataframe(inc_df, use_container_width=True, hide_index=True)

    with r_col2:
        st.markdown("### Simplified Balance Check (Current State)")
        equip = state["funding"]["equipment_assets"]
        cash_now = state["cash"]
        owner_eq = state["funding"]["owner_contribution"]
        retained = round(cash_now + equip - owner_eq, 2)
        bal_df = pd.DataFrame([
            {"Account": "Cash on Hand (Asset)", "Amount ($)": cash_now},
            {"Account": "Computer & Design Equipment (Asset)", "Amount ($)": equip},
            {"Account": "Total Assets", "Amount ($)": round(cash_now + equip, 2)},
            {"Account": "Owner Contribution (Equity)", "Amount ($)": owner_eq},
            {"Account": "Retained Earnings (Equity)", "Amount ($)": retained},
        ])
        st.dataframe(bal_df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### Record Two-Report Decision Memo")
    with st.form("decision_memo_form"):
        d_q = st.text_input("Decision Question (e.g., Should we raise package price to $275?)")
        d_reports = st.text_input("Two Reports Cited (e.g., Income Statement & Capacity/Operations Report)")
        d_choice = st.text_area("Chosen Action, Two Alternatives Compared, & Predicted Outcome")
        d_owner = st.text_input("Decision Owner & Review Date")
        save_memo = st.form_submit_button("Save Decision Memo")
        if save_memo and d_q.strip():
            state["decisions"].append({
                "snapshot_id": state["snapshot_id"],
                "version": f"v{state['state_version']}",
                "question": d_q.strip(),
                "reports_cited": d_reports.strip(),
                "action_and_prediction": d_choice.strip(),
                "owner_and_review": d_owner.strip(),
            })
            st.success("Decision Memo saved to snapshot.")

    if state["decisions"]:
        st.dataframe(pd.DataFrame(state["decisions"]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# TAB 6: COSTED MARKETING STUDIO
# ------------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Marketing Studio Module (Advertising Has a Real Cost)")
    st.info(
        "**Plain-Language Explanation:** Creating flyers or social ads costs real design time and printing money—even "
        "when using free software. Drafting an ad here does **not** automatically boost sales or charge your account "
        "until you approve it and enter the spend in Tab 1/Tab 3."
    )

    mc1, mc2 = st.columns(2)
    with mc1:
        camp_id = st.text_input("Draft Campaign ID", value="CAMP-LOCAL-01")
        offering = st.selectbox("Target Offering", ["Flyer design package", "Social campaign package", "Event promotion package"])
        audience = st.text_input("Target Local Audience", value="Neighborhood cafes and retail shops")
        ad_copy = st.text_area("Truthful Ad / Flyer Copy (No unverified claims)", value="Need local foot traffic? Launch a custom neighborhood flyer & social campaign with transparent pricing.")
    with mc2:
        d_hrs = st.number_input("Design Labor Hours", min_value=0.0, value=2.0, step=0.5)
        d_rate = st.number_input("Design Hourly Rate ($/hr)", min_value=0.0, value=20.0, step=5.0)
        assets_cost = st.number_input("Licensed Assets ($)", min_value=0.0, value=10.0, step=5.0)
        print_qty = st.number_input("Print Quantity (flyers)", min_value=0, value=100, step=25)
        print_unit = st.number_input("Print Unit Cost ($/flyer)", min_value=0.0, value=0.25, step=0.05)
        placement_cost = st.number_input("Distribution & Ad Placement ($)", min_value=0.0, value=25.0, step=5.0)

    total_camp_cost = round(d_hrs * d_rate + assets_cost + print_qty * print_unit + placement_cost, 2)
    st.metric("Calculated Total Campaign Cost", f"${total_camp_cost:,.2f}", "In-kind student labor explicitly priced")
    st.caption("Reminder: If conversions = 0, Customer Acquisition Cost (CAC) must be reported as N/A, never $0.")

# ------------------------------------------------------------------------------
# TAB 7: PRACTICE ASSESSMENT & CROSS-COURSE CONNECTIONS
# ------------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Practice Assessment & Cross-Course Connections")
    st.info(
        "**Plain-Language Explanation:** Freezing a snapshot locks your current numbers so practice math questions "
        "match the exact business state you are studying. Cross-course connections link your agency to at least two "
        "other school subjects."
    )

    if st.button("Freeze Snapshot & Generate Practice Questions"):
        state["frozen_assessment"] = {
            "snapshot_id": state["snapshot_id"],
            "version": state["state_version"],
            "price": preview["price"],
            "capacity": preview["capacity"],
            "var_cost": preview["variable_per_unit"],
            "fixed_cost": preview["fixed_total"],
        }

    if state["frozen_assessment"]:
        fa = state["frozen_assessment"]
        st.success(f"Frozen Record: {fa['snapshot_id']} (v{fa['version']}) | Price=${fa['price']}, Capacity={fa['capacity']}, v=${fa['var_cost']}, F=${fa['fixed_cost']}")
        st.markdown(
            f"""
            1. **Calculus Optimization Check:** Given $q(p) = 24 - 0.048p$ and variable cost $v = \${fa['var_cost']:.2f}$, compute the unconstrained critical price where $P'(p) = 0$. Is that price feasible under your capacity of **{fa['capacity']} packages**?
            2. **Units & Derivative Interpretation:** What are the exact units of $P'(p)$, and why is $P'(p)$ undefined at the capacity corner $p = \${(24 - fa['capacity'])/0.048:.2f}$?
            3. **Accounting Rule Check:** Why is your $1,500 equipment purchase excluded from monthly operating expenses?
            """
        )

    st.divider()
    st.markdown("### Cross-Course Connections (Choose at Least Two)")
    cc_df = pd.DataFrame([
        {"Subject": "English / Media", "Concept": "Truthful Rhetoric & Claim Verification", "Agency Use": "Auditing ad copy so claims match real evidence without exaggeration."},
        {"Subject": "Economics", "Concept": "Opportunity Cost & Capacity Constraints", "Agency Use": "Evaluating lost revenue when limited designer hours cap monthly packages."},
        {"Subject": "Computer Science", "Concept": "Idempotency & Version Validation", "Agency Use": "Using unique Run IDs and state_version checks to block duplicate transactions."},
    ])
    st.dataframe(cc_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# TAB 8: MKT-3 ACCEPTANCE TESTS & FIXTURES
# ------------------------------------------------------------------------------
with tabs[7]:
    st.subheader("MKT-3 Automated Acceptance & Fixture Tests")
    st.info(
        "**Plain-Language Explanation:** These tests automatically verify your math engine against the exact expected "
        "numbers in the Career Venture Lab Handbook (Page 100) before you submit or add extra features."
    )

    if st.button("Run All MKT-3 Acceptance Tests"):
        test_results = []

        # Test 1: Zero sales check
        t1_state = json.loads(json.dumps(DEFAULT_STATE))
        m_zero = compute_metrics(t1_state, requested_override=0)
        pass_t1 = (m_zero["gross_revenue"] == 0.0 and m_zero["variable_expense"] == 0.0 and m_zero["operating_profit"] == -900.0)
        test_results.append({
            "Test Name": "1. Zero Sales Check",
            "Expected": "Revenue $0, Variable $0, Profit -$900",
            "Actual": f"Revenue ${m_zero['gross_revenue']:.0f}, Variable ${m_zero['variable_expense']:.0f}, Profit ${m_zero['operating_profit']:.0f}",
            "Status": "PASS" if pass_t1 else "FAIL",
        })

        # Test 2: Demand exceeds capacity
        t2_state = json.loads(json.dumps(DEFAULT_STATE))
        m_cap = compute_metrics(t2_state)
        pass_t2 = (m_cap["sold"] == 10 and m_cap["unserved_demand"] == 2 and m_cap["operating_profit"] == 800.0)
        test_results.append({
            "Test Name": "2. Demand Exceeds Capacity (Baseline)",
            "Expected": "Sold 10, Unserved 2, Profit $800",
            "Actual": f"Sold {m_cap['sold']}, Unserved {m_cap['unserved_demand']}, Profit ${m_cap['operating_profit']:.0f}",
            "Status": "PASS" if pass_t2 else "FAIL",
        })

        # Test 3: Revision Shock (+2 hrs/package)
        t3_state = json.loads(json.dumps(DEFAULT_STATE))
        t3_state["inputs"]["revision_hours_per_package"] = 2.0
        m_rev = compute_metrics(t3_state)
        pass_t3 = (
            m_rev["capacity"] == 8
            and m_rev["variable_per_unit"] == 90.0
            and m_rev["gross_revenue"] == 2000.0
            and m_rev["variable_expense"] == 720.0
            and m_rev["operating_profit"] == 380.0
        )
        test_results.append({
            "Test Name": "3. Revision Disruption (+2 hrs/pkg)",
            "Expected": "Cap 8, Unit Cost $90, Rev $2,000, Var $720, Profit $380",
            "Actual": f"Cap {m_rev['capacity']}, Unit Cost ${m_rev['variable_per_unit']:.0f}, Rev ${m_rev['gross_revenue']:,.0f}, Var ${m_rev['variable_expense']:.0f}, Profit ${m_rev['operating_profit']:.0f}",
            "Status": "PASS" if pass_t3 else "FAIL",
        })

        # Test 4: 3-Month Fixture Replay
        t4_state = json.loads(json.dumps(DEFAULT_STATE))
        fixture_rows_out = []
        for _, row in MONTHLY_FIXTURE.iterrows():
            m_fix = compute_metrics(
                t4_state,
                requested_override=int(row["requested"]),
                capacity_override=int(row["capacity_override"]),
                ad_override=float(row["ad_cost"]),
            )
            record_simulation_step(
                t4_state,
                run_id=f"FIX-{row['month']}",
                sim_date=f"{row['month']}-28",
                metrics=m_fix,
                mode="Fixture",
                campaign_id="CAMP-FIX-FEB" if row["ad_cost"] > 0 else None,
            )
            fixture_rows_out.append((m_fix["sold"], m_fix["gross_revenue"], m_fix["total_operating_expense"], m_fix["operating_profit"], t4_state["cash"]))

        expected_fix = [
            (10, 2500.0, 1700.0, 800.0, 4800.0),
            (10, 2500.0, 1800.0, 700.0, 5500.0),
            (7, 1750.0, 1460.0, 290.0, 5790.0),
        ]
        pass_t4 = (fixture_rows_out == expected_fix)
        test_results.append({
            "Test Name": "4. 3-Month Fixture Replay (Jan-Mar 2027)",
            "Expected": "Closing Cash: $4,800 -> $5,500 -> $5,790",
            "Actual": f"Closing Cash: ${fixture_rows_out[0][4]:,.0f} -> ${fixture_rows_out[1][4]:,.0f} -> ${fixture_rows_out[2][4]:,.0f}",
            "Status": "PASS" if pass_t4 else "FAIL",
        })

        # Test 5: Duplicate Run Protection
        dup_ok, _ = record_simulation_step(
            t4_state,
            run_id="FIX-2027-01",
            sim_date="2027-01-28",
            metrics=m_cap,
            mode="Fixture",
        )
        test_results.append({
            "Test Name": "5. Duplicate Run Protection",
            "Expected": "Rejected (False)",
            "Actual": f"Rejected ({not dup_ok})",
            "Status": "PASS" if not dup_ok else "FAIL",
        })

        st.dataframe(pd.DataFrame(test_results), use_container_width=True, hide_index=True)

    with st.expander("View Reference Monthly Fixture (Simulated Test Data)"):
        st.dataframe(MONTHLY_FIXTURE, use_container_width=True, hide_index=True)
