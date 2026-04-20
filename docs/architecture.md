# Архитектура проекта

Этот документ коротко объясняет, как устроен проект `image_illumination_corrector`.

## Что делает программа

Утилита помогает:

- уменьшать виньетку по краям изображения;
- выравнивать яркость и фон по всему кадру;
- быстро подбирать параметры через GUI;
- сохранять и загружать пресеты;
- обрабатывать сразу папку изображений.

## Структура проекта

### Корень проекта

- [README.md](../README.md)
  Главная страница проекта: краткое описание, установка, запуск и ссылки на документы.

- [run.py](../run.py)
  Быстрый локальный запуск приложения из корня проекта без обращения к файлам внутри `src/`.

- [tests/](../tests/)
  Базовый каталог для тестов: benchmark, e2e, examples, integration, tools и unit.

- [pyproject.toml](../pyproject.toml)
  Главный файл Python-проекта. Здесь лежат зависимости, версия Python и точка входа.

- [poetry.lock](../poetry.lock)
  Зафиксированные версии библиотек для Poetry.

- [LICENSE](../LICENSE)
  Лицензия проекта.

### Папка `docs/`

- [methods-guide.md](./methods-guide.md)
  Подробный справочник по методам коррекции и параметрам.

- [ubuntu-run.md](./ubuntu-run.md)
  Как запускать готовую Ubuntu-сборку.

- [architecture.md](./architecture.md)
  Этот файл.

### Папка `src/image_illumination_corrector/`

- [__main__.py](../src/image_illumination_corrector/__main__.py)
  Единая внутренняя точка входа для запуска через `python -m image_illumination_corrector`, `run.py` и console script.

- [ui.py](../src/image_illumination_corrector/ui.py)
  Весь интерфейс на `tkinter`: окна, кнопки, ползунки, списки методов и работа с событиями.

- [processing_core.py](../src/image_illumination_corrector/processing_core.py)
  Основная логика обработки изображения и все методы нормализации.

- [processing.py](../src/image_illumination_corrector/processing.py)
  Вспомогательный слой совместимости. Если позже он станет не нужен, его можно упростить или убрать.

- [models.py](../src/image_illumination_corrector/models.py)
  Описание структур данных и настроек.

- [batch.py](../src/image_illumination_corrector/batch.py)
  Пакетная обработка папки с изображениями.

- [presets.py](../src/image_illumination_corrector/presets.py)
  Сохранение и загрузка пресетов в JSON.

### Остальные папки

- `presets/` - пользовательские пресеты.
- `images/` - пустой каталог под локальные примеры и ручные проверки, удерживается в git через `.gitkeep`.
- `tests/` - каркас для benchmark, e2e, examples, integration, tools и unit тестов.
- `.github/workflows/` - автоматическая сборка через GitHub Actions.

## Как идёт работа программы

1. Пользователь открывает изображение в интерфейсе.
2. `ui.py` собирает выбранный метод и значения всех параметров.
3. `processing_core.py` считает карту фона или освещённости.
4. На основе этой карты строится коррекция яркости.
5. UI показывает исходник, промежуточный фон и итоговый результат.
6. При желании можно сохранить картинку, пресет или обработать целую папку.

## Где что менять

- Алгоритмы и методы коррекции: [processing_core.py](../src/image_illumination_corrector/processing_core.py)
- Интерфейс и отображение параметров: [ui.py](../src/image_illumination_corrector/ui.py)
- Формат и хранение пресетов: [presets.py](../src/image_illumination_corrector/presets.py)
- Пакетная обработка: [batch.py](../src/image_illumination_corrector/batch.py)
- Зависимости и запуск: [pyproject.toml](../pyproject.toml)
- GitHub Actions сборка: [build.yml](../.github/workflows/build.yml)

## Что ещё можно улучшить потом

- добавить отдельные инструкции для Windows и macOS;
- вынести публикацию бинарников в GitHub Releases;
- при желании разделить `ui.py` на несколько файлов, если интерфейс станет ещё больше.
