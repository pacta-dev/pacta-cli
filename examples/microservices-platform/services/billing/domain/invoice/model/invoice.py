from libs.shared.money import Money


class Invoice:
    def __init__(self, amount: "Money"):
        self.amount = amount

    @classmethod
    def create(cls, data: dict) -> "Invoice":
        return cls(amount=Money(data["amount"]))
