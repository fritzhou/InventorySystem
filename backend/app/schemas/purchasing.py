import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.purchasing import PurchaseOrderStatus

class SupplierInput(BaseModel):
    name: str=Field(min_length=1,max_length=160); contact_person: str|None=None; phone: str|None=None; email: str|None=None; address: str|None=None; notes: str|None=None
    @field_validator("name")
    @classmethod
    def name_required(cls,v):
        if not v.strip(): raise ValueError("Supplier name is required.")
        return v.strip()
class SupplierUpdate(BaseModel):
    name: str|None=Field(None,min_length=1,max_length=160); contact_person: str|None=None; phone: str|None=None; email: str|None=None; address: str|None=None; notes: str|None=None; is_active: bool|None=None
class SupplierRead(SupplierInput):
    model_config=ConfigDict(from_attributes=True); id: uuid.UUID; is_active: bool; created_at: datetime; updated_at: datetime
class SupplierPage(BaseModel): items:list[SupplierRead]; page:int; page_size:int; total_items:int; total_pages:int

class POItemInput(BaseModel): product_id:uuid.UUID; quantity:int=Field(gt=0); unit_cost:Decimal=Field(ge=0,max_digits=12,decimal_places=2)
class POCreate(BaseModel): supplier_id:uuid.UUID; expected_date:date|None=None; notes:str|None=None; items:list[POItemInput]=Field(min_length=1)
class POUpdate(POCreate): pass
class ReceiveLine(BaseModel): item_id:uuid.UUID; quantity:int=Field(gt=0)
class ReceiveInput(BaseModel): items:list[ReceiveLine]=Field(min_length=1)
class POItemRead(BaseModel):
    model_config=ConfigDict(from_attributes=True); id:uuid.UUID; product_id:uuid.UUID; product_name:str; sku:str; ordered_quantity:int; received_quantity:int; unit_cost:Decimal; line_total:Decimal
class PORead(BaseModel):
    model_config=ConfigDict(from_attributes=True); id:uuid.UUID; po_number:str; supplier_id:uuid.UUID; supplier:SupplierRead; status:PurchaseOrderStatus; order_date:date; expected_date:date|None; notes:str|None; subtotal:Decimal; items:list[POItemRead]; created_at:datetime; updated_at:datetime
class POPage(BaseModel): items:list[PORead]; page:int; page_size:int; total_items:int; total_pages:int
