import asyncio
import json
from datetime import datetime
from aiohttp import web
import asyncpg

# Конфигурация базы данных
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ads_db',
    'user': 'postgres',
    'password': 'postgres'
}


async def init_db(app: web.Application):
    """Инициализация базы данных при запуске приложения"""
    # Создаем пул подключений
    app['db_pool'] = await asyncpg.create_pool(**DB_CONFIG)

    # Создаем таблицу, если она не существует
    async with app['db_pool'].acquire() as conn:
        await conn.execute('''
                           CREATE TABLE IF NOT EXISTS ads
                           (
                               id
                               SERIAL
                               PRIMARY
                               KEY,
                               title
                               VARCHAR
                           (
                               255
                           ) NOT NULL,
                               description TEXT NOT NULL,
                               owner VARCHAR
                           (
                               255
                           ) NOT NULL,
                               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                               )
                           ''')

    print("База данных инициализирована")


async def close_db(app: web.Application):
    """Закрытие подключения к базе данных при остановке приложения"""
    await app['db_pool'].close()
    print("Подключение к базе данных закрыто")


async def create_ad(request: web.Request) -> web.Response:
    """
    POST /ads - создание нового объявления
    """
    try:
        data = await request.json()

        # Валидация обязательных полей
        required_fields = ['title', 'description', 'owner']
        for field in required_fields:
            if field not in data:
                return web.json_response(
                    {'error': f'Поле "{field}" обязательно'},
                    status=400
                )

            if not data[field] or not str(data[field]).strip():
                return web.json_response(
                    {'error': f'Поле "{field}" не может быть пустым'},
                    status=400
                )

        # Получаем пул подключений из приложения
        pool = request.app['db_pool']

        # Асинхронная вставка в базу данных
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                                      INSERT INTO ads (title, description, owner)
                                      VALUES ($1, $2, $3) RETURNING id, title, description, owner, created_at
                                      ''',
                                      data['title'].strip(),
                                      data['description'].strip(),
                                      data['owner'].strip()
                                      )

        # Формируем ответ
        ad_data = {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'owner': row['owner'],
            'created_at': row['created_at'].isoformat()
        }

        return web.json_response(ad_data, status=201)

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
        ad_id = int(request.match_info['id'])

        # Получаем пул подключений
        pool = request.app['db_pool']

        # Асинхронный запрос к базе данных
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                                      SELECT id, title, description, owner, created_at
                                      FROM ads
                                      WHERE id = $1
                                      ''', ad_id)

        if not row:
            return web.json_response(
                {'error': f'Объявление с ID {ad_id} не найдено'},
                status=404
            )

        ad_data = {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'owner': row['owner'],
            'created_at': row['created_at'].isoformat()
        }

        return web.json_response(ad_data)

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
    """
    try:
        ad_id = int(request.match_info['id'])
        data = await request.json()

        # Получаем пул подключений
        pool = request.app['db_pool']

        # Сначала проверяем существование объявления
        async with pool.acquire() as conn:
            existing = await conn.fetchrow('''
                                           SELECT id
                                           FROM ads
                                           WHERE id = $1
                                           ''', ad_id)

            if not existing:
                return web.json_response(
                    {'error': f'Объявление с ID {ad_id} не найдено'},
                    status=404
                )

            # Строим динамический запрос для обновления
            update_fields = []
            values = []
            param_num = 1

            if 'title' in data:
                if not data['title'] or not str(data['title']).strip():
                    return web.json_response(
                        {'error': 'Поле "title" не может быть пустым'},
                        status=400
                    )
                update_fields.append(f'title = ${param_num}')
                values.append(data['title'].strip())
                param_num += 1

            if 'description' in data:
                if not data['description'] or not str(data['description']).strip():
                    return web.json_response(
                        {'error': 'Поле "description" не может быть пустым'},
                        status=400
                    )
                update_fields.append(f'description = ${param_num}')
                values.append(data['description'].strip())
                param_num += 1

            if 'owner' in data:
                if not data['owner'] or not str(data['owner']).strip():
                    return web.json_response(
                        {'error': 'Поле "owner" не может быть пустым'},
                        status=400
                    )
                update_fields.append(f'owner = ${param_num}')
                values.append(data['owner'].strip())
                param_num += 1

            # Если нет полей для обновления, возвращаем текущее объявление
            if not update_fields:
                row = await conn.fetchrow('''
                                          SELECT id, title, description, owner, created_at
                                          FROM ads
                                          WHERE id = $1
                                          ''', ad_id)
            else:
                # Добавляем ID в конец для WHERE
                values.append(ad_id)

                # Выполняем обновление
                query = f'''
                    UPDATE ads
                    SET {', '.join(update_fields)}
                    WHERE id = ${param_num}
                    RETURNING id, title, description, owner, created_at
                '''
                row = await conn.fetchrow(query, *values)

        ad_data = {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'owner': row['owner'],
            'created_at': row['created_at'].isoformat()
        }

        return web.json_response(ad_data)

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
        ad_id = int(request.match_info['id'])

        # Получаем пул подключений
        pool = request.app['db_pool']

        # Удаляем объявление и возвращаем данные
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                                      DELETE
                                      FROM ads
                                      WHERE id = $1 RETURNING id, title, description, owner, created_at
                                      ''', ad_id)

        if not row:
            return web.json_response(
                {'error': f'Объявление с ID {ad_id} не найдено'},
                status=404
            )

        deleted_ad = {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'owner': row['owner'],
            'created_at': row['created_at'].isoformat()
        }

        return web.json_response({
            'message': f'Объявление с ID {ad_id} успешно удалено',
            'deleted_ad': deleted_ad
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
        # Получаем пул подключений
        pool = request.app['db_pool']

        # Получаем все объявления
        async with pool.acquire() as conn:
            rows = await conn.fetch('''
                                    SELECT id, title, description, owner, created_at
                                    FROM ads
                                    ORDER BY created_at DESC
                                    ''')

        ads_list = []
        for row in rows:
            ads_list.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'owner': row['owner'],
                'created_at': row['created_at'].isoformat()
            })

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

    app = web.Application()

    # Добавляем хуки для инициализации и закрытия БД
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)

    # Добавляем маршруты
    app.router.add_get('/ads', list_ads)
    app.router.add_post('/ads', create_ad)
    app.router.add_get('/ads/{id}', get_ad)
    app.router.add_put('/ads/{id}', update_ad)
    app.router.add_delete('/ads/{id}', delete_ad)

    return app


if __name__ == '__main__':
    app = create_app()
    print("Запуск сервера на http://localhost:8080")
    web.run_app(app, host='localhost', port=8080)
