import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Page Configuration & CSS ---
st.set_page_config(page_title="Olist Analytics Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .stagger-1 { animation: slideUpFade 0.6s cubic-bezier(0.25, 0.8, 0.25, 1) 0.1s both; }
    .stagger-2 { animation: slideUpFade 0.6s cubic-bezier(0.25, 0.8, 0.25, 1) 0.2s both; }
    .stagger-3 { animation: slideUpFade 0.6s cubic-bezier(0.25, 0.8, 0.25, 1) 0.3s both; }
    .stagger-4 { animation: slideUpFade 0.6s cubic-bezier(0.25, 0.8, 0.25, 1) 0.4s both; }
    
    .title-pulse {
        animation: pulse 3s infinite ease-in-out;
        color: #1f5a82;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .kpi-card {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 20px;
    }
    .card-1 { border-top: 5px solid #FF4B4B; }
    .card-2 { border-top: 5px solid #00C896; }
    .card-3 { border-top: 5px solid #1E90FF; }
    .card-4 { border-top: 5px solid #FFC107; }
    
    .kpi-card:hover { transform: translateY(-8px); box-shadow: 0 12px 20px rgba(0,0,0,0.15); }
    .kpi-title { color: #888; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-value { font-size: 2.2rem; font-weight: 800; margin: 0; color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

def render_kpi(title, value, card_class, stagger_class):
    st.markdown(f"""
        <div class="kpi-card {card_class} {stagger_class}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# --- Base Data Loading Engine ---
@st.cache_data
def load_base_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    orders = pd.read_csv(os.path.join(base_dir, "olist_orders_dataset.csv"))
    order_items = pd.read_csv(os.path.join(base_dir, "olist_order_items_dataset.csv"))
    payments = pd.read_csv(os.path.join(base_dir, "olist_order_payments_dataset.csv"))
    reviews = pd.read_csv(os.path.join(base_dir, "olist_order_reviews_dataset.csv"))
    customers = pd.read_csv(os.path.join(base_dir, "olist_customers_dataset.csv"))
    products = pd.read_csv(os.path.join(base_dir, "olist_products_dataset.csv"))
    translation = pd.read_csv(os.path.join(base_dir, "product_category_name_translation.csv"))
    sellers = pd.read_csv(os.path.join(base_dir, "olist_sellers_dataset.csv"))

    date_cols = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col])
        
    orders['year'] = orders['order_purchase_timestamp'].dt.year.astype(str)
    orders = orders.merge(customers[['customer_id', 'customer_unique_id', 'customer_state']], on='customer_id', how='left')

    return orders, order_items, payments, reviews, customers, products, translation, sellers

with st.spinner("Loading Olist Dataset..."):
    orders_raw, order_items, payments, reviews, customers, products, translation, sellers = load_base_data()

# --- SIDEBAR FILTERS ---
st.sidebar.markdown("### 🎛️ Dashboard Controls")
year_options = ["All"] + sorted(orders_raw['year'].dropna().unique().tolist())
selected_year = st.sidebar.selectbox("📅 Select Year", year_options, index=0)

state_options = sorted(orders_raw['customer_state'].dropna().unique().tolist())
selected_states = st.sidebar.multiselect("🗺️ Select Customer State(s)", state_options, default=[])
st.sidebar.caption("Trend Charts fixed to Jan 2017 - Aug 2018 per rules.")

# Apply Filters
filtered_orders = orders_raw.copy()
if selected_year != "All":
    filtered_orders = filtered_orders[filtered_orders['year'] == selected_year]
if selected_states:
    filtered_orders = filtered_orders[filtered_orders['customer_state'].isin(selected_states)]

# --- Process Filtered Data ---
delivered_orders = filtered_orders[filtered_orders["order_status"] == "delivered"].copy()
deliv_items = delivered_orders.merge(order_items, on="order_id", how="inner")

kpis = {
    "K1": filtered_orders["order_id"].nunique(),
    "K2": deliv_items["price"].sum(),
    "K3": deliv_items["price"].sum() / delivered_orders["order_id"].nunique() if delivered_orders["order_id"].nunique() > 0 else 0,
    "K4": filtered_orders["customer_unique_id"].nunique(),
}

filtered_reviews = reviews.merge(filtered_orders[['order_id']], on='order_id', how='inner')
kpis["K5"] = filtered_reviews["review_score"].mean() if not filtered_reviews.empty else 0

delivered_orders["delivery_days"] = (delivered_orders["order_delivered_customer_date"] - delivered_orders["order_purchase_timestamp"]).dt.total_seconds() / (24 * 3600)
delivered_orders["on_time"] = delivered_orders["order_delivered_customer_date"] <= delivered_orders["order_estimated_delivery_date"]

kpis["K6"] = delivered_orders["delivery_days"].mean() if not delivered_orders.empty else 0
kpis["K7"] = (delivered_orders["on_time"].mean() * 100) if not delivered_orders.empty else 0
kpis["K8"] = deliv_items.merge(sellers[['seller_id']], on='seller_id', how='inner')["seller_id"].nunique()

start_date, end_date = "2017-01-01", "2018-09-01"
trend_orders = filtered_orders[(filtered_orders["order_purchase_timestamp"] >= start_date) & (filtered_orders["order_purchase_timestamp"] < end_date)].copy()
trend_orders["month"] = trend_orders["order_purchase_timestamp"].dt.to_period("M").astype(str)

trend_deliv = delivered_orders[(delivered_orders["order_purchase_timestamp"] >= start_date) & (delivered_orders["order_purchase_timestamp"] < end_date)].copy()
trend_deliv["month"] = trend_deliv["order_purchase_timestamp"].dt.to_period("M").astype(str)

q1 = trend_deliv.merge(order_items, on="order_id").groupby("month")["price"].sum().reset_index()
q2 = trend_orders.groupby("month")["order_id"].nunique().reset_index()

filtered_orders["day"] = filtered_orders["order_purchase_timestamp"].dt.day_name()
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
q3 = filtered_orders.groupby("day")["order_id"].nunique().reindex(day_order).reset_index()

prod_trans = products.merge(translation, on="product_category_name")
q4 = deliv_items.merge(prod_trans, on="product_id").groupby("product_category_name_english")["price"].sum().sort_values(ascending=False).head(10).reset_index()
q5 = filtered_orders.groupby("customer_state")["customer_unique_id"].nunique().sort_values(ascending=False).head(10).reset_index()
q6 = deliv_items.groupby("customer_state")["price"].sum().sort_values(ascending=False).head(10).reset_index()

filtered_payments = payments.merge(filtered_orders[['order_id']], on='order_id', how='inner')
q7 = filtered_payments.groupby("payment_type")["order_id"].count().reset_index()
q7 = q7[q7["order_id"] > (q7["order_id"].max() * 0.01)]

q8 = filtered_reviews.groupby("review_score")["review_id"].count().reset_index()
q9 = delivered_orders.groupby("customer_state")["delivery_days"].mean().sort_values(ascending=False).head(10).reset_index()
q10 = deliv_items.groupby("seller_id")["price"].sum().sort_values(ascending=False).head(10).reset_index()
q10["seller_id"] = q10["seller_id"].str[:6] + "..."

# --- UI Header ---
st.markdown('<div class="stagger-1">', unsafe_allow_html=True)
st.markdown('<h1 class="title-pulse">📊 Brazilian e-commerce dashboard</h1>', unsafe_allow_html=True)
st.caption(f"Showing data for: **Year:** {selected_year} | **States:** {', '.join(selected_states) if selected_states else 'All'}")
st.markdown('</div>', unsafe_allow_html=True)

# --- Top Level KPIs ---
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
with r1c1: render_kpi("K1: Total Orders", f"{kpis['K1']:,}", "card-1", "stagger-1")
with r1c2: render_kpi("K2: Total Revenue", f"R$ {kpis['K2']/1e6:.2f}M", "card-2", "stagger-2")
with r1c3: render_kpi("K3: Avg Order Value", f"R$ {kpis['K3']:.2f}", "card-3", "stagger-3")
with r1c4: render_kpi("K4: Unique Customers", f"{kpis['K4']:,}", "card-4", "stagger-4")

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1: render_kpi("K5: Avg Review", f"{kpis['K5']:.2f} / 5", "card-1", "stagger-1")
with r2c2: render_kpi("K6: Avg Delivery", f"{kpis['K6']:.1f} days", "card-2", "stagger-2")
with r2c3: render_kpi("K7: On-Time Delivery", f"{kpis['K7']:.1f}%", "card-3", "stagger-3")
with r2c4: render_kpi("K8: Total Sellers", f"{kpis['K8']:,}", "card-4", "stagger-4")

st.markdown("<br>", unsafe_allow_html=True)

layout_args = dict(margin=dict(l=20, r=20, t=50, b=20), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")

# --- Dashboard Sections Layout ---
col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.markdown('<div class="stagger-3">', unsafe_allow_html=True)
    st.caption("ORDERS & REVENUE TRENDS")
    
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.line(q1, x="month", y="price", title="Q1: Monthly Revenue (Delivered)", markers=True)
        fig1.update_traces(line_color='#00C896', line_width=3)
        fig1.update_layout(**layout_args, xaxis_title="", yaxis_title="Revenue (BRL)")
        st.plotly_chart(fig1, use_container_width=True, key="q1_chart")
        
    with c2:
        fig2 = px.bar(q2, x="month", y="order_id", title="Q2: Monthly Orders (All)", color="order_id", color_continuous_scale="Blues")
        fig2.update_layout(**layout_args, xaxis_title="", yaxis_title="Orders", coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True, key="q2_chart")
        
    st.markdown("<br>", unsafe_allow_html=True)

    st.caption("GEOGRAPHIC PERFORMANCE")
    
    c3, c4 = st.columns(2)
    with c3:
        fig3 = px.bar(q5, x="customer_unique_id", y="customer_state", orientation='h', title="Q5: Top States by Customers", color="customer_unique_id", color_continuous_scale="Purples")
        fig3.update_layout(**layout_args, xaxis_title="", yaxis_title="", yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True, key="q5_chart")
        
    with c4:
        fig4 = px.bar(q6, x="price", y="customer_state", orientation='h', title="Q6: Top States by Revenue", color="price", color_continuous_scale="Teal")
        fig4.update_layout(**layout_args, xaxis_title="", yaxis_title="", yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True, key="q6_chart")

    st.caption("SELLER PERFORMANCE")
    fig10 = px.bar(q10, x="price", y="seller_id", orientation='h', title="Q10: Top Sellers by Rev", color="price", color_continuous_scale="Greys")
    fig10.update_layout(**layout_args, xaxis_title="Revenue (R$)", yaxis_title="", yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
    st.plotly_chart(fig10, use_container_width=True, key="q10_chart")
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="stagger-4">', unsafe_allow_html=True)
    st.caption("DEMAND PATTERNS")
    
    c5, c6 = st.columns(2)
    with c5:
        fig5 = px.bar(q3, x="day", y="order_id", title="Q3: Orders by Day of Week", color="order_id", color_continuous_scale="Sunset")
        fig5.update_layout(**layout_args, xaxis_title="", yaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(fig5, use_container_width=True, key="q3_chart")
        
    with c6:
        fig6 = px.bar(q4, x="price", y="product_category_name_english", orientation='h', title="Q4: Top 10 Categories", color="price", color_continuous_scale="Magenta")
        fig6.update_layout(**layout_args, xaxis_title="", yaxis_title="", yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig6, use_container_width=True, key="q4_chart")
        
    st.markdown("<br>", unsafe_allow_html=True)

    st.caption("PAYMENT & EXPERIENCE")
    
    c7, c8 = st.columns(2)
    with c7:
        fig7 = px.pie(q7, values="order_id", names="payment_type", title="Q7: Payment Methods", hole=0.5)
        fig7.update_traces(marker=dict(colors=['#1E90FF', '#FFC107', '#00C896', '#FF4B4B']), textinfo="percent")
        fig7.update_layout(**layout_args, showlegend=False)
        st.plotly_chart(fig7, use_container_width=True, key="q7_chart")
        
    with c8:
        q8["review_score"] = q8["review_score"].astype(str)
        fig8 = px.bar(q8, x="review_score", y="review_id", title="Q8: Review Score Dist", color="review_score",
                      color_discrete_sequence=['#FF4B4B', '#FF7F50', '#FFC107', '#9ACD32', '#00C896'])
        fig8.update_layout(**layout_args, xaxis_title="Score", yaxis_title="", showlegend=False)
        st.plotly_chart(fig8, use_container_width=True, key="q8_chart")
        
    st.caption("DELIVERY PERFORMANCE")
    fig9 = px.bar(q9, x="delivery_days", y="customer_state", orientation='h', title="Q9: 10 Slowest States", color="delivery_days", color_continuous_scale="Reds")
    fig9.update_layout(**layout_args, xaxis_title="Avg Days", yaxis_title="", yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
    st.plotly_chart(fig9, use_container_width=True, key="q9_chart")
    st.markdown("</div>", unsafe_allow_html=True)
