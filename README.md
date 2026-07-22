# EIS Solver

[![Windows build](https://github.com/stpntrsvv/eis/actions/workflows/windows-build.yml/badge.svg)](https://github.com/stpntrsvv/eis/actions/workflows/windows-build.yml)
[![macOS build](https://github.com/stpntrsvv/eis/actions/workflows/macos-build.yml/badge.svg)](https://github.com/stpntrsvv/eis/actions/workflows/macos-build.yml)

**EIS Solver** — настольная программа и CLI для анализа данных
электрохимической импедансной спектроскопии (EIS). Она читает спектры,
проверяет их согласованность, подбирает эквивалентные электрические схемы,
показывает диагностику и экспортирует воспроизводимые результаты.

Текущая версия: **0.9.0 release candidate**. Вычислительный контур и сборка
прошли приёмку на машине разработки. До номера `1.0.0` остаются проверка на
чистой Windows-машине и короткая пользовательская приёмка.

## Что умеет программа

- открывает TXT, CSV, DAT и BioLogic MPT/MPR;
- находит доступные каналы импеданса и очищает некорректные точки;
- выполняет Lin-KK-проверку Крамерса—Кронига;
- автоматически выбирает физически правдоподобные семейства схем;
- фитит RC, CPE, Warburg и индуктивные модели;
- сравнивает модели по BIC и показывает статусы `OK`, `WARN`, `BAD`;
- строит Nyquist, Bode, residual и KK-графики;
- обрабатывает отдельные файлы и целые каталоги;
- экспортирует CSV, XLSX, текстовые отчёты и изображения;
- в Pro mode создаёт проверенные пакеты SPICE и C (`float32`/Q31).

EIS Solver не объявляет лучшую схему единственной физической истиной.
Статистика, качество параметров, Lin-KK, bootstrap и DRT являются разными
источниками свидетельства и должны интерпретироваться вместе с условиями
эксперимента.

## Быстрый запуск

### Готовая Windows-сборка

Скопируйте весь каталог `dist/eis_qt`, а не только `eis_qt.exe`, затем
запустите:

```text
dist\eis_qt\eis_qt.exe
```

### Готовая macOS-сборка

Распакуйте `EIS-Solver-macOS-arm64.zip` и перенесите `EIS Solver.app` в
`Applications`. Сборка предназначена для Apple Silicon (M1 и новее).

Пока приложение подписано ad-hoc и не нотарифицировано Apple. Поэтому после
скачивания macOS может потребовать первый запуск через **Finder → правый клик
→ Open / Открыть**. Для бесшовной установки потребуется Developer ID и
нотарификация.

### Запуск из исходников

Требуется Python 3.14 и зависимости проекта:

```bash
python -m venv .venv
python -m pip install -r requirements-lock.txt
python eis_qt.py
```

Для разработки можно использовать незакреплённый список
`requirements.txt`. Проверенный набор конкретных версий находится в
`requirements-lock.txt`.

## Обычный рабочий сценарий

1. Откройте один или несколько файлов либо перетащите папку в окно.
2. Проверьте найденный канал, количество точек и статус KK.
3. Нажмите **Run auto-fit / Автофит**.
4. Сравните лучшую модель с другими кандидатами и изучите residuals.
5. Проверьте параметры, предупреждения и попадание в границы.
6. Экспортируйте таблицы, отчёт и графики через **Export...**.

Для ручного выбора семейства, собственной схемы и границ параметров включите
**Pro mode**. Автоматический режим GUI и CLI использует один вычислительный
путь `adaptive_v2`; явные пресеты и ручные схемы не расширяются скрытыми
кандидатами.

## Командная строка

Один файл:

```bash
python eis_cli.py spectrum.csv --no-plot
```

BioLogic и выбор канала:

```bash
python eis_cli.py spectrum.mpr --channel Z1 --no-plot
```

Пакетная обработка с потоковым JSONL:

```bash
python eis_cli.py measurements --recursive --format jsonl --output artifacts/run
```

Фиксированный пресет:

```bash
python eis_cli.py spectrum.csv --preset interface --format json --output result.json
```

CLI продолжает работу после плохого файла по умолчанию. Используйте
`--fail-fast`, если нужно завершаться при первой ошибке, и `--mode parse` или
`--mode kk` для изолированной проверки входных данных.

## Инженерный экспорт

Проверенный SPICE-пакет:

```bash
python eis_cli.py spectrum.csv \
  --spice-export artifacts/cell_spice \
  --ngspice /path/to/ngspice
```

Пакет C для контроллера:

```bash
python eis_cli.py spectrum.csv \
  --controller-export artifacts/cell_controller \
  --sample-period-us 100 \
  --current-full-scale-a 10
```

Оба экспортёра работают по принципу fail-closed: при неприемлемой научной
модели, ошибке KK или провале инженерных ворот конечный каталог не создаётся.
SPICE требует настоящий запуск ngspice. Контроллерный пакет содержит общую
модель, варианты `float32` и Q31, паспорт и эталонные векторы.

## Поддерживаемые модели

Основные элементы:

- `R` — сопротивление;
- `C` — идеальная ёмкость;
- `CPE` — элемент постоянной фазы;
- `W`, `Wo`, `Ws` — варианты Warburg;
- `L` — индуктивность.

Пример строки схемы:

```text
R0-p(R1,CPE0)-p(R2,CPE1)
```

`-` означает последовательное соединение, `p(...,...)` — параллельное.
Списки схем, начальные оценки, bounds, фитинг и выбор модели находятся в
`eis_core.py`.

## Как читать результат

- `OK` — текущая диагностика не обнаружила явных проблем.
- `WARN` — результат может быть полезен, но требует проверки флагов,
  residuals и параметров.
- `BAD` — серьёзная неидентифицируемость, недопустимые параметры или
  попадание в границы.
- `PASS/WARN/FAIL` у KK относится к качеству и согласованности данных, а не к
  истинности конкретной эквивалентной схемы.

Точные рекомендации `W/Wo/Ws`, параметрические интервалы, bootstrap, profile
likelihood, DRT и joint-fit остаются исследовательскими возможностями. Версия
1 не выдаёт их за откалиброванную вероятность истины.

## Документация и воспроизводимость

- Начало документации: [`docs/EIS Solver Vault/00 Start Here.md`](docs/EIS%20Solver%20Vault/00%20Start%20Here.md)
- Архитектура: [`03 Architecture.md`](docs/EIS%20Solver%20Vault/03%20Architecture.md)
- Научная модель: [`04 Scientific Model.md`](docs/EIS%20Solver%20Vault/04%20Scientific%20Model.md)
- Проверка и тесты: [`09 Validation And Tests.md`](docs/EIS%20Solver%20Vault/09%20Validation%20And%20Tests.md)
- Выпускной контур: [`36 Контур выпуска версии 1.md`](docs/EIS%20Solver%20Vault/36%20Контур%20выпуска%20версии%201.md)
- Памятка следующему разработчику/AI: [`AI Handoff.md`](docs/EIS%20Solver%20Vault/AI%20Handoff.md)
- Отчёты воспроизводимой валидации: [`validation_data/reports`](validation_data/reports)

Vault можно открыть целиком в Obsidian. Исходные внешние корпуса и тяжёлые
сгенерированные артефакты намеренно не хранятся в Git; их происхождение и
контрольные суммы описаны в `validation_data`.

## Разработка и приёмка

Тесты:

```bash
python -m unittest discover -s tests -v
```

Исходная приёмка:

```bash
python eis_release_check.py --require-gcc --output release-passport.json
```

Полная Windows-приёмка дополнительно требует собранный exe и ngspice:

```powershell
.\.venv\Scripts\python.exe eis_release_check.py `
  --require-spice `
  --require-gcc `
  --require-packaged `
  --packaged-exe dist\eis_qt\eis_qt.exe `
  --ngspice C:\path\to\ngspice_con.exe `
  --gcc C:\path\to\gcc.exe
```

Workflow `.github/workflows/windows-build.yml` на каждом push в `main`
собирает Windows x64 folder build на чистом GitHub-hosted runner, запускает
тесты и packaged smoke на TXT и реальном BioLogic MPR, проверяет релизные
метаданные и публикует ZIP-артефакт на 30 дней. SPICE/ngspice остаётся
отдельным строгим воротом финальной локальной Windows-приёмки.

Workflow `.github/workflows/macos-build.yml` аналогично собирает `.app` для
macOS ARM64, проверяет ad-hoc подпись, TXT/MPR smoke, C-компиляцию и публикует
ZIP, SHA-256 и release passport на 30 дней. Локальная сборка выполняется так:

```bash
python -m PyInstaller --clean --noconfirm eis_macos.spec
open "dist/EIS Solver.app"
```

## Цитирование

Если EIS Solver использовался при подготовке результатов, укажите версию
программы и процитируйте её согласно [`CITATION.md`](CITATION.md). GitHub
также читает машинный файл [`CITATION.cff`](CITATION.cff) и предлагает готовые
ссылки в APA и BibTeX.

## Лицензия

Copyright © 2026 Stepan Tarasov (`stpntrsvv`).

EIS Solver распространяется на условиях **GNU General Public License v3.0
or later** (`GPL-3.0-or-later`). Полный текст находится в [`LICENSE`](LICENSE).
Программа предоставляется без каких-либо гарантий. Уведомления о сторонних
компонентах находятся в [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
