import csv
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import warnings

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__), ".matplotlib"))

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QAction, QActionGroup, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QInputDialog,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from eis_core import (
    ADVANCED_CIRCUITS,
    DEFAULT_CIRCUITS,
    DIFFUSION_CIRCUITS,
    FitResult,
    IDEAL_RC_CIRCUITS,
    INTERFACE_CIRCUITS,
    INDUCTIVE_CIRCUITS,
    KramersKronigResult,
    SIMPLE_CIRCUITS,
    build_bounds_and_guess,
    choose_best_result,
    circuit_to_latex,
    circuit_to_readable,
    estimate_dataset_scale,
    fit_circuit,
    lin_kk_check,
    parameter_names,
)
from eis_io import load_eis_file
from eis_gui_decision import format_reliable_decision

warnings.filterwarnings("ignore")


INTERFACE_PRESETS = {
    "Off": [],
    "Ideal RC": IDEAL_RC_CIRCUITS,
    "Charge transfer": ["R0-p(R1,CPE0)"],
    "Film + charge transfer": ["R0-p(R1,CPE0)-p(R2,CPE1)", "R0-p(R1-p(R2,CPE1),CPE0)"],
    "Interface screening": SIMPLE_CIRCUITS,
}

TRANSPORT_PRESETS = {
    "Off": [],
    "Diffusion / Warburg": DIFFUSION_CIRCUITS,
    "Inductive loop": INDUCTIVE_CIRCUITS,
    "Transport full": ADVANCED_CIRCUITS,
}


UI_TRANSLATIONS = {
    "ru": {
        "EIS Solver": "EIS Solver",
        "File": "Файл",
        "Fit": "Фитинг",
        "View": "Вид",
        "Help": "Справка",
        "Language": "Язык",
        "About / Guide": "О программе / гайд",
        "English": "English",
        "Russian": "Русский",
        "Open EIS files": "Открыть EIS файлы",
        "Open folder": "Открыть папку",
        "Import reliable result...": "Импорт reliable-результата...",
        "Run auto-fit": "Автофит",
        "Run selected presets": "Фит пресетов",
        "Run manual circuit": "Фит ручной схемы",
        "Cancel fit": "Отменить фитинг",
        "Export...": "Экспорт...",
        "Datasets": "Данные",
        "No files selected": "Файлы не выбраны",
        "Open one or many EIS files to inspect scale estimates.": "Откройте один или несколько EIS файлов для оценки масштаба.",
        "Open files": "Открыть файлы",
        "Cancel": "Отмена",
        "Channel": "Канал",
        "Pro mode": "Pro режим",
        "Pro circuit controls": "Pro настройки схем",
        "Interface": "Интерфейс",
        "Transport": "Транспорт",
        "Run selected presets": "Фит пресетов",
        "Run manual": "Ручной фит",
        "Fill guesses": "Заполнить оценки",
        "Parameter": "Параметр",
        "Initial": "Начальное",
        "Lower": "Низ",
        "Upper": "Верх",
        "Load": "Загрузить",
        "Save preset": "Сохранить пресет",
        "Delete": "Удалить",
        "Status": "Статус",
        "File": "Файл",
        "Format": "Формат",
        "Points": "Точки",
        "Best circuit": "Лучшая схема",
        "Fit, %": "Ошибка, %",
        "Flags": "Флаги",
        "Circuit": "Схема",
        "Params": "Параметры",
        "Param err, %": "Ошибка парам., %",
        "Flags / Message": "Флаги / сообщение",
        "Detected Columns": "Найденные колонки",
        "Best Parameters": "Лучшие параметры",
        "Value": "Значение",
        "Confidence": "Довер. интервал",
        "Rel. error, %": "Отн. ошибка, %",
        "No dataset loaded.": "Данные не загружены.",
        "No fit has been run.": "Фитинг ещё не запускался.",
        "No successful fit.": "Нет успешного фитинга.",
        "Ready": "Готово",
        "Export": "Экспорт",
        "Choose export outputs": "Выберите, что экспортировать",
        "Batch summary CSV": "Сводка batch CSV",
        "All model results CSV": "Все результаты моделей CSV",
        "Best parameters CSV": "Лучшие параметры CSV",
        "Parser metadata CSV": "Метаданные парсера CSV",
        "Kramers-Kronig check CSV": "Проверка Крамерса-Кронига CSV",
        "Excel workbook XLSX": "Excel workbook XLSX",
        "Selected report + plots": "Отчёт выбранного файла + графики",
        "Open EIS folder": "Открыть папку EIS",
        "EIS data (*.mpr *.mpt *.txt *.csv *.dat);;All files (*.*)": "Данные EIS (*.mpr *.mpt *.txt *.csv *.dat);;Все файлы (*.*)",
        "All files (*.*)": "Все файлы (*.*)",
        "No EIS files": "Нет EIS файлов",
        "No .mpr, .mpt, .txt, .csv, or .dat files found.": "Файлы .mpr, .mpt, .txt, .csv или .dat не найдены.",
        "Read error": "Ошибка чтения",
        "No files loaded.": "Файлы не загружены.",
        "No circuits selected": "Схемы не выбраны",
        "Select at least one Interface or Transport preset.": "Выберите хотя бы один пресет Interface или Transport.",
        "No circuit entered": "Схема не введена",
        "Enter a circuit string first.": "Сначала введите строку схемы.",
        "Manual parameter error": "Ошибка ручных параметров",
        "No dataset loaded": "Данные не загружены",
        "Open a dataset before filling guesses.": "Откройте данные перед заполнением оценок.",
        "Circuit error": "Ошибка схемы",
        "Circuit format": "Формат схемы",
        "Nothing to export": "Нечего экспортировать",
        "Run a fit before exporting results.": "Запустите фитинг перед экспортом результатов.",
        "Nothing selected": "Ничего не выбрано",
        "Select at least one export output.": "Выберите хотя бы один тип экспорта.",
        "Export base name": "Базовое имя экспорта",
        "Export error": "Ошибка экспорта",
        "Preset error": "Ошибка пресета",
        "Save Pro preset": "Сохранить Pro пресет",
        "Preset name:": "Имя пресета:",
        "Delete Pro preset": "Удалить Pro пресет",
        "Delete preset": "Удалить пресет",
        "Fit is running": "Фитинг выполняется",
        "A fit is still running. Cancel it and close when the current fit step finishes?": "Фитинг ещё выполняется. Отменить его и закрыть окно после текущего шага?",
        "Channel error": "Ошибка канала",
        "About EIS Solver": "О EIS Solver",
        "Close": "Закрыть",
        "Reliable Decision": "Надёжный вывод",
        "Inference result (*.json);;All files (*.*)": "Результат inference (*.json);;Все файлы (*.*)",
        "Inference import error": "Ошибка импорта inference",
        "Load the matching EIS dataset before importing its inference result.": "Сначала загрузите соответствующий EIS-спектр.",
    }
}


def translate(language, text):
    return UI_TRANSLATIONS.get(language, {}).get(text, text)


def format_metadata(metadata):
    if not metadata:
        return ""
    lines = []
    for key, value in metadata.items():
        if key == "comments" and isinstance(value, list):
            lines.append(f"{key}: {len(value)} comment line(s)")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def user_config_dir():
    candidates = [
        os.path.join(os.environ.get("APPDATA", ""), "EIS Solver") if os.environ.get("APPDATA") else "",
        os.path.join(os.path.expanduser("~"), ".config", "EIS Solver"),
        os.path.join(os.getcwd(), ".eis_solver_user"),
    ]
    for path in candidates:
        if not path:
            continue
        try:
            os.makedirs(path, exist_ok=True)
            probe_path = os.path.join(path, ".write_test")
            with open(probe_path, "w", encoding="utf-8") as file:
                file.write("ok")
            os.remove(probe_path)
            return path
        except OSError:
            continue
    return os.getcwd()


def user_presets_path():
    return os.path.join(user_config_dir(), "pro_presets.json")


class ExportDialog(QDialog):
    def __init__(self, parent=None, language="en"):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(translate(language, "Export"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(translate(language, "Choose export outputs")))

        self.summary_box = QCheckBox(translate(language, "Batch summary CSV"))
        self.all_results_box = QCheckBox(translate(language, "All model results CSV"))
        self.best_params_box = QCheckBox(translate(language, "Best parameters CSV"))
        self.parser_box = QCheckBox(translate(language, "Parser metadata CSV"))
        self.kk_box = QCheckBox(translate(language, "Kramers-Kronig check CSV"))
        self.excel_box = QCheckBox(translate(language, "Excel workbook XLSX"))
        self.selected_report_box = QCheckBox(translate(language, "Selected report + plots"))

        for checkbox in (
            self.summary_box,
            self.all_results_box,
            self.best_params_box,
            self.parser_box,
            self.kk_box,
            self.excel_box,
            self.selected_report_box,
        ):
            checkbox.setChecked(True)
            layout.addWidget(checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_exports(self):
        return {
            "summary": self.summary_box.isChecked(),
            "all_results": self.all_results_box.isChecked(),
            "best_params": self.best_params_box.isChecked(),
            "parser": self.parser_box.isChecked(),
            "kk": self.kk_box.isChecked(),
            "excel": self.excel_box.isChecked(),
            "selected_report": self.selected_report_box.isChecked(),
        }


class AboutGuideDialog(QDialog):
    def __init__(self, parent=None, language="en"):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(translate(language, "About EIS Solver"))
        self.resize(760, 620)

        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.guide_text(language))
        layout.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Close).setText(translate(language, "Close"))
        layout.addWidget(buttons)

    @staticmethod
    def guide_text(language):
        if language == "ru":
            return (
                "EIS Solver\n"
                "Рабочая программа для анализа EIS: загрузка спектров, подбор эквивалентных схем, "
                "Nyquist/Bode/residuals, batch-анализ и экспорт.\n\n"
                "Быстрый сценарий\n"
                "1. Нажмите Open files, Open folder или перетащите файлы/папку в окно.\n"
                "2. Проверьте таблицу Datasets и выбранный канал.\n"
                "3. Нажмите Run auto-fit.\n"
                "4. Смотрите Best Parameters, Nyquist, Bode и Residuals.\n"
                "5. Нажмите Export... и выберите CSV/XLSX/отчёт/графики.\n\n"
                "Pro mode\n"
                "- Включите Pro mode, если нужно выбрать семейства схем вручную.\n"
                "- Interface: RC/CPE, перенос заряда, две дуги.\n"
                "- Transport: Warburg/диффузия и индуктивные петли.\n"
                "- Run selected presets фитит только выбранные семейства.\n\n"
                "Ручная схема\n"
                "1. Введите строку схемы, например R0-p(R1,CPE0)-p(R2,CPE1).\n"
                "2. Нажмите Fill guesses, чтобы заполнить Initial/Lower/Upper.\n"
                "3. Отредактируйте значения при необходимости.\n"
                "4. Нажмите Run manual.\n"
                "5. Save preset сохранит схему и bounds локально на этом компьютере.\n\n"
                "Формат схем\n"
                "- '-' означает последовательное соединение.\n"
                "- p(...,...) означает параллельное соединение.\n"
                "- Поддержаны R, C, CPE, W, Wo, Ws, L.\n"
                "- Индексы важны: R0, R1, CPE0, CPE1.\n\n"
                "Диагностика модели\n"
                "- OK: явных предупреждений нет.\n"
                "- WARN: модель может быть полезной, но стоит проверить flags/residuals.\n"
                "- BAD: сильная неидентифицируемость, плохие параметры или попадание в границы.\n"
                "- Рекомендованная модель выбирается по BIC среди не-BAD кандидатов.\n\n"
                "Форматы файлов\n"
                "- Текстовые SmartStat/generic txt/csv/dat.\n"
                "- BioLogic .mpt через galvani.\n"
                "- BioLogic .mpr поддержан через galvani, но реальный EIS .mpr ещё нужно валидировать на лабораторном файле.\n"
            )

        return (
            "EIS Solver\n"
            "A desktop tool for EIS analysis: spectrum loading, equivalent-circuit fitting, "
            "Nyquist/Bode/residual plots, batch analysis, and export.\n\n"
            "Quick workflow\n"
            "1. Click Open files, Open folder, or drag files/folders into the window.\n"
            "2. Check the Datasets table and selected impedance channel.\n"
            "3. Click Run auto-fit.\n"
            "4. Inspect Best Parameters, Nyquist, Bode, and Residuals.\n"
            "5. Click Export... and choose CSV/XLSX/report/plot outputs.\n\n"
            "Pro mode\n"
            "- Enable Pro mode when you want manual control over circuit families.\n"
            "- Interface: RC/CPE, charge transfer, two-arc models.\n"
            "- Transport: Warburg/diffusion and inductive loops.\n"
            "- Run selected presets fits only the selected families.\n\n"
            "Manual circuit\n"
            "1. Enter a circuit string, e.g. R0-p(R1,CPE0)-p(R2,CPE1).\n"
            "2. Click Fill guesses to populate Initial/Lower/Upper.\n"
            "3. Edit values if needed.\n"
            "4. Click Run manual.\n"
            "5. Save preset stores the circuit and bounds locally on this computer.\n\n"
            "Circuit syntax\n"
            "- '-' means series connection.\n"
            "- p(...,...) means parallel connection.\n"
            "- Supported elements: R, C, CPE, W, Wo, Ws, L.\n"
            "- Index suffixes matter: R0, R1, CPE0, CPE1.\n\n"
            "Model diagnostics\n"
            "- OK: no current warnings.\n"
            "- WARN: useful candidate, but inspect flags/residuals.\n"
            "- BAD: severe non-identifiability, poor parameters, or bound issues.\n"
            "- Recommended model uses BIC among non-BAD candidates.\n\n"
            "KK Check\n"
            "- PASS/WARN/FAIL reports Lin-KK spectrum consistency before trusting fit parameters.\n"
            "- Inspect WARN/FAIL together with the KK Check tab, residuals, and experiment protocol.\n\n"
            "File formats\n"
            "- SmartStat/generic txt/csv/dat.\n"
            "- BioLogic .mpt through galvani.\n"
            "- BioLogic .mpr through galvani, still awaiting validation on a real lab EIS .mpr file.\n"
        )


@dataclass
class AnalysisCase:
    file_path: str
    frequencies: np.ndarray
    z_experimental: np.ndarray
    scale: object
    source_format: str = ""
    columns: list[str] | None = None
    metadata: dict | None = None
    selected_channel: str = "Z"
    available_channels: list[str] | None = None
    kk_result: KramersKronigResult | None = None
    results: list[FitResult] | None = None
    best_result: FitResult | None = None
    inference_decision: dict | None = None
    error_message: str = ""


class FitWorker(QObject):
    started_case = Signal(int, str)
    finished_case = Signal(int, object, object)
    failed_case = Signal(int, str)
    progress = Signal(int, int)
    log = Signal(str)
    finished = Signal(bool)

    def __init__(self, cases: list[AnalysisCase], circuits: list[str], run_label: str, parameter_overrides_by_circuit=None):
        super().__init__()
        self.cases = cases
        self.circuits = circuits
        self.run_label = run_label
        self.parameter_overrides_by_circuit = parameter_overrides_by_circuit or {}
        self.cancel_requested = False

    @Slot()
    def run(self):
        total = len(self.cases) * len(self.circuits)
        completed = 0
        cancelled = False
        self.log.emit(f"{self.run_label}: {len(self.circuits)} circuit(s) selected.")
        for index, case in enumerate(self.cases):
            if self.cancel_requested:
                cancelled = True
                break

            label = os.path.basename(case.file_path)
            self.started_case.emit(index, label)
            self.log.emit(f"Fitting {label}...")
            try:
                results = []
                for circuit_string in self.circuits:
                    if self.cancel_requested:
                        cancelled = True
                        break
                    self.log.emit(f"  {circuit_string}...")
                    result = fit_circuit(
                        case.frequencies,
                        case.z_experimental,
                        circuit_string,
                        case.scale,
                        parameter_overrides=self.parameter_overrides_by_circuit.get(circuit_string),
                    )
                    results.append(result)
                    completed += 1
                    self.progress.emit(completed, total)
                    outcome = (
                        f"{result.status}, fit={result.mean_fit_error:.3f}%"
                        if result.success
                        else f"{result.status}: {result.error_message}"
                    )
                    self.log.emit(f"  {circuit_string}: {outcome} ({result.elapsed_seconds:.2f}s)")
                if self.cancel_requested:
                    cancelled = True
                    break
                best_result = choose_best_result(results)
                self.finished_case.emit(index, results, best_result)
                self.log.emit(
                    f"Best for {label}: {best_result.circuit_string}, "
                    f"fit={best_result.mean_fit_error:.3f}%, BIC={best_result.bic:.2f}"
                )
            except Exception as exc:
                self.failed_case.emit(index, str(exc))
                self.log.emit(f"Fit error for {label}: {exc}")

        self.finished.emit(cancelled)

    @Slot()
    def cancel(self):
        self.cancel_requested = True


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)


class BodeCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.ax_magnitude = self.figure.add_subplot(211)
        self.ax_phase = self.figure.add_subplot(212, sharex=self.ax_magnitude)
        super().__init__(self.figure)


class ResidualCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.ax_complex = self.figure.add_subplot(211)
        self.ax_relative = self.figure.add_subplot(212, sharex=self.ax_complex)
        super().__init__(self.figure)


class KkCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.ax_nyquist = self.figure.add_subplot(211)
        self.ax_error = self.figure.add_subplot(212)
        super().__init__(self.figure)


class EisQtApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EIS Solver")
        self.resize(1280, 820)

        self.cases: list[AnalysisCase] = []
        self.current_case_index = -1
        self._updating_cases_table = False
        self._updating_channel_combo = False
        self.fit_thread = None
        self.fit_worker = None
        self.close_after_fit = False
        self.user_presets = {}
        self.language = "en"

        self.open_action = QAction("Open EIS files", self)
        self.open_action.triggered.connect(self.open_file)

        self.open_folder_action = QAction("Open folder", self)
        self.open_folder_action.triggered.connect(self.open_folder)

        self.import_inference_action = QAction("Import reliable result...", self)
        self.import_inference_action.triggered.connect(self.import_inference_result)

        self.run_action = QAction("Run auto-fit", self)
        self.run_action.setEnabled(False)
        self.run_action.triggered.connect(lambda _checked=False: self.run_auto_fit())

        self.run_selected_action = QAction("Run selected presets", self)
        self.run_selected_action.setEnabled(False)
        self.run_selected_action.triggered.connect(lambda _checked=False: self.run_selected_fit())

        self.run_manual_action = QAction("Run manual circuit", self)
        self.run_manual_action.setEnabled(False)
        self.run_manual_action.triggered.connect(lambda _checked=False: self.run_manual_fit())

        self.cancel_action = QAction("Cancel fit", self)
        self.cancel_action.setEnabled(False)
        self.cancel_action.triggered.connect(self.cancel_fit)

        self.save_action = QAction("Export...", self)
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self.export_results)

        self.about_action = QAction("About / Guide", self)
        self.about_action.triggered.connect(self.show_about_guide)

        self.file_menu = self.menuBar().addMenu("File")
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.open_folder_action)
        self.file_menu.addAction(self.import_inference_action)
        self.file_menu.addAction(self.save_action)

        self.fit_menu = self.menuBar().addMenu("Fit")
        self.fit_menu.addAction(self.run_action)
        self.fit_menu.addAction(self.run_selected_action)
        self.fit_menu.addAction(self.run_manual_action)
        self.fit_menu.addAction(self.cancel_action)

        self.view_menu = self.menuBar().addMenu("View")
        self.language_menu = self.view_menu.addMenu("Language")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.english_action = QAction("English", self, checkable=True)
        self.english_action.setChecked(True)
        self.russian_action = QAction("Русский", self, checkable=True)
        self.language_group.addAction(self.english_action)
        self.language_group.addAction(self.russian_action)
        self.language_menu.addAction(self.english_action)
        self.language_menu.addAction(self.russian_action)
        self.english_action.triggered.connect(lambda _checked=False: self.set_language("en"))
        self.russian_action.triggered.connect(lambda _checked=False: self.set_language("ru"))

        self.help_menu = self.menuBar().addMenu("Help")
        self.help_menu.addAction(self.about_action)

        toolbar = self.addToolBar("Main")
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.open_folder_action)
        toolbar.addAction(self.run_action)
        toolbar.addAction(self.cancel_action)
        toolbar.addAction(self.save_action)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready")
        self.setAcceptDrops(True)

        self._build_layout()
        self.load_user_presets()
        self.apply_language()

    def _build_layout(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        root_layout.addWidget(self.main_splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        left_layout.addWidget(self.left_splitter)

        self.file_box = QGroupBox("Datasets")
        file_layout = QVBoxLayout(self.file_box)
        self.file_label = QLabel("No files selected")
        self.scale_label = QLabel("Open one or many EIS files to inspect scale estimates.")
        self.scale_label.setWordWrap(True)
        buttons = QHBoxLayout()
        self.open_button = QPushButton("Open files")
        self.open_button.clicked.connect(self.open_file)
        self.open_folder_button = QPushButton("Open folder")
        self.open_folder_button.clicked.connect(self.open_folder)
        self.run_button = QPushButton("Run auto-fit")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(lambda _checked=False: self.run_auto_fit())
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_fit)
        self.save_button = QPushButton("Export...")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.export_results)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.open_folder_button)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.scale_label)
        channel_row = QHBoxLayout()
        self.channel_label = QLabel("Channel")
        channel_row.addWidget(self.channel_label)
        self.channel_combo = QComboBox()
        self.channel_combo.setEnabled(False)
        self.channel_combo.currentTextChanged.connect(self.on_channel_changed)
        channel_row.addWidget(self.channel_combo, stretch=1)
        file_layout.addLayout(channel_row)

        self.pro_toggle_button = QPushButton("Pro mode")
        self.pro_toggle_button.setCheckable(True)
        self.pro_toggle_button.toggled.connect(self.set_pro_mode)
        file_layout.addWidget(self.pro_toggle_button)

        self.pro_panel = QGroupBox("Pro circuit controls")
        pro_layout = QVBoxLayout(self.pro_panel)
        preset_row = QHBoxLayout()
        self.interface_label = QLabel("Interface")
        preset_row.addWidget(self.interface_label)
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(INTERFACE_PRESETS.keys())
        self.interface_combo.setCurrentText("Interface screening")
        preset_row.addWidget(self.interface_combo, stretch=1)
        self.transport_label = QLabel("Transport")
        preset_row.addWidget(self.transport_label)
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(TRANSPORT_PRESETS.keys())
        self.transport_combo.setCurrentText("Off")
        preset_row.addWidget(self.transport_combo, stretch=1)
        pro_layout.addLayout(preset_row)

        pro_buttons = QHBoxLayout()
        self.run_selected_button = QPushButton("Run selected presets")
        self.run_selected_button.setEnabled(False)
        self.run_selected_button.clicked.connect(lambda _checked=False: self.run_selected_fit())
        pro_buttons.addWidget(self.run_selected_button)
        pro_layout.addLayout(pro_buttons)

        manual_row = QHBoxLayout()
        self.manual_circuit_edit = QLineEdit()
        self.manual_circuit_edit.setPlaceholderText("R0-p(R1,CPE0)-p(R2,CPE1)")
        self.manual_circuit_edit.textChanged.connect(self.clear_manual_bounds_table)
        self.manual_circuit_edit.returnPressed.connect(self.run_manual_fit)
        manual_row.addWidget(self.manual_circuit_edit, stretch=1)
        self.manual_help_button = QPushButton("?")
        self.manual_help_button.setFixedWidth(32)
        self.manual_help_button.clicked.connect(self.show_circuit_help)
        manual_row.addWidget(self.manual_help_button)
        self.run_manual_button = QPushButton("Run manual")
        self.run_manual_button.setEnabled(False)
        self.run_manual_button.clicked.connect(lambda _checked=False: self.run_manual_fit())
        manual_row.addWidget(self.run_manual_button)
        pro_layout.addLayout(manual_row)

        manual_bounds_buttons = QHBoxLayout()
        self.fill_manual_bounds_button = QPushButton("Fill guesses")
        self.fill_manual_bounds_button.clicked.connect(self.populate_manual_bounds_table)
        manual_bounds_buttons.addWidget(self.fill_manual_bounds_button)
        pro_layout.addLayout(manual_bounds_buttons)

        self.manual_bounds_table = QTableWidget(0, 4)
        self.manual_bounds_table.setHorizontalHeaderLabels(["Parameter", "Initial", "Lower", "Upper"])
        self.manual_bounds_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.manual_bounds_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.manual_bounds_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.manual_bounds_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        pro_layout.addWidget(self.manual_bounds_table)

        preset_store_row = QHBoxLayout()
        self.user_preset_combo = QComboBox()
        self.user_preset_combo.setEnabled(False)
        preset_store_row.addWidget(self.user_preset_combo, stretch=1)
        self.load_user_preset_button = QPushButton("Load")
        self.load_user_preset_button.setEnabled(False)
        self.load_user_preset_button.clicked.connect(self.load_selected_user_preset)
        preset_store_row.addWidget(self.load_user_preset_button)
        self.save_user_preset_button = QPushButton("Save preset")
        self.save_user_preset_button.clicked.connect(self.save_current_user_preset)
        preset_store_row.addWidget(self.save_user_preset_button)
        self.delete_user_preset_button = QPushButton("Delete")
        self.delete_user_preset_button.setEnabled(False)
        self.delete_user_preset_button.clicked.connect(self.delete_selected_user_preset)
        preset_store_row.addWidget(self.delete_user_preset_button)
        pro_layout.addLayout(preset_store_row)

        self.pro_panel.setVisible(False)
        file_layout.addWidget(self.pro_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        file_layout.addWidget(self.progress_bar)
        file_layout.addLayout(buttons)
        self.left_splitter.addWidget(self.file_box)

        self.cases_table = QTableWidget(0, 9)
        self.cases_table.setHorizontalHeaderLabels(["Status", "File", "Format", "Points", "KK", "Best circuit", "Fit, %", "BIC", "Flags"])
        self.cases_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cases_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.cases_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.cases_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)
        self.cases_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cases_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cases_table.currentCellChanged.connect(self.on_case_changed)
        self.cases_table.setMinimumHeight(90)
        self.left_splitter.addWidget(self.cases_table)

        self.results_table = QTableWidget(0, 8)
        self.results_table.setHorizontalHeaderLabels(["Status", "Circuit", "Fit, %", "BIC", "AIC", "Params", "Param err, %", "Flags / Message"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setMinimumHeight(90)
        self.left_splitter.addWidget(self.results_table)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(70)
        self.left_splitter.addWidget(self.log_output)
        self.left_splitter.setStretchFactor(0, 0)
        self.left_splitter.setStretchFactor(1, 2)
        self.left_splitter.setStretchFactor(2, 3)
        self.left_splitter.setStretchFactor(3, 1)
        self.left_splitter.setSizes([250, 170, 250, 120])

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.tabs = QTabWidget()

        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        self.canvas = MplCanvas()
        self.nav_toolbar = NavigationToolbar2QT(self.canvas, self)
        plot_layout.addWidget(self.nav_toolbar)
        plot_layout.addWidget(self.canvas)
        self.tabs.addTab(plot_tab, "Nyquist")

        bode_tab = QWidget()
        bode_layout = QVBoxLayout(bode_tab)
        self.bode_canvas = BodeCanvas()
        self.bode_toolbar = NavigationToolbar2QT(self.bode_canvas, self)
        bode_layout.addWidget(self.bode_toolbar)
        bode_layout.addWidget(self.bode_canvas)
        self.tabs.addTab(bode_tab, "Bode")

        residual_tab = QWidget()
        residual_layout = QVBoxLayout(residual_tab)
        self.residual_canvas = ResidualCanvas()
        self.residual_toolbar = NavigationToolbar2QT(self.residual_canvas, self)
        residual_layout.addWidget(self.residual_toolbar)
        residual_layout.addWidget(self.residual_canvas)
        self.tabs.addTab(residual_tab, "Residuals")

        kk_tab = QWidget()
        kk_layout = QVBoxLayout(kk_tab)
        self.kk_summary = QLabel("No dataset loaded.")
        self.kk_summary.setWordWrap(True)
        self.kk_canvas = KkCanvas()
        self.kk_toolbar = NavigationToolbar2QT(self.kk_canvas, self)
        kk_layout.addWidget(self.kk_summary)
        kk_layout.addWidget(self.kk_toolbar)
        kk_layout.addWidget(self.kk_canvas)
        self.tabs.addTab(kk_tab, "KK Check")

        parser_tab = QWidget()
        parser_layout = QVBoxLayout(parser_tab)
        self.parser_summary = QLabel("No dataset loaded.")
        self.parser_summary.setWordWrap(True)
        self.columns_table = QTableWidget(0, 1)
        self.columns_table.setHorizontalHeaderLabels(["Detected Columns"])
        self.columns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.columns_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metadata_output = QTextEdit()
        self.metadata_output.setReadOnly(True)
        parser_layout.addWidget(self.parser_summary)
        self.parser_splitter = QSplitter(Qt.Vertical)
        self.parser_splitter.setChildrenCollapsible(False)
        self.parser_splitter.addWidget(self.columns_table)
        self.parser_splitter.addWidget(self.metadata_output)
        self.parser_splitter.setStretchFactor(0, 2)
        self.parser_splitter.setStretchFactor(1, 1)
        self.parser_splitter.setSizes([420, 220])
        parser_layout.addWidget(self.parser_splitter, stretch=1)
        self.tabs.addTab(parser_tab, "Parser")

        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)
        self.best_label = QLabel("No fit has been run.")
        self.best_label.setWordWrap(True)
        self.params_table = QTableWidget(0, 4)
        self.params_table.setHorizontalHeaderLabels(["Parameter", "Value", "Confidence", "Rel. error, %"])
        self.params_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.params_table.setEditTriggers(QTableWidget.NoEditTriggers)
        params_layout.addWidget(self.best_label)
        params_layout.addWidget(self.params_table)
        self.tabs.addTab(params_tab, "Best Parameters")

        decision_tab = QWidget()
        decision_layout = QVBoxLayout(decision_tab)
        self.reliable_decision_headline = QLabel()
        self.reliable_decision_headline.setWordWrap(True)
        headline_font = self.reliable_decision_headline.font()
        headline_font.setBold(True)
        headline_font.setPointSize(headline_font.pointSize() + 2)
        self.reliable_decision_headline.setFont(headline_font)
        self.reliable_decision_details = QTextEdit()
        self.reliable_decision_details.setReadOnly(True)
        decision_layout.addWidget(self.reliable_decision_headline)
        decision_layout.addWidget(self.reliable_decision_details)
        self.tabs.addTab(decision_tab, "Reliable Decision")

        right_layout.addWidget(self.tabs)

        self.main_splitter.addWidget(left)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 3)
        self.main_splitter.setSizes([470, 810])

        self.setCentralWidget(root)
        self.plot_data()

    def log(self, message=""):
        self.log_output.append(message)
        self.statusBar().showMessage(message or self.t("Ready"))

    def t(self, text):
        return translate(self.language, text)

    def set_language(self, language):
        self.language = language
        self.apply_language()

    def show_about_guide(self):
        dialog = AboutGuideDialog(self, language=self.language)
        dialog.exec()

    def apply_language(self):
        self.setWindowTitle(self.t("EIS Solver"))
        self.file_menu.setTitle(self.t("File"))
        self.fit_menu.setTitle(self.t("Fit"))
        self.view_menu.setTitle(self.t("View"))
        self.help_menu.setTitle(self.t("Help"))
        self.language_menu.setTitle(self.t("Language"))
        self.english_action.setText(self.t("English"))
        self.russian_action.setText(self.t("Russian"))

        self.open_action.setText(self.t("Open EIS files"))
        self.open_folder_action.setText(self.t("Open folder"))
        self.import_inference_action.setText(self.t("Import reliable result..."))
        self.run_action.setText(self.t("Run auto-fit"))
        self.run_selected_action.setText(self.t("Run selected presets"))
        self.run_manual_action.setText(self.t("Run manual circuit"))
        self.cancel_action.setText(self.t("Cancel fit"))
        self.save_action.setText(self.t("Export..."))
        self.about_action.setText(self.t("About / Guide"))

        self.file_box.setTitle(self.t("Datasets"))
        if not self.cases:
            self.file_label.setText(self.t("No files selected"))
            self.scale_label.setText(self.t("Open one or many EIS files to inspect scale estimates."))
        self.open_button.setText(self.t("Open files"))
        self.open_folder_button.setText(self.t("Open folder"))
        self.run_button.setText(self.t("Run auto-fit"))
        self.cancel_button.setText(self.t("Cancel"))
        self.save_button.setText(self.t("Export..."))
        self.channel_label.setText(self.t("Channel"))
        self.pro_toggle_button.setText(self.t("Pro mode"))
        self.pro_panel.setTitle(self.t("Pro circuit controls"))
        self.interface_label.setText(self.t("Interface"))
        self.transport_label.setText(self.t("Transport"))
        self.run_selected_button.setText(self.t("Run selected presets"))
        self.run_manual_button.setText(self.t("Run manual"))
        self.fill_manual_bounds_button.setText(self.t("Fill guesses"))
        self.load_user_preset_button.setText(self.t("Load"))
        self.save_user_preset_button.setText(self.t("Save preset"))
        self.delete_user_preset_button.setText(self.t("Delete"))

        self.manual_bounds_table.setHorizontalHeaderLabels(
            [self.t("Parameter"), self.t("Initial"), self.t("Lower"), self.t("Upper")]
        )
        self.cases_table.setHorizontalHeaderLabels(
            [
                self.t("Status"),
                self.t("File"),
                self.t("Format"),
                self.t("Points"),
                "KK",
                self.t("Best circuit"),
                self.t("Fit, %"),
                "BIC",
                self.t("Flags"),
            ]
        )
        self.results_table.setHorizontalHeaderLabels(
            [
                self.t("Status"),
                self.t("Circuit"),
                self.t("Fit, %"),
                "BIC",
                "AIC",
                self.t("Params"),
                self.t("Param err, %"),
                self.t("Flags / Message"),
            ]
        )
        self.columns_table.setHorizontalHeaderLabels([self.t("Detected Columns")])
        self.params_table.setHorizontalHeaderLabels(
            [self.t("Parameter"), self.t("Value"), self.t("Confidence"), self.t("Rel. error, %")]
        )
        self.tabs.setTabText(0, "Nyquist")
        self.tabs.setTabText(1, "Bode")
        self.tabs.setTabText(2, "Residuals")
        self.tabs.setTabText(3, "KK Check")
        self.tabs.setTabText(4, "Parser")
        self.tabs.setTabText(5, self.t("Best Parameters"))
        self.tabs.setTabText(6, self.t("Reliable Decision"))

        if not self.active_case():
            self.parser_summary.setText(self.t("No dataset loaded."))
            self.kk_summary.setText(self.t("No dataset loaded."))
        if self.params_table.rowCount() == 0:
            self.best_label.setText(self.t("No fit has been run."))
        self.populate_reliable_decision_tab()
        if not self.statusBar().currentMessage():
            self.statusBar().showMessage(self.t("Ready"))

    def active_case(self):
        if 0 <= self.current_case_index < len(self.cases):
            return self.cases[self.current_case_index]
        return None

    def accepted_eis_path(self, file_path):
        return os.path.splitext(file_path)[1].lower() in {".mpr", ".mpt", ".txt", ".csv", ".dat"}

    def collect_eis_paths(self, paths):
        file_paths = []
        for path in paths:
            if os.path.isdir(path):
                for root, _dirs, files in os.walk(path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        if self.accepted_eis_path(file_path):
                            file_paths.append(file_path)
            elif os.path.isfile(path) and self.accepted_eis_path(path):
                file_paths.append(path)
        return sorted(dict.fromkeys(file_paths))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if self.collect_eis_paths(paths):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        file_paths = self.collect_eis_paths(paths)
        if file_paths:
            self.load_file_paths(file_paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def load_user_presets(self):
        path = user_presets_path()
        try:
            with open(path, "r", encoding="utf-8") as file:
                self.user_presets = json.load(file)
        except FileNotFoundError:
            self.user_presets = {}
        except Exception as exc:
            self.user_presets = {}
            self.log(f"Could not load Pro presets: {exc}")
        self.refresh_user_preset_combo()

    def write_user_presets(self):
        with open(user_presets_path(), "w", encoding="utf-8") as file:
            json.dump(self.user_presets, file, indent=2, ensure_ascii=False)

    def refresh_user_preset_combo(self):
        self.user_preset_combo.clear()
        self.user_preset_combo.addItems(sorted(self.user_presets))
        has_presets = bool(self.user_presets)
        self.user_preset_combo.setEnabled(has_presets)
        self.load_user_preset_button.setEnabled(has_presets)
        self.delete_user_preset_button.setEnabled(has_presets)

    def current_manual_preset(self):
        circuit = self.manual_circuit()
        if not circuit:
            raise ValueError("Enter a manual circuit first.")
        if self.manual_bounds_table.rowCount() == 0:
            self.populate_manual_bounds_table()
        if self.manual_bounds_table.rowCount() == 0:
            raise ValueError("Fill parameter guesses before saving a preset.")
        bounds = []
        for row in range(self.manual_bounds_table.rowCount()):
            values = []
            for col in range(4):
                item = self.manual_bounds_table.item(row, col)
                values.append(item.text().strip() if item else "")
            bounds.append(
                {
                    "parameter": values[0],
                    "initial": values[1],
                    "lower": values[2],
                    "upper": values[3],
                }
            )
        return {"circuit": circuit, "bounds": bounds}

    def apply_manual_preset(self, preset):
        self.manual_circuit_edit.setText(preset.get("circuit", ""))
        bounds = preset.get("bounds", [])
        self.manual_bounds_table.setRowCount(len(bounds))
        for row, values in enumerate(bounds):
            name_item = QTableWidgetItem(str(values.get("parameter", "")))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.manual_bounds_table.setItem(row, 0, name_item)
            self.manual_bounds_table.setItem(row, 1, QTableWidgetItem(str(values.get("initial", ""))))
            self.manual_bounds_table.setItem(row, 2, QTableWidgetItem(str(values.get("lower", ""))))
            self.manual_bounds_table.setItem(row, 3, QTableWidgetItem(str(values.get("upper", ""))))

    def save_current_user_preset(self):
        try:
            preset = self.current_manual_preset()
        except Exception as exc:
            QMessageBox.critical(self, self.t("Preset error"), str(exc))
            return
        name, ok = QInputDialog.getText(self, self.t("Save Pro preset"), self.t("Preset name:"))
        if not ok or not name.strip():
            return
        self.user_presets[name.strip()] = preset
        try:
            self.write_user_presets()
        except Exception as exc:
            QMessageBox.critical(self, self.t("Preset error"), str(exc))
            return
        self.refresh_user_preset_combo()
        self.user_preset_combo.setCurrentText(name.strip())
        self.log(f"Saved Pro preset '{name.strip()}' to {user_presets_path()}")

    def load_selected_user_preset(self):
        name = self.user_preset_combo.currentText()
        if not name:
            return
        self.apply_manual_preset(self.user_presets.get(name, {}))
        self.log(f"Loaded Pro preset '{name}'")

    def delete_selected_user_preset(self):
        name = self.user_preset_combo.currentText()
        if not name:
            return
        answer = QMessageBox.question(
            self,
            self.t("Delete Pro preset"),
            f"{self.t('Delete preset')} '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.user_presets.pop(name, None)
        try:
            self.write_user_presets()
        except Exception as exc:
            QMessageBox.critical(self, self.t("Preset error"), str(exc))
            return
        self.refresh_user_preset_combo()
        self.log(f"Deleted Pro preset '{name}'")

    def open_file(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.t("Open EIS files"),
            "",
            self.t("EIS data (*.mpr *.mpt *.txt *.csv *.dat);;All files (*.*)"),
        )
        if not file_paths:
            return

        self.load_file_paths(file_paths)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, self.t("Open EIS folder"), "")
        if not folder_path:
            return

        file_paths = self.collect_eis_paths([folder_path])

        if not file_paths:
            QMessageBox.information(self, self.t("No EIS files"), self.t("No .mpr, .mpt, .txt, .csv, or .dat files found."))
            return

        self.load_file_paths(sorted(file_paths))

    def import_inference_result(self):
        result_path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("Import reliable result..."),
            "",
            self.t("Inference result (*.json);;All files (*.*)"),
        )
        if not result_path:
            return
        try:
            payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
            decision = payload.get("decision")
            source_file = payload.get("file")
            if not isinstance(decision, dict):
                raise ValueError("JSON does not contain a decision object")
            source_resolved = os.path.normcase(os.path.abspath(source_file)) if source_file else ""
            matched_index = next(
                (
                    index for index, case in enumerate(self.cases)
                    if source_resolved
                    and os.path.normcase(os.path.abspath(case.file_path)) == source_resolved
                ),
                None,
            )
            if matched_index is None and source_file:
                source_name = os.path.basename(source_file)
                matches = [
                    index for index, case in enumerate(self.cases)
                    if os.path.basename(case.file_path) == source_name
                ]
                matched_index = matches[0] if len(matches) == 1 else None
            if matched_index is None:
                raise ValueError(
                    self.t("Load the matching EIS dataset before importing its inference result.")
                )
            self.cases[matched_index].inference_decision = decision
            self.set_current_case(matched_index)
            self.tabs.setCurrentIndex(6)
            self.log(f"Imported reliable inference: {result_path}")
        except Exception as exc:
            QMessageBox.critical(self, self.t("Inference import error"), str(exc))

    def load_file_paths(self, file_paths):
        loaded_cases = []
        failures = []
        for file_path in file_paths:
            try:
                dataset = load_eis_file(file_path)
                scale = estimate_dataset_scale(dataset.frequencies, dataset.z)
                kk_result = lin_kk_check(dataset.frequencies, dataset.z)
                loaded_cases.append(
                    AnalysisCase(
                        file_path=file_path,
                        frequencies=dataset.frequencies,
                        z_experimental=dataset.z,
                        scale=scale,
                        source_format=dataset.source_format,
                        columns=dataset.columns,
                        metadata=dataset.metadata,
                        selected_channel=dataset.metadata.get("selected_channel", "Z"),
                        available_channels=dataset.metadata.get("available_channels", ["Z"]),
                        kk_result=kk_result,
                    )
                )
            except Exception as exc:
                failures.append(f"{os.path.basename(file_path)}: {exc}")

        if not loaded_cases:
            QMessageBox.critical(self, self.t("Read error"), "\n".join(failures) or self.t("No files loaded."))
            return

        self.cases = loaded_cases
        self.current_case_index = 0

        self.results_table.setRowCount(0)
        self.params_table.setRowCount(0)
        self.best_label.setText("No fit has been run.")
        self.log_output.clear()
        self.log(f"Loaded {len(loaded_cases)} file(s).")
        for case in loaded_cases:
            self.log(f"Loaded {case.file_path}")
        for failure in failures:
            self.log(f"Read error: {failure}")

        self.run_action.setEnabled(True)
        self.run_button.setEnabled(True)
        pro_enabled = self.pro_toggle_button.isChecked()
        self.run_selected_action.setEnabled(pro_enabled)
        self.run_selected_button.setEnabled(pro_enabled)
        self.run_manual_action.setEnabled(pro_enabled)
        self.run_manual_button.setEnabled(pro_enabled)
        self.save_action.setEnabled(False)
        self.save_button.setEnabled(False)
        self.populate_cases_table()
        self.set_current_case(0)

    def set_pro_mode(self, enabled):
        self.pro_panel.setVisible(enabled)
        self.run_selected_action.setEnabled(enabled and self.fit_thread is None and bool(self.cases))
        self.run_manual_action.setEnabled(enabled and self.fit_thread is None and bool(self.cases))
        self.run_selected_button.setEnabled(enabled and self.fit_thread is None and bool(self.cases))
        self.run_manual_button.setEnabled(enabled and self.fit_thread is None and bool(self.cases))
        self.log("Pro mode enabled." if enabled else "Pro mode hidden.")

    def selected_preset_circuits(self):
        circuits = []
        for circuit in INTERFACE_PRESETS.get(self.interface_combo.currentText(), []):
            if circuit not in circuits:
                circuits.append(circuit)
        for circuit in TRANSPORT_PRESETS.get(self.transport_combo.currentText(), []):
            if circuit not in circuits:
                circuits.append(circuit)
        return circuits

    def run_auto_fit(self):
        self.run_fit(list(DEFAULT_CIRCUITS), "Auto-fit")

    def run_selected_fit(self):
        circuits = self.selected_preset_circuits()
        if not circuits:
            QMessageBox.information(self, self.t("No circuits selected"), self.t("Select at least one Interface or Transport preset."))
            return
        label = f"Preset fit: {self.interface_combo.currentText()} + {self.transport_combo.currentText()}"
        self.run_fit(circuits, label)

    def manual_circuit(self):
        return self.manual_circuit_edit.text().strip()

    def run_manual_fit(self):
        circuit = self.manual_circuit()
        if not circuit:
            QMessageBox.information(self, self.t("No circuit entered"), self.t("Enter a circuit string first."))
            return
        try:
            overrides = self.manual_parameter_overrides(circuit)
        except Exception as exc:
            QMessageBox.critical(self, self.t("Manual parameter error"), str(exc))
            return
        self.run_fit([circuit], f"Manual circuit: {circuit}", parameter_overrides_by_circuit={circuit: overrides})

    def clear_manual_bounds_table(self, *_args):
        self.manual_bounds_table.setRowCount(0)

    def populate_manual_bounds_table(self):
        case = self.active_case()
        circuit = self.manual_circuit()
        if not case:
            QMessageBox.information(self, self.t("No dataset loaded"), self.t("Open a dataset before filling guesses."))
            return
        if not circuit:
            QMessageBox.information(self, self.t("No circuit entered"), self.t("Enter a circuit string first."))
            return

        try:
            low_bounds, high_bounds, initial_guess = build_bounds_and_guess(circuit, case.scale)
            names = parameter_names(circuit)
        except Exception as exc:
            QMessageBox.critical(self, self.t("Circuit error"), str(exc))
            return

        self.manual_bounds_table.setRowCount(len(names))
        for row, (name, initial, lower, upper) in enumerate(zip(names, initial_guess, low_bounds, high_bounds)):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.manual_bounds_table.setItem(row, 0, name_item)
            self.manual_bounds_table.setItem(row, 1, QTableWidgetItem(f"{initial:.6e}"))
            self.manual_bounds_table.setItem(row, 2, QTableWidgetItem(f"{lower:.6e}"))
            self.manual_bounds_table.setItem(row, 3, QTableWidgetItem(f"{upper:.6e}"))

    def manual_parameter_overrides(self, circuit):
        if self.manual_bounds_table.rowCount() == 0:
            case = self.active_case()
            if case is None:
                return {}
            low_bounds, high_bounds, initial_guess = build_bounds_and_guess(circuit, case.scale)
            return {
                name: {"initial": initial, "lower": lower, "upper": upper}
                for name, initial, lower, upper in zip(parameter_names(circuit), initial_guess, low_bounds, high_bounds)
            }

        overrides = {}
        for row in range(self.manual_bounds_table.rowCount()):
            name_item = self.manual_bounds_table.item(row, 0)
            initial_item = self.manual_bounds_table.item(row, 1)
            lower_item = self.manual_bounds_table.item(row, 2)
            upper_item = self.manual_bounds_table.item(row, 3)
            if not all((name_item, initial_item, lower_item, upper_item)):
                raise ValueError(f"Incomplete manual parameter row {row + 1}.")

            name = name_item.text().strip()
            initial = float(initial_item.text())
            lower = float(lower_item.text())
            upper = float(upper_item.text())
            if lower >= upper:
                raise ValueError(f"Lower bound must be below upper bound for {name}.")
            overrides[name] = {"initial": initial, "lower": lower, "upper": upper}
        return overrides

    def show_circuit_help(self):
        QMessageBox.information(
            self,
            self.t("Circuit format"),
            "Use impedance.py circuit strings.\n\n"
            "Series: separate elements with '-'\n"
            "Parallel: wrap branches as p(...,...)\n\n"
            "Examples:\n"
            "R0-p(R1,CPE0)\n"
            "R0-p(R1,CPE0)-p(R2,CPE1)\n"
            "R0-p(R1,CPE0)-W0\n"
            "L0-R0-p(R1,CPE0)\n\n"
            "Supported elements here:\n"
            "R, C, CPE, W, Wo, Ws, L.\n"
            "Number suffixes matter: R0, R1, CPE0, CPE1.",
        )

    def run_fit(self, circuits=None, run_label="Auto-fit", parameter_overrides_by_circuit=None):
        if not self.cases:
            return
        if self.fit_thread is not None:
            return

        circuits = list(circuits or DEFAULT_CIRCUITS)
        self.log(f"Running {run_label} for {len(self.cases)} file(s)...")

        for case in self.cases:
            case.results = None
            case.best_result = None
            case.error_message = ""

        self.progress_bar.setRange(0, len(self.cases) * len(circuits))
        self.progress_bar.setValue(0)
        self.populate_cases_table()
        self.set_fit_controls_running(True)

        self.fit_thread = QThread(self)
        self.fit_worker = FitWorker(self.cases, circuits, run_label, parameter_overrides_by_circuit)
        self.fit_worker.moveToThread(self.fit_thread)
        self.fit_thread.started.connect(self.fit_worker.run)
        self.fit_worker.started_case.connect(self.on_fit_started_case)
        self.fit_worker.finished_case.connect(self.on_fit_finished_case)
        self.fit_worker.failed_case.connect(self.on_fit_failed_case)
        self.fit_worker.progress.connect(self.on_fit_progress)
        self.fit_worker.log.connect(self.log)
        self.fit_worker.finished.connect(self.on_fit_finished)
        self.fit_worker.finished.connect(self.fit_thread.quit)
        self.fit_worker.finished.connect(self.fit_worker.deleteLater)
        self.fit_thread.finished.connect(self.fit_thread.deleteLater)
        self.fit_thread.finished.connect(self.clear_fit_thread)
        self.fit_thread.start()

    def cancel_fit(self):
        if self.fit_worker is not None:
            self.log("Cancel requested. Waiting for the current fit to finish...")
            self.fit_worker.cancel()
            self.cancel_action.setEnabled(False)
            self.cancel_button.setEnabled(False)

    def set_fit_controls_running(self, running: bool):
        self.open_action.setEnabled(not running)
        self.open_folder_action.setEnabled(not running)
        self.open_button.setEnabled(not running)
        self.open_folder_button.setEnabled(not running)
        self.run_action.setEnabled((not running) and bool(self.cases))
        self.run_button.setEnabled((not running) and bool(self.cases))
        pro_enabled = self.pro_toggle_button.isChecked()
        self.run_selected_action.setEnabled((not running) and pro_enabled and bool(self.cases))
        self.run_selected_button.setEnabled((not running) and pro_enabled and bool(self.cases))
        self.run_manual_action.setEnabled((not running) and pro_enabled and bool(self.cases))
        self.run_manual_button.setEnabled((not running) and pro_enabled and bool(self.cases))
        self.manual_circuit_edit.setEnabled(not running)
        self.manual_help_button.setEnabled(not running)
        self.fill_manual_bounds_button.setEnabled(not running)
        self.manual_bounds_table.setEnabled(not running)
        self.user_preset_combo.setEnabled((not running) and bool(self.user_presets))
        self.load_user_preset_button.setEnabled((not running) and bool(self.user_presets))
        self.save_user_preset_button.setEnabled(not running)
        self.delete_user_preset_button.setEnabled((not running) and bool(self.user_presets))
        self.pro_toggle_button.setEnabled(not running)
        self.interface_combo.setEnabled(not running)
        self.transport_combo.setEnabled(not running)
        self.cancel_action.setEnabled(running)
        self.cancel_button.setEnabled(running)
        self.channel_combo.setEnabled((not running) and self.channel_combo.count() > 1)
        self.save_action.setEnabled((not running) and any(case.best_result for case in self.cases))
        self.save_button.setEnabled((not running) and self.active_case() is not None and self.active_case().best_result is not None)

    @Slot(int, str)
    def on_fit_started_case(self, index: int, label: str):
        self.statusBar().showMessage(f"Fitting {label}")
        if 0 <= index < len(self.cases):
            self.current_case_index = index
            self.populate_cases_table()
            self.set_current_case(index)

    @Slot(int, object, object)
    def on_fit_finished_case(self, index: int, results, best_result):
        if not (0 <= index < len(self.cases)):
            return
        case = self.cases[index]
        case.results = results
        case.best_result = best_result
        case.error_message = ""
        self.populate_cases_table()
        if index == self.current_case_index:
            self.set_current_case(index)

    @Slot(int, str)
    def on_fit_failed_case(self, index: int, error_message: str):
        if not (0 <= index < len(self.cases)):
            return
        case = self.cases[index]
        case.results = []
        case.best_result = None
        case.error_message = error_message
        self.populate_cases_table()
        if index == self.current_case_index:
            self.set_current_case(index)

    @Slot(int, int)
    def on_fit_progress(self, completed: int, total: int):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(completed)

    @Slot(bool)
    def on_fit_finished(self, cancelled: bool):
        if cancelled:
            self.log("Fit cancelled.")
            self.statusBar().showMessage("Fit cancelled")
        else:
            self.log("Fit complete.")
            self.statusBar().showMessage("Fit complete")
        self.populate_cases_table()
        if self.cases:
            self.set_current_case(max(0, self.current_case_index))
        self.set_fit_controls_running(False)

    @Slot()
    def clear_fit_thread(self):
        self.fit_thread = None
        self.fit_worker = None

    def closeEvent(self, event):
        if self.fit_thread is None:
            event.accept()
            return

        if self.close_after_fit:
            event.ignore()
            return

        answer = QMessageBox.question(
            self,
            self.t("Fit is running"),
            self.t("A fit is still running. Cancel it and close when the current fit step finishes?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            event.ignore()
            return

        self.close_after_fit = True
        self.setEnabled(False)
        self.cancel_fit()
        self.fit_thread.finished.connect(self.close)
        event.ignore()

    def populate_cases_table(self):
        self._updating_cases_table = True
        self.cases_table.setRowCount(len(self.cases))
        for row, case in enumerate(self.cases):
            if case.best_result:
                status = "FIT"
                best_circuit = case.best_result.circuit_string
                fit_error = f"{case.best_result.mean_fit_error:.3f}"
                bic = f"{case.best_result.bic:.2f}"
                flags = ", ".join(case.best_result.flags) if case.best_result.flags else "-"
            elif case.error_message:
                status = "ERROR"
                best_circuit = case.error_message
                fit_error = ""
                bic = ""
                flags = case.error_message
            else:
                status = "LOADED"
                best_circuit = ""
                fit_error = ""
                bic = ""
                flags = ""

            kk_result = case.kk_result
            kk_status = kk_result.status if kk_result else "-"
            values = [
                status,
                os.path.basename(case.file_path),
                case.source_format,
                str(len(case.frequencies)),
                kk_status,
                best_circuit,
                fit_error,
                bic,
                flags,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if case.best_result:
                    item.setBackground(QColor("#e7f3ff"))
                    item.setForeground(QColor("#111827"))
                if col == 4 and kk_result:
                    if kk_result.status == "PASS":
                        item.setBackground(QColor("#dff3e4"))
                        item.setForeground(QColor("#102015"))
                    elif kk_result.status == "WARN":
                        item.setBackground(QColor("#fff4cc"))
                        item.setForeground(QColor("#332400"))
                    else:
                        item.setBackground(QColor("#fde2e2"))
                        item.setForeground(QColor("#3b0a0a"))
                self.cases_table.setItem(row, col, item)

        if 0 <= self.current_case_index < len(self.cases):
            self.cases_table.selectRow(self.current_case_index)
        self._updating_cases_table = False

    def on_case_changed(self, current_row, _current_col, _previous_row, _previous_col):
        if self._updating_cases_table or current_row < 0:
            return
        self.set_current_case(current_row)

    def set_current_case(self, index):
        if not (0 <= index < len(self.cases)):
            return

        self.current_case_index = index
        case = self.cases[index]
        self.file_label.setText(os.path.basename(case.file_path))
        self.scale_label.setText(
            f"Selected: {index + 1} / {len(self.cases)}\n"
            f"Format: {case.source_format or 'unknown'}\n"
            f"Points: {len(case.frequencies)}\n"
            f"KK: {case.kk_result.status if case.kk_result else '-'}\n"
            f"R0 ~= {case.scale.r0:.2f} Ohm\n"
            f"R_transfer ~= {case.scale.r_transfer:.2f} Ohm\n"
            f"C ~= {case.scale.capacitance:.2e} F"
        )
        self.populate_results_table()
        self.populate_params_table()
        self.populate_parser_tab()
        self.populate_kk_tab()
        self.populate_reliable_decision_tab()
        self.populate_channel_combo(case)
        self.plot_data()
        has_result = case.best_result is not None
        if self.fit_thread is None:
            self.save_action.setEnabled(has_result)
            self.save_button.setEnabled(has_result)
        else:
            self.save_action.setEnabled(False)
            self.save_button.setEnabled(False)
            self.channel_combo.setEnabled(False)

    def populate_channel_combo(self, case):
        channels = case.available_channels or [case.selected_channel or "Z"]
        self._updating_channel_combo = True
        self.channel_combo.clear()
        self.channel_combo.addItems(channels)
        selected = case.selected_channel or channels[0]
        index = self.channel_combo.findText(selected)
        self.channel_combo.setCurrentIndex(index if index >= 0 else 0)
        self.channel_combo.setEnabled(len(channels) > 1)
        self._updating_channel_combo = False

    def on_channel_changed(self, channel):
        if self._updating_channel_combo or not channel:
            return

        case = self.active_case()
        if not case or channel == case.selected_channel:
            return

        try:
            dataset = load_eis_file(case.file_path, channel=channel)
            scale = estimate_dataset_scale(dataset.frequencies, dataset.z)
            kk_result = lin_kk_check(dataset.frequencies, dataset.z)
        except Exception as exc:
            QMessageBox.critical(self, self.t("Channel error"), str(exc))
            self.populate_channel_combo(case)
            return

        case.frequencies = dataset.frequencies
        case.z_experimental = dataset.z
        case.scale = scale
        case.source_format = dataset.source_format
        case.columns = dataset.columns
        case.metadata = dataset.metadata
        case.selected_channel = dataset.metadata.get("selected_channel", channel)
        case.available_channels = dataset.metadata.get("available_channels", [channel])
        case.kk_result = kk_result
        case.results = None
        case.best_result = None
        case.inference_decision = None
        case.error_message = ""
        self.log(f"Switched {os.path.basename(case.file_path)} to channel {case.selected_channel}")
        self.populate_cases_table()
        self.set_current_case(self.current_case_index)

    def populate_results_table(self):
        case = self.active_case()
        results = case.results if case and case.results else []
        best_result = case.best_result if case else None
        self.results_table.setRowCount(len(results))
        for row, result in enumerate(results):
            status = result.status
            fit_error = f"{result.mean_fit_error:.3f}" if result.success else ""
            bic = f"{result.bic:.2f}" if result.success else ""
            aic = f"{result.aic:.2f}" if result.success else ""
            n_params = str(result.n_params) if result.success else ""
            param_error = f"{result.max_param_error:.2f}" if result.success else ""
            flags = ", ".join(result.flags) if result.flags else result.error_message
            values = [status, result.circuit_string, fit_error, bic, aic, n_params, param_error, flags]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if best_result and result is best_result:
                    item.setBackground(QColor("#dff3e4"))
                    item.setForeground(QColor("#102015"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif result.success and result.status == "BAD":
                    item.setBackground(QColor("#fde2e2"))
                    item.setForeground(QColor("#3b0a0a"))
                elif result.success and result.status == "WARN":
                    item.setBackground(QColor("#fff4cc"))
                    item.setForeground(QColor("#332400"))
                self.results_table.setItem(row, col, item)

    def populate_parser_tab(self):
        case = self.active_case()
        if not case:
            self.parser_summary.setText("No dataset loaded.")
            self.columns_table.setRowCount(0)
            self.metadata_output.clear()
            return

        metadata = case.metadata or {}
        available_channels = case.available_channels or metadata.get("available_channels", [])
        self.parser_summary.setText(
            f"File: {case.file_path}\n"
            f"Format: {case.source_format}\n"
            f"Selected channel: {case.selected_channel}\n"
            f"Available channels: {', '.join(available_channels) if available_channels else '-'}\n"
            f"Frequency: {metadata.get('frequency_column', '-')}\n"
            f"Re: {metadata.get('real_column', '-')}\n"
            f"Im: {metadata.get('imaginary_column', '-')} ({metadata.get('imaginary_mode', '-')})"
        )
        columns = case.columns or []
        self.columns_table.setRowCount(len(columns))
        for row, column in enumerate(columns):
            self.columns_table.setItem(row, 0, QTableWidgetItem(str(column)))
        self.metadata_output.setPlainText(format_metadata(metadata))

    def populate_kk_tab(self):
        case = self.active_case()
        if not case:
            self.kk_summary.setText("No dataset loaded.")
            return

        kk = case.kk_result
        if not kk:
            self.kk_summary.setText("Kramers-Kronig check was not run.")
            return
        if not kk.success:
            self.kk_summary.setText(
                f"{os.path.basename(case.file_path)}\n"
                f"KK status: {kk.status}\n"
                f"Flags: {', '.join(kk.flags) if kk.flags else '-'}\n"
                f"Message: {kk.error_message}"
            )
            return

        self.kk_summary.setText(
            f"{os.path.basename(case.file_path)}\n"
            f"KK status: {kk.status} | RMSE: {kk.rmse_percent:.3f}% | "
            f"Max: {kk.max_error_percent:.3f}% | "
            f"mu: {kk.mu:.3f} | "
            f"RC terms: {kk.n_rc}\n"
            f"Flags: {', '.join(kk.flags) if kk.flags else '-'}"
        )

    def populate_params_table(self):
        case = self.active_case()
        if not case or not case.best_result or not case.best_result.model:
            self.best_label.setText("No successful fit.")
            self.params_table.setRowCount(0)
            return

        result = case.best_result
        self.best_label.setText(
            f"{os.path.basename(case.file_path)}\n"
            f"{result.circuit_string}\n"
            f"{circuit_to_readable(result.circuit_string)}\n"
            f"Mean fit error: {result.mean_fit_error:.3f}% | "
            f"BIC: {result.bic:.2f} | "
            f"Status: {result.status} | "
            f"Flags: {', '.join(result.flags) if result.flags else '-'}"
        )

        model = result.model
        names = parameter_names(result.circuit_string)
        self.params_table.setRowCount(len(names))
        for row, (name, value, confidence) in enumerate(zip(names, model.parameters_, model.conf_)):
            rel_error = (abs(confidence / value) * 100) if value != 0 and confidence is not None else np.inf
            values = [name, f"{value:.6e}", f"{confidence:.6e}", f"{rel_error:.2f}"]
            for col, cell_value in enumerate(values):
                self.params_table.setItem(row, col, QTableWidgetItem(cell_value))

    def populate_reliable_decision_tab(self):
        case = self.active_case()
        presentation = format_reliable_decision(
            case.inference_decision if case else None,
            language=self.language,
        )
        self.reliable_decision_headline.setText(presentation["headline"])
        self.reliable_decision_details.setPlainText(presentation["details"])
        colors = {
            "supported": ("#dff3e4", "#102015"),
            "refused": ("#fff4cc", "#332400"),
            "not_loaded": ("#eeeeee", "#333333"),
        }
        background, foreground = colors[presentation["status"]]
        self.reliable_decision_headline.setStyleSheet(
            f"padding: 10px; background: {background}; color: {foreground};"
        )

    def plot_data(self):
        self.plot_nyquist()
        self.plot_bode()
        self.plot_residuals()
        self.plot_kk()

    def plot_nyquist(self):
        case = self.active_case()
        ax = self.canvas.ax
        ax.clear()
        ax.set_xlabel("Re(Z) [Ohm]")
        ax.set_ylabel("-Im(Z) [Ohm]")
        ax.grid(True, linestyle="--", alpha=0.5)

        if case is not None:
            ax.plot(case.z_experimental.real, -case.z_experimental.imag, "o", color="royalblue", label="Experiment")

            if case.best_result and case.best_result.model:
                f_grid = np.logspace(np.log10(case.frequencies.min()), np.log10(case.frequencies.max()), 500)
                z_predicted = case.best_result.model.predict(f_grid)
                ax.plot(
                    z_predicted.real,
                    -z_predicted.imag,
                    "-",
                    color="crimson",
                    lw=2.5,
                    label=f"Fit: {case.best_result.circuit_string}",
                )
                ax.set_title(
                    f"{os.path.basename(case.file_path)} | "
                    f"{circuit_to_readable(case.best_result.circuit_string)} "
                    f"({case.best_result.mean_fit_error:.2f}%)"
                )
            else:
                ax.set_title(os.path.basename(case.file_path))

            ax.axis("equal")
            ax.legend()
        else:
            ax.set_title("Open an EIS file")

        self.canvas.draw()

    def plot_bode(self):
        case = self.active_case()
        ax_mag = self.bode_canvas.ax_magnitude
        ax_phase = self.bode_canvas.ax_phase
        ax_mag.clear()
        ax_phase.clear()

        ax_mag.set_ylabel("|Z| [Ohm]")
        ax_phase.set_ylabel("Phase(Z) [deg]")
        ax_phase.set_xlabel("Frequency [Hz]")
        ax_mag.grid(True, which="both", linestyle="--", alpha=0.35)
        ax_phase.grid(True, which="both", linestyle="--", alpha=0.35)

        if case is not None:
            order = np.argsort(case.frequencies)
            frequencies = case.frequencies[order]
            z_data = case.z_experimental[order]
            magnitude = np.abs(z_data)
            phase = np.angle(z_data, deg=True)

            ax_mag.semilogx(frequencies, magnitude, "o", color="royalblue", label="Experiment")
            ax_phase.semilogx(frequencies, phase, "o", color="royalblue", label="Experiment")

            if case.best_result and case.best_result.model:
                f_grid = np.logspace(np.log10(case.frequencies.min()), np.log10(case.frequencies.max()), 500)
                z_predicted = case.best_result.model.predict(f_grid)
                ax_mag.semilogx(f_grid, np.abs(z_predicted), "-", color="crimson", lw=2.2, label="Fit")
                ax_phase.semilogx(f_grid, np.angle(z_predicted, deg=True), "-", color="crimson", lw=2.2, label="Fit")
                ax_mag.set_title(
                    f"{os.path.basename(case.file_path)} | "
                    f"{circuit_to_readable(case.best_result.circuit_string)}"
                )
            else:
                ax_mag.set_title(os.path.basename(case.file_path))

            ax_mag.legend()
            ax_phase.legend()
        else:
            ax_mag.set_title("Open an EIS file")

        self.bode_canvas.draw()

    def plot_residuals(self):
        case = self.active_case()
        ax_complex = self.residual_canvas.ax_complex
        ax_relative = self.residual_canvas.ax_relative
        ax_complex.clear()
        ax_relative.clear()

        ax_complex.set_ylabel("Residual [Ohm]")
        ax_relative.set_ylabel("|Residual| / |Z| [%]")
        ax_relative.set_xlabel("Frequency [Hz]")
        ax_complex.grid(True, which="both", linestyle="--", alpha=0.35)
        ax_relative.grid(True, which="both", linestyle="--", alpha=0.35)

        if case is not None and case.best_result and case.best_result.model:
            order = np.argsort(case.frequencies)
            frequencies = case.frequencies[order]
            z_data = case.z_experimental[order]
            z_predicted = case.best_result.model.predict(frequencies)
            residual = z_data - z_predicted
            relative = np.abs(residual) / np.maximum(np.abs(z_data), 1e-30) * 100

            ax_complex.semilogx(frequencies, residual.real, "o-", color="darkgreen", label="Re residual")
            ax_complex.semilogx(frequencies, residual.imag, "o-", color="darkorange", label="Im residual")
            ax_relative.semilogx(frequencies, relative, "o-", color="crimson", label="Relative residual")
            ax_complex.axhline(0, color="black", lw=1.0, alpha=0.5)
            ax_complex.set_title(
                f"{os.path.basename(case.file_path)} | "
                f"{circuit_to_readable(case.best_result.circuit_string)}"
            )
            ax_complex.legend()
            ax_relative.legend()
        elif case is not None:
            ax_complex.set_title("Run fit to inspect residuals")
        else:
            ax_complex.set_title("Open an EIS file")

        self.residual_canvas.draw()

    def plot_kk(self):
        case = self.active_case()
        ax_nyquist = self.kk_canvas.ax_nyquist
        ax_error = self.kk_canvas.ax_error
        ax_nyquist.clear()
        ax_error.clear()

        ax_nyquist.set_xlabel("Re(Z) [Ohm]")
        ax_nyquist.set_ylabel("-Im(Z) [Ohm]")
        ax_error.set_ylabel("KK error [%]")
        ax_error.set_xlabel("Frequency [Hz]")
        ax_nyquist.grid(True, linestyle="--", alpha=0.35)
        ax_error.grid(True, which="both", linestyle="--", alpha=0.35)

        if case is not None and case.kk_result and case.kk_result.success:
            kk = case.kk_result
            ax_nyquist.plot(case.z_experimental.real, -case.z_experimental.imag, "o", color="royalblue", label="Experiment")
            ax_nyquist.plot(kk.z_fit.real, -kk.z_fit.imag, "-", color="darkgreen", lw=2.0, label="Lin-KK RC fit")
            ax_nyquist.axis("equal")
            ax_nyquist.legend()
            ax_nyquist.set_title(
                f"{os.path.basename(case.file_path)} | KK {kk.status} "
                f"(RMSE {kk.rmse_percent:.2f}%)"
            )

            ax_error.semilogx(kk.frequencies, kk.relative_error_percent, "o-", color="crimson", label="Relative error")
            ax_error.axhline(2.0, color="darkgreen", lw=1.0, alpha=0.55, linestyle="--")
            ax_error.axhline(5.0, color="darkred", lw=1.0, alpha=0.55, linestyle="--")
            ax_error.legend()
        elif case is not None and case.kk_result:
            ax_nyquist.set_title(f"KK check failed: {case.kk_result.error_message}")
        elif case is not None:
            ax_nyquist.set_title("Kramers-Kronig check was not run")
        else:
            ax_nyquist.set_title("Open an EIS file")

        self.kk_canvas.draw()

    def fitted_cases(self):
        return [case for case in self.cases if case.best_result]

    def write_csv(self, path, headers, rows):
        with open(path, "w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def write_xlsx(self, path):
        from openpyxl import Workbook

        sheets = [
            ("Summary", self.batch_summary_rows()),
            ("All Results", self.all_results_rows()),
            ("Best Parameters", self.best_parameter_rows()),
            ("Parser Metadata", self.parser_metadata_rows()),
            ("KK Check", self.kk_check_rows()),
        ]
        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        for sheet_name, rows in sheets:
            worksheet = workbook.create_sheet(sheet_name)
            if not rows:
                continue
            headers = list(rows[0].keys())
            worksheet.append(headers)
            for row in rows:
                worksheet.append([row.get(header, "") for header in headers])
            worksheet.freeze_panes = "A2"
            for column_cells in worksheet.columns:
                values = [str(cell.value) if cell.value is not None else "" for cell in column_cells]
                width = min(max(len(value) for value in values) + 2, 60)
                worksheet.column_dimensions[column_cells[0].column_letter].width = width

        workbook.save(path)

    def batch_summary_rows(self):
        rows = []
        for index, case in enumerate(self.cases, start=1):
            result = case.best_result
            rows.append(
                {
                    "case_index": index,
                    "file": case.file_path,
                    "file_name": os.path.basename(case.file_path),
                    "source_format": case.source_format,
                    "selected_channel": case.selected_channel,
                    "points": len(case.frequencies),
                    "kk_status": case.kk_result.status if case.kk_result else "",
                    "kk_rmse_percent": case.kk_result.rmse_percent if case.kk_result and case.kk_result.success else "",
                    "kk_max_error_percent": case.kk_result.max_error_percent if case.kk_result and case.kk_result.success else "",
                    "kk_mu": case.kk_result.mu if case.kk_result and case.kk_result.success else "",
                    "kk_flags": ", ".join(case.kk_result.flags) if case.kk_result and case.kk_result.flags else "",
                    "r0_guess_ohm": case.scale.r0,
                    "r_transfer_guess_ohm": case.scale.r_transfer,
                    "capacitance_guess_f": case.scale.capacitance,
                    "best_circuit": result.circuit_string if result else "",
                    "best_circuit_readable": circuit_to_readable(result.circuit_string) if result else "",
                    "fit_percent": result.mean_fit_error if result else "",
                    "max_param_error_percent": result.max_param_error if result else "",
                    "weighted_rss": result.rss_weighted if result else "",
                    "aic": result.aic if result else "",
                    "bic": result.bic if result else "",
                    "n_params": result.n_params if result else "",
                    "fit_elapsed_seconds": result.elapsed_seconds if result else "",
                    "fit_starts_attempted": result.starts_attempted if result else "",
                    "fit_starts_succeeded": result.starts_succeeded if result else "",
                    "fit_best_start_index": result.best_start_index if result else "",
                    "fit_status": result.status if result else ("ERROR" if case.error_message else "NOT_FIT"),
                    "flags": ", ".join(result.flags) if result and result.flags else case.error_message,
                }
            )
        return rows

    def all_results_rows(self):
        rows = []
        for case_index, case in enumerate(self.cases, start=1):
            for result_index, result in enumerate(case.results or [], start=1):
                rows.append(
                    {
                        "case_index": case_index,
                        "result_index": result_index,
                        "file": case.file_path,
                        "file_name": os.path.basename(case.file_path),
                        "selected_channel": case.selected_channel,
                        "circuit": result.circuit_string,
                        "is_best": result is case.best_result,
                        "success": result.success,
                        "status": result.status,
                        "fit_percent": result.mean_fit_error if result.success else "",
                        "max_param_error_percent": result.max_param_error if result.success else "",
                        "weighted_rss": result.rss_weighted if result.success else "",
                        "aic": result.aic if result.success else "",
                        "bic": result.bic if result.success else "",
                        "n_params": result.n_params if result.success else "",
                        "elapsed_seconds": result.elapsed_seconds,
                        "starts_attempted": result.starts_attempted,
                        "starts_succeeded": result.starts_succeeded,
                        "best_start_index": result.best_start_index,
                        "flags": ", ".join(result.flags) if result.flags else "",
                        "error_message": result.error_message,
                    }
                )
        return rows

    def best_parameter_rows(self):
        rows = []
        for case_index, case in enumerate(self.cases, start=1):
            result = case.best_result
            if not result or not result.model:
                continue
            for name, value, confidence in zip(parameter_names(result.circuit_string), result.model.parameters_, result.model.conf_):
                rel_error = (abs(confidence / value) * 100) if value != 0 and confidence is not None else np.inf
                rows.append(
                    {
                        "case_index": case_index,
                        "file": case.file_path,
                        "file_name": os.path.basename(case.file_path),
                        "selected_channel": case.selected_channel,
                        "circuit": result.circuit_string,
                        "parameter": name,
                        "value": value,
                        "confidence": confidence,
                        "relative_error_percent": rel_error,
                    }
                )
        return rows

    def kk_check_rows(self):
        rows = []
        for case_index, case in enumerate(self.cases, start=1):
            kk = case.kk_result
            rows.append(
                {
                    "case_index": case_index,
                    "file": case.file_path,
                    "file_name": os.path.basename(case.file_path),
                    "source_format": case.source_format,
                    "selected_channel": case.selected_channel,
                    "status": kk.status if kk else "",
                    "success": kk.success if kk else "",
                    "rmse_percent": kk.rmse_percent if kk and kk.success else "",
                    "max_error_percent": kk.max_error_percent if kk and kk.success else "",
                    "mu": kk.mu if kk and kk.success else "",
                    "n_rc": kk.n_rc if kk and kk.success else "",
                    "flags": ", ".join(kk.flags) if kk and kk.flags else "",
                    "error_message": kk.error_message if kk else "",
                }
            )
        return rows

    def parser_metadata_rows(self):
        rows = []
        for case_index, case in enumerate(self.cases, start=1):
            metadata = case.metadata or {}
            base = {
                "case_index": case_index,
                "file": case.file_path,
                "file_name": os.path.basename(case.file_path),
                "source_format": case.source_format,
                "selected_channel": case.selected_channel,
            }
            rows.append({**base, "key": "columns", "value": ", ".join(case.columns or [])})
            for key, value in metadata.items():
                if isinstance(value, (list, tuple)):
                    value = ", ".join(str(item) for item in value)
                rows.append({**base, "key": key, "value": value})
        return rows

    def export_results(self):
        if not self.cases:
            return
        if not self.fitted_cases():
            QMessageBox.information(self, self.t("Nothing to export"), self.t("Run a fit before exporting results."))
            return

        dialog = ExportDialog(self, language=self.language)
        if dialog.exec() != QDialog.Accepted:
            return
        exports = dialog.selected_exports()
        if not any(exports.values()):
            QMessageBox.information(self, self.t("Nothing selected"), self.t("Select at least one export output."))
            return

        save_base, _ = QFileDialog.getSaveFileName(self, self.t("Export base name"), "", self.t("All files (*.*)"))
        if not save_base:
            return

        saved_paths = []
        try:
            if exports["summary"]:
                path = save_base + "_summary.csv"
                rows = self.batch_summary_rows()
                self.write_csv(path, list(rows[0].keys()) if rows else [], rows)
                saved_paths.append(path)

            if exports["all_results"]:
                path = save_base + "_all_results.csv"
                rows = self.all_results_rows()
                headers = [
                    "case_index",
                    "result_index",
                    "file",
                    "file_name",
                    "selected_channel",
                    "circuit",
                    "is_best",
                    "success",
                    "status",
                    "fit_percent",
                    "max_param_error_percent",
                    "weighted_rss",
                    "aic",
                    "bic",
                    "n_params",
                    "elapsed_seconds",
                    "flags",
                    "error_message",
                ]
                self.write_csv(path, headers, rows)
                saved_paths.append(path)

            if exports["best_params"]:
                path = save_base + "_best_parameters.csv"
                rows = self.best_parameter_rows()
                headers = [
                    "case_index",
                    "file",
                    "file_name",
                    "selected_channel",
                    "circuit",
                    "parameter",
                    "value",
                    "confidence",
                    "relative_error_percent",
                ]
                self.write_csv(path, headers, rows)
                saved_paths.append(path)

            if exports["parser"]:
                path = save_base + "_parser_metadata.csv"
                rows = self.parser_metadata_rows()
                headers = ["case_index", "file", "file_name", "source_format", "selected_channel", "key", "value"]
                self.write_csv(path, headers, rows)
                saved_paths.append(path)

            if exports["kk"]:
                path = save_base + "_kk_check.csv"
                rows = self.kk_check_rows()
                headers = [
                    "case_index",
                    "file",
                    "file_name",
                    "source_format",
                    "selected_channel",
                    "status",
                    "success",
                    "rmse_percent",
                    "max_error_percent",
                    "mu",
                    "n_rc",
                    "flags",
                    "error_message",
                ]
                self.write_csv(path, headers, rows)
                saved_paths.append(path)

            if exports["excel"]:
                path = save_base + "_workbook.xlsx"
                self.write_xlsx(path)
                saved_paths.append(path)

            if exports["selected_report"]:
                saved_paths.extend(self.export_selected_report(save_base))
        except Exception as exc:
            QMessageBox.critical(self, self.t("Export error"), str(exc))
            return

        for path in saved_paths:
            self.log(f"Saved {path}")

    def save_results(self):
        self.export_results()

    def export_selected_report(self, save_base):
        case = self.active_case()
        if not case or not case.best_result:
            return []

        report_path = save_base + "_report.txt"
        plot_path = save_base + "_nyquist.png"
        bode_path = save_base + "_bode.png"
        residual_path = save_base + "_residuals.png"
        kk_path = save_base + "_kk_check.png"

        with open(report_path, "w", encoding="utf-8") as file:
            file.write("EIS equivalent-circuit report\n")
            file.write(f"Source file: {case.file_path}\n")
            file.write(f"Source format: {case.source_format}\n")
            file.write(f"Selected channel: {case.selected_channel}\n")
            if case.metadata:
                file.write(f"Parser metadata: {case.metadata}\n")
            if case.kk_result:
                kk = case.kk_result
                file.write(
                    "Kramers-Kronig check: "
                    f"{kk.status}, RMSE={kk.rmse_percent:.3f}%, "
                    f"max={kk.max_error_percent:.3f}%, "
                    f"mu={kk.mu:.3f}, "
                    f"flags={', '.join(kk.flags) if kk.flags else '-'}\n"
                )
            file.write(f"Circuit: {case.best_result.circuit_string}\n")
            file.write(f"Model: ${circuit_to_latex(case.best_result.circuit_string)}$\n")
            file.write(f"Mean fit error: {case.best_result.mean_fit_error:.3f}%\n")
            file.write(f"Max parameter error: {case.best_result.max_param_error:.2f}%\n\n")
            file.write(f"Weighted RSS: {case.best_result.rss_weighted:.6e}\n")
            file.write(f"AIC: {case.best_result.aic:.6f}\n")
            file.write(f"BIC: {case.best_result.bic:.6f}\n")
            file.write(f"Status: {case.best_result.status}\n")
            file.write(f"Fit time: {case.best_result.elapsed_seconds:.3f} s\n")
            file.write(f"Flags: {', '.join(case.best_result.flags) if case.best_result.flags else '-'}\n\n")
            file.write("All circuit attempts:\n")
            for result in case.results or []:
                if result.success:
                    file.write(
                        f"  [{result.status}] {result.circuit_string}: "
                        f"fit={result.mean_fit_error:.3f}%, "
                        f"BIC={result.bic:.3f}, "
                        f"AIC={result.aic:.3f}, "
                        f"param={result.max_param_error:.2f}%, "
                        f"time={result.elapsed_seconds:.3f}s, "
                        f"flags={', '.join(result.flags) if result.flags else '-'}\n"
                    )
                else:
                    file.write(
                        f"  [{result.status}] {result.circuit_string}: "
                        f"time={result.elapsed_seconds:.3f}s, {result.error_message}\n"
                    )

            file.write("\nBest parameters:\n")
            model = case.best_result.model
            for name, value, confidence in zip(parameter_names(case.best_result.circuit_string), model.parameters_, model.conf_):
                rel_error = (abs(confidence / value) * 100) if value != 0 and confidence is not None else np.inf
                file.write(f"  {name:<12} = {value:.6e} +/- {confidence:.6e} ({rel_error:.2f}%)\n")

        self.canvas.figure.savefig(plot_path, dpi=200, bbox_inches="tight")
        self.bode_canvas.figure.savefig(bode_path, dpi=200, bbox_inches="tight")
        self.residual_canvas.figure.savefig(residual_path, dpi=200, bbox_inches="tight")
        self.kk_canvas.figure.savefig(kk_path, dpi=200, bbox_inches="tight")
        return [report_path, plot_path, bode_path, residual_path, kk_path]


def main():
    app = QApplication(sys.argv)
    window = EisQtApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
