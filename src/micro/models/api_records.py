from __future__ import annotations

from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field, ConfigDict, BaseModel

# fmt: off


class StaffServiceLink(BaseModel):
    length: int


class CompanyServiceLink(BaseModel):
    price_min: int
    price_max: int


class Service(BaseModel):
    id: int
    title: str
    cost: int
    cost_to_pay: int
    manual_cost: int
    cost_per_unit: int
    discount: int
    first_cost: int
    amount: int
    staff_service_link: StaffServiceLink
    company_service_link: CompanyServiceLink


class Position(BaseModel):
    id: int
    title: str
    services_binding_type: int


class Staff(BaseModel):
    """Test describe"""

    # model_config = ConfigDict(title="test title") # noqa
    id: int
    api_id: str
    name: str
    specialization: str
    position: Position
    avatar: str
    avatar_big: str
    rating: int
    votes_count: int


class Client(BaseModel):
    id: int = Field(..., description="Идентификатор клиента") # noqa # noqa
    name: str = Field(..., description="Имя клиента") # noqa
    surname: str = Field(..., description="Фамилия клиента") # noqa
    patronymic: str = Field(..., description="Отчество клиента") # noqa
    display_name: str = Field(..., description="Отображаемое имя клиента") # noqa
    comment: str = Field(..., description="Комментарий") # noqa
    phone: str = Field(..., description="Номер телефона клиента") # noqa
    card: str = Field(..., description="Номер карты лояльности клиента") # noqa
    email: str = Field(..., description="Email клиента") # noqa
    success_visits_count: int = Field(..., description="Количество завершенных визитов") # noqa
    fail_visits_count: int = Field(..., description='Количество визитов в статусе "Не пришел"') # noqa
    discount: int = Field(..., description="Скидка клиента") # noqa
    is_new: bool = Field(..., description="Клиент является новым") # noqa
    # custom_fields: List
    sex: int = Field(..., description="Пол клиента") # noqa
    birthday: str = Field(..., description="День рождение клиента") # noqa
    # client_tags: List
    phone_country_id: int = Field(..., description="") # noqa


class Document(BaseModel):
    id: int
    type_id: int
    storage_id: int
    user_id: int
    company_id: int
    number: int
    comment: str
    date_created: str
    category_id: int
    visit_id: int
    record_id: int
    type_title: str
    is_sale_bill_printed: bool


class YclientsRecord(AvroBase, title="api.yclientsRecord"):
    id: int = Field(..., description="Идентификатор записи") # noqa
    company_id: int = Field(..., description="Идентификатор компании") # noqa
    staff_id: int = Field(..., description="Идентификатор сотрудника") # noqa
    services: List[Service] = Field(..., description="Массив объектов с услугами в записи") # noqa
    # goods_transactions: List = Field(..., description="Массив товарных транзакций") # noqa
    staff: Staff = Field(..., description="Объект данных о сотруднике") # noqa
    client: Client | None = Field(None, description="Данные клиента (может быть пустым)") # noqa
    comer: str | None = Field(None, description="Данные о посетителе (может быть null)") # noqa
    comer_person_info: str = Field(..., description="comer_person_info") # noqa
    clients_count: int = Field(..., description="Количество клиентов (В индивидуальной записи всегда = 1)") # noqa
    date: str = Field(..., description='Дата сеанса, формат "2019-01-16 16:00:00"') # noqa
    datetime: str = Field(..., description='Дата сеанса в ISO, формат "2019-01-16T16:00:00+09:00"') # noqa
    create_date: str = Field(..., description='Дата создания сеанса, формат "2019-01-16T16:00:00+09:00"') # noqa
    comment: str
    online: bool
    visit_attendance: int
    attendance: int
    confirmed: int
    seance_length: int
    length: int
    sms_before: int
    sms_now: int
    sms_now_text: str
    email_now: int
    notified: int
    master_request: int
    api_id: str
    from_url: str
    review_requested: int
    visit_id: int
    created_user_id: int
    deleted: bool
    paid_full: int
    prepaid: bool
    prepaid_confirmed: bool
    is_update_blocked: bool
    last_change_date: str
    custom_color: str
    custom_font_color: str
    # record_labels: List
    activity_id: int
    # custom_fields: List
    documents: List[Document]
    sms_remain_hours: int
    email_remain_hours: int
    bookform_id: int
    record_from: str
    is_mobile: int
    short_link: str
    is_remind_sms_sent: bool
    payment_status: int
    # consumables: List
    # finance_transactions: List
