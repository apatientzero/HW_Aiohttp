import asyncio
import json
from datetime import datetime
from aiohttp import web

# Хранилище объявлений в памяти
ads_storage = {}
ad_counter = 0


class Ad:
    """Класс объявления"""

    def __init__(self, title: str, description: str, owner: str):
        self.id = None
        self.title = title
        self.description = description
        self.owner = owner
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Преобразует объект в словарь для JSON-ответа"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'owner': self.owner,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Ad':
        """Создает объект из словаря"""
        ad = cls(
            title=data['title'],
            description=data['description'],
            owner=data['owner']
        )
        if 'id' in data:
            ad.id = data['id']
        if 'created_at' in data:
            ad.created_at = data['created_at']
        return ad


async def create_ad(request: web.Request) -> web.Response:
    """
    POST /ads - создание нового объявления

    Ожидаемый JSON:
    {
        "title": "Продам велосипед",
        "description": "Отличное состояние",
        "owner": "Mike Tyson"
    }
    """
    try:
        # Получаем данные из тела запроса
        data = await request.json()

        # Валидация обязательных полей
        required_fields = ['title', 'description', 'owner']
        for field in required_fields:
            if field not in data:
                return web.json_response(
                    {'error': f'Поле "{field}" обязательно'},
                    status=400
                )

            # Проверка на пустые значения
            if not data[field] or not str(data[field]).strip():
                return web.json_response(
                    {'error': f'Поле "{field}" не может быть пустым'},
                    status=400
                )

        # Создаем новое объявление
        global ad_counter
        ad_counter += 1

        ad = Ad(
            title=data['title'].strip(),
            description=data['description'].strip(),
            owner=data['owner'].strip()
        )
        ad.id = ad_counter

        # Сохраняем в хранилище
        ads_storage[ad.id] = ad

        # Возвращаем созданное объявление с кодом 201 (Created)
        return web.json_response(
            ad.to_dict(),
            status=201
        )

    except json.JSONDecodeError:
        return web.json_response(
            {'error': 'Неверный формат JSON'},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {'error': f'Ошибка при создании объявления: {str(e)}'},
            status=500
        )


async def get_ad(request: web.Request) -> web.Response:
    """
    GET /ads/{id} - получение объявления по ID
    """
    try:
        # Получаем ID из URL
        ad_id = int(request.match_info['id'])

        # Ищем объявление
        ad = ads_storage.get(ad_id)

        if not ad:
            return web.json_response(
                {'error': f'Объявление с ID {ad_id} не найдено'},
                status=404
            )

        # Возвращаем объявление
        return web.json_response(ad.to_dict())

    except ValueError:
        return web.json_response(
            {'error': 'ID должен быть числом'},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {'error': f'Ошибка при получении объявления: {str(e)}'},
            status=500
        )


async def update_ad(request: web.Request) -> web.Response:
    """
    PUT /ads/{id} - обновление объявления

    Ожидаемый JSON (все поля опциональны):
    {
        "title": "Новый заголовок",
        "description": "Новое описание",
        "owner": "Новый владелец"
    }
    """
    try:
        # Получаем ID из URL
        ad_id = int(request.match_info['id'])

        # Ищем объявление
        ad = ads_storage.get(ad_id)

        if not ad:
            return web.json_response(
                {'error': f'Объявление с ID {ad_id} не найдено'},
                status=404
            )

        # Получаем данные для обновления
        data = await request.json()

        # Обновляем только переданные поля
        if 'title' in data:
            if not data['title'] or not str(data['title']).strip():
                return web.json_response(
                    {'error': 'Поле "title" не может быть пустым'},
                    status=400
                )
            ad.title = data['title'].strip()

        if 'description' in data:
            if not data['description'] or not str(data['description']).strip():
                return web.json_response(
                    {'error': 'Поле "description" не может быть пустым'},
                    status=400
                )
            ad.description = data['description'].strip()

        if 'owner' in data:
            if not data['owner'] or not str(data['owner']).strip():
                return web.json_response(
                    {'error': 'Поле "owner" не может быть пустым'},
                    status=400
                )
            ad.owner = data['owner'].strip()

        # Возвращаем обновленное объявление
        return web.json_response(ad.to_dict())

    except ValueError:
        return web.json_response(
            {'error': 'ID должен быть числом'},
            status=400
        )
    except json.JSONDecodeError:
        return web.json_response(
            {'error': 'Неверный формат JSON'},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {'error': f'Ошибка при обновлении объявления: {str(e)}'},
            status=500
        )


async def delete_ad(request: web.Request) -> web.Response:
    """
    DELETE /ads/{id} - удаление объявления
    """
    try:
        # Получаем ID из URL
        ad_id = int(request.match_info['id'])

        # Проверяем существование
        if ad_id not in ads_storage:
            return web.json_response(
                {'error': f'Объявление с ID {ad_id} не найдено'},
                status=404
            )

        # Удаляем объявление
        deleted_ad = ads_storage.pop(ad_id)

        # Возвращаем подтверждение удаления
        return web.json_response({
            'message': f'Объявление с ID {ad_id} успешно удалено',
            'deleted_ad': deleted_ad.to_dict()
        })

    except ValueError:
        return web.json_response(
            {'error': 'ID должен быть числом'},
            status=400
        )
    except Exception as e:
        return web.json_response(
            {'error': f'Ошибка при удалении объявления: {str(e)}'},
            status=500
        )


async def list_ads(request: web.Request) -> web.Response:
    """
    GET /ads - получение списка всех объявлений
    """
    try:
        # Преобразуем все объявления в список словарей
        ads_list = [ad.to_dict() for ad in ads_storage.values()]

        return web.json_response({
            'count': len(ads_list),
            'ads': ads_list
        })

    except Exception as e:
        return web.json_response(
            {'error': f'Ошибка при получении списка объявлений: {str(e)}'},
            status=500
        )


def create_app() -> web.Application:
    """Создает и настраивает приложение aiohttp"""

    # Создаем приложение
    app = web.Application()

    # Добавляем маршруты (routes)
    # Список всех объявлений
    app.router.add_get('/ads', list_ads)

    # Создание объявления
    app.router.add_post('/ads', create_ad)

    # Получение, обновление и удаление конкретного объявления
    app.router.add_get('/ads/{id}', get_ad)
    app.router.add_put('/ads/{id}', update_ad)
    app.router.add_delete('/ads/{id}', delete_ad)

    return app


if __name__ == '__main__':
    # Создаем приложение
    app = create_app()

    # Запускаем сервер
    print("Запуск сервера на http://localhost:8080")
    web.run_app(app, host='localhost', port=8080)