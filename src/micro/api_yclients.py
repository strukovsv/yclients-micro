import asyncio
import datetime
import itertools
import logging
import os

import httpx  # type: ignore

import micro.config as config
from micro.singleton import MetaSingleton

from .metrics import (
    API_YCLIENTS_DELETE_REQUEST_CNT,
    API_YCLIENTS_GET_REQUEST_CNT,
    API_YCLIENTS_POST_REQUEST_CNT,
    API_YCLIENTS_REQUEST_ERROR_CNT,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 4
MIN_REQUEST_INTERVAL = 1.0
IMOBIS_PAGE_COUNT = 10
IMOBIS_TIMEOUT = 60.0


class Yclients(metaclass=MetaSingleton):

    partner_token: str | None = None
    headers_partner: dict[str, str] | None = None
    headers_user: dict[str, str] | None = None
    # Включен режим отладки
    debug: bool | None = None
    # Каналы отправки закэшировать
    fromni_channels: list | None = None

    def __init__(self, is_create_yaml: bool | None = None):
        self.chain_id = config.CHAIN_ID
        self.company_id = config.COMPANY_ID
        self.is_create_yaml = is_create_yaml
        # Включен режим отладки, не отправляем данные в yclient
        self.debug = str(os.environ.get("YCLIENTS_DEBUG", "0")) != "0"

    def imobis_url(self, com):
        return f"https://api.fromni.ru/user/{com}"

    async def imobis_post(self, url, body=None):
        logger.debug("imobis post !!!")
        async with httpx.AsyncClient() as client:
            # Сформировать заголовок для авторизации imobis
            self.headers_imobis = {
                "Authorization": f"Token {config.IMOBIS_TOKEN}",
                "Content-Type": "application/json",
            }
            logger.debug(f"{self.headers_partner=}")
            # Авторизоваться в системе
            try:
                API_YCLIENTS_POST_REQUEST_CNT.inc()
                r = await client.post(
                    self.imobis_url(url),
                    headers=self.headers_imobis,
                    json=body,
                    timeout=60.0,
                )
                logger.info(f"imobis_post: {r.text=}")
                logger.info(f"imobis_post: {r.content=}")
            except Exception as e:
                API_YCLIENTS_REQUEST_ERROR_CNT.inc()
                # Получить user token
                logger.error(f"{e=}")
                logger.error(f"{self.imobis_url(url)=}")
                logger.error(f"{self.headers_imobis=}")
                try:
                    logger.error(r.text)
                except Exception:
                    pass
                raise
            try:
                result = r.json()
            except Exception as e:
                API_YCLIENTS_REQUEST_ERROR_CNT.inc()
                # Получить user token
                logger.error(r.text)
                logger.error(e)
                raise
            return result

    def url(self, com):
        return f"https://api.yclients.com/api/v1/{com}"

    def _build_partner_headers(self) -> dict:
        """Формирует заголовки для авторизации по партнёрскому токену."""
        return {
            "Authorization": f"Bearer {config.PARTNER_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.yclients.v2+json",
        }

    def _build_user_headers(self, user_token: str) -> dict:
        """Формирует заголовки для авторизации по пользовательскому токену."""
        return {
            "Authorization": f"Bearer {config.PARTNER_TOKEN}, User {user_token}",  # noqa
            "Content-Type": "application/json",
            "Accept": "application/vnd.yclients.v2+json",
        }

    async def _fetch_user_token(self, headers: dict) -> str:
        """Выполняет запрос авторизации и возвращает user_token."""
        async with httpx.AsyncClient() as client:
            r = await self._send_auth_request(client, headers)
            return self._extract_user_token(r)

    async def _send_auth_request(self, client, headers: dict):
        """Отправляет POST-запрос авторизации."""
        API_YCLIENTS_POST_REQUEST_CNT.inc()
        try:
            return await client.post(
                self.url("auth"),
                headers=headers,
                json={
                    "login": config.YCLIENT_LOGIN,
                    "password": config.YCLIENT_PASSWORD,
                },
                timeout=10.0,
            )
        except Exception as e:
            API_YCLIENTS_REQUEST_ERROR_CNT.inc()
            logger.error(f"Auth request failed: {e=}")
            logger.error(f"URL: {self.url('auth')=}")
            logger.error(f"Headers: {headers=}")
            raise

    def _extract_user_token(self, r) -> str:
        """Парсит ответ авторизации и извлекает user_token."""
        try:
            auth = r.json()
            return auth["data"]["user_token"]
        except Exception as e:
            API_YCLIENTS_REQUEST_ERROR_CNT.inc()
            logger.error(f"Failed to parse auth response: {r.text}, {e}")
            raise

    async def auth(self) -> dict:
        """Авторизация в YClients.
        Возвращает заголовки пользователя,
        кэшируя результат."""
        if self.headers_user is not None:
            return self.headers_user

        logger.debug("auth: starting authentication")

        partner_headers = self._build_partner_headers()
        user_token = await self._fetch_user_token(partner_headers)

        self.user_token = user_token
        self.headers_user = self._build_user_headers(user_token)

        logger.debug(f"{self.user_token=}")
        return self.headers_user

    async def load_object(
        self,
        obj_name: str | None,
        url: str,
        params: dict,
        headers: dict | None = None,
        method: str = "get",
        pagination: bool = True,
    ) -> list:
        """Запросить объект из API.

        :param obj_name: наименование объекта, yaml файла и базовой таблицы
        :param url: ручка api
        :param params: параметры запроса
        :param headers: заголовок; по умолчанию заголовок пользователя
        :param method: http метод (get/post)
        :param pagination: включить постраничную загрузку
        :return: список объектов
        """
        _headers = headers or await self.auth()

        async with httpx.AsyncClient() as client:
            return await self._load_all_pages(
                client, url, params, _headers, method, pagination
            )

    async def _load_all_pages(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
        method: str,
        pagination: bool,
    ) -> list:
        """Постранично загружает данные из API."""
        records = []

        for page in itertools.count(start=1):
            rows = await self._load_page(
                client,
                url,
                {**params, "page": page, "count": config.PAGE_COUNT},
                headers,
                method,
            )

            if isinstance(rows, list):
                records.extend(rows)
                if not pagination or len(rows) < config.PAGE_COUNT:
                    break
            elif rows:
                records.append(rows)
                break
            else:
                break

        return records

    async def _load_page(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
        method: str,
    ) -> list | dict | None:
        """Загружает одну страницу с повторными попытками и rate limiting."""
        start = datetime.datetime.now()
        rows = await self._request_with_retries(
            client, url, params, headers, method
        )
        await self._enforce_rate_limit(start)
        return rows

    async def _request_with_retries(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
        method: str,
    ) -> list | dict | None:
        """Выполняет запрос с повторными попытками при ошибках."""
        full_url = self.url(url)
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                return await self._execute_request(
                    client, full_url, params, headers, method
                )
            except Exception as e:
                last_exception = e
                is_last_attempt = attempt == MAX_RETRIES - 1

                if is_last_attempt:
                    break

                logger.debug(
                    f'attempt: "{attempt}", error: "{e}", url: "{full_url}"'
                )
                await asyncio.sleep(10)

        return self._handle_final_error(
            last_exception, method, full_url, params, client  # type: ignore
        )

    async def _execute_request(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
        method: str,
    ) -> list | dict:
        """Выполняет один HTTP-запрос и валидирует ответ."""
        if method == "get":
            API_YCLIENTS_GET_REQUEST_CNT.inc()
            r = await client.get(
                url, headers=headers, params=params, timeout=10.0
            )
        else:
            API_YCLIENTS_POST_REQUEST_CNT.inc()
            r = await client.post(
                url, headers=headers, json=params, timeout=10.0
            )

        js = r.json()
        if not js["success"]:
            raise Exception(js["meta"]["message"])

        return js["data"]

    def _handle_final_error(
        self,
        e: Exception,
        method: str,
        url: str,
        params: dict,
        client,
    ) -> list | None:
        """Обрабатывает финальную ошибку после исчерпания попыток."""
        API_YCLIENTS_REQUEST_ERROR_CNT.inc()

        try:
            response = (
                client._transport
            )  # получаем последний ответ если доступен
        except Exception:
            response = None

        context = f'url: "{method} {url}", response: "{response}", params: "{params}"'  # noqa

        if str(e) == "Не найдено":
            logger.error(
                f'{context}, message: "Не найдено записей, вернуть []"'
            )
            return []

        raise Exception(f'{context}, message: "{e}"')

    async def _enforce_rate_limit(self, start: datetime.datetime) -> None:
        """Обеспечивает минимальный интервал между запросами (1 запрос/сек)."""
        elapsed = (datetime.datetime.now() - start).total_seconds()
        remain = MIN_REQUEST_INTERVAL - elapsed
        if remain > 0:
            logger.debug(f"rate limit sleep: {remain:.3f}s")
            await asyncio.sleep(remain)

    def imobis_get_transport(self) -> httpx.AsyncHTTPTransport | None:
        """Возвращает транспорт с прокси для Imobis, если задан в конфиге."""
        if not config.IMOBIS_HTTP_PROXY:
            return None
        return httpx.AsyncHTTPTransport(proxy=config.IMOBIS_HTTP_PROXY)

    async def imobis_load_object(
        self,
        obj_name: str,
        url: str,
        params: dict,
        pagination: bool = True,
        is_get_blocks: bool = True,
    ) -> list:
        """Загружает объекты из Imobis API с поддержкой пагинации.

        :param obj_name: наименование объекта / yaml файла / базовой таблицы
        :param url: ручка api
        :param params: параметры запроса
        :param pagination: включить постраничную загрузку
        :param is_get_blocks: использовать offset/limit пагинацию
        :return: список объектов
        """
        headers = self._build_imobis_headers()

        async with httpx.AsyncClient(
            transport=self.imobis_get_transport()
        ) as client:
            return await self._imobis_load_all_pages(
                client, url, params, headers, pagination, is_get_blocks
            )

    def _build_imobis_headers(self) -> dict:
        """Формирует заголовки для запросов к Imobis API."""
        return {
            "Authorization": f"Token {config.IMOBIS_TOKEN}",
            "Content-Type": "application/json",
        }

    async def _imobis_load_all_pages(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
        pagination: bool,
        is_get_blocks: bool,
    ) -> list:
        """Постранично загружает данные из Imobis API."""
        records = []

        for page in itertools.count(start=0):
            page_params = self._build_page_params(params, page, is_get_blocks)
            rows = await self._imobis_load_page(
                client, url, page_params, headers
            )

            if isinstance(rows, list):
                records.extend(rows)
                if self._imobis_should_stop(rows, pagination, is_get_blocks):
                    break
            elif rows:
                records.append(rows)
                break
            else:
                break

        return records

    def _build_page_params(
        self, params: dict, page: int, is_get_blocks: bool
    ) -> dict:
        """Добавляет offset/limit к параметрам запроса."""
        if not is_get_blocks:
            return {**params}
        return {
            **params,
            "offset": page * IMOBIS_PAGE_COUNT,
            "limit": IMOBIS_PAGE_COUNT,
        }

    def _imobis_should_stop(
        self, rows: list, pagination: bool, is_get_blocks: bool
    ) -> bool:
        """Определяет, нужно ли прекратить загрузку следующих страниц."""
        if not pagination:
            return True
        if not is_get_blocks:
            return True
        return len(rows) < IMOBIS_PAGE_COUNT

    async def _imobis_load_page(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
    ) -> list | dict | None:
        """Загружает одну страницу с повторными попытками и rate limiting."""
        start = datetime.datetime.now()
        rows = await self._imobis_request_with_retries(
            client, url, params, headers
        )
        await self._enforce_rate_limit(start)
        return rows

    async def _imobis_request_with_retries(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
    ) -> list | dict | None:
        """Выполняет запрос с повторными попытками при ошибках."""
        full_url = self.imobis_url(url)
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                return await self._imobis_execute_request(
                    client, full_url, params, headers
                )
            except Exception as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    logger.debug(
                        f'attempt: "{attempt}", error: "{e}", url: "{full_url}"'  # noqa
                    )
                    await asyncio.sleep(10)

        return self._imobis_handle_final_error(
            last_exception, full_url, params  # type: ignore
        )

    async def _imobis_execute_request(
        self,
        client,
        url: str,
        params: dict,
        headers: dict,
    ) -> list | dict:
        """Выполняет один POST-запрос к Imobis и валидирует ответ."""
        API_YCLIENTS_POST_REQUEST_CNT.inc()
        r = await self._imobis_post_with_error_handling(
            client, url, params, headers
        )

        js = r.json()
        if js.get("result") != "success":
            raise Exception(js.get("meta", {}).get("message", "Unknown error"))

        return js["data"]

    async def _imobis_post_with_error_handling(
        self, client, url: str, params: dict, headers: dict
    ):
        """Отправляет POST-запрос с детальным логированием сетевых ошибок."""
        try:
            return await client.post(
                url, headers=headers, json=params, timeout=IMOBIS_TIMEOUT
            )
        except httpx.ConnectTimeout:
            logger.error("Таймаут подключения к Imobis API")
            raise
        except httpx.ReadTimeout:
            logger.error("Таймаут ожидания ответа от Imobis API")
            raise
        except httpx.NetworkError as e:
            logger.error(f"Сетевая ошибка при обращении к Imobis: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP ошибка от Imobis: {e.response.status_code} - {e}"
            )
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке в Imobis: {e}")
            raise

    def _imobis_handle_final_error(
        self,
        e: Exception,
        url: str,
        params: dict,
    ) -> list | None:
        """Обрабатывает финальную ошибку после исчерпания попыток."""
        API_YCLIENTS_REQUEST_ERROR_CNT.inc()
        context = f'url: "{url}", params: "{params}"'

        if str(e) == "Не найдено":
            logger.error(
                f'{context}, message: "Не найдено записей, вернуть []"'
            )
            return []

        raise Exception(f'{context}, message: "{e}"')

    async def write_transaction(self, params: dict):
        if self.debug:
            return {
                "success": False,
                "meta": {
                    "message": f'Debug On: execute "write_transaction" with params: {params}'  # noqa
                },
            }
        else:
            _headers = await self.auth()
            async with httpx.AsyncClient() as client:
                API_YCLIENTS_POST_REQUEST_CNT.inc()
                r = await client.post(
                    self.url(f"finance_transactions/{self.company_id}"),
                    headers=_headers,
                    json=params,
                    timeout=10.0,
                )
            return r.json()

    async def card_set_period(self, params: dict):
        if self.debug:
            return {"success": True}
        else:
            _headers = await self.auth()
            async with httpx.AsyncClient() as client:
                API_YCLIENTS_POST_REQUEST_CNT.inc()
                r = await client.post(
                    self.url(
                        f'chain/{self.chain_id}/loyalty/abonements/{params["card_id"]}/set_period'  # noqa
                    ),
                    headers=_headers,
                    json={
                        "period": params["period"],
                        "period_unit_id": params["period_unit_id"],
                    },
                    timeout=10.0,
                )
            return r.json()

    async def delete_activity(self, params: dict):
        if self.debug:
            return {"success": True}
        else:
            _headers = await self.auth()
            activity_id = params["activity_id"]
            async with httpx.AsyncClient() as client:
                API_YCLIENTS_DELETE_REQUEST_CNT.inc()
                r = await client.delete(
                    self.url(f"activity/{self.company_id}/{activity_id}"),
                    headers=_headers,
                    timeout=10.0,
                )
            return r.json()

    async def write_activity(self, params: dict):
        if self.debug:
            return {"success": True}
        else:
            _headers = await self.auth()
            async with httpx.AsyncClient() as client:
                API_YCLIENTS_POST_REQUEST_CNT.inc()
                r = await client.post(
                    self.url(f"activity/{self.company_id}"),
                    headers=_headers,
                    json=params,
                    timeout=10.0,
                )
            try:
                return r.json()
            except Exception as e:
                raise Exception(f"{e}, {params=}, {r.text=}")

    async def get_records_after(self, changed_after):
        rows = await self.load_object(
            obj_name="records",
            url=f"records/{self.company_id}",
            params={
                "changed_after": changed_after,
                "include_consumables": 1,
                "include_finance_transactions": 1,
                "with_deleted": 1,
            },
        )
        logger.debug(f"get_records_after {changed_after}, rows: {len(rows)}")
        return rows

    async def get_records(self, start_date, end_date, ids=None):
        """Записи за период

        :param _type_ start_date: _description_
        :param _type_ end_date: _description_
        :return _type_: _description_
        """
        rows = await self.load_object(
            obj_name="records",
            url=f"records/{self.company_id}",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "include_consumables": 1,
                "include_finance_transactions": 1,
                "with_deleted": 1,
            },
        )
        logger.debug(f"get_records {start_date}-{end_date}, rows: {len(rows)}")
        return rows

    async def get_record(self, id):
        """Запись
        :param _type_ id: _description_
        :return _type_: _description_
        """
        rows = await self.load_object(
            obj_name="records",
            url=f"record/{self.company_id}/{id}",
            params={
                "include_consumables": 1,
                "include_finance_transactions": 1,
            },
        )
        return rows

    async def get_cards(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="cards",
            url=f"chain/{self.chain_id}/loyalty/abonements",
            params={
                "created_after": start_date,
                "created_before": end_date,
            },
        )
        logger.debug(f"get_cards {start_date}-{end_date}, rows: {len(rows)}")
        return rows

    async def get_card(self, id):
        rows = await self.load_object(
            obj_name="cards",
            url=f"chain/{self.chain_id}/loyalty/abonements",
            params={
                "abonements_ids": id,
            },
        )
        return rows

    async def get_staff(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="staff",
            url=f"company/{self.company_id}/staff",
            params={},
            pagination=False,
        )
        logger.debug(f"get_staff, rows: {len(rows)}")
        return rows

    async def get_services(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="services",
            url=f"company/{self.company_id}/services",
            params={},
            pagination=False,
        )
        logger.debug(f"get_services, rows: {len(rows)}")
        return rows

    async def get_storage_transactions(self, start_date, end_date, ids=None):
        """Товарные транзакции

        :param _type_ start_date: _description_
        :param _type_ end_date: _description_
        :return _type_: _description_
        """
        rows = await self.load_object(
            obj_name="storage_transactions",
            url=f"storages/transactions/{self.company_id}",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        logger.debug(
            f"get_storage_transactions {start_date}-{end_date}, rows: {len(rows)}"  # noqa
        )
        return rows

    async def get_transactions(self, start_date, end_date, ids=None):
        """Финансовые транзакции

        :param _type_ start_date: _description_
        :param _type_ end_date: _description_
        :return _type_: _description_
        """
        rows = await self.load_object(
            obj_name="transactions",
            url=f"transactions/{self.company_id}",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        logger.debug(
            f"get_transactions {start_date}-{end_date}, rows: {len(rows)}"
        )
        return rows

    async def get_visit(self, record_id, visit_id):
        rows = await self.load_object(
            obj_name=None,
            url=f"visit/details/{self.company_id}/{record_id}/{visit_id}",
            params={},
        )
        logger.debug(f"get_visit: {visit_id}")
        return rows

    async def get_clients(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="all_clients",
            url=f"company/{self.company_id}/clients/search",
            method="post",
            params={
                "fields": [
                    "id",
                    "name",
                    "phone",
                    "email",
                    "discount",
                    "first_visit_date",
                    "last_visit_date",
                    "sold_amount",
                    "visits_count",
                    # Не возвращает :(
                    "last_change_date",
                ]
            },
        )
        logger.debug(f"get_clients, rows: {len(rows)}")
        return rows

    async def get_clients2(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="all_clients2",
            url=f"clients/{self.company_id}",
            method="get",
            params={},
        )
        logger.debug(f"get_clients2, rows: {len(rows)}")
        return rows

    async def get_detail_clients(self, start_date, end_date, ids=None):
        return await self.load_object(
            obj_name=None,
            url=f"client/{self.company_id}/{ids}",
            params={},
        )

    async def get_detail_activity(self, start_date, end_date, ids=None):
        return await self.load_object(
            obj_name=None,
            url=f"activity/{self.company_id}/{ids}",
            params={},
        )

    async def get_activity(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="activity",
            url=f"activity/{self.company_id}/search/",
            params={
                "from": start_date,
                "till": end_date,
            },
        )
        logger.debug(
            f"get_activity {start_date}-{end_date}, rows: {len(rows)}"
        )
        return rows

    async def get_schedule(self, start_date, end_date, ids=None):
        rows = await self.load_object(
            obj_name="schedule",
            url=f"company/{self.company_id}/staff/schedule",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "staff_ids": ids,
                "include": "busy_intervals",
            },
            pagination=False,
        )
        logger.debug(
            f"get_schedule {start_date}-{end_date}, rows: {len(rows)}"
        )
        return rows

    async def get_goods(self):
        rows = await self.load_object(
            obj_name="goods",
            url=f"goods/{self.company_id}",
            method="get",
            params={},
        )
        logger.debug(f"get_goods, rows: {len(rows)}")
        return rows

    async def send_message(self, message, client_ids: list):
        """Отправить сообщение средствами yclients"""
        # Установлена переменная тестовой отправки только этому клиенту
        test_client_id = 222715438 if not config.production else None
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    self.url(f"sms/clients/by_id/{self.company_id}"),
                    headers=await self.auth(),
                    json={
                        "client_ids": (
                            [test_client_id] if test_client_id else client_ids
                        ),
                        "text": (
                            f"""yclients for: {client_ids}
-----------------------
{message}"""
                            if test_client_id
                            else message
                        ),
                    },
                    timeout=10.0,
                )
                # {"success": true or false,
                # "meta": {"message": "текст ошибки"}}
                return r.json()
            except Exception as e:
                logger.error(e)
                return {"success": False, "meta": {"message": e}}

    async def close(self):
        pass

    async def get_contacts(self, start_date, end_date, ids=None):
        rows = await self.imobis_load_object(
            obj_name="contacts",
            url="contacts",
            params={},
        )
        logger.debug(f"get_contacts, rows: {len(rows)}")
        return rows
        # rows = await self.imobis_post(url="contacts")
        # return rows

    async def get_conversations(
        self,
        start_date=None,
        end_date=None,
        ids=None,
        offset: int = 0,
        limit: int = 5,
    ):
        """Получить все диалоги из fromni"""
        rows = await self.imobis_load_object(
            obj_name="conversations",
            url="conversations",
            params={"offset": offset, "limit": limit},
            # is_get_blocks=True,
        )
        logger.debug(f"get_conversations, rows: {len(rows)}")
        return rows

    async def get_conversation_messages(
        self, start_date=None, end_date=None, ids=None
    ):
        """Получить сообщения диалога"""
        rows = await self.imobis_load_object(
            obj_name="messages",
            url="conversation/messages",
            params={"conversationId": ids},
            is_get_blocks=False,
        )
        logger.debug(f"get_conversation_messages, rows: {len(rows)}")
        return rows

    async def get_fromni_channels(self):
        """Получить из fromni список каналов для отправки"""
        if not self.fromni_channels:
            connections = await self.imobis_post(url="/channels/connections")
            self.fromni_channels = []
            # Порядок отправки сообщения по каналам
            for name in ["max", "telegram", "telegram-web", "vk", "max-web"]:
                channel_connections = connections.get("data", {}).get(name, [])
                channel_ids = [conn.get("id") for conn in channel_connections]
                self.fromni_channels.append(
                    {"name": name, "connections": channel_ids}
                )
        return self.fromni_channels

    async def send_imobis_message(
        self,
        message: str,
        phone: str | None = None,
        contact_id: str | None = None,
    ) -> str:
        """Отправить сообщение напрямую через Imobis.

        :return: ID нотификации или 'Не доставлен'.
        Результат доставки —
        через webhook notification_message_updated.
        """
        if not phone and not contact_id:
            raise ValueError(
                "Не задан параметр phone или contact_id при отправке в Imobis"
            )

        body = await self._build_imobis_message_body(
            message, phone, contact_id
        )
        result = await self.imobis_post(url="/notifications/send", body=body)
        return result.get("id", "Не доставлен")

    async def _build_imobis_message_body(
        self,
        message: str,
        phone: str | None,
        contact_id: str | None,
    ) -> dict:
        """Формирует тело запроса отправки сообщения с учётом окружения."""
        if config.production:
            recipient = {
                k: v
                for k, v in {"phone": phone, "contactId": contact_id}.items()
                if v
            }
            text = message
        else:
            recipient = {"phone": "79233549672"}
            text = f"imobis for: {phone or contact_id}\n-----------------------\n{message}"  # noqa

        return {
            **recipient,
            "message": {"text": text},
            "channels": await self.get_fromni_channels(),
        }


async def sms_send_message(message: dict) -> None:
    """Отправляет SMS через YClients для одного или нескольких клиентов."""
    client_ids = message.get("client_id")
    texts = message.get("text")

    if not client_ids or not texts:
        return

    client_ids = client_ids if isinstance(client_ids, list) else [client_ids]
    texts = texts if isinstance(texts, list) else [texts]

    yclients = Yclients()
    for client_id, text in itertools.product(client_ids, texts):
        await yclients.send_message(message=text, client_ids=[client_id])
