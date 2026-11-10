"""
IRRBB Risk Dashboard
Interactive web interface for Economic Value of Equity analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys
import os
import uuid

# Add models and utils to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.enhanced_eve_calculator import EnhancedEVECalculator
from utils.market_data import FederalReserveData

# Page config
st.set_page_config(
    page_title="IRRBB Risk Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="main-header">🏦 IRRBB Risk Dashboard</p>', unsafe_allow_html=True)
st.markdown("**Real-time Interest Rate Risk Analysis with AI-Powered Insights**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    use_real_data = st.checkbox("Use Real Fed Data", value=True, 
                                 help="Fetch live rates from Federal Reserve")
    
    if use_real_data:
        st.success("✅ Live data enabled")
    else:
        st.warning("⚠️ Demo mode (assumed rates)")
    
    st.markdown("---")
    
    st.header("📊 Analysis Options")
    
    show_yield_curve = st.checkbox("Show Yield Curve", value=True)
    show_historical = st.checkbox("Show Historical Rates", value=True)
    show_ai_analysis = st.checkbox("Show AI Analysis", value=True)
    
    st.markdown("---")
    
    st.header("ℹ️ About")
    st.info("""
    This dashboard provides real-time IRRBB analysis using:
    - Live Federal Reserve data
    - Basel-compliant scenarios
    - AI-powered insights
    - Regulatory compliance checks
    """)

# Initialize calculator
@st.cache_resource
def get_calculator(use_real):
    return EnhancedEVECalculator(use_real_data=use_real)


@st.cache_resource
def get_irrbb_graph():
    from agents.langgraph_orchestrator import build_graph
    return build_graph(interrupt_for_review=True)

calc = get_calculator(use_real_data)

# Market Data Section
if use_real_data:
    st.header("📈 Current Market Conditions")
    
    try:
        fed_data = FederalReserveData()
        
        # Current rates metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            rate_10y = fed_data.get_treasury_rate('10Y')
            st.metric(
                label="10Y Treasury",
                value=f"{rate_10y*100:.2f}%",
                delta=None
            )
        
        with col2:
            change_30d = fed_data.get_rate_change('10Y', 30)
            st.metric(
                label="30-Day Change",
                value=f"{change_30d:+.0f} bp",
                delta=f"{change_30d:+.0f} bp"
            )
        
        with col3:
            change_90d = fed_data.get_rate_change('10Y', 90)
            st.metric(
                label="90-Day Change",
                value=f"{change_90d:+.0f} bp",
                delta=f"{change_90d:+.0f} bp"
            )
        
        with col4:
            volatility = abs(change_30d)
            risk_level = "HIGH" if volatility > 50 else "MODERATE" if volatility > 25 else "LOW"
            st.metric(
                label="Volatility",
                value=risk_level,
                delta=f"{volatility:.0f} bp/30d"
            )
        
        # Yield Curve
        if show_yield_curve:
            st.subheader("📊 Treasury Yield Curve")
            
            yields = fed_data.get_yield_curve()
            
            # Convert to DataFrame for plotting
            curve_data = pd.DataFrame({
                'Maturity': list(yields.keys()),
                'Yield': [y*100 for y in yields.values()]
            })
            
            # Define maturity order
            maturity_order = ['3M', '2Y', '5Y', '10Y', '30Y']
            curve_data['Maturity'] = pd.Categorical(curve_data['Maturity'], 
                                                     categories=maturity_order, 
                                                     ordered=True)
            curve_data = curve_data.sort_values('Maturity')
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=curve_data['Maturity'],
                y=curve_data['Yield'],
                mode='lines+markers',
                name='Current Yield Curve',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=10)
            ))
            
            fig.update_layout(
                title="U.S. Treasury Yield Curve",
                xaxis_title="Maturity",
                yaxis_title="Yield (%)",
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Curve analysis
            slope = yields['30Y'] - yields['3M']
            if slope > 0.005:
                curve_shape = "Normal (Upward Sloping)"
                interpretation = "Healthy economic expectations"
            elif slope < -0.005:
                curve_shape = "Inverted (Downward Sloping)"
                interpretation = "⚠️ Potential recession signal"
            else:
                curve_shape = "Flat"
                interpretation = "Economic uncertainty"
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Curve Shape:** {curve_shape}")
            with col2:
                st.info(f"**Interpretation:** {interpretation}")
        
        # Historical Rates
        if show_historical:
            st.subheader("📉 Historical 10Y Treasury Rate (Last 90 Days)")
            
            historical = fed_data.get_historical_rates('10Y', 90)
            
            if not historical.empty:
                hist_df = pd.DataFrame({
                    'Date': historical.index,
                    'Rate': historical.values * 100
                })
                
                fig = px.line(hist_df, x='Date', y='Rate',
                             title='10Y Treasury Rate Trend')
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Yield (%)",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Could not fetch market data: {e}")
        st.info("Continuing with fallback rate...")

st.markdown("---")

# EVE Analysis Section
st.header("💰 Economic Value of Equity (EVE) Analysis")

# Get balance sheet
bs = calc.create_sample_balance_sheet()
stats = calc.get_summary_stats(bs)

# Balance Sheet Summary
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Assets", f"${stats['total_assets']:,.0f}")
with col2:
    st.metric("Total Liabilities", f"${stats['total_liabilities']:,.0f}")
with col3:
    st.metric("Equity", f"${stats['equity']:,.0f}")
with col4:
    st.metric("Leverage Ratio", f"{stats['leverage_ratio']:.2f}x")

# Show balance sheet details
with st.expander("📋 View Balance Sheet Details"):
    st.dataframe(bs.style.format({
        'balance': '${:,.0f}',
        'rate': '{:.2%}',
        'maturity_years': '{:.1f}'
    }), use_container_width=True)

st.markdown("---")

# Sensitivity Analysis
st.header("⚡ Interest Rate Sensitivity Analysis")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Data Source")
    st.info(f"**Base Rate:** {calc.base_rate*100:.2f}%  \n**Source:** {calc.data_source}")

with col2:
    # Run analysis button
    if st.button("🔄 Refresh Analysis", type="primary"):
        st.rerun()

# Run sensitivity analysis
results, scenario_info = calc.run_sensitivity_analysis()

# Scenario rationale
st.info(f"**Scenario Selection:** {scenario_info['rationale']}  \n**Risk Level:** {scenario_info['risk_level']}")

# Results table
st.subheader("📊 Sensitivity Results")

# Format the results
results_display = results.copy()
results_display['eve'] = results_display['eve'].apply(lambda x: f"${x:,.2f}")
results_display['change_$'] = results_display['change_$'].apply(lambda x: f"${x:,.2f}")
results_display['change_%'] = results_display['change_%'].apply(lambda x: f"{x:+.2f}%")

st.dataframe(results_display, use_container_width=True, hide_index=True)

# Visualization
st.subheader("📈 EVE Sensitivity Chart")

fig = go.Figure()

# Add bar chart
colors = ['green' if x > 0 else 'red' for x in results['change_$']]
fig.add_trace(go.Bar(
    x=results['scenario'],
    y=results['change_$'],
    marker_color=colors,
    name='EVE Change',
    text=results['change_$'].apply(lambda x: f"${x:,.0f}"),
    textposition='outside'
))

fig.update_layout(
    title="EVE Change by Scenario",
    xaxis_title="Rate Shock Scenario",
    yaxis_title="EVE Change ($)",
    height=400,
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# Waterfall chart
st.subheader("💧 EVE Waterfall Analysis")

base_eve = results[results['shock_bp'] == 0]['eve'].iloc[0]

# Create waterfall data
waterfall_data = [base_eve] + results[results['shock_bp'] != 0]['eve'].tolist()
waterfall_labels = ['Base EVE'] + results[results['shock_bp'] != 0]['scenario'].tolist()

fig_waterfall = go.Figure(go.Waterfall(
    x=waterfall_labels,
    y=[base_eve] + results[results['shock_bp'] != 0]['change_$'].tolist(),
    measure=['absolute'] + ['relative']*(len(waterfall_labels)-1),
    text=[f"${v:,.0f}" for v in waterfall_data],
    textposition="outside",
    connector={"line": {"color": "rgb(63, 63, 63)"}},
))

fig_waterfall.update_layout(
    title="EVE Waterfall by Scenario",
    showlegend=False,
    height=400
)

st.plotly_chart(fig_waterfall, use_container_width=True)

st.markdown("---")

# Regulatory Compliance
st.header("🏛️ Regulatory Compliance (Basel IRRBB)")

max_decline_pct = abs(results['change_%'].min())
basel_threshold = 15.0

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Maximum EVE Decline", f"{max_decline_pct:.2f}%")

with col2:
    st.metric("Basel Threshold", f"{basel_threshold:.2f}%")

with col3:
    buffer = basel_threshold - max_decline_pct
    st.metric("Safety Buffer", f"{buffer:.2f}%", 
             delta=f"{buffer:.2f}%" if buffer > 0 else None,
             delta_color="normal" if buffer > basel_threshold*0.2 else "inverse")

# Compliance status
if max_decline_pct > basel_threshold:
    st.error("⚠️ **EXCEEDS THRESHOLD** - Supervisory outlier, immediate remediation required")
elif max_decline_pct > basel_threshold * 0.8:
    st.warning("⚡ **APPROACHING THRESHOLD** - Enhanced monitoring recommended")
else:
    st.success("✅ **WITHIN LIMITS** - Continue quarterly monitoring")

# Progress bar
st.write("**Compliance Status:**")
progress = min(max_decline_pct / basel_threshold, 1.0)
st.progress(progress)

st.markdown("---")

# LangGraph AI Analysis: parallel data nodes -> Basel gate -> optional human review -> report
if show_ai_analysis:
    st.header("🤖 AI-Powered Analysis (LangGraph)")
    st.caption(
        "Market and balance-sheet nodes run in parallel, then EVE sensitivity feeds a "
        "Basel compliance gate. Runs over the 10% watch / 15% outlier thresholds pause "
        "for a risk-manager sign-off before the narrative is written."
    )

    _doc_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "docs",
        "LangGraph_IRRBB_Workflow.docx",
    )
    if os.path.exists(_doc_path):
        with open(_doc_path, "rb") as _doc_file:
            st.download_button(
                label="Download Word explanation",
                data=_doc_file,
                file_name="LangGraph_IRRBB_Workflow.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    try:
        from agents.langgraph_orchestrator import (
            initial_state_from_dashboard,
            is_interrupted,
        )

        app = get_irrbb_graph()
        run_fingerprint = f"{use_real_data}-{max_decline_pct:.4f}-{float(results['eve'].iloc[0]):.2f}"

        if st.session_state.get("lg_fingerprint") != run_fingerprint:
            st.session_state.lg_fingerprint = run_fingerprint
            st.session_state.lg_thread = str(uuid.uuid4())
            st.session_state.lg_phase = "idle"
            st.session_state.lg_snapshot = None
            st.session_state.lg_report = None

        config = {"configurable": {"thread_id": st.session_state.lg_thread}}

        if st.session_state.lg_phase == "idle":
            with st.spinner("Running LangGraph IRRBB workflow..."):
                seed = initial_state_from_dashboard(
                    results, bs, stats, use_real_data=use_real_data
                )
                snapshot = app.invoke(seed, config=config)
                st.session_state.lg_snapshot = snapshot
                if is_interrupted(app, config):
                    st.session_state.lg_phase = "review"
                else:
                    st.session_state.lg_phase = "done"
                    st.session_state.lg_report = snapshot.get("report")

        snapshot = st.session_state.lg_snapshot or {}

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Worst scenario", snapshot.get("worst_scenario", "—"))
        with col_b:
            worst_pct = snapshot.get("worst_change_pct")
            st.metric("Worst EVE change", f"{worst_pct:+.2f}%" if worst_pct is not None else "—")
        with col_c:
            st.metric("Compliance", snapshot.get("compliance_status", "—").split(" - ")[0])

        if st.session_state.lg_phase == "review":
            st.warning(
                f"**Human review required.** {snapshot.get('compliance_action', '')}"
            )
            notes = st.text_area(
                "Reviewer notes (optional)",
                key="lg_review_notes",
                placeholder="e.g. Approve with instruction to size a 2y payer swap hedge.",
            )
            if st.button("Approve and generate report", type="primary"):
                if notes.strip():
                    app.update_state(config, {"review_notes": notes.strip()})
                with st.spinner("Resuming graph after human review..."):
                    resumed = app.invoke(None, config=config)
                st.session_state.lg_snapshot = resumed
                st.session_state.lg_report = resumed.get("report")
                st.session_state.lg_phase = "done"
                st.rerun()

        if st.session_state.lg_phase == "done" and st.session_state.lg_report:
            st.markdown("### 📋 AI Analyst Report")
            st.markdown(st.session_state.lg_report)

    except Exception as e:
        st.warning(f"AI analysis unavailable: {e}")
        if "OPENAI_API_KEY" in str(e) or "api_key" in str(e).lower():
            st.info("Make sure your OpenAI API key is configured in .env file")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>📊 IRRBB Risk Dashboard | Built with Streamlit & Federal Reserve Data</p>
    <p>Data Source: Federal Reserve Economic Data (FRED) | Updated: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)