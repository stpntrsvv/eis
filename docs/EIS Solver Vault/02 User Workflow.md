# Рабочие сценарии

Здесь описаны два основных способа работы: быстрый автоматический анализ и управляемый подбор модели в расширенном режиме.

## Быстрый сценарий

Этот сценарий подходит для быстрой и воспроизводимой первичной оценки спектра.

```mermaid
flowchart TD
    A[Open files / Open folder / Drag and drop] --> B[Check Datasets table]
    B --> C[Choose channel if parser found multiple]
    C --> D[Run auto-fit]
    D --> E[Inspect best circuit and status]
    E --> F[Check Nyquist / Bode / Residuals]
    F --> G[Export CSV/XLSX/report/plots]
```

## Расширенный сценарий

Этот сценарий нужен, если стандартный набор моделей слишком широк или физическая схема системы уже известна.

```mermaid
flowchart TD
    A[Enable Pro mode] --> B{Use presets or manual circuit?}
    B -->|Presets| C[Choose Interface and Transport families]
    C --> D[Run selected presets]
    B -->|Manual| E[Enter circuit string]
    E --> F[Fill guesses]
    F --> G[Edit Initial / Lower / Upper]
    G --> H[Run manual]
    H --> I[Save preset if useful]
    D --> J[Inspect diagnostics]
    I --> J
    J --> K[Export]
```

## Что проверить после фитинга

1. Какая схема рекомендована.
2. Какова средняя ошибка фитинга.
3. Как соотносятся BIC и AIC у конкурирующих моделей.
4. Какое состояние присвоено результату: `OK`, `WARN` или `BAD`.
5. Какие диагностические флаги выставлены.
6. Есть ли структура на графике остатков.
7. Правдоподобны ли параметры с точки зрения физики системы.

## Обычный набор для экспорта

Для обычной лабораторной таблицы:

- `_summary.csv`
- `_workbook.xlsx`

Для воспроизводимости и разбора результата:

- `_all_results.csv`
- `_best_parameters.csv`
- `_parser_metadata.csv`

Для отдельного отчёта по выбранному образцу:

- `_report.txt`
- `_nyquist.png`
- `_bode.png`
- `_residuals.png`

## Переключение языка

По умолчанию интерфейс открывается на английском. Русский язык включается через меню:

`View -> Language -> Русский`

Имена колонок в экспорте и строки эквивалентных схем намеренно не переводятся: это стабильный машинно-читаемый контракт.
