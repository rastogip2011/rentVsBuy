"""
Rent vs. Buy comparison calculator.

This module implements a financial model to compare renting a home versus buying
a home over a fixed horizon.  The comparison attempts to keep the total cash
outflow the same across both scenarios by investing any difference in monthly
costs (mortgage vs. rent) into a hypothetical stock market portfolio.  The
portfolio earns a fixed annual rate of return, compounded monthly.

Functions are provided to compute mortgage payments, amortization schedules,
future values of lump‑sum and periodic investments, and the net proceeds from
selling a home after paying agent commissions and closing costs.  You can
adjust the parameters to explore different financial outcomes.

Assumptions:

* Mortgage term is 30 years (360 months) unless otherwise specified.
* Mortgage payments are fixed rate and fully amortizing.
* Property taxes and homeowners insurance are paid monthly at rates
  specified as percentages of the initial purchase price.
* Rent increases annually at a fixed rate.
* Down payment money and any monthly cost differences are invested in a
  portfolio earning a fixed annual return (compounded monthly).
* The home appreciates at a constant annual growth rate.  Net sale proceeds
  are calculated after subtracting real estate commissions and closing costs.

This file can be executed directly to run a simple example or imported as
needed.  See the ``main`` block at the bottom for a demonstration.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ScenarioInput:
    """Container for the input parameters of the rent vs. buy comparison.

    Note:
        In a dataclass, fields without default values must appear before fields
        that have default values.  To satisfy this requirement, `initial_rent`,
        `rent_increase_rate`, and `home_price` are positioned before any fields
        with default values.
    """

    # Required parameters (no defaults)
    initial_rent: float  # Monthly rent at time zero
    rent_increase_rate: float  # Annual rent increase rate (e.g., 0.03 for 3%)
    home_price: float  # Purchase price of the home

    # Renting parameters
    renters_insurance: float = 50.0  # Monthly renter's insurance (constant)

    # Buying parameters
    down_payment_rate: float = 0.20  # Down payment as a fraction of price
    mortgage_rate: float = 0.0715  # Annual mortgage interest rate
    mortgage_term_years: int = 30  # Duration of the mortgage in years
    property_tax_rate: float = 0.0094  # Annual property tax as a fraction of price
    home_insurance_rate: float = 0.0033  # Annual home insurance as a fraction of price
    hoa_monthly: float = 0.0  # Monthly HOA fee in dollars

    # Investment parameters
    investment_return_rate: float = 0.10  # Annual return on invested cash
    horizon_years: int = 5  # Number of years to compare

    # Sale parameters
    appreciation_rate: float = 0.05  # Annual home appreciation rate
    sales_cost_rate: float = 0.05  # Fraction of sale price lost to commissions/fees


def mortgage_payment(principal: float, annual_rate: float, term_years: int) -> float:
    """Compute the fixed monthly payment for a mortgage.

    Args:
        principal: Amount borrowed (purchase price minus down payment).
        annual_rate: Annual interest rate (e.g., 0.07 for 7%).
        term_years: Loan term in years.

    Returns:
        The monthly mortgage payment.
    """
    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    if monthly_rate == 0:
        return principal / n_payments
    discount_factor = (1 - (1 + monthly_rate) ** -n_payments) / monthly_rate
    return principal / discount_factor


def amortization_schedule(
    principal: float, annual_rate: float, term_years: int, months: int
) -> Tuple[List[float], List[float], float]:
    """Generate an amortization schedule for the first `months` of a loan.

    Args:
        principal: Initial loan amount.
        annual_rate: Annual interest rate.
        term_years: Duration of the loan in years.
        months: Number of months for which to compute the schedule.

    Returns:
        A tuple containing three items:
            * A list of interest payments for each month.
            * A list of principal payments for each month.
            * The remaining principal after the specified number of months.
    """
    monthly_payment = mortgage_payment(principal, annual_rate, term_years)
    monthly_rate = annual_rate / 12
    remaining_principal = principal
    interest_payments: List[float] = []
    principal_payments: List[float] = []
    for _ in range(months):
        interest = remaining_principal * monthly_rate
        principal_paid = monthly_payment - interest
        remaining_principal -= principal_paid
        # Prevent negative principal due to rounding
        if remaining_principal < 0:
            principal_paid += remaining_principal
            remaining_principal = 0
        interest_payments.append(interest)
        principal_payments.append(principal_paid)
    return interest_payments, principal_payments, remaining_principal


def future_value_lump_sum(amount: float, annual_rate: float, years: float) -> float:
    """Compute the future value of a lump sum after a certain number of years.

    Args:
        amount: Initial investment amount.
        annual_rate: Annual return rate.
        years: Number of years.

    Returns:
        Future value of the investment.
    """
    return amount * (1 + annual_rate) ** years


def future_value_periodic_contribution(
    contribution: List[float], annual_rate: float, months: int
) -> float:
    """Compute the future value of a series of periodic contributions.

    Contributions are assumed to occur at the end of each month.  Each
    contribution compounds at a fixed annual rate until the end of the
    investment horizon.  The function accepts a list of contributions, one per
    month.

    Args:
        contribution: List of monthly contribution amounts (length equal to
            number of months).
        annual_rate: Annual return rate (e.g., 0.10 for 10%).
        months: Number of months in the investment horizon.

    Returns:
        Future value of all contributions combined.
    """
    monthly_rate = annual_rate / 12
    fv = 0.0
    for i, c in enumerate(contribution):
        # Number of months the contribution will be invested
        months_left = months - i
        fv += c * (1 + monthly_rate) ** months_left
    return fv


def rent_vs_buy(scenario: ScenarioInput) -> Tuple[float, float]:
    """Compare renting versus buying over a specified horizon.

    The function returns a tuple with two values: (rent_final, buy_final)
    representing the portfolio value (for renting) and the combined
    portfolio + net home sale proceeds (for buying) at the end of the horizon.

    Args:
        scenario: A ScenarioInput instance containing all input parameters.

    Returns:
        A tuple (final_rent_value, final_buy_value).
    """
    # Derived values
    horizon_months = scenario.horizon_years * 12
    down_payment = scenario.home_price * scenario.down_payment_rate
    loan_amount = scenario.home_price - down_payment
    monthly_mortgage_payment = mortgage_payment(
        loan_amount, scenario.mortgage_rate, scenario.mortgage_term_years
    )
    monthly_prop_tax = scenario.home_price * scenario.property_tax_rate / 12
    monthly_home_ins = scenario.home_price * scenario.home_insurance_rate / 12

    # Generate amortization schedule for the horizon
    interest_payments, principal_payments, remaining_principal = amortization_schedule(
        loan_amount,
        scenario.mortgage_rate,
        scenario.mortgage_term_years,
        horizon_months,
    )

    # Monthly rent values over the horizon
    monthly_rent = []
    rent = scenario.initial_rent
    for year in range(scenario.horizon_years):
        for _ in range(12):
            monthly_rent.append(rent)
        rent *= (1 + scenario.rent_increase_rate)
    # Ensure length matches horizon
    monthly_rent = monthly_rent[:horizon_months]

    # Monthly cost lists
    owning_costs = []
    renting_costs = []

    for month in range(horizon_months):
        owning_cost = monthly_mortgage_payment + monthly_prop_tax + monthly_home_ins + scenario.hoa_monthly
        rent_cost = monthly_rent[month] + scenario.renters_insurance
        owning_costs.append(owning_cost)
        renting_costs.append(rent_cost)

    # Determine the cashflow target (the higher of owning and renting each month)
    cashflow_target = [max(o, r) for o, r in zip(owning_costs, renting_costs)]

    # Calculate monthly contributions to the investment portfolio for both scenarios
    rent_contributions = []  # contributions for the renting scenario
    buy_contributions = []   # contributions for the buying scenario
    for o, r, target in zip(owning_costs, renting_costs, cashflow_target):
        rent_contributions.append(target - r)  # renter invests difference
        buy_contributions.append(target - o)   # buyer invests difference

    # Compute future value of the lump‑sum (down payment) invested at the start
    fv_lump_sum = future_value_lump_sum(
        down_payment, scenario.investment_return_rate, scenario.horizon_years
    )

    # Future value of monthly contributions (invested at the end of each month)
    fv_rent_contrib = future_value_periodic_contribution(
        rent_contributions, scenario.investment_return_rate, horizon_months
    )
    fv_buy_contrib = future_value_periodic_contribution(
        buy_contributions, scenario.investment_return_rate, horizon_months
    )

    # Final portfolio values
    final_rent_value = fv_lump_sum + fv_rent_contrib

    # For the buyer, also consider the value of the home and remaining mortgage
    # after the horizon.
    # Calculate the home's appreciated value
    future_home_value = scenario.home_price * (1 + scenario.appreciation_rate) ** scenario.horizon_years
    # Net sale proceeds after commissions/closing costs
    net_sale_price = future_home_value * (1 - scenario.sales_cost_rate)
    # Mortgage payoff is the remaining principal
    net_proceeds = net_sale_price - remaining_principal

    final_buy_value = fv_buy_contrib + net_proceeds

    return final_rent_value, final_buy_value


def main():  # pragma: no cover
    """Run a sample comparison using typical inputs.

    This example prints the final values for both renting and buying scenarios.
    You can modify the parameters below to explore different situations.
    """
    scenario = ScenarioInput(
        initial_rent=3000,
        rent_increase_rate=0.03,
        renters_insurance=50,
        home_price=800000,
        down_payment_rate=0.2,
        mortgage_rate=0.0715,
        mortgage_term_years=30,
        property_tax_rate=0.0094,
        home_insurance_rate=0.0033,
        investment_return_rate=0.10,
        horizon_years=5,
        appreciation_rate=0.055,
        sales_cost_rate=0.05,
    )
    rent_value, buy_value = rent_vs_buy(scenario)
    print(f"Renting scenario portfolio value after {scenario.horizon_years} years: ${rent_value:,.2f}")
    print(f"Buying scenario total value after {scenario.horizon_years} years:  ${buy_value:,.2f}")


if __name__ == "__main__":  # pragma: no cover
    main()
