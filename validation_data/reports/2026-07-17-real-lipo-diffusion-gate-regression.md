# Сквозная regression diffusion-gate на реальном Li-polymer корпусе

Дата: 2026-07-17.

## Цель

Проверить новый положительный production-gate сначала на charge/discharge
SOC50, затем на всех 42 сырых спектрах Li-polymer. Пороги не менялись:

```text
family bootstrap >= 90%
family ΔBIC >= 10
positive-only inductive_diffusion recommendation
```

Bootstrap полной серии не пересчитывался: использованы ранее замороженные
20-repeat отчёты с конкуренцией base против `W/Wo/Ws`. Fit и BIC-свидетельство
пересчитаны текущим кодом, затем каждый результат пропущен через новый
`build_inference_decision`.

## SOC50 smoke

| Ветка | Файл | best_statistical | Bootstrap | ΔBIC | Рекомендация |
|---|---|---|---:|---:|---|
| charge | `0012` | `W` | 20/20 | 464,53 | `inductive_diffusion` |
| discharge | `0034` | `Wo` | 20/20 | 471,93 | `inductive_diffusion` |

В обоих случаях `recommended_topology: null`, старые `best` и новые
`best_statistical` присутствуют одновременно.

## Полный корпус

| Ветка | Спектры | Family recommendation | Отказ по KK |
|---|---:|---:|---:|
| charge | 21 | 19 | 2 |
| discharge | 21 | 19 | 2 |
| всего | 42 | 38 | 4 |

Отказы относятся к `0002`, `0003`, `0024` и `0025`. Их bootstrap поддерживал
diffusion-family, но Lin-KK имел статус `FAIL`, поэтому data-validity gate
корректно запретил рекомендацию.

Итог:

- `recommended_family: inductive_diffusion` — `38/42`;
- точных топологических рекомендаций — `0/42`;
- `best` и `best_statistical` сохранены — `42/42`;
- статистические победители: `Wo 26`, `W 10`, `Ws 6`;
- BIC-окно содержит одну топологию в 36 случаях и две в 6;
- `ΔBIC`: минимум `414,58`, среднее `481,45`, максимум `540,50`.

`42/42` bootstrap-поддержки семейства не превращаются в `42/42`
production-рекомендаций: качество данных остаётся независимым обязательным
воротом.

Машинные результаты:

```text
validation_data/artifacts/lipo_diffusion_gate_reliable/charge_soc50.json
validation_data/artifacts/lipo_diffusion_gate_reliable/discharge_soc50.json
validation_data/artifacts/lipo_diffusion_gate_reliable/full_42.jsonl
validation_data/artifacts/lipo_diffusion_gate_reliable/full_42_summary.json
```
