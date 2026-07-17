---
tags:
  - handoff
  - ai
  - roadmap
status: active
updated: 2026-07-17
---

# AI Handoff: что делать следующему чату

> [!success] Эстафета выполнена
> Семейный inference реализован в headless-контракте. Старое поле `best`
> сохранено; добавлены `best_statistical`, BIC-окно поддержанных топологий,
> агрегированное свидетельство семейства и раздельная bootstrap-устойчивость
> топологии/семейства.
>
> Калибровка показала, что 5 повторов завышают уверенность; полный прогон
> выполнен с 20. На всех 42 Li-polymer спектрах при честной конкуренции
> `inductive` против `inductive_diffusion` семейство получило `840/840`
> выборов без отказов. Точная топология прошла 90%-ворота только в `23/42`.
> Bootstrap внутри одного семейства теперь явно считается условным и не даёт
> семейной рекомендации. Unified/batch inference переведены на ту же
> семантику `adaptive_v2`. Отчёт:
> [семейный inference](../../../validation_data/reports/2026-07-17-diffusion-family-inference.md).

> [!important] Следующее прямое поручение
> **Реплицировать pilot-gate по seeds и только затем решить вопрос production.**
>
> Текущий benchmark-only gate:
> `inductive_diffusion winner AND bootstrap >= 90% AND family ΔBIC >= 10`.
> Повторить сильные, пограничные и отрицательные ячейки минимум на нескольких
> seeds. Production-интеграция разрешена только при отсутствии
> ложноположительной диффузии и заранее зафиксированной допустимой частоте
> отказов. Точную `W/Wo/Ws` пока всегда оставлять `null`.

> [!success] Первая карта наблюдаемости
> На 42 fit-ячейках семейство восстановлено в `28/42`, топология — `7/42`.
> Pilot-gate на 11 bootstrap-ячейках дал 4 правильные рекомендации, 7 отказов
> и 0 ложноположительных диффузионных выводов. Это ещё не production
> calibration. [Отчёт](../../../validation_data/reports/2026-07-17-diffusion-observability-map.md).

> [!warning] Результат синтетической калибровки
> На 16 спектрах пороги 90% и 95% сохранили три ложные топологические и две
> ложные семейные рекомендации. Все шесть отрицательных контролей избежали
> ложноположительной диффузии; семейные ошибки были пропусками слабой
> диффузии. Bootstrap — условная стабильность, не вероятность истины.
> [Отчёт](../../../validation_data/reports/2026-07-17-synthetic-family-calibration.md).

> [!note] Закрытое поручение предыдущей эстафеты
> **Следующая задача — реализовать семейный inference для диффузионных моделей
> и проверить его bootstrap по всей Li-polymer SOC-серии.**
>
> Программа уже уверенно обнаруживает необходимость диффузионного семейства,
> но пока выдаёт одного победителя `W`, `Wo` или `Ws`. Новый слой должен уметь
> сказать: **«диффузионное семейство поддержано, конкретное граничное условие
> неразличимо»**.

## Прочитать перед изменениями

1. [[26 Где лежит истина - статистический вывод и иерархический EIS]]
2. [[33 Адаптивный селектор семейств]]
3. [разбор Li-polymer `BAD`](../../../validation_data/reports/2026-07-17-lipo-bad-diagnosis.md)
4. `eis_core.py`, затем `eis_pipeline.py`, `eis_inference.py` и
   `eis_uncertainty.py`.

Не начинай с GUI. Сначала научный контракт и headless-конвейер, затем
представление результата в интерфейсе.

## Что уже реализовано

Основные модули:

| Модуль | Роль |
|---|---|
| `eis_io.py` | CSV/TXT, BioLogic `.mpt/.mpr`, embedded vendor headers |
| `eis_core.py` | Lin-KK, схемы, bounds, multi-start, fit, AIC/BIC, adaptive routing |
| `eis_pipeline.py` | одиночный и пакетный headless-анализ, JSON-контракт |
| `eis_cli.py` | CLI и потоковая запись JSONL |
| `eis_inference.py` | решение fast/reliable, bootstrap/DRT-вето |
| `eis_uncertainty.py` | topology bootstrap и profile likelihood |
| `eis_drt.py` | DRT и устойчивость временных областей |
| `eis_series.py` | диагностика и pooled evidence серий |
| `eis_joint.py` | опциональный совместный fit сырых SOC-серий |
| `eis_qt.py` | действующий PySide6 GUI |

Важные правила:

- одиночный неизвестный EIS остаётся полноценным режимом без manifest;
- `BAD` нельзя превращать в `OK` ослаблением порогов;
- конкретному элементу нельзя присваивать химическое имя только по fit;
- BIC, качество параметров, Lin-KK, bootstrap и DRT — разные оси, не одно
  магическое число;
- явные `--preset` и `--circuit` должны оставаться фиксированными и
  воспроизводимыми.

## Текущее состояние adaptive selector

CLI `--preset auto` теперь означает `adaptive_v2`, а не полный фиксированный
перебор 17 схем.

Первый уровень:

```text
форма сырого спектра
    → simple всегда
    → inductive при устойчивом положительном Im(Z) сверху
    → diffusion при низкочастотном признаке без доминирующей индуктивности
```

Второй уровень:

```text
лучший fit первого уровня
    → комплексный относительный остаток
    → локализация ошибки на низких частотах
    → проверка когерентности
    → допуск L + W / Wo / Ws
    → повторный BIC/status-отбор
```

Решение прозрачно записывается в:

```text
metadata.circuit_routing.mode
metadata.circuit_routing.families
metadata.circuit_routing.candidate_count
metadata.circuit_routing.features
metadata.circuit_routing.tiers
```

Нижние границы сопротивлений масштабно-зависимые; старый абсолютный пол
`R >= 1 мОм` удалён.

> [!warning] Важная граница интеграции
> Adaptive v2 сейчас проходит через `eis_cli.py → eis_pipeline.py`.
> Проверить и отдельно спланировать перенос той же семантики в GUI и
> `eis_inference.py`: не предполагать, что все точки входа уже используют
> двухступенчатый `auto`.

## Главный внешний результат

Корпус:

```text
validation_data/raw/zenodo_19608839_lipo_multimodal
```

В нём 42 сырых EIS-спектра. Файлы `0001` и `0023` — авторские таблицы fit, а
не сырые спектры; README также не является EIS.

Эволюция результата:

| Анализ | OK | WARN | BAD | Средняя ошибка |
|---|---:|---:|---:|---:|
| старый `simple` | 2 | 1 | 39 | около 20–24% |
| adaptive tier 1 | 0 | 42 | 0 | 10,52% |
| adaptive tier 2 | 42 | 0 | 0 | 1,91% |

Второй уровень:

- `L0-R0-p(R1,CPE0)-Wo0`: 26 побед;
- `L0-R0-p(R1,CPE0)-W0`: 10 побед;
- `L0-R0-p(R1,CPE0)-Ws0`: 6 побед;
- среднее улучшение BIC: `471,5`;
- минимальное улучшение BIC: `347,6`;
- в 6 спектрах две диффузионные версии лежат в `ΔBIC <= 2`;
- два SOC50 подтверждены тремя стартами: `1,94%` и `1,56%`, оба `OK`.

Интерпретация: данные сильно требуют диффузионного семейства, но точное
граничное условие слабее идентифицировано и меняется по SOC.

Машинные результаты:

```text
validation_data/artifacts/lipo_adaptive_v2/results.jsonl
validation_data/artifacts/lipo_adaptive_v2_smoke/results.jsonl
```

## Следующая задача: критерии готовности

Реализовать family-level inference без разрушения существующего
`best_statistical`.

Минимальный целевой контракт:

```json
{
  "best_statistical": "L0-R0-p(R1,CPE0)-Wo0",
  "recommended_family": "inductive_diffusion",
  "recommended_topology": null,
  "family_status": "supported",
  "topology_status": "models_indistinguishable",
  "supported_topologies": [
    "L0-R0-p(R1,CPE0)-W0",
    "L0-R0-p(R1,CPE0)-Wo0"
  ],
  "reason": "diffusion family stable; boundary condition unstable"
}
```

Нужно:

1. Ввести явное отображение схем в семейства, не определять семейство
   ненадёжным поиском подстроки по месту использования.
2. Для одного спектра вернуть все допустимые топологии в BIC-окне, а также
   агрегированное свидетельство семейства.
3. Bootstrap должен считать отдельно:
   - частоту победы точной топологии;
   - суммарную частоту победы семейства.
4. На SOC-серии посчитать устойчивость `W/Wo/Ws` и общего
   `inductive_diffusion`.
5. Рекомендовать точную топологию только при заранее заданной устойчивости
   (текущий ориентир `>= 90%`); иначе рекомендовать семейство и вернуть
   `recommended_topology: null`.
6. Не называть семейство физически доказанной диффузией без оговорки:
   формулировка — «данные поддерживают диффузионный ECM-механизм».
7. Сохранить обратную совместимость текущего JSON: добавлять поля, не удалять
   `best`.
8. Добавить тесты минимум для трёх случаев:
   - точная топология и семейство устойчивы;
   - семейство устойчиво, `W/Wo/Ws` меняются;
   - даже семейство неустойчиво — полный отказ от рекомендации.

Этот порядок выполнен: сначала charge/discharge SOC50 и стратифицированный
smoke, затем калибровка 5/20/50 повторов и полный прогон 42 спектров с 20
повторами.

## Команды проверки

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile eis_core.py eis_pipeline.py eis_inference.py eis_uncertainty.py
git diff --check
```

Повтор adaptive v2:

```powershell
.\.venv\Scripts\python.exe eis_cli.py `
  validation_data\raw\zenodo_19608839_lipo_multimodal `
  --preset auto --restarts 1 --max-evaluations 1200 `
  --format jsonl --output validation_data\artifacts\lipo_adaptive_v2 --quiet
```

Код возврата для каталога может быть ненулевым из-за README и авторских fit-
таблиц. Статистику считать только по 42 сырым файлам `0002–0022` и
`0024–0044`.

## Текущая проверенная база

- `75` автоматических тестов проходят;
- `py_compile` проходит;
- `git diff --check` проходит;
- предупреждение matplotlib о невозможности записать пользовательский
  font-cache в sandbox не является падением тестов;
- предупреждения `overflow in tanh` возникают внутри пробных `Wo/Ws` и сами
  по себе не означают провал итогового fit.

## Когда остановиться и передать результат

Задача следующего чата завершена, если:

- family-level контракт реализован и покрыт тестами;
- старый `best` сохранён;
- bootstrap различает устойчивость семейства и точной топологии;
- на реальных SOC50 программа может честно выбрать одно из двух:
  `recommended_topology` либо `recommended_family` с `null` topology;
- отчёт и эта памятка обновлены фактическими цифрами.

Не переходить к нейросети, GUI-полировке или новым экзотическим элементам,
пока этот уровень неоднозначности не выражен в машинном контракте.

## Последняя репликация diffusion-gate

Замороженное правило `family bootstrap >= 90%` и семейное `ΔBIC >= 10`
проверено без подбора порогов на новой карте:

- fit-only: 210 положительных сценариев и 20 отрицательных контролей;
- bootstrap: 35 strong, 35 boundary и 20 negative;
- strong: 23 рекомендации, все верные;
- boundary: 22 рекомендации, все верные;
- negative: 0 рекомендаций из 20;
- всего: precision `45/45`, 45 отказов;
- точная `W/Wo/Ws` всегда остаётся `null`.

Production-интеграция сознательно не выполнена. При `0/20` ложных срабатываний
односторонняя 95%-граница false-positive rate равна `13,9%`, что слишком
слабо. Отчёт:
`validation_data/reports/2026-07-17-diffusion-gate-replication.md`.

Следующая прямая задача: не менять пороги, расширить отрицательный корпус
минимум до 59 независимых контролей, варьировать параметры базовой дуги,
частотную сетку и шумовую модель. Переносить gate в основной inference только
если повторная проверка сохранит precision и верхняя 95%-граница false-positive
rate станет ниже `5%`.

## Production-калибровка завершена

Следующая задача выполнена без изменения порогов:

- 60/60 разнообразных отрицательных контролей завершены;
- raw family bootstrap winner верен в 58/60;
- raw bootstrap `>=90%` дал одно ложноположительное diffusion-решение;
- замороженный `bootstrap >=90% + ΔBIC >=10` дал `0/60`;
- верхняя односторонняя 95%-граница false-positive rate: `4,8703%`.

Положительный gate перенесён в `eis_inference.py`. При конкуренции
`inductive_diffusion` с другой семьёй он:

- рекомендует только семейство и только после обоих порогов;
- всегда скрывает точную `W/Wo/Ws`;
- не превращает победу base в доказательство отсутствия диффузии;
- публикует в `decision.diffusion_gate` пороги, `ΔBIC` и `positive_only`.

Отчёт:
`validation_data/reports/2026-07-17-diffusion-gate-production-calibration.md`.

Следующая прямая задача — сквозная regression-проверка reliable inference на
реальных Li-polymer SOC50 и полном 42-спектральном корпусе с новым контрактом,
после чего обновить batch/schema и GUI только если сериализация доказанно
стабильна.

## Реальная сквозная regression завершена

Charge SOC50 (`0012`) и discharge SOC50 (`0034`) прошли новый контракт:
family bootstrap `20/20`, `ΔBIC` `464,53` и `471,93`,
`recommended_family: inductive_diffusion`, `recommended_topology: null`.

На полном корпусе:

- 42/42 fit завершены;
- 38/42 получили семейную рекомендацию;
- 4/42 получили отказ по `KK FAIL`: `0002`, `0003`, `0024`, `0025`;
- точных топологических рекомендаций: `0/42`;
- победители: `Wo 26`, `W 10`, `Ws 6`;
- `ΔBIC`: минимум `414,58`, среднее `481,45`, максимум `540,50`;
- `best` и `best_statistical` присутствуют в `42/42`.

Отчёт:
`validation_data/reports/2026-07-17-real-lipo-diffusion-gate-regression.md`.

Следующая прямая задача — обновить batch flattening и JSON schema полями
`diffusion_gate`, покрыть сериализацию тестами. Затем переносить в GUI только
отображение готового решения, без новой математики.

## Batch/schema diffusion-gate завершены

Compact summary v1 аддитивно расширен шестью nullable-полями gate:
evaluated, passed, positive-only, фактический `ΔBIC` и два порога. JSONL и CSV
используют один список полей; старый decision без gate сериализуется с `null`.

Реальный reliable batch-smoke на charge/discharge SOC50 дал две строки с
`passed=true`, `positive_only=true`, `recommended_topology=null`, `ΔBIC`
`464,53` и `471,93`. Schema v1 не сломана: обязательные поля не менялись.

Отчёт:
`validation_data/reports/2026-07-17-batch-diffusion-gate-contract.md`.

Следующая прямая задача — показать готовое решение в GUI без повторной
реализации математики: семейная рекомендация, отсутствие точной topology,
причина отказа и calibrated-gate details должны читаться из headless
decision contract.

## GUI reliable decision завершён

Добавлен presentation-only мост:

```text
eis_inference.py JSON → File / Import reliable result... → Reliable Decision
```

GUI не повторяет математику. Он показывает statistical winner,
recommended family/topology, data validity, причину, next action, `ΔBIC`,
пороги и positive-only статус. Supported/refused/not-loaded различаются
визуально; RU/EN переключаются; смена канала сбрасывает старое решение.

Headless Qt smoke пройден на реальном charge SOC50.
Отчёт:
`validation_data/reports/2026-07-17-gui-reliable-decision.md`.

Следующая прямая научная задача — калибровка параметрической неопределённости:
замороженный synthetic truth, измеренное покрытие covariance/bootstrap/profile
likelihood и машинные статусы `identified/weak/unbounded`. GUI-полировка не
должна задерживать эту ветку.

## Первый pilot покрытия интервалов завершён

На 12 frozen truth-спектрах получено фактическое nominal-95% покрытие:

- covariance: `72,7%`, среди `identified` — `69,8%`;
- residual bootstrap, 20 повторов: `78,8%` и `80,4%`;
- profile likelihood: `36,1%` и `27,3%`.

Near-bound эвристика исправлена для логарифмических параметров; profile grid
теперь содержит fitted center и интерполирует `Δχ²`-пересечения. Несмотря на
это, production-критерий не пройден. `calibrated=true` и parameter-status в
основной контракт не добавлены.

Отчёт:
`validation_data/reports/2026-07-17-parameter-interval-coverage-pilot.md`.

Следующая прямая задача — второй, заранее стратифицированный benchmark:
observable против weakly observable truth, больше повторов, parametric
bootstrap и profile в log-параметризации с адаптивным диапазоном. До него
поле confidence остаётся локальной fit-ошибкой, не гарантированным
95%-интервалом.

## Стратифицированная калибровка интервалов завершена

Добавлены frozen observable/weak CPE и `Wo`, parametric bootstrap и
раздельная сводка по целевым параметрам. Из 20 сценариев завершены 16:
четыре из пяти weak-`Wo` корректно отказались со статусом `BAD`.

На observable CPE parametric bootstrap дал `14/15` покрытий, на observable
`Wo` — `10/10`. Однако weak CPE почти всегда ошибочно остаётся `identified`,
а representative profile накрыл только `3/8`. Поэтому
`calibrated=true` и production-статусы параметров не добавлены.

Отчёт:
`validation_data/reports/2026-07-17-stratified-parameter-interval-coverage.md`.

Следующая прямая задача — калибровать identifiability по устойчивости к
частотному окну: holdout/расширение краёв диапазона и контроль bias. Profile
likelihood сначала перевести на log-параметризацию положительных параметров
и адаптивное расширение сетки; до этого не публиковать его как 95%-интервал.

## Frequency-window identifiability gate реализован

Benchmark-only gate требует устойчивости параметра после удаления 10%/20%
частот с каждого края и попадания характерной частоты `R-CPE`/`Wo` в
измеренный диапазон.

На frozen-корпусе false `identified` у weak CPE снижены:

- covariance: `14 → 0`;
- residual bootstrap: `14 → 0`;
- parametric bootstrap: `13 → 0`.

Все identified observable CPE/Wo сохранены. Но nominal coverage residual
bootstrap для observable CPE остаётся `80%`, поэтому production-интеграции
нет и `calibrated=true` запрещён.

Отчёт:
`validation_data/reports/2026-07-17-frequency-window-identifiability-gate.md`.

Следующая прямая задача — репликация карты по seeds, шумам `0,5/1/2%` и
характерным частотам внутри, около и снаружи обоих краёв диапазона. Пороги
trim `10/20%` и fold-change `1,5` не менять до завершения репликации.
