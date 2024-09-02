import tkinter as tk
from tkinter import ttk
import json

class TagDisplay:
    def __init__(self, tag_frequency):
        self.root = tk.Tk()
        self.root.title("Tag Frequency Display")
        self.tag_frequency = tag_frequency
        self.checkbox_vars = []  # Store references to BooleanVar objects

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="3 3 12 12")
        main_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        canvas = tk.Canvas(main_frame)
        canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(column=1, row=0, sticky=(tk.N, tk.S))

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        ttk.Label(inner_frame, text="Showing", font=('Arial', 12, 'bold')).grid(column=0, row=0, sticky=tk.W, pady=(0, 10), columnspan=2)

        for i, (tag, frequency) in enumerate(sorted(self.tag_frequency.items(), key=lambda x: x[1], reverse=True), start=1):
            ttk.Label(inner_frame, text=f"{tag} ({frequency})", anchor="w").grid(column=0, row=i, sticky=tk.W, padx=(0, 10))
            var = tk.BooleanVar()
            self.checkbox_vars.append(var)  # Keep reference to var
            ttk.Checkbutton(inner_frame, variable=var).grid(column=1, row=i, sticky=tk.E)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        # Clean up resources
        for var in self.checkbox_vars:
            del var
        self.checkbox_vars.clear()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

def load_tag_frequency(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Example usage
if __name__ == "__main__":
    file_path = 'cache/display_tags/tag_frequency.json'
    tag_frequency = load_tag_frequency(file_path)
    app = TagDisplay(tag_frequency)
    app.run()