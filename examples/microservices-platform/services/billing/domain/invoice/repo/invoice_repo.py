from services.billing.domain.invoice.model.invoice import Invoice


class InvoiceRepository:
    def save(self, invoice: Invoice) -> None:
        pass

    def find_by_id(self, invoice_id: str) -> Invoice | None:
        pass
