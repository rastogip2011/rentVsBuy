"""
Streamlit application for comparing renting versus buying a home.

Usage:
    streamlit run rent_vs_buy_app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from rent_vs_buy_calculator import (
    ScenarioInput,
    mortgage_payment,
)


def compute_renter_net_worth(
    lumpsum: float,
    monthly_contributions: list,
    annual_return: float,
) -> pd.Series:
    """Monthly renter net worth: down-payment lump sum + accumulated contributions."""
    monthly_rate = annual_return / 12
    value = lumpsum
    values = []
    for m, contrib in enumerate(monthly_contributions, start=1):
        value *= (1 + monthly_rate)
        value += contrib
        values.append(value)
    return pd.Series(values, index=range(1, len(monthly_contributions) + 1))


def compute_buyer_net_worth(
    scenario: ScenarioInput,
    buy_contributions: list,
    loan_amount: float,
) -> pd.Series:
    """Monthly buyer net worth: (home value − sales cost − remaining mortgage) + side portfolio."""
    monthly_rate = scenario.investment_return_rate / 12
    monthly_appreciation = (1 + scenario.appreciation_rate) ** (1 / 12) - 1
    monthly_mortgage_rate = scenario.mortgage_rate / 12
    monthly_payment = mortgage_payment(loan_amount, scenario.mortgage_rate, scenario.mortgage_term_years)

    remaining_principal = loan_amount
    home_value = scenario.home_price
    portfolio = 0.0
    values = []

    for contrib in buy_contributions:
        # Mortgage amortization
        interest = remaining_principal * monthly_mortgage_rate
        principal_paid = monthly_payment - interest
        remaining_principal = max(0.0, remaining_principal - principal_paid)

        # Home appreciation
        home_value *= (1 + monthly_appreciation)

        # Side portfolio
        portfolio *= (1 + monthly_rate)
        portfolio += contrib

        net_worth = home_value * (1 - scenario.sales_cost_rate) - remaining_principal + portfolio
        values.append(net_worth)

    return pd.Series(values, index=range(1, len(buy_contributions) + 1))


def find_crossover(rent_series: pd.Series, buy_series: pd.Series) -> int | None:
    """Return the first month where buying net worth exceeds renting, or None."""
    diff = buy_series - rent_series
    crossings = diff[diff > 0].index
    return int(crossings[0]) if len(crossings) > 0 else None


def main():
    st.set_page_config(page_title="Rent vs. Buy Calculator", layout="wide")
    st.title("Rent vs. Buy Comparison Tool")
    st.markdown(
        "Enter your assumptions below. The tool normalizes monthly cash outflow "
        "across both scenarios — any surplus is invested in a portfolio earning "
        "the specified return. The chart shows net worth over time for each path."
    )

    st.sidebar.header("Input Parameters")
    with st.sidebar.form(key="input_form"):
        st.markdown("#### General")
        horizon_years = st.number_input(
            "Comparison horizon (years)", min_value=1, max_value=30, value=10, step=1
        )

        st.divider()
        st.markdown("#### Renting")
        initial_rent = st.number_input(
            "Initial monthly rent ($)", min_value=0.0, value=3000.0, step=100.0
        )
        rent_increase_rate = st.number_input(
            "Annual rent increase (%)", min_value=0.0, value=3.0, step=0.1
        ) / 100.0
        renters_insurance = st.number_input(
            "Monthly renters insurance ($)", min_value=0.0, value=50.0, step=5.0
        )
        investment_return_rate = st.number_input(
            "Annual investment return — nominal pre-tax (%)", min_value=0.0, value=10.0, step=0.1
        ) / 100.0

        st.divider()
        st.markdown("#### Buying")
        home_price = st.number_input(
            "Home purchase price ($)", min_value=1.0, value=800000.0, step=10000.0
        )
        down_payment_rate = st.number_input(
            "Down payment (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0
        ) / 100.0
        mortgage_rate = st.number_input(
            "Mortgage interest rate (%)", min_value=0.0, value=7.15, step=0.1
        ) / 100.0
        mortgage_term_years = st.number_input(
            "Mortgage term (years)", min_value=1, max_value=30, value=30, step=1
        )
        property_tax_rate = st.number_input(
            "Annual property tax rate (%)", min_value=0.0, value=0.94, step=0.01
        ) / 100.0
        home_insurance_monthly = st.number_input(
            "Monthly homeowners insurance ($)", min_value=0.0, value=220.0, step=10.0
        )
        hoa_monthly = st.number_input(
            "Monthly HOA fee ($)", min_value=0.0, value=200.0, step=50.0
        )
        appreciation_rate = st.number_input(
            "Home appreciation rate (%)", min_value=0.0, value=5.5, step=0.1
        ) / 100.0
        sales_cost_rate = st.number_input(
            "Sales cost at exit — agent + closing (%)", min_value=0.0, value=5.0, step=0.1
        ) / 100.0

        st.divider()
        submitted = st.form_submit_button("Run Comparison", use_container_width=True)

    if submitted:
        scenario = ScenarioInput(
            initial_rent=initial_rent,
            rent_increase_rate=rent_increase_rate,
            home_price=home_price,
            renters_insurance=renters_insurance,
            down_payment_rate=down_payment_rate,
            mortgage_rate=mortgage_rate,
            mortgage_term_years=int(mortgage_term_years),
            property_tax_rate=property_tax_rate,
            home_insurance_rate=home_insurance_monthly * 12 / home_price,
            investment_return_rate=investment_return_rate,
            horizon_years=int(horizon_years),
            appreciation_rate=appreciation_rate,
            sales_cost_rate=sales_cost_rate,
            hoa_monthly=hoa_monthly,
        )

        horizon_months = scenario.horizon_years * 12
        down_payment = scenario.home_price * scenario.down_payment_rate
        loan_amount = scenario.home_price - down_payment
        monthly_mortgage_payment = mortgage_payment(
            loan_amount, scenario.mortgage_rate, scenario.mortgage_term_years
        )
        monthly_prop_tax = scenario.home_price * scenario.property_tax_rate / 12
        monthly_home_ins = home_insurance_monthly

        # Build monthly cost lists
        owning_costs, renting_costs = [], []
        rent = scenario.initial_rent
        for year in range(scenario.horizon_years):
            for _ in range(12):
                renting_costs.append(rent + scenario.renters_insurance)
                owning_costs.append(
                    monthly_mortgage_payment + monthly_prop_tax
                    + monthly_home_ins + scenario.hoa_monthly
                )
            rent *= (1 + scenario.rent_increase_rate)
        owning_costs = owning_costs[:horizon_months]
        renting_costs = renting_costs[:horizon_months]

        cashflow_target = [max(o, r) for o, r in zip(owning_costs, renting_costs)]
        rent_contrib = [t - r for t, r in zip(cashflow_target, renting_costs)]
        buy_contrib  = [t - o for t, o in zip(cashflow_target, owning_costs)]

        rent_nw = compute_renter_net_worth(down_payment, rent_contrib, scenario.investment_return_rate)
        buy_nw  = compute_buyer_net_worth(scenario, buy_contrib, loan_amount)

        crossover_month = find_crossover(rent_nw, buy_nw)

        # --- Chart ---
        months = list(rent_nw.index)
        year_labels = [f"Year {m // 12}" for m in months]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=months,
            y=rent_nw.values,
            name="Renting (portfolio)",
            line=dict(color="#2196F3", width=2),
            hovertemplate="<b>Renting</b><br>%{customdata}<br>Net worth: $%{y:,.0f}<extra></extra>",
            customdata=year_labels,
        ))

        fig.add_trace(go.Scatter(
            x=months,
            y=buy_nw.values,
            name="Buying (home equity + portfolio)",
            line=dict(color="#FF5722", width=2),
            hovertemplate="<b>Buying</b><br>%{customdata}<br>Net worth: $%{y:,.0f}<extra></extra>",
            customdata=year_labels,
        ))

        if crossover_month is not None:
            fig.add_vline(
                x=crossover_month,
                line=dict(color="gray", dash="dash", width=1),
                annotation_text=f"Break-even Year {crossover_month / 12:.1f}",
                annotation_position="top right",
                annotation_font_color="gray",
            )

        tick_vals = list(range(12, horizon_months + 1, 12))
        fig.update_layout(
            title="Renting vs. Buying — Net Worth Over Time",
            xaxis=dict(
                title="Year",
                tickvals=tick_vals,
                ticktext=[str(v // 12) for v in tick_vals],
            ),
            yaxis=dict(
                title="Net Worth ($)",
                tickformat="$,.0f",
            ),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            height=480,
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Summary ---
        final_rent = rent_nw.iloc[-1]
        final_buy  = buy_nw.iloc[-1]
        advantage  = final_buy - final_rent
        winner     = "Buying" if advantage > 0 else "Renting"

        col1, col2, col3 = st.columns(3)
        col1.metric(
            f"Renting net worth at year {scenario.horizon_years}",
            f"${final_rent:,.0f}",
        )
        sign = "+" if advantage >= 0 else "-"
        col2.metric(
            f"Buying net worth at year {scenario.horizon_years}",
            f"${final_buy:,.0f}",
            delta=f"{sign}${abs(advantage):,.0f} vs renting",
        )
        col3.metric(
            "Break-even",
            f"Year {crossover_month / 12:.1f}" if crossover_month else "Never in horizon",
        )

        if advantage > 0:
            st.success(f"**Buying wins** by ${advantage:,.0f} after {scenario.horizon_years} years.")
        else:
            st.info(f"**Renting wins** by ${-advantage:,.0f} after {scenario.horizon_years} years.")


if __name__ == "__main__":  # pragma: no cover
    main()
