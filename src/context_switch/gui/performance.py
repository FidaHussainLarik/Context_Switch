import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from context_switch.domain.exceptions import ValidationError
from context_switch.domain.models import Process
from context_switch.simulation.comparison import ComparisonResult, compare_processes

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError:
    FigureCanvasTkAgg = None
    Figure = None


class ComparisonViewBase:
    algorithms = (
        "FCFS",
        "SJF",
        "Priority",
        "Priority (Preemptive)",
        "Round Robin",
        "SRTN",
    )

    def __init__(
        self,
        process_provider: Callable[[], list[Process]],
        quantum_provider: Callable[[], int],
    ) -> None:
        self.process_provider = process_provider
        self.quantum_provider = quantum_provider
        self.comparison: ComparisonResult | None = None

    def _compare(self) -> ComparisonResult | None:
        try:
            processes = self.process_provider()
            if not processes:
                return None
            return compare_processes(processes, self.quantum_provider())
        except (ValidationError, ValueError):
            return None


class PerformanceAnalysisView(ComparisonViewBase):
    metric_labels = {
        "average_waiting_time": "Average WT",
        "average_turnaround_time": "Average TAT",
        "average_weighted_turnaround_time": "Average WTT",
        "cpu_utilization": "CPU Utilization",
    }

    def __init__(
        self,
        parent: ttk.Frame,
        process_provider: Callable[[], list[Process]],
        quantum_provider: Callable[[], int],
    ) -> None:
        super().__init__(process_provider, quantum_provider)
        self.status_label: ttk.Label
        self.winner_label: ttk.Label
        self.summary_frame: ttk.Frame
        self.metric_winners_label: ttk.Label
        self._build(parent)

    def _build(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        controls = ttk.Frame(parent)
        controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ttk.Button(
            controls,
            text="Compare All Algorithms",
            command=self.refresh,
        ).pack(side="left")
        self.status_label = ttk.Label(controls, text="Add processes to begin comparison.")
        self.status_label.pack(side="left", padx=12)

        winner_frame = ttk.LabelFrame(parent, text="Overall Winner")
        winner_frame.grid(row=1, column=0, padx=10, sticky="ew")
        winner_frame.columnconfigure(0, weight=1)
        self.winner_label = ttk.Label(
            winner_frame,
            text="Run comparison to determine the best algorithm for this workload.",
            justify="left",
        )
        self.winner_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        summary_container = ttk.LabelFrame(parent, text="Comparison Summary")
        summary_container.grid(row=2, column=0, padx=10, pady=(8, 0), sticky="ew")
        summary_container.columnconfigure(0, weight=1)
        self.summary_frame = ttk.Frame(summary_container)
        self.summary_frame.grid(row=0, column=0, sticky="ew")

        winners_frame = ttk.LabelFrame(parent, text="Individual Metric Winners")
        winners_frame.grid(row=3, column=0, padx=10, pady=(8, 0), sticky="ew")
        winners_frame.columnconfigure(0, weight=1)
        self.metric_winners_label = ttk.Label(winners_frame, justify="left")
        self.metric_winners_label.grid(
            row=0, column=0, padx=10, pady=6, sticky="w"
        )
        self.refresh()

    def refresh(self) -> None:
        processes = self.process_provider()
        if not processes:
            self.comparison = None
            self._clear_analysis()
            self.status_label.configure(text="Add processes to begin comparison.")
            return
        try:
            self.comparison = compare_processes(
                processes, self.quantum_provider()
            )
        except (ValidationError, ValueError) as error:
            self.comparison = None
            self._clear_analysis()
            self.status_label.configure(text="Comparison unavailable.")
            messagebox.showerror("Comparison error", str(error))
            return
        self.status_label.configure(
            text="All six algorithms compared using the same process dataset."
        )
        self._draw_summary()

    def _draw_summary(self) -> None:
        if self.comparison is None:
            return
        for child in self.summary_frame.winfo_children():
            child.destroy()

        columns = (
            ("Algorithm", None),
            ("Avg. WT", "average_waiting_time"),
            ("Avg. TAT", "average_turnaround_time"),
            ("Avg. WTT", "average_weighted_turnaround_time"),
            ("CPU Utilization", "cpu_utilization"),
            ("Overall Score", None),
        )
        for column, (heading, _) in enumerate(columns):
            tk.Label(
                self.summary_frame,
                text=heading,
                font=("TkDefaultFont", 9, "bold"),
                borderwidth=1,
                relief="solid",
                padx=8,
                pady=4,
            ).grid(row=0, column=column, sticky="nsew")
            self.summary_frame.columnconfigure(column, weight=1)

        for row, algorithm in enumerate(self.algorithms, start=1):
            summary = self.comparison.metrics[algorithm]
            values = (
                algorithm,
                summary.average_waiting_time,
                summary.average_turnaround_time,
                summary.average_weighted_turnaround_time,
                summary.cpu_utilization,
                self.comparison.analysis.overall_scores[algorithm],
            )
            for column, value in enumerate(values):
                metric_name = columns[column][1]
                background, foreground = self._summary_cell_style(
                    algorithm, metric_name
                )
                display = value if isinstance(value, str) else f"{value:.2f}"
                tk.Label(
                    self.summary_frame,
                    text=display,
                    bg=background,
                    fg=foreground,
                    borderwidth=1,
                    relief="solid",
                    padx=8,
                    pady=3,
                ).grid(row=row, column=column, sticky="nsew")

        winners = self.comparison.analysis.overall_winners
        score = self.comparison.analysis.overall_scores[winners[0]]
        winner_metrics = self.comparison.metrics[winners[0]]
        first_place_count = sum(
            winners[0] in self.comparison.analysis.metric_winners[metric]
            for metric in (
                "average_waiting_time",
                "average_turnaround_time",
                "average_weighted_turnaround_time",
            )
        )
        self.winner_label.configure(
            text=(
                f"Winner: {', '.join(winners)}\n"
                f"Overall score: {score:.2f}    "
                f"Average WT: {winner_metrics.average_waiting_time:.2f}    "
                f"Average TAT: {winner_metrics.average_turnaround_time:.2f}    "
                f"Average WTT: "
                f"{winner_metrics.average_weighted_turnaround_time:.2f}\n"
                f"Lowest average rank for this workload; first in "
                f"{first_place_count} of three ranked metrics."
            )
        )

        lines = []
        for metric_name in self.metric_labels:
            names = ", ".join(
                self.comparison.analysis.metric_winners[metric_name]
            )
            lines.append(f"{self.metric_labels[metric_name]}: {names}")
        self.metric_winners_label.configure(text="\n".join(lines))

    def _summary_cell_style(
        self,
        algorithm: str,
        metric_name: str | None,
    ) -> tuple[str, str]:
        if self.comparison is None or metric_name is None:
            return ("white", "black")
        values = {
            name: getattr(summary, metric_name)
            for name, summary in self.comparison.metrics.items()
        }
        if algorithm in self.comparison.analysis.metric_winners[metric_name]:
            return ("#c6efce", "#006100")
        if self.comparison.analysis.rankings[algorithm][metric_name] == 2:
            return ("#ffeb9c", "#9c6500")
        worst = (
            min(values.values())
            if metric_name == "cpu_utilization"
            else max(values.values())
        )
        if abs(values[algorithm] - worst) <= 1e-9:
            return ("#ffc7ce", "#9c0006")
        return ("white", "black")

    def _clear_analysis(self) -> None:
        self.winner_label.configure(
            text="Run comparison to determine the best algorithm for this workload."
        )
        self.metric_winners_label.configure(text="")
        for child in self.summary_frame.winfo_children():
            child.destroy()


class PerformanceGraphsView(ComparisonViewBase):
    def __init__(
        self,
        parent: ttk.Frame,
        process_provider: Callable[[], list[Process]],
        quantum_provider: Callable[[], int],
    ) -> None:
        super().__init__(process_provider, quantum_provider)
        self.status_label: ttk.Label
        self.figure = None
        self.chart = None
        self._build(parent)

    def _build(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        controls = ttk.Frame(parent)
        controls.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ttk.Button(
            controls,
            text="Refresh Graphs",
            command=self.refresh,
        ).pack(side="left")
        self.status_label = ttk.Label(
            controls, text="Add processes to display comparison graphs."
        )
        self.status_label.pack(side="left", padx=12)

        if FigureCanvasTkAgg is None or Figure is None:
            self.chart = tk.Canvas(parent, background="white")
            self.chart.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        else:
            self.figure = Figure(figsize=(10, 7), dpi=100)
            self.chart = FigureCanvasTkAgg(self.figure, master=parent)
            self.chart.get_tk_widget().grid(
                row=1, column=0, padx=10, pady=10, sticky="nsew"
            )
        self.refresh()

    def refresh(self) -> None:
        processes = self.process_provider()
        if not processes:
            self.comparison = None
            self.status_label.configure(text="Add processes to display comparison graphs.")
            self._clear_chart()
            return
        try:
            self.comparison = compare_processes(
                processes, self.quantum_provider()
            )
        except (ValidationError, ValueError) as error:
            self.comparison = None
            self.status_label.configure(text="Graphs unavailable.")
            self._clear_chart()
            messagebox.showerror("Graph error", str(error))
            return
        self.status_label.configure(
            text="Graphs compare the complete process batch across all six algorithms."
        )
        self._draw()

    def _draw(self) -> None:
        if self.comparison is None:
            return
        if self.figure is None:
            self.chart.delete("all")
            self.chart.create_text(
                20,
                20,
                anchor="nw",
                text="Matplotlib's Tk backend is unavailable in this environment.",
            )
            return

        self.figure.clear()
        axes = self.figure.subplots(2, 2)
        names = list(self.comparison.metrics)
        metrics = self.comparison.metrics
        charts = (
            (
                axes[0, 0],
                "average_waiting_time",
                "Average Waiting Time",
                [metrics[name].average_waiting_time for name in names],
            ),
            (
                axes[0, 1],
                "average_turnaround_time",
                "Average Turnaround Time",
                [metrics[name].average_turnaround_time for name in names],
            ),
            (
                axes[1, 0],
                "average_weighted_turnaround_time",
                "Average Weighted Turnaround",
                [
                    metrics[name].average_weighted_turnaround_time
                    for name in names
                ],
            ),
            (
                axes[1, 1],
                "cpu_utilization",
                "CPU Utilization (%)",
                [metrics[name].cpu_utilization for name in names],
            ),
        )
        for axis, metric_name, title, values in charts:
            winner = self.comparison.analysis.metric_winners[metric_name][0]
            self._bar_chart(
                axis,
                names,
                values,
                title,
                names.index(winner),
            )
        self.figure.tight_layout()
        self.chart.draw()

    @staticmethod
    def _bar_chart(axis, labels, values, title, highlight_index: int) -> None:
        colors = ["#4c78a8"] * len(values)
        colors[highlight_index] = "#54a24b"
        axis.bar(labels, values, color=colors)
        axis.set_title(title)
        axis.set_ylabel("Value")
        axis.tick_params(axis="x", rotation=30, labelsize=8)
        axis.grid(axis="y", linestyle=":", alpha=0.5)

    def _clear_chart(self) -> None:
        if self.figure is not None:
            self.figure.clear()
            self.chart.draw()
        elif self.chart is not None:
            self.chart.delete("all")
