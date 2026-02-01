from services.billing.domain.invoice.model.invoice import Invoice
from services.identity.core.auth import verify_token


def create_invoice(request):
    verify_token(request.token)
    return Invoice.create(request.data)
