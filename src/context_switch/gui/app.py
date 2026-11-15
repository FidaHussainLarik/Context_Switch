import tkinter as tk
from tkinter import messagebox, ttk

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError:
    FigureCanvasTkAgg = None
    Figure = None

from context_switch.domain.exceptions import ValidationError
from context_switch.domain.models import Process, SimulationResult
from context_switch.generation.random_process_generator import (
    RandomGenerationConfig,
    RandomProcessGenerator,
)
from context_switch.metrics.calculator import MetricsSummary, calculate_metrics
from context_switch.scheduling.base import Scheduler
from context_switch.scheduling.fcfs import FCFSScheduler
from context_switch.scheduling.priority import (
    PreemptivePriorityScheduler,
    PriorityScheduler,
)
from context_switch.scheduling.round_robin import RoundRobinScheduler
from context_switch.scheduling.sjf import SJFScheduler
from context_switch.scheduling.srtn import SRTNScheduler
from context_switch.gui.performance import (
    PerformanceAnalysisView,
    PerformanceGraphsView,
)


class ContextSwitchApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Context Switch")
        self.root.geometry("1100x760")
        self.processes: list[Process] = []
        self.result: SimulationResult | None = None
        self.metrics: MetricsSummary | None = None
        self.random_generator = RandomProcessGenerator()
        self.preview_processes: list[Process] = []
        self.results_window: tk.Toplevel | None = None
        self._build_interface()

    def _build_interface(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew")
        simulation_tab = ttk.Frame(notebook)
        analysis_tab = ttk.Frame(notebook)
        graphs_tab = ttk.Frame(notebook)
        notebook.add(simulation_tab, text="Simulation")
        notebook.add(analysis_tab, text="Algorithm Comparison")
        notebook.add(graphs_tab, text="Performance Graphs")
        simulation_tab.columnconfigure(0, weight=1)
        simulation_tab.rowconfigure(1, weight=1)

        controls = ttk.LabelFrame(simulation_tab, text="Simulation")
        controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls.columnconfigure(7, weight=1)

        self.algorithm_var = tk.StringVar(value="FCFS")
        self.quantum_var = tk.StringVar(value="2")
        ttk.Label(controls, text="Algorithm").grid(row=0, column=0, padx=5, pady=5)
        algorithm_box = ttk.Combobox(
            controls,
            textvariable=self.algorithm_var,
            values=(
                "FCFS",
                "SJF",
                "Priority",
                "Priority (Preemptive)",
                "Round Robin",
                "SRTN",
            ),
            state="readonly",
            width=16,
        )
        algorithm_box.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(controls, text="Quantum").grid(row=0, column=2, padx=5, pady=5)
        ttk.Entry(controls, textvariable=self.quantum_var, width=8).grid(
            row=0, column=3, padx=5, pady=5
        )
        ttk.Button(controls, text="Run Simulation", command=self.run_simulation).grid(
            row=0, column=4, padx=5, pady=5
        )
        ttk.Button(
            controls,
            text="View Results",
            command=self._show_results_window,
        ).grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(controls, text="Clear All", command=self.clear_all).grid(
            row=0, column=6, padx=5, pady=5
        )

        content = ttk.Frame(simulation_tab)
        content.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        content.columnconfigure(1, weight=1)
        content.rowconfigure(1, weight=1)

        process_frame = ttk.LabelFrame(content, text="Processes")
        process_frame.grid(row=0, column=0, rowspan=2, padx=(0, 10), sticky="ns")
        self._build_input_controls(process_frame)

        table_frame = ttk.Frame(content)
        table_frame.grid(row=0, column=1, sticky="ew")
        table_frame.columnconfigure(0, weight=1)
        self.process_table = ttk.Treeview(
            table_frame,
            columns=(
                "id",
                "arrival",
                "burst",
                "priority",
                "completion",
                "turnaround",
                "waiting",
                "weighted",
            ),
            show="headings",
            height=8,
        )
        for column, heading in (
            ("id", "ID"),
            ("arrival", "Arrival"),
            ("burst", "Burst"),
            ("priority", "Priority"),
            ("completion", "Completion Time (CT)"),
            ("turnaround", "Turnaround Time (TAT)"),
            ("waiting", "Waiting Time (WT)"),
            ("weighted", "Weighted Turnaround Time (WTT)"),
        ):
            self.process_table.heading(column, text=heading)
            self.process_table.column(
                column,
                width=85 if column in {"id", "arrival", "burst", "priority"} else 125,
                anchor="center",
            )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.process_table.xview,
        )
        self.process_table.configure(xscrollcommand=horizontal_scrollbar.set)
        self.process_table.grid(row=0, column=0, sticky="ew")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        ttk.Button(content, text="Remove Selected", command=self.remove_selected).grid(
            row=0, column=2, padx=(10, 0), sticky="n"
        )

        self._build_results(content)
        self.performance_view = PerformanceAnalysisView(
            analysis_tab,
            process_provider=lambda: list(self.processes),
            quantum_provider=lambda: self._parse_int(self.quantum_var.get(), "Quantum"),
        )
        self.graphs_view = PerformanceGraphsView(
            graphs_tab,
            process_provider=lambda: list(self.processes),
            quantum_provider=lambda: self._parse_int(self.quantum_var.get(), "Quantum"),
        )

    def _build_input_controls(self, parent: ttk.LabelFrame) -> None:
        self.input_mode_var = tk.StringVar(value="Manual Input")
        ttk.Label(parent, text="Input mode").grid(
            row=0, column=0, padx=8, pady=(8, 3), sticky="w"
        )
        mode_box = ttk.Combobox(
            parent,
            textvariable=self.input_mode_var,
            values=("Manual Input", "Random Generation"),
            state="readonly",
            width=14,
        )
        mode_box.grid(row=0, column=1, padx=8, pady=(8, 3))
        mode_box.bind("<<ComboboxSelected>>", self._change_input_mode)

        self.manual_input_frame = ttk.Frame(parent)
        self.manual_input_frame.grid(row=1, column=0, columnspan=2)
        self._build_process_form(self.manual_input_frame)

        self.random_input_frame = ttk.Frame(parent)
        self._build_random_form(self.random_input_frame)

    def _build_process_form(self, parent: ttk.Frame) -> None:
        self.process_id_var = tk.StringVar()
        self.arrival_var = tk.StringVar()
        self.burst_var = tk.StringVar()
        self.priority_var = tk.StringVar()
        fields = (
            ("Process ID", self.process_id_var),
            ("Arrival time", self.arrival_var),
            ("Burst time", self.burst_var),
            ("Priority", self.priority_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row, column=0, padx=8, pady=5, sticky="w")
            ttk.Entry(parent, textvariable=variable, width=14).grid(
                row=row, column=1, padx=8, pady=5
            )
        ttk.Button(parent, text="Add Process", command=self.add_process).grid(
            row=len(fields), column=0, columnspan=2, padx=8, pady=8
        )

    def _build_random_form(self, parent: ttk.Frame) -> None:
        self.random_count_var = tk.StringVar(value="5")
        self.random_arrival_min_var = tk.StringVar(value="0")
        self.random_arrival_max_var = tk.StringVar(value="10")
        self.random_burst_min_var = tk.StringVar(value="1")
        self.random_burst_max_var = tk.StringVar(value="10")
        self.random_priority_min_var = tk.StringVar(value="1")
        self.random_priority_max_var = tk.StringVar(value="5")
        self.random_seed_var = tk.StringVar()
        fields = (
            ("Number of processes", self.random_count_var),
            ("Arrival minimum", self.random_arrival_min_var),
            ("Arrival maximum", self.random_arrival_max_var),
            ("Burst minimum", self.random_burst_min_var),
            ("Burst maximum", self.random_burst_max_var),
            ("Priority minimum", self.random_priority_min_var),
            ("Priority maximum", self.random_priority_max_var),
            ("Seed (optional)", self.random_seed_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(parent, text=label).grid(
                row=row, column=0, padx=8, pady=3, sticky="w"
            )
            ttk.Entry(parent, textvariable=variable, width=14).grid(
                row=row, column=1, padx=8, pady=3
            )
        ttk.Button(
            parent,
            text="Generate Processes",
            command=self.generate_processes,
        ).grid(row=len(fields), column=0, columnspan=2, padx=8, pady=8)

    def _change_input_mode(self, _event: tk.Event) -> None:
        if self.input_mode_var.get() == "Random Generation":
            self.manual_input_frame.grid_remove()
            self.random_input_frame.grid(row=1, column=0, columnspan=2)
        else:
            self.random_input_frame.grid_remove()
            self.manual_input_frame.grid(row=1, column=0, columnspan=2)

    def generate_processes(self) -> None:
        try:
            config = self._random_generation_config()
            self.preview_processes = self.random_generator.generate(
                config,
                existing_ids=(process.process_id for process in self.processes),
            )
        except ValidationError as error:
            messagebox.showerror("Random generation error", str(error))
            return

        self._show_preview()

    def _random_generation_config(self) -> RandomGenerationConfig:
        seed_text = self.random_seed_var.get().strip()
        return RandomGenerationConfig(
            process_count=self._parse_int(
                self.random_count_var.get(), "Number of processes"
            ),
            arrival_min=self._parse_int(
                self.random_arrival_min_var.get(), "Minimum arrival time"
            ),
            arrival_max=self._parse_int(
                self.random_arrival_max_var.get(), "Maximum arrival time"
            ),
            burst_min=self._parse_int(
                self.random_burst_min_var.get(), "Minimum burst time"
            ),
            burst_max=self._parse_int(
                self.random_burst_max_var.get(), "Maximum burst time"
            ),
            priority_min=self._parse_int(
                self.random_priority_min_var.get(), "Minimum priority"
            ),
            priority_max=self._parse_int(
                self.random_priority_max_var.get(), "Maximum priority"
            ),
            seed=self._parse_int(seed_text, "Seed") if seed_text else None,
        )

    def _show_preview(self) -> None:
        existing_window = getattr(self, "preview_window", None)
        if existing_window is not None and existing_window.winfo_exists():
            existing_window.destroy()

        window = tk.Toplevel(self.root)
        self.preview_window = window
        window.title("Generated Process Preview")
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        content = ttk.Frame(window, padding=10)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        preview_table = ttk.Treeview(
            content,
            columns=("id", "arrival", "burst", "priority"),
            show="headings",
            selectmode="browse",
            height=8,
        )
        for column, heading in (
            ("id", "ID"),
            ("arrival", "Arrival"),
            ("burst", "Burst"),
            ("priority", "Priority"),
        ):
            preview_table.heading(column, text=heading)
            preview_table.column(column, width=110, anchor="center")
        preview_table.grid(row=0, column=0, columnspan=2, sticky="nsew")
        preview_table.bind(
            "<<TreeviewSelect>>",
            lambda _event: self._load_preview_selection(
                preview_table, preview_id_var, preview_arrival_var,
                preview_burst_var, preview_priority_var
            ),
        )

        edit_frame = ttk.LabelFrame(content, text="Edit selected process")
        edit_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=(10, 0), sticky="ew")
        preview_id_var = tk.StringVar()
        preview_arrival_var = tk.StringVar()
        preview_burst_var = tk.StringVar()
        preview_priority_var = tk.StringVar()
        fields = (
            ("ID", preview_id_var),
            ("Arrival", preview_arrival_var),
            ("Burst", preview_burst_var),
            ("Priority", preview_priority_var),
        )
        for column, (label, variable) in enumerate(fields):
            ttk.Label(edit_frame, text=label).grid(
                row=0, column=column * 2, padx=(6, 2), pady=6
            )
            ttk.Entry(edit_frame, textvariable=variable, width=10).grid(
                row=0, column=column * 2 + 1, padx=(0, 6), pady=6
            )

        buttons = ttk.Frame(content)
        buttons.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        ttk.Button(
            buttons,
            text="Update Selected",
            command=lambda: self._update_preview_selection(
                preview_table,
                preview_id_var,
                preview_arrival_var,
                preview_burst_var,
                preview_priority_var,
            ),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Remove Selected",
            command=lambda: self._remove_preview_selection(preview_table),
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons,
            text="Regenerate",
            command=self.generate_processes,
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons,
            text="Add to Process Table",
            command=lambda: self._add_preview_to_table(window),
        ).pack(side="right", padx=(6, 0))

        self.preview_table = preview_table
        self._refresh_preview_table()
        window.grab_set()

    def _refresh_preview_table(self) -> None:
        if not hasattr(self, "preview_table"):
            return
        for item in self.preview_table.get_children():
            self.preview_table.delete(item)
        for process in self.preview_processes:
            self.preview_table.insert("", "end", values=self._input_values(process)[:4])

    def _load_preview_selection(
        self,
        table: ttk.Treeview,
        id_var: tk.StringVar,
        arrival_var: tk.StringVar,
        burst_var: tk.StringVar,
        priority_var: tk.StringVar,
    ) -> None:
        selected = table.selection()
        if not selected:
            return
        values = table.item(selected[0])["values"]
        id_var.set(str(values[0]))
        arrival_var.set(str(values[1]))
        burst_var.set(str(values[2]))
        priority_var.set(str(values[3]))

    def _update_preview_selection(
        self,
        table: ttk.Treeview,
        id_var: tk.StringVar,
        arrival_var: tk.StringVar,
        burst_var: tk.StringVar,
        priority_var: tk.StringVar,
    ) -> None:
        selected = table.selection()
        if not selected:
            messagebox.showerror("Preview", "Select a generated process to update.")
            return
        index = table.index(selected[0])
        try:
            updated = Process(
                id_var.get(),
                self._parse_int(arrival_var.get(), "Arrival time"),
                self._parse_int(burst_var.get(), "Burst time"),
                self._parse_int(priority_var.get(), "Priority"),
            )
            if any(
                process.process_id == updated.process_id
                for position, process in enumerate(self.preview_processes)
                if position != index
            ) or any(
                process.process_id == updated.process_id for process in self.processes
            ):
                raise ValidationError("Process IDs must be unique.")
        except ValidationError as error:
            messagebox.showerror("Invalid generated process", str(error))
            return

        self.preview_processes[index] = updated
        self._refresh_preview_table()
        table.selection_set(table.get_children()[index])

    def _remove_preview_selection(self, table: ttk.Treeview) -> None:
        selected = table.selection()
        if not selected:
            messagebox.showerror("Preview", "Select a generated process to remove.")
            return
        del self.preview_processes[table.index(selected[0])]
        self._refresh_preview_table()

    def _add_preview_to_table(self, window: tk.Toplevel) -> None:
        if not self.preview_processes:
            messagebox.showerror("Preview", "Generate at least one process first.")
            return
        existing_ids = {process.process_id for process in self.processes}
        if any(process.process_id in existing_ids for process in self.preview_processes):
            messagebox.showerror("Preview", "Process IDs must be unique.")
            return

        self._clear_simulation_result()
        for process in self.preview_processes:
            self.processes.append(process)
            self.process_table.insert("", "end", values=self._input_values(process))
        self.preview_processes = []
        window.grab_release()
        window.destroy()
        self._refresh_analysis_views()

    def _build_results(self, parent: ttk.Frame) -> None:
        results = ttk.LabelFrame(parent, text="Results")
        results.grid(row=1, column=1, columnspan=2, pady=(10, 0), sticky="nsew")
        parent.rowconfigure(1, weight=1)
        results.columnconfigure(0, weight=1)
        results.rowconfigure(1, weight=1)

        self.metrics_label = ttk.Label(results, text="Run a simulation to view metrics.")
        self.metrics_label.grid(row=0, column=0, padx=8, pady=8, sticky="w")
        if FigureCanvasTkAgg is not None and Figure is not None:
            self.figure = Figure(figsize=(8, 3.2), dpi=100)
            self.chart = FigureCanvasTkAgg(self.figure, master=results)
            self.chart.get_tk_widget().grid(
                row=1, column=0, padx=8, pady=8, sticky="nsew"
            )
        else:
            self.figure = None
            self.chart = tk.Canvas(results, height=220, background="white")
            self.chart.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")

    def add_process(self) -> None:
        try:
            process = Process(
                self.process_id_var.get(),
                self._parse_int(self.arrival_var.get(), "Arrival time"),
                self._parse_int(self.burst_var.get(), "Burst time"),
                self._parse_int(self.priority_var.get(), "Priority"),
            )
            if any(existing.process_id == process.process_id for existing in self.processes):
                raise ValidationError("Process IDs must be unique.")
        except ValidationError as error:
            messagebox.showerror("Invalid process", str(error))
            return

        self._clear_simulation_result()
        self.processes.append(process)
        self.process_table.insert(
            "",
            "end",
            values=self._input_values(process),
        )
        for variable in (
            self.process_id_var,
            self.arrival_var,
            self.burst_var,
            self.priority_var,
        ):
            variable.set("")
        self._refresh_analysis_views()

    def remove_selected(self) -> None:
        selected = self.process_table.selection()
        if not selected:
            return
        self._clear_simulation_result()
        selected_ids = {
            str(self.process_table.item(item)["values"][0]) for item in selected
        }
        self.processes = [
            process for process in self.processes if process.process_id not in selected_ids
        ]
        for item in selected:
            self.process_table.delete(item)
        self._refresh_analysis_views()

    def clear_all(self) -> None:
        self._close_results_window()
        self.processes.clear()
        for item in self.process_table.get_children():
            self.process_table.delete(item)
        self.metrics_label.configure(text="Run a simulation to view metrics.")
        if self.figure is not None:
            self.figure.clear()
            self.chart.draw()
        else:
            self.chart.delete("all")
        self.result = None
        self.metrics = None
        self._refresh_analysis_views()

    def _clear_simulation_result(self) -> None:
        self.result = None
        self.metrics = None
        self._close_results_window()
        self.metrics_label.configure(text="Run a simulation to view metrics.")
        for item in self.process_table.get_children():
            values = list(self.process_table.item(item)["values"])
            self.process_table.item(item, values=values[:4] + [""] * 4)

    def run_simulation(self) -> None:
        try:
            scheduler = self._create_scheduler()
            self.result = scheduler.run(self.processes)
            self.metrics = calculate_metrics(self.result)
        except (ValidationError, ValueError) as error:
            messagebox.showerror("Simulation error", str(error))
            return

        self._display_result()
        self._refresh_analysis_views()
        self._show_results_window()

    def _refresh_analysis_views(self) -> None:
        self.performance_view.refresh()
        self.graphs_view.refresh()

    def _create_scheduler(self) -> Scheduler:
        schedulers = {
            "FCFS": FCFSScheduler,
            "SJF": SJFScheduler,
            "Priority": PriorityScheduler,
            "Priority (Preemptive)": PreemptivePriorityScheduler,
            "SRTN": SRTNScheduler,
        }
        if self.algorithm_var.get() == "Round Robin":
            return RoundRobinScheduler(
                self._parse_int(self.quantum_var.get(), "Quantum")
            )
        return schedulers[self.algorithm_var.get()]()

    def _display_result(self) -> None:
        if self.result is None or self.metrics is None:
            return
        self.metrics_label.configure(
            text=(
                f"Algorithm: {self.result.algorithm}   "
                f"Average waiting: {self.metrics.average_waiting_time:.2f}   "
                f"Average turnaround: {self.metrics.average_turnaround_time:.2f}   "
                f"Average weighted turnaround: "
                f"{self.metrics.average_weighted_turnaround_time:.2f}   "
                f"CPU utilization: {self.metrics.cpu_utilization:.2f}%"
            )
        )
        process_metrics = {
            process.process_id: process for process in self.result.processes
        }
        for item in self.process_table.get_children():
            process_id = str(self.process_table.item(item)["values"][0])
            process = process_metrics[process_id]
            self.process_table.item(item, values=self._result_values(process))
        self._draw_chart()

    def _show_results_window(self) -> None:
        if self.result is None or self.metrics is None:
            messagebox.showinfo("Simulation results", "Run a simulation first.")
            return

        self._close_results_window()
        window = tk.Toplevel(self.root)
        self.results_window = window
        window.title("Average Simulation Results")
        window.geometry("430x245")
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", self._close_results_window)
        content = ttk.Frame(window, padding=16)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text=f"{self.result.algorithm} Average Results",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 12))

        metrics = (
            ("Average Waiting Time", self.metrics.average_waiting_time),
            ("Average Turnaround Time", self.metrics.average_turnaround_time),
            (
                "Average Weighted Turnaround",
                self.metrics.average_weighted_turnaround_time,
            ),
            ("CPU Utilization", f"{self.metrics.cpu_utilization:.2f}%"),
        )
        for row, (label, value) in enumerate(metrics, start=1):
            ttk.Label(content, text=label).grid(
                row=row, column=0, padx=(0, 20), pady=4, sticky="w"
            )
            formatted_value = (
                value if isinstance(value, str) else f"{value:.2f}"
            )
            ttk.Label(content, text=formatted_value).grid(
                row=row, column=1, pady=4, sticky="e"
            )
        content.columnconfigure(1, weight=1)

    def _close_results_window(self) -> None:
        if self.results_window is not None:
            if self.results_window.winfo_exists():
                self.results_window.destroy()
            self.results_window = None

    @staticmethod
    def _result_values(process: Process) -> tuple[object, ...]:
        return (
            process.process_id,
            process.arrival_time,
            process.burst_time,
            process.priority,
            process.completion_time,
            process.turnaround_time,
            process.waiting_time,
            f"{process.weighted_turnaround_time:.2f}",
        )

    @staticmethod
    def _input_values(process: Process) -> tuple[object, ...]:
        return (
            process.process_id,
            process.arrival_time,
            process.burst_time,
            process.priority,
            "",
            "",
            "",
            "",
        )

    def _draw_chart(self) -> None:
        if self.result is None:
            return
        if self.figure is None:
            self._draw_fallback_chart()
            return
        self._draw_result_chart(self.figure, self.chart)

    def _draw_result_chart(self, figure, chart) -> None:
        if self.result is None:
            return
        figure.clear()
        axis = figure.add_subplot(111)
        colors: dict[str, str] = {}
        for index, segment in enumerate(self.result.timeline):
            label = segment.process_id or "Idle"
            color = colors.setdefault(
                label,
                "grey" if label == "Idle" else f"C{len(colors)}",
            )
            axis.barh(
                0,
                segment.end_time - segment.start_time,
                left=segment.start_time,
                color=color,
                edgecolor="black",
                height=0.5,
            )
            axis.text(
                (segment.start_time + segment.end_time) / 2,
                0,
                label,
                ha="center",
                va="center",
            )
            if index:
                axis.axvline(segment.start_time, color="gray", linewidth=0.5)
        axis.set_yticks([])
        axis.set_xlabel("Time")
        axis.set_title(f"{self.result.algorithm} Schedule")
        axis.grid(axis="x", linestyle=":", alpha=0.5)
        figure.tight_layout()
        chart.draw()

    def _draw_fallback_chart(self, chart=None) -> None:
        if self.result is None:
            return
        target = chart or self.chart
        target.delete("all")
        width = max(target.winfo_width(), 500)
        total_time = self.result.timeline[-1].end_time
        scale = (width - 40) / total_time if total_time else 1
        palette = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2"]
        colors: dict[str, str] = {}
        for segment in self.result.timeline:
            label = segment.process_id or "Idle"
            color = colors.setdefault(
                label,
                "grey" if label == "Idle" else palette[len(colors) % len(palette)],
            )
            left = 20 + segment.start_time * scale
            right = 20 + segment.end_time * scale
            target.create_rectangle(left, 85, right, 135, fill=color, outline="black")
            target.create_text((left + right) / 2, 110, text=label)
        target.create_text(width / 2, 25, text=f"{self.result.algorithm} Schedule")
        target.create_text(20, 155, text="0", anchor="w")
        target.create_text(width - 20, 155, text=str(total_time), anchor="e")
        target.create_line(20, 150, width - 20, 150)

    @staticmethod
    def _parse_int(value: str, field_name: str) -> int:
        try:
            return int(value)
        except ValueError as error:
            raise ValidationError(f"{field_name} must be an integer.") from error


def main() -> None:
    root = tk.Tk()
    ContextSwitchApp(root)
    root.mainloop()
