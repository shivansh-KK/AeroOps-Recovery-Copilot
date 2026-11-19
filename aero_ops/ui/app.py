"""Dark themed Streamlit control center for disruption planning."""
import streamlit as st

from aero_ops.agent.core import AeroOpsAgent
from aero_ops.agent.state import AgentState
from aero_ops.database.db_manager import DatabaseManager
from aero_ops.database.seed_data import seed_database

st.set_page_config(page_title="AeroOps Control Center", page_icon="✈️", layout="wide")
st.markdown("""<style>
.stApp {background:#08111d;color:#e7eef7}.block-container{padding-top:1.2rem}
div[data-testid="stMetric"]{background:#102033;border:1px solid #243b55;padding:16px;border-radius:12px}
.dispatch{background:#102033;border-left:5px solid #3ddc97;padding:20px;border-radius:10px;white-space:pre-wrap}
.alert{background:#302819;border-left:5px solid #f4c542;padding:14px;border-radius:8px}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def resources() -> tuple[DatabaseManager, AeroOpsAgent]:
    database = DatabaseManager()
    seed_database(database)
    return database, AeroOpsAgent(database)


db, agent = resources()
st.title("✈️ AeroOps | Aviation Operations Control Center")
flights = db.query("SELECT COUNT(*) AS total FROM flights WHERE status!='CANCELLED'")[0]["total"]
disruptions = db.query("SELECT COUNT(*) AS total FROM flights WHERE status='DELAYED'")[0]["total"]
left, middle, right = st.columns(3)
left.metric("Active flights", flights)
middle.metric("Hub weather alerts", "1", "DXB thunderstorm sample")
right.metric("Active disruptions", disruptions)

with st.sidebar:
    st.header("Disruption scenario")
    scenario = st.selectbox("Select scenario", [
        "Scenario A · Severe thunderstorm at DXB",
        "Scenario B · Hydraulic snag on EK001; evaluate tail swap",
        "Scenario C · Four-hour delay and crew duty timeout",
    ])
    flight = st.selectbox("Affected flight", ["EK001", "EK101", "EK102"])
    delay = 4.0 if "Scenario C" in scenario else st.slider("Planning delay (hours)", 0.0, 8.0, 2.0, 0.5)
    launch = st.button("Generate recovery brief", type="primary", use_container_width=True)

if launch:
    try:
        st.session_state["agent_state"] = agent.run(scenario, flight, delay)
    except Exception as exc:
        st.error(f"Unable to complete a grounded recovery assessment: {exc}")

state: AgentState | None = st.session_state.get("agent_state")
if state:
    if state.self_healing_events:
        st.markdown('<div class="alert"><b>Safety / self-correction alerts</b><br>' + "<br>".join(state.self_healing_events) + "</div>", unsafe_allow_html=True)
    st.subheader("Live agent reasoning stream")
    for trace in state.traces:
        with st.expander(f"Step {trace.step}: {trace.tool_call.tool_name if trace.tool_call else 'Reasoning'}", expanded=False):
            st.write(trace.thought)
            st.json({"arguments": trace.tool_call.arguments if trace.tool_call else {}, "observation": trace.observation})
    st.subheader("Official dispatch recovery brief")
    st.markdown(f'<div class="dispatch">{state.final_brief}</div>', unsafe_allow_html=True)
    st.caption(f"Output verification: {'PASS' if state.verification.get('verified') else 'HOLD'} · {len(state.tool_calls)} tool calls · {state.recovery_options_evaluated} options evaluated")
else:
    st.info("Choose a disruption scenario and generate a tool-grounded assessment to begin.")
