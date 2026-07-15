---
tags:
  - decisions
  - architecture
  - history
status: active
---

# Decision Log

Эта заметка нужна, чтобы через полгода не спрашивать: “почему мы сделали именно так?”

## PySide6 Вместо tkinter

Причина:

- нужен нормальный desktop GUI;
- нужна масштабируемость;
- проще делать меню, таблицы, вкладки, worker threads, localization.

Решение:

- `eis_qt.py` — active GUI target;
- tkinter/customtkinter не возвращать.

## Core Отдельно От GUI

Причина:

- научная логика должна тестироваться отдельно;
- GUI не должен владеть fit model;
- будущий Chem Suite сможет переиспользовать core.

Решение:

- fit logic в `eis_core.py`;
- parser logic в `eis_io.py`;
- GUI вызывает их как service layer.

## galvani Для BioLogic

Причина:

- не писать бинарный `.mpr` parser руками;
- использовать существующую библиотеку electrochem-data ecosystem.

Tradeoff:

- GPL-3.0-or-later;
- `.mpr` EIS всё равно надо валидировать на реальном lab file.

## BIC Вместо Raw Fit Error

Причина:

- raw fit error любит overfit;
- сложные модели почти всегда могут улучшить residual;
- нужен penalty за число параметров.

Решение:

- best model = lowest BIC among non-BAD candidates.

## Pro Mode Скрыт

Причина:

- обычному пользователю не нужны bounds и manual circuit;
- advanced controls пугают и создают ошибочные решения.

Решение:

- default workflow: open -> auto-fit -> inspect -> export;
- Pro mode: presets/manual/bounds/local presets.

## Экспорт Не Локализуется

Причина:

- CSV/XLSX должны быть стабильными для скриптов и шаблонов;
- язык интерфейса не должен ломать data contract.

Решение:

- UI переводится;
- export columns/sheet names/circuit strings остаются стабильными.

## Local Presets Не В Репе

Причина:

- bounds и схемы могут быть личными lab habits;
- нельзя случайно коммитить user config.

Решение:

- `%APPDATA%\EIS Solver\pro_presets.json`;
- fallback `.eis_solver_user/pro_presets.json`;
- fallback folder в `.gitignore`.

