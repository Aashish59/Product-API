
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Input schema for a single checkout item
class LineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(ge=1, le=1000, strict=True)


# Input schema for checkout request
class CheckoutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    items: list[LineIn] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_products(self):
        ids = [line.product_id for line in self.items]

        if len(ids) != len(set(ids)):
            raise ValueError("Send one line per product")

        return self


# Output schema for a single receipt item
class ReceiptLine(BaseModel):
    product_id: int
    name: str
    unit_price_minor: int
    quantity: int


# Output schema for checkout receipt
class Receipt(BaseModel):
    request_id: UUID
    total_minor: int
    items: list[ReceiptLine]
