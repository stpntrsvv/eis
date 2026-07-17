# Покрытие параметрических интервалов: truth-aware pilot

Дата: 2026-07-17.

## Цель

Проверить, можно ли уже называть локальные covariance, residual bootstrap и
profile likelihood интервалы калиброванными 95%-интервалами и выпускать
статусы `identified/weak/unbounded` в production.

## Корпус

Заморожены 12 синтетических спектров с известными параметрами:

- 6 × `R0-p(R1,CPE0)`;
- 6 × `L0-R0-p(R1,CPE0)-Wo0`;
- 61 частота от `0,01` до `100000` Hz;
- 1% относительного комплексного Gaussian noise;
- параметры случайно выбраны из широкой synthetic-области.

Для каждого спектра:

- covariance-интервал трактовался как estimate ± `1,96σ`;
- residual bootstrap использовал 20 повторов;
- profile считался для `R1`, `CPE alpha`, `Wo strength` и `Wo tau`.

## Исправления во время pilot

Первый прототип ошибочно определял near-bound как 1% линейной ширины bounds.
Для логарифмически распределённых параметров это помечало почти всё как
границу. Проверка заменена на мультипликативную близость.

Profile grid теперь явно содержит fitted center, а пересечения
`Δχ² = 3,841` интерполируются между узлами. Попадание интервала в край сетки
остаётся `unbounded`.

## Результат

| Метод | Интервалы | Общее покрытие | Покрытие среди `identified` |
|---|---:|---:|---:|
| covariance | 66 | 72,7% | 69,8% |
| residual bootstrap | 66 | 78,8% | 80,4% |
| profile likelihood | 36 | 36,1% | 27,3% |

Для diffusion-параметров ситуация особенно слабая:

- covariance: `Wo strength 3/6`, `Wo tau 2/6`;
- bootstrap: `Wo strength 3/6`, `Wo tau 1/6`;
- profile: `Wo strength 3/6`, `Wo tau 1/6`.

Даже после исправления сетки profile часто даёт слишком узкий локальный
интервал либо попадает в край диапазона. Текущий `identified` также не
калиброван: интервалы с этим ярлыком систематически недопокрывают truth.

## Решение

- не добавлять `calibrated: true` в production;
- не экспортировать `identified/weak/unbounded` как научно проверенный verdict;
- сохранить benchmark и status только как исследовательский прототип;
- covariance `confidence` продолжать трактовать как локальную ошибку fit, не
  гарантированный 95%-интервал;
- следующий эксперимент разделить на заранее наблюдаемую и слабонаблюдаемую
  области, увеличить число truth-спектров и проверить parametric bootstrap;
- profile доработать в лог-параметризации с адаптивным расширением сетки и
  повторными стартами.

Пилот выполнил роль предохранителя: красивый локальный интервал не был
перенесён в продукт без проверки покрытия.

Машинные результаты:

```text
validation_data/artifacts/parameter_interval_pilot/truth.jsonl
validation_data/artifacts/parameter_interval_pilot/interval_results_v2.jsonl
validation_data/artifacts/parameter_interval_pilot/interval_results_v2_summary.json
```
