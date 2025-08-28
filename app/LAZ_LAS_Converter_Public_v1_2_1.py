#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversor LAZ ⇄ LAS (Edição Pública, sem CLIs externos)
v1.2.1 — Sobre com contactos do autor (LinkedIn, ResearchGate, GitHub, email)

Licença: MIT
"""

import os
import sys
import queue
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Dependências Python (sem executáveis externos)
try:
    import laspy
except Exception as e:
    laspy = None
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None

APP_TITLE   = "Conversor LAZ ⇄ LAS"
APP_VERSION = "1.2.1 (Public)"
AUTHOR_NAME = "Edgar Figueira"
AUTHOR_EMAIL = "edgarjunceiro@gmail.com"
LINKEDIN    = "https://www.linkedin.com/in/edgarfigueira/"
RESEARCHGATE= "https://www.researchgate.net/profile/Edgar-Figueira-2?ev=hdr_xprf"
GITHUB      = "https://github.com/edgarfigueira"

HELP_COPY = {
    "entrada": (
        "Pasta de ENTRADA\n\n"
        "Selecione a pasta que contém ficheiros LAS (.las) e/ou LAZ (.laz). "
        "O modo 'Automático' escolhe a direção conforme o tipo que encontrar:\n"
        "  - Se houver LAZ, faz LAZ → LAS.\n"
        "  - Caso contrário, se houver LAS, faz LAS → LAZ.\n\n"
        "A pesquisa é recursiva (inclui subpastas)."
    ),
    "saida": (
        "Pasta de SAÍDA\n\n"
        "Onde serão guardados os ficheiros convertidos. "
        "Por defeito, a app preserva a estrutura de subpastas da entrada dentro da pasta de saída, "
        "evitando colisões de nomes. Pode desligar essa opção em 'Opções'."
    ),
    "modo": (
        "Modo de conversão\n\n"
        "• Automático: deteta se há .laz (faz LAZ→LAS) ou .las (faz LAS→LAZ).\n"
        "• LAZ → LAS: descompressão para ficheiros LAS não comprimidos.\n"
        "• LAS → LAZ: compressão para LAZ (menor tamanho; ideal para arquivar/partilhar)."
    ),
    "preservar": (
        "Preservar estrutura de subpastas\n\n"
        "Se ativo, replica a mesma hierarquia de pastas da entrada dentro da saída.\n"
        "Se desligado, todos os ficheiros convertidos são colocados diretamente na pasta de saída "
        "e podem ocorrer colisões de nomes (ex.: ficheiros com o mesmo nome vindos de subpastas diferentes)."
    ),
    "sobrescrever": (
        "Sobrescrever existentes\n\n"
        "Se ativo, ficheiros de saída já existentes serão substituídos. "
        "Se desativado (recomendado), ficheiros existentes são SALTADOS, poupando tempo."
    ),
    "boaspraticas": (
        "Boas práticas & notas:\n"
        "• Espaço em disco: LAS pode ocupar ~5–10× o tamanho do LAZ.\n"
        "• OneDrive/Cloud: pausar a sincronização pode acelerar o processo.\n"
        "• Metadados: sistema de coordenadas, classes e atributos são preservados.\n"
        "• Ficheiros muito grandes: a app processa por blocos para poupar memória."
    ),
}

class ToolTip:
    def __init__(self, widget, text, wrap=70):
        self.widget = widget
        self.text = text
        self.wrap = wrap
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(tw, text=self.text, justify="left", relief="solid", borderwidth=1,
                       background="#ffffe0", wraplength=self.wrap*6)
        lbl.pack(ipadx=6, ipady=3)

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class ConverterThread(threading.Thread):
    def __init__(self, in_dir: Path, out_dir: Path, direction: str, preserve: bool, overwrite: bool, q: queue.Queue):
        super().__init__(daemon=True)
        self.in_dir   = in_dir
        self.out_dir  = out_dir
        self.direction = direction
        self.preserve = preserve
        self.overwrite = overwrite
        self.q = q
        self.stop_flag = False
        self.converted = 0
        self.skipped = 0
        self.failed = 0
        self.log_path = None

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts} {msg}"
        self.q.put(("log", line))
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _dest(self, src: Path, ext: str) -> Path:
        if self.preserve:
            rel = src.relative_to(self.in_dir)
            dest = self.out_dir.joinpath(rel).with_suffix(ext)
        else:
            dest = self.out_dir.joinpath(src.stem + ext)
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    def _convert_stream(self, src: Path, dest: Path):
        to_laz = dest.suffix.lower() == ".laz"
        try:
            with laspy.open(src, mode="r") as reader:
                header = reader.header
                with laspy.open(dest, mode="w", header=header, do_compress=to_laz) as writer:
                    for pts in reader.chunk_iterator(5_000_000):
                        writer.write_points(pts)
            return True, ""
        except Exception as e:
            return False, str(e)

    def run(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = str(self.out_dir / f"convert_{datetime.now():%Y%m%d_%H%M%S}.log")
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"=== {APP_TITLE} {APP_VERSION} ===\n")
            f.write(f"Início: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"Entrada: {self.in_dir}\nSaída: {self.out_dir}\n")
            f.write(f"Modo: {self.direction} | Preservar: {self.preserve} | Overwrite: {self.overwrite}\n\n")

        laz = sorted(self.in_dir.rglob("*.laz"))
        las = sorted(self.in_dir.rglob("*.las"))

        direction = self.direction
        if direction == "auto":
            direction = "laz2las" if laz else ("las2laz" if las else None)
        if direction is None:
            self._log("Não há .laz ou .las na pasta de entrada.")
            self.q.put(("done", (self.converted, self.skipped, self.failed, self.log_path)))
            return

        src_list = laz if direction == "laz2las" else las
        ext = ".las" if direction == "laz2las" else ".laz"

        total = len(src_list)
        if total == 0:
            self._log("Não há ficheiros para processar no modo escolhido.")
            self.q.put(("done", (self.converted, self.skipped, self.failed, self.log_path)))
            return

        self.q.put(("total", total))
        for i, src in enumerate(src_list, 1):
            if self.stop_flag:
                self._log("Interrompido pelo utilizador.")
                break
            dest = self._dest(src, ext)
            self._log(f"[proc] ({i}/{total}) {src.name}")

            if dest.exists() and not self.overwrite:
                self.skipped += 1
                self._log(f"[skip] {src} -> {dest} (já existe)")
            else:
                ok, err = self._convert_stream(src, dest)
                if ok:
                    self.converted += 1
                    self._log(f"[ok]   {src} -> {dest}")
                else:
                    self.failed += 1
                    self._log(f"[fail] {src} :: {err}")

            self.q.put(("progress", i))

        self.q.put(("done", (self.converted, self.skipped, self.failed, self.log_path)))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("900x640")
        self.minsize(860, 600)

        self.in_var  = tk.StringVar()
        self.out_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="auto")
        self.preserve_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)

        self.q = queue.Queue()
        self.worker = None

        self._build_ui()
        self.after(120, self._poll_queue)

        self.bind("<F1>", lambda e: self._help_full())
        self.bind("<F5>", lambda e: self._start())
        self.bind("<Escape>", lambda e: self._stop())

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        header = ttk.Frame(self)
        header.pack(fill="x", **pad)
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 15, "bold")).pack(side="left")
        ttk.Label(header, text=APP_VERSION, foreground="#555").pack(side="left", padx=10)
        ttk.Button(header, text="Ajuda (F1)", command=self._help_full).pack(side="right")
        ttk.Button(header, text="Sobre", command=self._about_window).pack(side="right", padx=8)

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, **pad)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        frm_io = ttk.LabelFrame(left, text="Pastas")
        frm_io.pack(fill="x", **pad)

        row = 0
        lbl_in = ttk.Label(frm_io, text="Entrada:")
        lbl_in.grid(row=row, column=0, sticky="w", padx=8, pady=6)
        ent_in = ttk.Entry(frm_io, textvariable=self.in_var)
        ent_in.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        btn_in = ttk.Button(frm_io, text="Escolher…", command=self._choose_in)
        btn_in.grid(row=row, column=2, padx=8, pady=6)
        frm_io.columnconfigure(1, weight=1)
        ToolTip(ent_in, HELP_COPY["entrada"])
        ent_in.bind("<FocusIn>", lambda e: self._set_help(HELP_COPY["entrada"]))
        lbl_in.bind("<Button-1>", lambda e: self._info("Entrada", HELP_COPY["entrada"]))

        row = 1
        lbl_out = ttk.Label(frm_io, text="Saída:")
        lbl_out.grid(row=row, column=0, sticky="w", padx=8, pady=6)
        ent_out = ttk.Entry(frm_io, textvariable=self.out_var)
        ent_out.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        btn_out = ttk.Button(frm_io, text="Escolher…", command=self._choose_out)
        btn_out.grid(row=row, column=2, padx=8, pady=6)
        ToolTip(ent_out, HELP_COPY["saida"])
        ent_out.bind("<FocusIn>", lambda e: self._set_help(HELP_COPY["saida"]))
        lbl_out.bind("<Button-1>", lambda e: self._info("Saída", HELP_COPY["saida"]))

        adv = ttk.LabelFrame(left, text="Opções")
        adv.pack(fill="x", **pad)

        ttk.Label(adv, text="Modo:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        cmb = ttk.Combobox(adv, textvariable=self.mode_var, state="readonly",
                           values=("auto", "laz2las", "las2laz"), width=12)
        cmb.grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ToolTip(cmb, HELP_COPY["modo"])
        cmb.bind("<FocusIn>", lambda e: self._set_help(HELP_COPY["modo"]))
        ttk.Label(adv, text=" ").grid(row=0, column=2)
        chk_pres = ttk.Checkbutton(adv, text="Preservar estrutura de subpastas", variable=self.preserve_var)
        chk_pres.grid(row=0, column=3, sticky="w", padx=8, pady=6, columnspan=2)
        ToolTip(chk_pres, HELP_COPY["preservar"])
        chk_pres.bind("<FocusIn>", lambda e: self._set_help(HELP_COPY["preservar"]))

        chk_over = ttk.Checkbutton(adv, text="Sobrescrever existentes", variable=self.overwrite_var)
        chk_over.grid(row=1, column=3, sticky="w", padx=8, pady=6, columnspan=2)
        ToolTip(chk_over, HELP_COPY["sobrescrever"])
        chk_over.bind("<FocusIn>", lambda e: self._set_help(HELP_COPY["sobrescrever"]))

        adv.columnconfigure(5, weight=1)

        btns = ttk.Frame(left)
        btns.pack(fill="x", **pad)
        self.btn_start = ttk.Button(btns, text="Iniciar (F5)", command=self._start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(btns, text="Parar (Esc)", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        ttk.Button(btns, text="Abrir pasta de saída", command=self._open_out).pack(side="right")

        prog = ttk.Frame(left)
        prog.pack(fill="x", **pad)
        self.prog = ttk.Progressbar(prog, orient="horizontal", mode="determinate", maximum=100)
        self.prog.pack(fill="x", expand=True, side="left")
        self.lbl_prog = ttk.Label(prog, text="0/0")
        self.lbl_prog.pack(side="left", padx=10)

        logf = ttk.LabelFrame(left, text="Log")
        logf.pack(fill="both", expand=True, **pad)
        self.txt = tk.Text(logf, wrap="none", height=14)
        self.txt.pack(fill="both", expand=True)
        self.txt.configure(state="disabled")

        right = ttk.LabelFrame(main, text="Ajuda contextual")
        right.pack(side="left", fill="both", expand=False, padx=(10,0), pady=6)
        self.help_txt = tk.Text(right, wrap="word", width=42, height=24, background="#fafafa")
        self.help_txt.pack(fill="both", expand=True, padx=6, pady=6)
        self.help_txt.insert("1.0", HELP_COPY["boaspraticas"])
        self.help_txt.configure(state="disabled")

        if laspy is None:
            msg = ("A biblioteca 'laspy' não está disponível.\n\n"
                   "Instalação sugerida:\n  pip install \"laspy[lazrs]\"\n\n"
                   "De seguida, reabre a aplicação.")
            messagebox.showwarning("Dependência em falta", msg)

    def _choose_in(self):
        d = filedialog.askdirectory(title="Escolher pasta de entrada")
        if d:
            self.in_var.set(d)
            self._set_help(HELP_COPY["entrada"])

    def _choose_out(self):
        d = filedialog.askdirectory(title="Escolher pasta de saída")
        if d:
            self.out_var.set(d)
            self._set_help(HELP_COPY["saida"])

    def _set_help(self, text: str):
        self.help_txt.configure(state="normal")
        self.help_txt.delete("1.0", "end")
        self.help_txt.insert("1.0", text)
        self.help_txt.configure(state="disabled")

    def _info(self, title: str, text: str):
        messagebox.showinfo(title, text)

    def _append_log(self, line: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", line + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _start(self):
        if laspy is None:
            messagebox.showerror("Dependência em falta",
                                 f"O módulo 'laspy' não está disponível:\n{_IMPORT_ERR}\n\nInstala com:\n  pip install \"laspy[lazrs]\"")
            return

        in_dir = Path(self.in_var.get().strip())
        out_dir = Path(self.out_var.get().strip())
        if not in_dir.exists() or not in_dir.is_dir():
            messagebox.showerror("Erro", "Pasta de entrada inválida.")
            return
        if not out_dir.exists():
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível criar a pasta de saída:\n{e}")
                return

        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")
        self.prog["value"] = 0
        self.lbl_prog.config(text="0/0")

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

        self.worker = ConverterThread(
            in_dir=in_dir,
            out_dir=out_dir,
            direction=self.mode_var.get(),
            preserve=self.preserve_var.get(),
            overwrite=self.overwrite_var.get(),
            q=self.q
        )
        self.worker.start()

    def _stop(self):
        if self.worker:
            self.worker.stop_flag = True

    def _open_out(self):
        out_dir = self.out_var.get().strip()
        if not out_dir:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(out_dir)
            elif sys.platform == "darwin":
                import subprocess; subprocess.run(["open", out_dir])
            else:
                import subprocess; subprocess.run(["xdg-open", out_dir])
        except Exception:
            pass

    def _help_full(self):
        text = (
            "Como usar o Conversor LAZ ⇄ LAS\n\n"
            "1) Escolha a PASTA DE ENTRADA (com .laz e/ou .las).\n"
            "2) Escolha a PASTA DE SAÍDA.\n"
            "3) Mantenha o MODO em 'Automático' (recomendado) ou force a direção.\n"
            "4) (Opcional) Ajuste as opções 'Preservar subpastas' e 'Sobrescrever existentes'.\n"
            "5) Carregue em INICIAR (F5).\n\n"
            + HELP_COPY["boaspraticas"]
        )
        messagebox.showinfo("Ajuda", text)

    def _about_window(self):
        top = tk.Toplevel(self)
        top.title("Sobre")
        top.resizable(False, False)
        frm = ttk.Frame(top, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"{APP_TITLE} {APP_VERSION}", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="Autor: " + AUTHOR_NAME).grid(row=1, column=0, sticky="w", pady=(4,0))
        ttk.Label(frm, text="Licença: MIT").grid(row=2, column=0, sticky="w")

        def hyperlink(parent, text, url, row):
            lbl = tk.Label(parent, text=text, fg="#1a0dab", cursor="hand2", font=("Segoe UI", 10, "underline"))
            lbl.grid(row=row, column=0, sticky="w", pady=2)
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

        ttk.Separator(frm, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=8)

        hyperlink(frm, "LinkedIn: " + LINKEDIN, LINKEDIN, 4)
        hyperlink(frm, "ResearchGate: " + RESEARCHGATE, RESEARCHGATE, 5)
        hyperlink(frm, "GitHub: " + GITHUB, GITHUB, 6)

        email_frame = ttk.Frame(frm)
        email_frame.grid(row=7, column=0, sticky="w", pady=(6,0))
        ttk.Label(email_frame, text="Email: ").pack(side="left")
        email_lbl = ttk.Label(email_frame, text=AUTHOR_EMAIL)
        email_lbl.pack(side="left")
        def copy_email():
            self.clipboard_clear()
            self.clipboard_append(AUTHOR_EMAIL)
            messagebox.showinfo("Email copiado", "O endereço foi copiado para a área de transferência.")
        ttk.Button(email_frame, text="Copiar", command=copy_email).pack(side="left", padx=6)

        ttk.Button(frm, text="Fechar", command=top.destroy).grid(row=8, column=0, sticky="e", pady=(12,0))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "total":
                    total = payload
                    self.prog["maximum"] = total
                    self.lbl_prog.config(text=f"0/{total}")
                elif kind == "progress":
                    i = payload
                    self.prog["value"] = i
                    total = int(self.prog["maximum"])
                    self.lbl_prog.config(text=f"{i}/{total}")
                elif kind == "log":
                    self._append_log(payload)
                elif kind == "done":
                    conv, skip, fail, logp = payload
                    self._append_log("")
                    self._append_log(f"Resumo: Convertidos={conv}  Saltados={skip}  Falhados={fail}")
                    self._append_log(f"Log: {logp}")
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled")
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)


if __name__ == "__main__":
    app = App()
    app.mainloop()
