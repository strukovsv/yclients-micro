import logging
import httpx
import asyncio
import datetime
import os

from micro.singleton import MetaSingleton
import micro.utils

import micro.config as config

from .metrics import (
    API_YCLIENTS_POST_REQUEST_CNT,
    API_YCLIENTS_GET_REQUEST_CNT,
    API_YCLIENTS_DELETE_REQUEST_CNT,
    API_YCLIENTS_REQUEST_ERROR_CNT,
)

logger = logging.getLogger(__name__)


class Yclients(metaclass=MetaSingleton):

    partner_token: str = None
    headers_partner: str = None
    headers_user: str = None
    # Включен режим отладки
    debug: bool = None
    # Каналы отправки закэшировать
    fromni_channels: list = None

    def __init__(self, is_create_yaml: bool = None):
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

    async def auth(self):
        if self.headers_user is None:
            logger.debug("auth !!!")
            # Получить токен партнера из настроек
            self.partner_token = config.PARTNER_TOKEN
            async with httpx.AsyncClient() as client:
                # Сформировать заголовок для авторизации по партнеру
                self.headers_partner = {
                    "Authorization": f"Bearer {self.partner_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.yclients.v2+json",
                }
                logger.info(f"{self.headers_partner=}")
                # Авторизоваться в системе
                try:
                    API_YCLIENTS_POST_REQUEST_CNT.inc()
                    r = await client.post(
                        self.url("auth"),
                        headers=self.headers_partner,
                        json={
                            "login": config.YCLIENT_LOGIN,
                            "password": config.YCLIENT_PASSWORD,
                        },
                        timeout=10.0,
                    )
                    # logger.info(f'auth: {r.content}')
                except Exception as e:
                    API_YCLIENTS_REQUEST_ERROR_CNT.inc()
                    # Получить user token
                    logger.error(f"{e=}")
                    logger.error(f'{self.url("auth")=}')
                    logger.error(f"{self.headers_partner=}")
                    logger.error(r.text)
                    raise
                try:
                    auth = r.json()
                except Exception as e:
                    API_YCLIENTS_REQUEST_ERROR_CNT.inc()
                    # Получить user token
                    logger.error(r.text)
                    logger.error(e)
                    raise
                self.user_token = auth["data"]["user_token"]
                logger.debug(f"{self.user_token=}")
                # Сформировать заголовок для авторизации по пользователю
                self.headers_user = {
                    "Authorization": f"Bearer {self.partner_token}, User {self.user_token}",  # noqa
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.yclients.v2+json",
                }
        return self.headers_user

    async def load_object(
        self,
        obj_name: str,
        url: str,
        params: dict,
        headers: str = None,
        method: str = "get",
        pagination: bool = True,
    ) -> list:
        """Запросить объект из api

        :param str obj_name: наименование объекта, yaml файла и базовой таблицы
        :param str url: ручка api
        :param dict params: параметры
        :param str headers: заголовок, по умолчанию заголовок пользователя
        :param str method: http метод. По умолчанию get
        :return list: возвращает список объектов
        """
        # По умолчанию заголовок пользователья
        _headers = headers
        if _headers is None:
            _headers = await self.auth()
        async with httpx.AsyncClient() as client:
            page = 0
            page_count = config.PAGE_COUNT
            records = []
            while 1:
                page += 1
                params["page"] = page
                params["count"] = page_count
                # Зафиксировать время запроса
                start = datetime.datetime.now()
                # logger.info(f"{self.url(url)=} {params=}")
                # Запросить в API
                for i in range(0, 4):
                    try:
                        __url__ = self.url(url)
                        if method == "get":
                            API_YCLIENTS_GET_REQUEST_CNT.inc()
                            r = await client.get(
                                __url__,
                                headers=_headers,
                                params=params,
                                timeout=10.0,
                            )
                        else:
                            API_YCLIENTS_POST_REQUEST_CNT.inc()
                            r = await client.post(
                                __url__,
                                headers=_headers,
                                json=params,
                                timeout=10.0,
                            )
                        # logger.info(f'{r.content=}')
                        js = r.json()
                        if not js["success"]:
                            raise Exception(js["meta"]["message"])
                        rows = js["data"]
                        break
                    except Exception as e:
                        # Получить user token
                        if i < 3:
                            logger.debug(
                                f'attempt: "{i}", error: "{e}", url: "{__url__}"'  # noqa
                            )
                            # await asyncio.sleep(10)
                            await asyncio.sleep(10)
                            continue
                        try:
                            response = r.text
                        except Exception:
                            response = None
                        API_YCLIENTS_REQUEST_ERROR_CNT.inc()
                        if f"{e}" == "Не найдено":
                            logger.error(
                                f'httpx url: "{method} + {__url__}", response: "{response}", message: "Не найдено записей, вернуть []", params: "{params}"'  # noqa
                            )  # noqa
                            rows = []
                        else:
                            raise Exception(
                                f'httpx url: "{method} + {__url__}", response: "{response}", message: "{e}", params: "{params}"'  # noqa
                            )
                # Поспать немного.
                # Один запрос, не менее 1 сек
                # Осталось до одной секуды
                remain = (
                    1.0 - (datetime.datetime.now() - start).total_seconds()
                )
                if remain > 0:
                    logger.debug(f"sleep remain: {remain}")
                    # В linux периоды можно задать меньше одной секунды
                    await asyncio.sleep(remain)
                if rows:
                    if isinstance(rows, list):
                        records.extend(rows)
                        # Если строк вернули, меньше чем запросили,
                        # то завершить чтение
                        if not pagination:
                            break
                        if len(rows) < page_count:
                            break
                    else:
                        records.append(rows)
                        break
                else:
                    break
            return records

    async def imobis_load_object(
        self,
        obj_name: str,
        url: str,
        params: dict,
        headers: str = None,
        method: str = "get",
        pagination: bool = True,
        is_get_blocks: bool = True,
    ) -> list:
        """Запросить объект из api

        :param str obj_name: наименование объекта, yaml файла и базовой таблицы
        :param str url: ручка api
        :param dict params: параметры
        :param str headers: заголовок, по умолчанию заголовок пользователя
        :param str method: http метод. По умолчанию get
        :return list: возвращает список объектов
        """
        # По умолчанию заголовок пользователья
        PAGE_COUNT = 10
        headers_imobis = {
            "Authorization": f"Token {config.IMOBIS_TOKEN}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            page = 0
            records = []
            while 1:
                if is_get_blocks:
                    params["offset"] = page * PAGE_COUNT
                    params["limit"] = PAGE_COUNT
                    page += 1
                # Зафиксировать время запроса
                start = datetime.datetime.now()
                # logger.info(f"{self.url(url)=} {params=}")
                # Запросить в API
                for i in range(0, 4):
                    try:
                        __url__ = self.url(url)
                        API_YCLIENTS_POST_REQUEST_CNT.inc()
                        logger.info(f"{__url__=} {params=}")
                        try:
                            r = await client.post(
                                self.imobis_url(url),
                                headers=headers_imobis,
                                json=params,
                                timeout=60.0,
                            )
                        except httpx.ConnectTimeout:
                            logger.error("Таймаут подключения к fromni API")
                            raise
                        except httpx.ReadTimeout:
                            logger.error(
                                "Таймаут ожидания ответа от fromni API"
                            )
                            raise
                        except httpx.NetworkError as e:
                            # Включает: ConnectError, ReadError, WriteError и др.
                            logger.error(
                                f"Сетевая ошибка при обращении к fromni: {e}"
                            )
                            raise
                        except httpx.HTTPStatusError as e:
                            # Сервер вернул 4xx или 5xx
                            logger.error(
                                f"HTTP ошибка от fromni: {e.response.status_code} - {e}"  # noqa
                            )
                            raise
                        except ValueError as e:
                            # Например, ответ не в JSON
                            logger.error(f"Ответ не в формате JSON: {e}")
                            raise
                        except Exception:
                            # Любая другая непредвиденная ошибка
                            logger.error(
                                "Неожиданная ошибка при отправке в fromni"
                            )
                            raise
                        js = r.json()
                        if js["result"] == "success":
                            rows = js["data"]
                            break
                        raise
                    except Exception as e:
                        # Получить user token
                        if i < 3:
                            logger.info(
                                f'attempt: "{i}", error: "{e}", url: "{__url__}"'  # noqa
                            )
                            # await asyncio.sleep(10)
                            await asyncio.sleep(10)
                            continue
                        try:
                            response = r.text
                        except Exception:
                            response = None
                        API_YCLIENTS_REQUEST_ERROR_CNT.inc()
                        if f"{e}" == "Не найдено":
                            logger.error(
                                f'httpx url: "{method} + {__url__}", response: "{response}", message: "Не найдено записей, вернуть []", params: "{params}"'  # noqa
                            )  # noqa
                            rows = []
                        else:
                            raise Exception(
                                f'httpx url: "{method} + {__url__}", response: "{response}", message: "{e}", params: "{params}"'  # noqa
                            )
                # Поспать немного.
                # Один запрос, не менее 1 сек
                # Осталось до одной секуды
                remain = (
                    1.0 - (datetime.datetime.now() - start).total_seconds()
                )
                if remain > 0:
                    logger.debug(f"sleep remain: {remain}")
                    # В linux периоды можно задать меньше одной секунды
                    await asyncio.sleep(remain)
                if rows:
                    if isinstance(rows, list):
                        records.extend(rows)
                        # Если строк вернули, меньше чем запросили,
                        # то завершить чтение
                        if not pagination:
                            break
                        if is_get_blocks and len(rows) < PAGE_COUNT:
                            break
                        if not is_get_blocks:
                            break
                    else:
                        records.append(rows)
                        break
                else:
                    break
            return records

    async def write_transaction(self, params: dict):
        if self.debug:
            logger.info(f'debug "write_transaction" with params: {params}')
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
            logger.info(f'debug "card_set_period" with params: {params}')
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
            logger.info(f'debug "delete_activity" with params: {params}')
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
            logger.info(f'debug "write_activity" with params: {params}')
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
            method="post",
            params={},
        )
        logger.debug(f"get_contacts, rows: {len(rows)}")
        return rows
        # rows = await self.imobis_post(url="contacts")
        # return rows

    async def get_conversations(
        self, start_date=None, end_date=None, ids=None
    ):
        """Получить все диалоги из fromni"""
        rows = await self.imobis_load_object(
            obj_name="conversations",
            url="conversations",
            method="post",
            params={"offset": 0, "limit": 5},
            is_get_blocks=False,
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
            method="post",
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
            for name in ["telegram", "telegram-web", "whatsapp"]:
                channel_connections = connections.get("data", {}).get(name, [])
                channel_ids = [conn.get("id") for conn in channel_connections]
                self.fromni_channels.append(
                    {"name": name, "connections": channel_ids}
                )
        return self.fromni_channels

    async def send_imobis_message(
        self, message: str, phone: str = None, contact_id: str = None
    ):
        """Отправить сообщение напрямую через fromni
        Возвращает идентификатор сообщения ID нотификации: str
        Результат доставки через webhook - notification_message_updated"""
        body = {}
        if not phone and not contact_id:
            raise Exception(
                "Не задан параметр phone или contactId при отправке в Fromni"
            )
        else:
            if config.production:
                if phone:
                    body["phone"] = phone
                if contact_id:
                    body["contactId"] = contact_id
                text = message
            else:
                body["phone"] = "79233549672"
                text = f"""fromni for: {phone}
-----------------------
{message}"""
            body["message"] = {"text": text}
            body["channels"] = await self.get_fromni_channels()
            result = await self.imobis_post(
                url="/notifications/send",
                body=body,
            )
            return result["id"]


async def sms_send_message(message):
    """Отправить sms сообщение через yclients"""
    # Получить идентификатор клиента из сообщения
    client_ids = message.get("client_id", None)
    # Получить текст сообщения
    texts = message.get("text", None)
    # если отчет напрвляется клиенту через sms yclients
    if client_ids and texts:
        # Если несколько текстов отправить отдельными сообщениями
        for text in texts if isinstance(texts, list) else [texts]:
            # Если несколько клиентов
            for client_id in (
                client_ids if isinstance(client_ids, list) else [client_ids]
            ):
                # Отправить sms сообщение yclients
                await Yclients().send_message(
                    message=text, client_ids=[client_id]
                )
