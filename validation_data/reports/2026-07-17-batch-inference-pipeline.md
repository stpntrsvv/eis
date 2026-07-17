# Batch inference pipeline

Дата: 2026-07-17.

Добавлен `eis_inference_batch.py` — потоковый пакетный запуск единого inference-контракта.

Поддерживаются:

- несколько файлов и каталогов;
- рекурсивный поиск EIS-форматов;
- режимы `fast` и `reliable`;
- компактный JSONL, полный JSONL и плоский CSV;
- немедленная запись и `flush` после каждого файла;
- продолжение после ошибки;
- опциональный `fail-fast`;
- детерминированные seed для каждого файла;
- сводный счётчик вердиктов.

Компактная схема зафиксирована в `schemas/inference-summary-v1.schema.json`.

## Smoke test

На `sample_data/` обнаружены два файла:

- `bio_logic1.mpr` → `analysis_failed`: файл не содержит распознаваемого EIS-канала с частотой, `Re(Z)` и `Im(Z)`; пакет продолжил работу;
- `EIS_latin1.mpt` → `insufficient_information`: статистический победитель найден, но fast-режим не запускал bootstrap и поэтому предлагает `run reliable mode`.

Это важное разделение: отсутствие надёжной проверки не называется неразличимостью моделей. `models_indistinguishable` может появиться только после реально выполненного reliable-анализа.

## Команда

```powershell
.\.venv\Scripts\python.exe eis_inference_batch.py sample_data `
  --recursive --mode fast --format jsonl --detail decision `
  --output validation_data\artifacts\batch_inference_smoke\results.jsonl
```

Следующий рабочий прогон — fast-screening всего открытого корпуса. Затем reliable-режим применяется к стратифицированной выборке и проблемным классам, поскольку полный bootstrap каждого из сотен спектров существенно дороже.
