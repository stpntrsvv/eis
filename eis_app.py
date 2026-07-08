import os
import re
import warnings
import numpy as np
import customtkinter as ctk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt

from impedance.models.circuits import CustomCircuit
from eis_utils import load_any_eis_file, estimate_dataset_scale

warnings.filterwarnings('ignore')

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class EisApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EIS Universal Solver & Selector")
        self.geometry("1200x800")

        self.file_path = None
        self.best_circuit = None

        self.universal_circuits = [
            # Базовый пул (без индуктивности)
            'R0-p(R1,C1)', 'R0-p(R1,CPE0)',
            'R0-p(R1,CPE0)-W0', 'R0-p(R1,CPE0)-Wo0', 'R0-p(R1,CPE0)-Ws0',
            'R0-p(R1-W0,CPE0)', 'R0-p(R1-Wo0,CPE0)', 'R0-p(R1-Ws0,CPE0)',
            'R0-p(R1,CPE0)-p(R2,CPE1)',
            'R0-p(R1-p(R2,CPE1),CPE0)',

            # Индуктивный пул (на случай косяков кабеля на ВЧ)
            'L0-R0-p(R1,CPE0)',
            'L0-R0-p(R1,CPE0)-p(R2,CPE1)',
            'L0-R0-p(R1-p(R2,CPE1),CPE0)'
        ]

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ctk.CTkFrame(self, width=350, corner_radius=10)
        self.left_panel.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.left_panel.grid_propagate(False)

        self.btn_open = ctk.CTkButton(self.left_panel, text="📂 Открыть файл данных", command=self.open_file,
                                      font=("Segoe UI", 14, "bold"))
        self.btn_open.pack(padx=20, pady=20, fill="x")

        self.lbl_status = ctk.CTkLabel(self.left_panel, text="Файл не выбран", text_color="gray", font=("Segoe UI", 12))
        self.lbl_status.pack(padx=20, pady=5)

        self.btn_run = ctk.CTkButton(self.left_panel, text="⚡ Запустить автоподбор", command=self.run_fit,
                                     state="disabled", fg_color="gray")
        self.btn_run.pack(padx=20, pady=10, fill="x")

        self.txt_output = ctk.CTkTextbox(self.left_panel, font=("Consolas", 12))
        self.txt_output.pack(padx=15, pady=15, fill="both", expand=True)

        self.btn_save = ctk.CTkButton(self.left_panel, text="💾 Сохранить отчет и график", command=self.save_results,
                                      state="disabled", fg_color="gray")
        self.btn_save.pack(padx=20, pady=15, fill="x")

        self.right_panel = ctk.CTkFrame(self, corner_radius=10)
        self.right_panel.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        self.fig, self.ax = plt.subplots(figsize=(7, 6))
        self.ax.grid(True, linestyle='--', alpha=0.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_panel)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(padx=15, pady=15, fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.right_panel)
        self.toolbar.update()
        self.canvas_widget.pack(padx=15, pady=15, fill="both", expand=True)

    def log(self, text):
        self.txt_output.insert("end", text + "\n")
        self.txt_output.see("end")
        self.update_idletasks()

    def open_file(self):
        file = ctk.filedialog.askopenfilename(filetypes=[("Text files", "*.txt;*.csv;*.dat"), ("All files", "*.*")])
        if file:
            self.file_path = file
            self.lbl_status.configure(text=os.path.basename(file), text_color="#1f538d")
            self.btn_run.configure(state="normal", fg_color="#1f6aa5")
            self.txt_output.delete("0.0", "end")

            try:
                self.frequencies, self.Z_experimental = load_any_eis_file(self.file_path)
                self.R0_est, self.R1_est, self.C_est = estimate_dataset_scale(self.frequencies, self.Z_experimental)
                self.plot_data(only_experimental=True)
            except Exception as e:
                self.log(f"Ошибка чтения: {str(e)}")

    def build_bounds_and_guess(self, circuit_string):
        clean_str = re.sub(r'[p()\s,]', '-', circuit_string)
        elements = [e for e in clean_str.split('-') if e]
        low_b, high_b, initial_guess = [], [], []
        r_idx, cpe_idx, c_idx, w_idx = 0, 0, 0, 0

        for el in elements:
            el_type = re.match(r'([a-zA-Z]+)', el).group(1)
            if el_type == 'R':
                r_val = self.R0_est if r_idx == 0 else self.R1_est / max(1, r_idx)
                initial_guess.append(r_val)
                low_b.append(1e-3);
                high_b.append(1e8)
                r_idx += 1
            elif el_type == 'CPE':
                q_val = self.C_est * (10 ** cpe_idx)
                initial_guess.extend([q_val, 0.75])
                low_b.extend([1e-10, 0.501])
                high_b.extend([10.0, 1.0])
                cpe_idx += 1
            elif el_type == 'C':
                initial_guess.append(self.C_est)
                low_b.append(1e-10);
                high_b.append(10.0)
                c_idx += 1
            elif el_type in ['Wo', 'Ws']:
                initial_guess.extend([self.R1_est * 1.5, 5.0])
                low_b.extend([1e-2, 1e-3]);
                high_b.extend([1e7, 1e5])
                w_idx += 1
            elif el_type == 'W':
                initial_guess.append(self.R1_est * 0.5)
                low_b.append(1e-2);
                high_b.append(1e7)
                w_idx += 1
        return low_b, high_b, initial_guess

    def run_fit(self):
        if not self.file_path:
            return

        self.txt_output.delete("0.0", "end")
        results = []

        for circuit_str in self.universal_circuits:
            try:
                low_b, high_b, guess = self.build_bounds_and_guess(circuit_str)
                safe_guess = np.clip(guess, np.array(low_b) + 1e-4, np.array(high_b) - 1e-4).tolist()

                circuit = CustomCircuit(circuit_str, initial_guess=safe_guess)
                circuit.fit(self.frequencies, self.Z_experimental, bounds=(low_b, high_b), weight_by_modulus=True)

                Z_pred = circuit.predict(self.frequencies)
                mean_fit_error = np.mean(np.abs(self.Z_experimental - Z_pred) / np.abs(self.Z_experimental)) * 100

                param_errors = []
                for p, conf in zip(circuit.parameters_, circuit.conf_):
                    if p != 0 and conf is not None:
                        param_errors.append(abs(conf / p) * 100)
                    else:
                        param_errors.append(np.inf)
                max_param_error = np.max(param_errors) if param_errors else np.inf

                results.append({
                    'circuit_string': circuit_str,
                    'model': circuit,
                    'mean_fit_error': mean_fit_error,
                    'max_param_error': max_param_error
                })
            except:
                pass

        if not results:
            self.log("Ошибка оптимизации.")
            return

        valid_circuits = [r for r in results if r['max_param_error'] < 40.0]
        self.best_circuit = min(valid_circuits if valid_circuits else results, key=lambda x: x['mean_fit_error'])

        readable_circuit = self.best_circuit['circuit_string'].replace('p(', '(').replace(',', ' || ').replace('-',
                                                                                                               ' + ')

        self.log("Анализ спектра электрохимического импеданса")
        self.log(f"Эквивалентная схема: {self.best_circuit['circuit_string']}")
        self.log(f"Математическая модель: {readable_circuit}")
        self.log(f"Среднеквадратичная ошибка трека (Mean Fit Error): {self.best_circuit['mean_fit_error']:.3f}%")
        self.log(f"Максимальная относительная погрешность параметров: {self.best_circuit['max_param_error']:.2f}%")
        self.log("\nОптимизированные параметры элементов:")

        model = self.best_circuit['model']

        # Безопасное извлечение имен параметров напрямую из структуры модели
        clean_circuit_str = re.sub(r'[p()\s,]', '-', self.best_circuit['circuit_string'])
        elements = [e for e in clean_circuit_str.split('-') if e]

        # Разворачиваем элементы (например, CPE преобразуется в CPE_0 и CPE_1 для Y0 и alpha)
        param_names = []
        for el in elements:
            if el.startswith('CPE') or el.startswith('Wo') or el.startswith('Ws'):
                param_names.extend([f"{el}_0", f"{el}_1"])
            else:
                param_names.append(el)

        for name, value, conf in zip(param_names, model.parameters_, model.conf_):
            p_err = (abs(conf / value) * 100) if (value != 0 and conf is not None) else np.inf

            unit = "-"
            if name.startswith('R'):
                unit = "Ohm"
                subscript = "".join(["₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in name[1:] if d.isdigit()])
                el_label = f"R{subscript}"
            elif name.startswith('CPE'):
                if name.endswith('_0'):
                    unit = "Ohm^-1 * sec^α"
                    subscript = "".join(["₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in name[3:-2] if d.isdigit()])
                    el_label = f"Y₀,{subscript}"
                else:
                    unit = "-"
                    subscript = "".join(["₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in name[3:-2] if d.isdigit()])
                    el_label = f"α{subscript}"
            elif name.startswith('C'):
                unit = "F"
                subscript = "".join(["₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in name[1:] if d.isdigit()])
                el_label = f"C{subscript}"
            elif name.startswith('W'):
                unit = "Ohm"
                subscript = "".join(["₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in name[1:] if d.isdigit()])
                el_label = f"W{subscript}"
            elif name.startswith('L'):
                unit = "H"
                subscript = "".join(["₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in name[1:] if d.isdigit()])
                el_label = f"L{subscript}"
            else:
                el_label = name

            self.log(f"  {el_label:<15} = {value:.2e} ± {conf:.2e} ({p_err:.2f}%) [{unit}]")

        self.plot_data(only_experimental=False)
        self.btn_save.configure(state="normal", fg_color="#24a148")

    def save_results(self):
        if not self.best_circuit:
            return

        save_base = ctk.filedialog.asksaveasfilename(defaultextension="", filetypes=[("All Files", "*.*")])
        if save_base:
            latex_circuit = self.best_circuit['circuit_string'].replace('p(', '(').replace(',', ' \\parallel ').replace(
                '-', ' + ')

            with open(save_base + "_report.txt", "w", encoding="utf-8") as f:
                f.write("Анализ спектра электрохимического импеданса\n")
                f.write(f"Эквивалентная схема (строковая запись): {self.best_circuit['circuit_string']}\n")
                f.write(f"Математическая модель: ${latex_circuit}$\n")
                f.write(
                    f"Среднеквадратичная ошибка аппроксимации трека (Mean Fit Error): {self.best_circuit['mean_fit_error']:.3f}%\n")
                f.write(
                    f"Максимальная относительная погрешность определения параметров: {self.best_circuit['max_param_error']:.2f}%\n\n")
                f.write("Оптимизированные параметры элементов эквивалентной схемы:\n")

                clean_circuit_str = re.sub(r'[p()\s,]', '-', self.best_circuit['circuit_string'])
                elements = [e for e in clean_circuit_str.split('-') if e]

                param_names = []
                for el in elements:
                    if el.startswith('CPE') or el.startswith('Wo') or el.startswith('Ws'):
                        param_names.extend([f"{el}_0", f"{el}_1"])
                    else:
                        param_names.append(el)

                model = self.best_circuit['model']
                for name, value, conf in zip(param_names, model.parameters_, model.conf_):
                    p_err = (abs(conf / value) * 100) if (value != 0 and conf is not None) else np.inf

                    unit = "Ohm"
                    if name.startswith('R'):
                        el_label = f"R_{{{name[1:]}}}"
                    elif name.startswith('CPE'):
                        if name.endswith('_0'):
                            unit = "Ohm^-1 * sec^a"
                            el_label = f"Y_{{0,{name[3:-2]}}}"
                        else:
                            unit = "-"
                            el_label = f"alpha_{{{name[3:-2]}}}"
                    elif name.startswith('C'):
                        unit = "F"
                        el_label = f"C_{{{name[1:]}}}"
                    elif name.startswith('W'):
                        el_label = f"W_{{{name[1:]}}}"
                    else:
                        el_label = name

                    f.write(f"  ${el_label:<15}$ = {value:.2e} \\pm {conf:.2e} ({p_err:.2f}%) [{unit}]\n")

            self.fig.savefig(save_base + "_nyquist.png", dpi=200, bbox_inches='tight')
            self.log(f"\nДанные сохранены:\n-> {save_base}_report.txt\n-> {save_base}_nyquist.png")


    def plot_data(self, only_experimental=True):
        self.ax.clear()
        self.ax.plot(self.Z_experimental.real, -self.Z_experimental.imag, 'o', color='royalblue', label='Эксперимент')

        if not only_experimental and self.best_circuit:
            f_grid = np.logspace(np.log10(self.frequencies.min()), np.log10(self.frequencies.max()), 500)
            Z_pred = self.best_circuit['model'].predict(f_grid)

            # Подготовка строки названия для совместимости с рендером Matplotlib (без экранирования под проценты)
            title_circuit = self.best_circuit['circuit_string'].replace('p(', '(').replace(',', ' || ').replace('-',
                                                                                                                ' + ')
            self.ax.plot(Z_pred.real, -Z_pred.imag, '-', color='crimson', lw=2.5,
                         label=f"Аппроксимация: {self.best_circuit['circuit_string']}")
            self.ax.set_title(f"{title_circuit} (Ошибка: {self.best_circuit['mean_fit_error']:.2f}%)", fontweight='bold')
        else:
            self.ax.set_title(f"{os.path.basename(self.file_path)}", fontweight='bold')

        self.ax.set_xlabel('Re(Z) [Ohm]')
        self.ax.set_ylabel('-Im(Z) [Ohm]')
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.axis('equal')
        self.ax.legend()
        self.canvas.draw()


if __name__ == "__main__":
    app = EisApp()
    app.mainloop()