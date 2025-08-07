"""
Streamlit application for comparing renting versus buying a home.

This app builds on the `rent_vs_buy_calculator.py` module.  It provides a simple
web interface where users can enter their own assumptions (rent, rent growth,
home price, mortgage rate, etc.) and visualize the results.  The left side of
the split screen shows how a renter’s investment portfolio grows over time as
they invest their down payment and monthly savings.  The right side shows the
estimated net proceeds a homeowner would receive if they sell the house after
each year in the comparison horizon.

Usage:
    streamlit run rent_vs_buy_app.py

You must have `streamlit` installed in your Python environment.  The app
imports functions from `rent_vs_buy_calculator.py` to perform the underlying
financial calculations.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from rent_vs_buy_calculator import (
    ScenarioInput,
    mortgage_payment,
    amortization_schedule,
    future_value_lump_sum,
    future_value_periodic_contribution,
)


def compute_investment_growth(
    lumpsum: float,
    monthly_contributions: list,
    annual_return: float,
    horizon_years: int,
) -> pd.Series:
    """Return a time series of the portfolio value (lump sum + contributions).

    The series has one entry per month and runs for `horizon_years` years.  The
    lump sum is invested at the beginning, and contributions occur at the end
    of each month.

    Args:
        lumpsum: Initial lump sum invested at time 0.
        monthly_contributions: List of contribution amounts for each month.
        annual_return: Annual return on the investments (e.g., 0.10 for 10%).
        horizon_years: Duration of the investment in years.

    Returns:
        A pandas Series indexed by month number (starting at 1) with the total
        portfolio value at the end of each month.
    """
    months = horizon_years * 12
    monthly_rate = annual_return / 12
    values = []
    value = lumpsum  # value at time 0
    # We'll track the value each month.  At the beginning of each month, the
    # existing value compounds; then we add the contribution at the end.
    for m in range(1, months + 1):
        # compound existing balance
        value *= (1 + monthly_rate)
        # add contribution at end of month
        value += monthly_contributions[m - 1]
        values.append(value)
    return pd.Series(values, index=range(1, months + 1))


def compute_yearly_buy_proceeds(
    scenario: ScenarioInput,
    owning_costs: list,
    monthly_contributions: list,
    loan_amount: float,
) -> pd.Series:
    """Compute net proceeds for the buy scenario if selling after each year.

    Args:
        scenario: Input parameters.
        owning_costs: List of total owning costs per month.
        monthly_contributions: List of monthly contributions invested in the
            stock market (buyer invests the difference between target cashflow
            and owning cost).
        loan_amount: Initial mortgage principal.

    Returns:
        A pandas Series indexed by year (1 to horizon) with net proceeds if
        selling at the end of each year.
    """
    results = []
    # Precompute amortization schedule for entire horizon to reuse principal
    total_months = scenario.horizon_years * 12
    _, _, _ = amortization_schedule(
        loan_amount, scenario.mortgage_rate, scenario.mortgage_term_years, total_months
    )
    # We'll compute schedule incrementally to avoid recalculating from scratch for each year.
    # But amortization_schedule returns the same results each time for a given number of months.
    for year in range(1, scenario.horizon_years + 1):
        m = year * 12
        # Amortization for m months
        _, _, remaining_principal = amortization_schedule(
            loan_amount, scenario.mortgage_rate, scenario.mortgage_term_years, m
        )
        # Value of contributions invested up to m months at year m
        # We take the contributions for months 0..m-1 and compute future value at month m
        contrib_slice = monthly_contributions[:m]
        contrib_value = future_value_periodic_contribution(
            contrib_slice, scenario.investment_return_rate, m
        )
        # House value at year m
        future_home_value = scenario.home_price * (1 + scenario.appreciation_rate) ** year
        net_sale_price = future_home_value * (1 - scenario.sales_cost_rate)
        net_proceeds = net_sale_price - remaining_principal + contrib_value
        results.append(net_proceeds)
    return pd.Series(results, index=range(1, scenario.horizon_years + 1))


def main():
    st.set_page_config(page_title="Rent vs. Buy Calculator", layout="wide")
    st.title("Rent vs. Buy Comparison Tool")
    st.markdown(
        "Enter your assumptions below. The tool keeps the total monthly cash "
        "outflow the same for both scenarios by investing any savings in a "
        "stock market portfolio that earns a fixed return."
    )

    # Sidebar inputs
    st.sidebar.header("Input Parameters")
    with st.sidebar.form(key="input_form"):
        initial_rent = st.number_input(
            "Initial monthly rent ($)", min_value=0.0, value=3000.0, step=100.0
        )
        rent_increase_rate = st.number_input(
            "Annual rent increase (%)", min_value=0.0, value=3.0, step=0.1
        ) / 100.0
        renters_insurance = st.number_input(
            "Monthly renters insurance ($)", min_value=0.0, value=50.0, step=5.0
        )
        home_price = st.number_input(
            "Home purchase price ($)", min_value=0.0, value=800000.0, step=10000.0
        )
        down_payment_rate = st.number_input(
            "Down payment (%)", min_value=0.0, value=20.0, step=1.0
        ) / 100.0
        mortgage_rate = st.number_input(
            "Mortgage interest rate (%)", min_value=0.0, value=7.15, step=0.1
        ) / 100.0
        mortgage_term_years = st.number_input(
            "Mortgage term (years)", min_value=1, value=30, step=1
        )
        property_tax_rate = st.number_input(
            "Annual property tax rate (%)", min_value=0.0, value=0.94, step=0.01
        ) / 100.0
        home_insurance_rate = st.number_input(
            "Annual homeowners insurance rate (%)", min_value=0.0, value=0.33, step=0.01
        ) / 100.0
        investment_return_rate = st.number_input(
            "Annual investment return (%)", min_value=0.0, value=10.0, step=0.1
        ) / 100.0
        horizon_years = st.number_input(
            "Comparison horizon (years)", min_value=1, value=5, step=1
        )
        appreciation_rate = st.number_input(
            "Home appreciation rate (%)", min_value=0.0, value=5.5, step=0.1
        ) / 100.0
        sales_cost_rate = st.number_input(
            "Sales cost rate (% of sale price)", min_value=0.0, value=5.0, step=0.1
        ) / 100.0
        submitted = st.form_submit_button("Run Comparison")

    if submitted:
        # Build scenario object
        scenario = ScenarioInput(
            initial_rent=initial_rent,
            rent_increase_rate=rent_increase_rate,
            home_price=home_price,
            renters_insurance=renters_insurance,
            down_payment_rate=down_payment_rate,
            mortgage_rate=mortgage_rate,
            mortgage_term_years=int(mortgage_term_years),
            property_tax_rate=property_tax_rate,
            home_insurance_rate=home_insurance_rate,
            investment_return_rate=investment_return_rate,
            horizon_years=int(horizon_years),
            appreciation_rate=appreciation_rate,
            sales_cost_rate=sales_cost_rate,
        )
        # Derived quantities
        horizon_months = scenario.horizon_years * 12
        down_payment = scenario.home_price * scenario.down_payment_rate
        loan_amount = scenario.home_price - down_payment
        monthly_mortgage_payment = mortgage_payment(
            loan_amount, scenario.mortgage_rate, scenario.mortgage_term_years
        )
        monthly_prop_tax = scenario.home_price * scenario.property_tax_rate / 12
        monthly_home_ins = scenario.home_price * scenario.home_insurance_rate / 12

        # Build rent and owning cost lists
        monthly_rent = []
        rent = scenario.initial_rent
        for year in range(scenario.horizon_years):
            for _ in range(12):
                monthly_rent.append(rent)
            rent *= (1 + scenario.rent_increase_rate)
        monthly_rent = monthly_rent[:horizon_months]
        owning_costs = []
        renting_costs = []
        for month in range(horizon_months):
            own_cost = monthly_mortgage_payment + monthly_prop_tax + monthly_home_ins
            rent_cost = monthly_rent[month] + scenario.renters_insurance
            owning_costs.append(own_cost)
            renting_costs.append(rent_cost)
        # Cashflow target per month
        cashflow_target = [max(o, r) for o, r in zip(owning_costs, renting_costs)]
        # Contributions
        rent_contrib = [target - r for target, r in zip(cashflow_target, renting_costs)]
        buy_contrib = [target - o for target, o in zip(cashflow_target, owning_costs)]

        # Investment growth for renting scenario (with down payment)
        rent_growth = compute_investment_growth(
            down_payment, rent_contrib, scenario.investment_return_rate, scenario.horizon_years
        )

        # Net proceeds for buying scenario if sold each year
        buy_proceeds = compute_yearly_buy_proceeds(
            scenario, owning_costs, buy_contrib, loan_amount
        )

        # Display results using split columns
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Renting: Investment Growth")
            st.write(
                "The chart below shows how your investment portfolio (down payment "
                "plus monthly savings) grows over the horizon while renting."
            )
            fig, ax = plt.subplots(figsize=(6, 4))
            rent_growth.plot(ax=ax)
            ax.set_xlabel("Month")
            ax.set_ylabel("Portfolio Value ($)")
            ax.set_title("Renting Investment Growth Over Time")
            ax.grid(True, which="both", linestyle="--", linewidth=0.5)
            st.pyplot(fig)
            st.write(
                f"Final portfolio value after {scenario.horizon_years} years: "
                f"${rent_growth.iloc[-1]:,.2f}"
            )

        with col2:
            st.subheader("Buying: Net Proceeds by Year")
            st.write(
                "If you sell the home at the end of each year, this chart shows "
                "the estimated net proceeds after paying off the remaining mortgage "
                "and deducting sales costs.  Positive monthly savings are also "
                "invested in the stock market."
            )
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            buy_proceeds.plot(kind="bar", ax=ax2)
            ax2.set_xlabel("Years")
            ax2.set_ylabel("Net Proceeds ($)")
            ax2.set_title("Buying: Net Proceeds if Sold Each Year")
            ax2.grid(True, axis="y", linestyle="--", linewidth=0.5)
            st.pyplot(fig2)
            st.write(
                f"Net proceeds after {scenario.horizon_years} years (keep the home): "
                f"${buy_proceeds.iloc[-1]:,.2f}"
            )


if __name__ == "__main__":  # pragma: no cover
    main()