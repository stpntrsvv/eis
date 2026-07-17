# Единый inference-вердикт: LG MJ1 SOC 50%

Дата: 2026-07-17.

`eis_inference.py` объединил независимый fit, Lin-KK, topology bootstrap, DRT stability и калиброванную resolution-карту в один машинный контракт.

## Итог

```json
{
  "verdict": "insufficient_information",
  "best_statistical": "R0-p(R1,CPE0)-p(R2,CPE1)",
  "recommended_reliable": null,
  "data_validity": "PASS",
  "fit_status": "WARN",
  "reason": "low_frequency_repeatability_or_model_mismatch",
  "next_action": "repeat 0.01-0.1 Hz and verify stationarity/model adequacy"
}
```

Статистический победитель не скрывается, но не превращается в рекомендацию: topology bootstrap не дал 90% устойчивости. Lin-KK прошёл, поэтому проблема не классифицирована как общий провал данных.

DRT-разрешимость:

- область около `570 кГц` устойчива, худшая доля совпадений `93,3%`;
- область около `0,0194 Гц` неустойчива, худшая доля `0%`.

Resolution-калибровка показывает, что нижняя граница `0,01 Гц` уже достаточна для идеального процесса с таким временем. Поэтому engine не предлагает механически расширять диапазон, а локализует следующий эксперимент в `0,01–0,1 Гц`: повторяемость, стационарность и проверка формы модели.

## Архитектурное решение

Доступны два режима:

- `fast` — прежний Lin-KK + multi-start + селектор;
- `reliable` — добавляет topology bootstrap и DRT stability, а калиброванную resolution-карту подключает явно.

Тяжёлая карта не считается универсальной: её можно повторно использовать только для совместимого сценария либо перестроить вокруг нового процесса.

Машинный результат: `validation_data/artifacts/inference_lg_soc50/result.json`.
