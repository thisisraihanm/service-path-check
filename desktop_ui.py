"""Small local desktop interface. Worker threads never touch Tk widgets."""
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid
import webbrowser

from friendly import explain, friendly_error
from report import write_report


def data_root():
    return Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.local' / 'share')) / 'RaihanTools'


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


class App:
    def __init__(self, root, kind, title, demo, check, collect=None, validate_output=None):
        self.root, self.kind, self.title = root, kind, title
        self.demo_fn, self.check_fn, self.collect_fn = demo, check, collect
        self.validate_output = validate_output
        self.events = queue.Queue()
        self.busy, self.report, self.result, self.report_base = False, None, None, None
        self.controls, self.audited_roots = [], None
        self.host, self.profile = tk.StringVar(), tk.StringVar(value='Secure website')
        self.port, self.tls = tk.StringVar(value='443'), tk.BooleanVar(value=True)
        self.first, self.second = tk.StringVar(), tk.StringVar()
        self.root.title(title)
        self.root.geometry('820x710')
        self.root.minsize(700, 630)
        self.root.configure(background='#f1f5f9')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 11), background='#f1f5f9')
        style.configure('TButton', padding=(12, 8))
        style.configure('Primary.TButton', background='#175e65', foreground='white', font=('Segoe UI', 11, 'bold'))
        style.map('Primary.TButton', background=[('active', '#124950'), ('disabled', '#8ba7a9')])
        style.configure('TEntry', padding=6, fieldbackground='white')
        style.configure('TCombobox', padding=5)
        self.frame = ttk.Frame(root, padding=24)
        self.frame.pack(fill='both', expand=True)
        self.label('RAIHAN TOOLS  /  LOCAL CHECKS', 10, '#175e65')
        self.label(title, 25, '#102b3a', bold=True, pady=(5, 5))
        descriptions = {
            'service': 'Check whether this computer can connect to a website or server.',
            'backup': 'Choose your original folder and its backup copy. Find missing or different files.',
            'drift': 'Save settings before and after a change, then see what changed.'}
        self.label(descriptions[kind], 12, '#465866', pady=(0, 6))
        self.label('These tools check and report. They do not repair, delete, or change settings.', 10, '#465866', pady=(0, 12))
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 12))
        self.check_tab = ttk.Frame(self.notebook, padding=14)
        self.result_tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.check_tab, text='1. Choose what to check')
        self.notebook.add(self.result_tab, text='2. Read the result')
        self.form = ttk.Frame(self.check_tab)
        self.form.pack(fill='x')
        if kind == 'service': self.service_form()
        elif kind == 'backup': self.folder_form()
        else: self.drift_form()
        toolbar = ttk.Frame(self.check_tab)
        toolbar.pack(fill='x', pady=(16, 10))
        names = {'service': 'Check connection', 'backup': 'Check backup', 'drift': 'Compare saved settings'}
        self.run_button = self.button(toolbar, names[kind], self.start_check, primary=True)
        self.run_button.pack(side='left')
        self.demo_button = self.button(toolbar, 'Try a safe example', self.start_demo)
        self.demo_button.pack(side='left', padx=10)
        self.progress = ttk.Progressbar(self.frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=(0, 8))
        self.status = tk.StringVar(value='Ready. You can try the example without using your own files or network.')
        ttk.Label(self.frame, textvariable=self.status, wraplength=740).pack(anchor='w')
        self.output = tk.Text(self.result_tab, height=10, font=('Segoe UI', 11), wrap='word', background='white',
                              foreground='#102b3a', relief='flat', padx=16, pady=12, cursor='arrow')
        self.output.tag_configure('heading', font=('Segoe UI', 15, 'bold'), spacing3=8)
        self.output.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(self.result_tab, command=self.output.yview)
        scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')
        self.output.configure(yscrollcommand=scrollbar.set)
        self.set_output('Your result will appear here', 'Start with the safe example to see how this tool works.',
                        'No commands or configuration-file editing are needed.')
        bottom = ttk.Frame(self.frame)
        bottom.pack(fill='x')
        self.open_button = ttk.Button(bottom, text='Open detailed report', command=self.open_report, state='disabled')
        self.open_button.pack(side='left')
        self.save_button = ttk.Button(bottom, text='Save report copy…', command=self.save_copy, state='disabled')
        self.save_button.pack(side='left', padx=8)
        self.label('Reports may contain server or file names. Share them with your IT support when needed.', 9, '#465866', pady=(8, 0))
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(100, self.poll)

    def label(self, text, size, color, bold=False, pady=0):
        label = ttk.Label(self.frame, text=text, foreground=color,
                          font=('Segoe UI', size, 'bold' if bold else 'normal'), wraplength=740)
        label.pack(anchor='w', pady=pady)
        return label

    def button(self, parent, title, command, primary=False):
        button = ttk.Button(parent, text=title, command=command, style='Primary.TButton' if primary else 'TButton')
        self.controls.append(button)
        return button

    def entry(self, parent, variable, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=(8, 4), columnspan=2)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row+1, column=0, sticky='ew')
        self.controls.append(entry)
        parent.columnconfigure(0, weight=1)
        return entry

    def service_form(self):
        entry = self.entry(self.form, self.host, 'Website address or server name', 0)
        entry.bind('<Return>', lambda _: self.start_check())
        entry.focus_set()
        ttk.Label(self.form, text='For example: https://example.com   •   Use an office server name only when provided by IT.',
                  font=('Segoe UI', 9), wraplength=730).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        line = ttk.Frame(self.form)
        line.grid(row=3, column=0, sticky='ew', pady=6)
        ttk.Label(line, text='What are you checking?').pack(side='left')
        combo = ttk.Combobox(line, textvariable=self.profile, state='readonly',
                             values=['Secure website', 'Plain website', 'Windows file server', 'Other connection'], width=22)
        combo.pack(side='left', padx=12)
        self.controls.append(combo)
        combo.bind('<<ComboboxSelected>>', self.preset)
        self.advanced = ttk.Frame(self.form)
        toggle = self.button(self.form, 'Connection options (if IT gave you details)', self.toggle_options)
        toggle.grid(row=4, column=0, sticky='w', pady=3)
        ttk.Label(self.advanced, text='Port number').pack(side='left')
        port = ttk.Entry(self.advanced, textvariable=self.port, width=7)
        port.pack(side='left', padx=8)
        self.controls.append(port)
        tls = ttk.Checkbutton(self.advanced, text='Verify a secure connection', variable=self.tls)
        tls.pack(side='left', padx=8)
        self.controls.append(tls)
        ttk.Label(self.form, text='Three checks are made. A slow or unreachable server can take a few minutes.',
                  font=('Segoe UI', 9)).grid(row=6, column=0, sticky='w', pady=4)

    def toggle_options(self):
        if self.advanced.winfo_ismapped(): self.advanced.grid_remove()
        else: self.advanced.grid(row=5, column=0, sticky='w', pady=5)

    def preset(self, _=None):
        options = {'Secure website': ('443', True), 'Plain website': ('80', False), 'Windows file server': ('445', False)}
        if self.profile.get() in options:
            port, tls = options[self.profile.get()]
            self.port.set(port); self.tls.set(tls)
        else: self.advanced.grid(row=5, column=0, sticky='w', pady=5)

    def folder_form(self):
        self.path_row(self.first, '1. Original files folder', 0, folder=True)
        self.path_row(self.second, '2. Backup copy folder', 2, folder=True)
        ttk.Label(self.form, text='Select the matching folders, such as Documents and its copied Documents folder on a backup drive.',
                  wraplength=730, font=('Segoe UI', 9)).grid(row=4, column=0, columnspan=2, sticky='w', pady=7)

    def drift_form(self):
        button = self.button(self.form, 'Save current settings…', self.start_collect)
        button.grid(row=0, column=0, sticky='w', pady=5)
        if sys.platform != 'win32': button.configure(state='disabled'); self.controls.remove(button)
        ttk.Label(self.form, text='On Windows: save once while things work, then save again after a change. You never need to edit the saved files.',
                  wraplength=730, font=('Segoe UI', 9)).grid(row=1, column=0, columnspan=2, sticky='w')
        self.path_row(self.first, '1. Earlier saved settings', 2)
        self.path_row(self.second, '2. Later saved settings', 4)

    def path_row(self, variable, title, row, folder=False):
        self.entry(self.form, variable, title, row)
        def choose():
            value = filedialog.askdirectory(title=title) if folder else filedialog.askopenfilename(title=title, filetypes=[('Saved settings', '*.json')])
            if value: variable.set(value)
        self.button(self.form, 'Choose folder…' if folder else 'Choose file…', choose).grid(row=row+1, column=1, padx=(8, 0))

    def output_path(self):
        return data_root() / self.title.replace(' ', '-') / ('report-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])

    def start_check(self):
        if self.busy: return
        values = {'host': self.host.get().strip(), 'profile': self.profile.get(), 'port': self.port.get(),
                  'tls': self.tls.get(), 'first': self.first.get(), 'second': self.second.get()}
        output = self.output_path()
        self.audited_roots = None
        if self.kind == 'backup':
            if not values['first'] or not values['second']:
                messagebox.showinfo('Choose both folders', 'Choose the original files folder and its backup copy first.'); return
            try: self.validate_output(values['first'], values['second'], output)
            except (OSError, ValueError) as error:
                if 'outside both' not in str(error): self.show_error(error); return
                chosen = filedialog.asksaveasfilename(title='Save the report outside both checked folders', defaultextension='.html', filetypes=[('Report', '*.html')])
                if not chosen: return
                output = Path(chosen)
                try: self.validate_output(values['first'], values['second'], output)
                except (OSError, ValueError) as error: self.show_error(error); return
            self.audited_roots = (values['first'], values['second'])
        self.start_job(lambda: self.check_fn(values), output, demo=False)

    def start_demo(self):
        if not self.busy:
            self.audited_roots = None
            self.start_job(self.demo_fn, self.output_path(), demo=True)

    def start_job(self, work, output, demo=False):
        self.busy = True
        self.report = None
        self.open_button.configure(state='disabled'); self.save_button.configure(state='disabled')
        for control in self.controls: control.configure(state='disabled')
        self.status.set('Checking… You can leave this window open while the check finishes.')
        self.progress.start(12)
        self.set_output('Checking…', 'Please wait. The selected items are being read.', 'Your files and settings are not being changed.')
        self.notebook.select(self.result_tab)
        def worker():
            try:
                result = work()
                if demo: result['demo'] = True
                report = write_report(result, output, self.title)
                self.events.put(('result', result, report))
            except Exception as error:
                self.events.put(('error', error))
        threading.Thread(target=worker, daemon=True).start()

    def start_collect(self):
        if self.busy or not self.collect_fn: return
        destination = filedialog.asksaveasfilename(title='Save current computer settings',
            initialfile='settings-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json',
            defaultextension='.json', filetypes=[('Saved settings', '*.json')])
        if not destination: return
        self.busy = True
        for control in self.controls: control.configure(state='disabled')
        self.open_button.configure(state='disabled'); self.save_button.configure(state='disabled')
        self.progress.start(12); self.status.set('Reading current Windows settings…')
        self.set_output('Saving current settings…', 'Please wait while Windows settings are read.', 'Your settings are not being changed.')
        self.notebook.select(self.result_tab)
        def worker():
            try: self.events.put(('snapshot', self.collect_fn(Path(destination)), Path(destination)))
            except Exception as error: self.events.put(('error', error))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            self.root.after(100, self.poll); return
        self.busy = False; self.progress.stop()
        for control in self.controls:
            control.configure(state='readonly' if isinstance(control, ttk.Combobox) else 'normal')
        if event[0] == 'error': self.show_error(event[1])
        elif event[0] == 'snapshot':
            snapshot, path = event[1:]
            incomplete = any(s != 'ok' for s in snapshot['coverage'].values())
            self.set_output('Settings saved — some checks were blocked' if incomplete else 'Current settings saved',
                            f"Computer: {snapshot['host']}\nSaved to: {path}",
                            'Save another snapshot after the change, then choose the earlier and later files to compare them.')
            if not self.first.get(): self.first.set(str(path))
            else: self.second.set(str(path))
            self.status.set('Saved. These files contain settings, not passwords. Keep them private.')
            self.report = None
        else:
            self.result, self.report = event[1:]
            headline, meaning, action = explain(self.result, self.title)
            if self.result.get('demo'): headline = 'EXAMPLE — ' + headline
            self.set_output(headline, meaning, action)
            self.status.set('Example finished. Fictional data only.' if self.result.get('demo') else 'Finished. Report saved on this computer.')
            self.open_button.configure(state='normal'); self.save_button.configure(state='normal')
        self.root.after(100, self.poll)

    def set_output(self, headline, meaning, action):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.insert('end', headline + '\n', 'heading')
        self.output.insert('end', meaning + '\n\nNext step\n' + action)
        self.output.configure(state='disabled')

    def show_error(self, error):
        self.status.set('Could not finish. Check the message below.')
        self.set_output('A little help is needed', friendly_error(error), 'Details for IT support: ' + str(error))
        self.notebook.select(self.result_tab)

    def open_report(self):
        if self.report and self.report.exists():
            if not webbrowser.open(self.report.resolve().as_uri()):
                messagebox.showinfo('Open this report', str(self.report))

    def save_copy(self):
        if not self.report: return
        chosen = filedialog.asksaveasfilename(title='Save report copy', initialfile=self.report.name,
                                            defaultextension='.html', filetypes=[('Report', '*.html')])
        if not chosen: return
        try:
            if self.audited_roots: self.validate_output(*self.audited_roots, chosen)
            if Path(chosen).resolve() != self.report.resolve(): shutil.copyfile(self.report, chosen)
            self.status.set('Report copy saved: ' + chosen)
        except (OSError, ValueError) as error: self.show_error(error)

    def close(self):
        if self.busy and not messagebox.askyesno('A check is running', 'Close the tool before the check finishes? Your original files and settings will not be changed.'):
            return
        self.root.destroy()
