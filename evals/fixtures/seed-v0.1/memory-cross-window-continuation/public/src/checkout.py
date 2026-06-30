from decimal import Decimal


def checkout_total(subtotal, discount_percent, tax_percent):
    """Return the v2 checkout total. The previous window left this unfinished."""
    subtotal = Decimal(str(subtotal))
    discount_percent = Decimal(str(discount_percent))
    tax_percent = Decimal(str(tax_percent))
    raise NotImplementedError("continue checkout-implementation from the current requirement")
