#!/usr/bin/env python3
"""Print a month-by-month repayment table for a fixed-rate loan.

Usage:
    p09_loan_table.py AMOUNT YEARLY_RATE_PERCENT MONTHS

Example: 10,000 borrowed at 6% a year over 12 months
    p09_loan_table.py 10000 6 12

Interest is charged monthly at one twelfth of the yearly rate. All figures
are rounded to cents, and the final payment is adjusted so the balance ends
at exactly zero.
"""

import argparse
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def to_cents(value):
    """Round a Decimal to two places, halves away from zero."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_payment(amount, monthly_rate, months):
    """Standard annuity formula: P * r / (1 - (1 + r)^-n)."""
    if monthly_rate == 0:
        return to_cents(amount / months)
    factor = (1 + monthly_rate) ** months
    return to_cents(amount * monthly_rate * factor / (factor - 1))


def schedule(amount, yearly_rate_percent, months):
    """Yield (month, payment, interest, principal, balance) for each month."""
    monthly_rate = yearly_rate_percent / Decimal(100) / Decimal(12)
    payment = monthly_payment(amount, monthly_rate, months)
    balance = amount

    for month in range(1, months + 1):
        interest = to_cents(balance * monthly_rate)
        if month == months:
            # Last month clears whatever rounding has left over.
            payment = balance + interest
        principal = payment - interest
        balance -= principal
        yield month, payment, interest, principal, balance


def print_table(amount, yearly_rate_percent, months):
    """Print the repayment table followed by totals."""
    print(f"Loan {amount:,.2f} at {yearly_rate_percent}% per year over {months} months")
    print()
    header = f"{'Month':>5}  {'Payment':>12}  {'Interest':>12}  {'Principal':>12}  {'Balance':>14}"
    print(header)
    print("-" * len(header))

    total_paid = total_interest = Decimal(0)
    for month, payment, interest, principal, balance in schedule(
        amount, yearly_rate_percent, months
    ):
        total_paid += payment
        total_interest += interest
        print(
            f"{month:>5}  {payment:>12,.2f}  {interest:>12,.2f}"
            f"  {principal:>12,.2f}  {balance:>14,.2f}"
        )

    print("-" * len(header))
    print(f"{'Total':>5}  {total_paid:>12,.2f}  {total_interest:>12,.2f}")


def decimal_arg(text):
    """argparse type: a finite decimal number."""
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not value.is_finite():
        raise argparse.ArgumentTypeError(f"not a finite number: {text!r}")
    return value


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Print a repayment table for a fixed-rate loan."
    )
    parser.add_argument("amount", type=decimal_arg, help="amount borrowed, e.g. 10000")
    parser.add_argument(
        "rate", type=decimal_arg, help="yearly interest rate in percent, e.g. 6.5"
    )
    parser.add_argument("months", type=int, help="number of monthly payments")
    args = parser.parse_args(argv)

    if args.amount <= 0:
        parser.error("amount must be greater than zero")
    if args.amount != to_cents(args.amount):
        parser.error("amount must have at most two decimal places")
    if args.rate < 0:
        parser.error("rate cannot be negative")
    if args.months <= 0:
        parser.error("months must be greater than zero")
    return args


def main(argv=None):
    args = parse_args(argv)
    print_table(args.amount, args.rate, args.months)
    return 0


if __name__ == "__main__":
    sys.exit(main())
