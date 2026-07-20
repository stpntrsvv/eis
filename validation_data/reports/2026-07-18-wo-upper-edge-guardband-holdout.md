# Wo upper-edge guard band: calibration и независимый holdout

Дата: 2026-07-18.

## Цель

Предыдущая карта показала, что формальное попадание characteristic frequency
в измеренную полосу недостаточно, особенно для `Wo` около верхнего края.
Этот benchmark заранее разделяет:

1. calibration, где выбирается минимальный допустимый guard band;
2. независимый holdout с новыми seeds, параметрами и частотными сетками;
3. запрет переизбирать порог после просмотра holdout.

Production parameter-status разрешён только при прохождении holdout.

## Замороженный дизайн

Модуль: `eis_wo_guardband.py`.

Truth-distance определяется как:

```text
d_upper = log10(f_max / f_characteristic)
```

Положительное значение находится внутри полосы. Проверены позиции:

```text
-0,3; 0; 0,15; 0,3; 0,5; 0,7; 1,0; 1,3 декады
```

Candidate guard bands до численного запуска:

```text
0,4; 0,6; 0,85; 1,1 декады
```

Кандидаты лежат между truth-узлами, поэтому точка прямо на decision boundary
не используется ни как positive, ни как negative truth.

Оба split содержат по `432` спектра:

```text
2 сетки × 3 parameter profiles × 8 расстояний × 3 шума × 3 seeds
```

Общее для обоих split:

- circuit: `R0-Wo0`;
- noise: `0,5%`, `1%`, `2%` relative complex Gaussian;
- trim: `10%` и `20%` отдельно с каждого края;
- maximum window fold-change: `1,5`;
- три детерминированных старта.

Calibration:

- сетки `0,01–10 Гц / 61 точка` и `0,03–30 Гц / 51 точка`;
- profiles `(R0, Wo strength)`: `(1,5)`, `(5,20)`, `(20,80)`;
- seeds `20260723–20260725`.

Holdout:

- сетки `0,1–100 Гц / 41 точка` и `0,005–5 Гц / 81 точка`;
- profiles: `(10,5)`, `(2,30)`, `(50,150)`;
- seeds `20260823–20260825`.

## Критерий выбора

Выбирается минимальный candidate, который одновременно даёт:

- `100%` техническое завершение;
- минимум 59 ineligible и 50 eligible сценариев;
- `0` ложных проходов;
- retention не ниже `90%`;
- долю eligible сценариев, которые прошли gate и имеют truth fold-error не
  выше `1,5`, не ниже `90%`.

Тот же критерий применяется к holdout. Holdout не переизбирает порог.

## Calibration

Завершены `432/432`.

| Guard, decade | Eligible pass | Retention | False pass |
|---:|---:|---:|---:|
| `0,4` | `207/216` | `95,8%` | `0/216` |
| `0,6` | `162/162` | `100%` | `0/270` |
| `0,85` | `108/108` | `100%` | `0/324` |
| `1,1` | `54/54` | `100%` | `0/378` |

Минимальный прошедший кандидат: `0,4` декады, то есть characteristic
frequency должна быть ниже `f_max` примерно в `10^0,4 = 2,51` раза.

## Независимый holdout

Замороженный `0,4` не прошёл.

| Guard | Eligible pass | Retention | Accurate retention | False pass |
|---:|---:|---:|---:|---:|
| `0,4` frozen | `183/216` | `84,7%` | `84,7%` | `0/216` |

Специфичность сохранилась: ложных проходов нет, односторонняя 95%-граница
false-pass rate равна `1,377%`. Провал относится к sensitivity/retention.

Все `33` пропуска вызваны `frequency_window_stable=false`:

- ни одного `BAD` среди eligible;
- fitted characteristic support не был причиной отказа;
- все прошедшие сценарии имели maximum truth fold-error `<=1,5`.

Главная стратификация:

| Holdout grid | Pass при frozen `0,4` | Retention |
|---|---:|---:|
| 41 точка | `79/108` | `73,1%` |
| 81 точка | `104/108` | `96,3%` |

На ближайшем eligible truth-distance `0,5` ухудшение с шумом особенно резко:

- `15/18` при `0,5%`;
- `14/18` при `1%`;
- `7/18` при `2%`.

Постфактум кандидат `0,6` прошёл бы агрегированный holdout с `147/162 =
90,7%`, но его нельзя выбирать после просмотра holdout. Более того, на
41-точечной страте он даёт только `66/81 = 81,5%`, поэтому простой сдвиг
guard band не устраняет найденный класс нестабильности.

## Решение

- Calibration-selected guard `0,4` отвергнут независимым holdout.
- Ни `0,4`, ни постфактум `0,6` не переносятся в production.
- Inclusive characteristic support и frequency-window stability остаются
  benchmark-only diagnostics.
- `calibrated=true` и production parameter-status по-прежнему запрещены.
- Отрицательный результат не означает, что `Wo` отсутствует; он означает,
  что текущая процедура не гарантирует устойчивую идентификацию на новых
  плотностях частотной сетки.

Следующая прямая задача — заранее замороженная карта плотности сетки:
point-count/points-per-decade × trim rule × noise на новых seeds и profiles.
Критерии должны проверяться отдельно в каждой grid-density страте, а не
только агрегированно. До неё нельзя менять trim `10/20%`, fold-change `1,5`
или переобучать guard по holdout.

## Воспроизведение

Calibration:

```powershell
.\.venv\Scripts\python.exe eis_wo_guardband.py `
  validation_data\artifacts\wo_guardband_calibration `
  --split calibration `
  --trim-fraction 0.10 --trim-fraction 0.20 `
  --max-fold-change 1.5 --restarts 3 `
  --max-evaluations 2000 --fit-seed 20260723
```

Holdout:

```powershell
.\.venv\Scripts\python.exe eis_wo_guardband.py `
  validation_data\artifacts\wo_guardband_holdout `
  --split holdout `
  --selection-summary `
  validation_data\artifacts\wo_guardband_calibration\results_summary.json `
  --trim-fraction 0.10 --trim-fraction 0.20 `
  --max-fold-change 1.5 --restarts 3 `
  --max-evaluations 2000 --fit-seed 20260823
```
