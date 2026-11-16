from pydantic import BaseModel, ConfigDict, Field, model_validator

class ProductCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    sku: str = Field(pattern=r"^[A-Z0-9-]{3,24}$")
    name: str = Field(min_length=3, max_length=80)
    price_minor: int = Field(ge=1, le=2_000_000_000, strict=True)
    stock: int = Field(ge=0, le=1_000_000, strict=True)
   

class ProductOut(ProductCreate):
  id: int


class ProductPatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    name: str | None = Field(default=None, min_length=3, max_length=80)
    price_minor: int | None = Field(default=None, ge=1, le=2_000_000_000,strict=True)
    stock: int | None = Field(default=None, ge=0, le=1_000_000, strict=True)

    @model_validator(mode="after")
    def check_changes(self):
      if not self.model_fields_set:
        raise ValueError("Provide at least one change")

      if any(
        getattr(self, key) is None
        for key in self.model_fields_set
      ):
        raise ValueError("Provided fields cannot be null")

      return self

class ProductPage(BaseModel):
  items: list[ProductOut]
  total: int
  offset: int
  limit: int

class ProductBatch(BaseModel):
  model_config = ConfigDict(extra="forbid")
  products: list[ProductCreate] = Field(min_length=1, max_length=20)