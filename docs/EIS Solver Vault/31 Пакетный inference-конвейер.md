---
tags:
  - architecture
  - cli
  - batch
status: active
---

# Пакетный inference-конвейер

`eis_inference_batch.py` превращает единый inference engine в инструмент массовой проверки. Каждый файл независимо попадает в один из четырёх классов:

```text
recommended
models_indistinguishable
insufficient_information
analysis_failed
```

Результат записывается сразу после файла. Ошибка парсинга или fit не уничтожает уже выполненную работу и по умолчанию не останавливает пакет.

## Быстрый и надёжный проход

Fast-проход предназначен для screening сотен спектров. По умолчанию он
использует ту же двухступенчатую маршрутизацию `adaptive_v2`, что и основной
CLI. Он сохраняет `best_statistical` и BIC-окно поддержанных топологий, но без
bootstrap возвращает `insufficient_information` и предлагает запустить
reliable-режим. Это не ошибка: программа явно различает «не проверено» и
«проверено, но неразличимо».

Reliable-проход дороже и добавляет topology/family bootstrap и DRT stability.
Точная схема и семейство имеют независимые поля рекомендации. Практический
массовый workflow:

```text
весь корпус → fast JSONL
            → стратификация по данным/статусам/схемам
            → reliable на выборке и проблемных спектрах
            → калибровка порогов
```

## Замороженная сводка v1

JSON Schema находится в `schemas/inference-summary-v1.schema.json`. Основные поля:

```text
file, verdict, best_statistical, recommended_reliable,
recommended_family, recommended_topology, family_status, topology_status,
data_validity, fit_status, information_gap,
stable_time_regions, unstable_time_regions, next_action
```

После production-калибровки diffusion-family compact summary v1 также
содержит nullable-поля:

```text
diffusion_gate_evaluated
diffusion_gate_passed
diffusion_gate_positive_only
diffusion_family_delta_bic
diffusion_family_stability_threshold
diffusion_family_delta_bic_threshold
```

Версия schema не менялась: поля добавлены необязательно, старые решения
сериализуются с `null`. Реальный batch-smoke на charge/discharge SOC50
подтвердил `passed=true`, `positive_only=true`, `recommended_topology=null`.
[Отчёт](../../../validation_data/reports/2026-07-17-batch-diffusion-gate-contract.md).

Полный технический отчёт: [batch inference pipeline](../../../validation_data/reports/2026-07-17-batch-inference-pipeline.md).

Связанные главы: [[30 Единый inference engine]], [[25 Пакетный конвейер и CLI]], [[29 Где именно не хватает данных]].
