# Batch-контракт calibrated diffusion-gate

Дата: 2026-07-17.

## Изменение

Компактный inference summary v1 расширен аддитивными полями:

```text
diffusion_gate_evaluated
diffusion_gate_passed
diffusion_gate_positive_only
diffusion_family_delta_bic
diffusion_family_stability_threshold
diffusion_family_delta_bic_threshold
```

Поля включены одновременно в JSONL и CSV `SUMMARY_FIELDS`. Они nullable:
старые решения, ранние отказы и потребители прежнего контракта продолжают
работать. Обязательные поля schema v1 не менялись.

## Реальный smoke

Batch reliable inference выполнен для Li-polymer charge SOC50 (`0012`) и
discharge SOC50 (`0034`) с 20 bootstrap-повторами.

| Ветка | gate evaluated | gate passed | positive only | ΔBIC | topology |
|---|---:|---:|---:|---:|---|
| charge | true | true | true | 464,53 | null |
| discharge | true | true | true | 471,93 | null |

В обеих строках сохранены прежние поля `best_statistical`,
`recommended_family`, `family_status`, `data_validity` и остальные поля
summary v1.

## Совместимость

- schema остаётся `inference-summary-v1`;
- новые поля не входят в `required`;
- при отсутствии вложенного `decision.diffusion_gate` они равны `null`;
- `additionalProperties: true` сохранено;
- потоковая обработка после ошибочного файла не изменилась.

Машинный результат:

```text
validation_data/artifacts/lipo_diffusion_gate_reliable/batch_soc50_summary.jsonl
```
