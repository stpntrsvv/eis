# GUI-представление reliable inference

Дата: 2026-07-17.

## Архитектурное решение

GUI не реализует calibrated gate повторно. Он импортирует полный JSON,
созданный `eis_inference.py`, и отображает вложенный `decision`.

Это сохраняет единственный источник математической истины:

```text
headless reliable inference → JSON decision → GUI presentation
```

## Реализация

В меню `File` добавлен пункт `Import reliable result...`. Результат
привязывается к уже открытому EIS-файлу по абсолютному пути либо по
единственному совпадающему имени.

Новая вкладка `Reliable Decision` показывает:

- статистического победителя;
- рекомендованное семейство;
- рекомендованную topology либо `indistinguishable`;
- Lin-KK data validity;
- причину рекомендации или отказа;
- следующее действие;
- evaluated/passed/positive-only calibrated gate;
- фактический `ΔBIC` и использованные пороги.

Состояния визуально разделены на supported, refused и not loaded. Переключение
языка обновляет представление. При смене измерительного канала импортированное
решение сбрасывается, поскольку оно относится к предыдущим данным.

## Smoke

Headless Qt с `QT_QPA_PLATFORM=offscreen` загрузил реальный charge SOC50 и
его calibrated result:

```text
Data support a diffusion-family ECM mechanism.
Recommended family: inductive_diffusion
Recommended topology: indistinguishable
positive-only: True
```

Отдельные тесты проверяют английское и русское представление, отказ по
Lin-KK и безопасное отображение legacy/missing decision.

Машинный источник smoke:

```text
validation_data/artifacts/lipo_diffusion_gate_reliable/charge_soc50.json
```
