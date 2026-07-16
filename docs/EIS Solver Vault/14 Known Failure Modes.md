---
tags:
  - science
  - debugging
  - failure-modes
status: active
---

# Known Failure Modes

Эта страница — список вещей, которые могут сломать смысл анализа даже при работающем коде.

## Данные И Парсинг

| Симптом | Возможная причина | Что делать |
|---|---|---|
| Nyquist перевёрнут | знак Im перепутан | проверить parser metadata и raw columns |
| странная линия вместо дуги | частоты/колонки перепутаны | открыть Parser tab |
| fit падает на BioLogic | файл не EIS или другой schema | проверить metadata/columns |
| мало точек | слишком короткий спектр | не доверять сложным моделям |
| повторяющиеся частоты | прибор/export artifact | чистить или агрегировать |
| NaN/inf | плохой экспорт | parser clean должен выкинуть |

## Фитинг

| Симптом | Возможная причина | Что делать |
|---|---|---|
| `BAD:param_uncertainty_gt_200pct` | параметр неидентифицируем | упростить схему |
| `near_lower_bound` | bound давит fit | проверить guess/bounds |
| CPE alpha у нижней границы | модель имитирует распределение/Warburg | проверить физику и residuals |
| fit слишком хороший у сложной схемы | overfit | смотреть BIC и flags |
| ручная схема не сходится | плохой initial guess | Pro mode bounds table |

## Физические Ловушки

> [!danger] Warburg как мусорная корзина
> Warburg может улучшить fit, но не обязан означать реальную диффузию. Нужна форма спектра и воспроизводимость.

> [!danger] Inductor как оправдание артефакта
> Индуктивная петля может быть реальной, но часто это wiring/fixture/instability. Нельзя принимать `L` только потому, что BIC стал лучше.

## GUI И UX

| Симптом | Причина | Решение |
|---|---|---|
| Cancel не мгновенный | cooperative cancel | дождаться текущей схемы; следующая уже не запустится |
| сложная схема долго оптимизируется | poor identifiability / bad initial guess | production budget остановит fit после 5,000 evaluations и пометит `LIMIT` |
| `.mpt` долго фитится | большой/сложный набор точек | normal, worker keeps GUI alive |
| presets не в AppData | нет write access | fallback `.eis_solver_user` |
| русская локализация не меняет экспорт | намеренно | export contract stable |
