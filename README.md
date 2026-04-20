# image_illumination_corrector

Утилита для коррекции виньетки и выравнивания яркости по всему изображению с живым предпросмотром, пресетами и пакетной обработкой.

GitHub:

- [omigutin/image_illumination_corrector](https://github.com/omigutin/image_illumination_corrector)

## Что умеет

- оценивать плавную неравномерность яркости по кадру;
- исправлять виньетку разными методами;
- настраивать параметры в GUI с предпросмотром;
- сохранять и загружать пресеты;
- обрабатывать целую папку изображений;
- использовать опорный кадр и радиальную модель виньетки.

## Документация

- [Архитектура](docs/architecture.md)
- [Справочник по методам](docs/methods-guide.md)
- [Запуск на Ubuntu](docs/ubuntu-run.md)

## Установка через Poetry

```bash
poetry env use 3.12
poetry install
```

## Быстрый запуск

После установки зависимостей основной локальный запуск идёт через корневой файл:

```bash
python run.py
```

## Запуск через Poetry

```bash
poetry run python run.py
```

## Запуск без Poetry

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python run.py
```

## Структура проекта

- `run.py` - быстрый запуск приложения из корня проекта
- `src/image_illumination_corrector/` - исходный код приложения
- `tests/` - базовая структура для benchmark, e2e, examples, integration, tools и unit
- `docs/` - документация
- `images/` - каталог для локальных примеров, в git хранится пустым через `.gitkeep`
- `presets/` - пресеты пользователя

## Альтернативные способы запуска

После `pip install -e .` также работают:

```bash
python -m image_illumination_corrector
image-illumination-corrector
```

## Сборки

Готовые исполняемые файлы лучше публиковать через GitHub Releases или получать как артефакты GitHub Actions, а не хранить внутри репозитория.
