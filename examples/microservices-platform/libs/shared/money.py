# This import violates the library-no-service-deps rule
# Libraries should not depend on service code
from services.billing.domain.invoice.model.invoice import Invoice


class Money:
    def __init__(self, amount: float):
        self.amount = amount

    def to_invoice(self) -> Invoice:
        # This method couples library code to service code - a violation!
        return Invoice(amount=self.amount)
