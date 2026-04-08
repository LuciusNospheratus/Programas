#!/usr/bin/env python3
"""
USB Boot Tool for Ubuntu/Linux.

Features:
- Detect removable USB drives.
- Format the selected drive (FAT32/NTFS/ext4/exFAT).
- Create bootable USB from an ISO image.
  - Windows ISO: uses WoeUSB when available.
  - Other ISOs: uses dd.

IMPORTANT:
- This app performs destructive operations.
- Run with sudo/root privileges.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional


class USBBootTool(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("USB Boot Tool (Ubuntu)")
        self.geometry("860x560")
        self.minsize(800, 520)

        self.devices: Dict[str, dict] = {}
        self.selected_device = tk.StringVar()
        self.iso_path = tk.StringVar()
        self.fs_type = tk.StringVar(value="fat32")

        self._build_ui()
        self.refresh_devices()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(
            frame,
            text="Ferramenta gráfica: detectar, formatar e tornar USB bootável",
            font=("Ubuntu", 14, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        warning = ttk.Label(
            frame,
            text=(
                "⚠️ Atenção: todas as operações apagam os dados do dispositivo selecionado. "
                "Execute como root (sudo)."
            ),
            foreground="#b00020",
            wraplength=810,
        )
        warning.pack(anchor="w", pady=(0, 12))

        # Device section
        device_box = ttk.LabelFrame(frame, text="1) Detectar pendrive", padding=10)
        device_box.pack(fill="x", pady=6)

        top_row = ttk.Frame(device_box)
        top_row.pack(fill="x")

        ttk.Label(top_row, text="Dispositivo USB removível:").pack(side="left")
        self.device_combo = ttk.Combobox(
            top_row,
            textvariable=self.selected_device,
            state="readonly",
            width=70,
        )
        self.device_combo.pack(side="left", padx=10, fill="x", expand=True)

        ttk.Button(top_row, text="Atualizar", command=self.refresh_devices).pack(side="left")

        self.device_info = ttk.Label(device_box, text="Selecione um dispositivo.")
        self.device_info.pack(anchor="w", pady=(8, 0))

        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)

        # ISO section
        iso_box = ttk.LabelFrame(frame, text="2) Selecionar ISO", padding=10)
        iso_box.pack(fill="x", pady=6)

        iso_row = ttk.Frame(iso_box)
        iso_row.pack(fill="x")

        self.iso_entry = ttk.Entry(iso_row, textvariable=self.iso_path)
        self.iso_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(iso_row, text="Procurar ISO", command=self.choose_iso).pack(side="left", padx=(10, 0))

        # Format section
        format_box = ttk.LabelFrame(frame, text="3) Formatar pendrive", padding=10)
        format_box.pack(fill="x", pady=6)

        fmt_row = ttk.Frame(format_box)
        fmt_row.pack(fill="x")

        ttk.Label(fmt_row, text="Sistema de arquivos:").pack(side="left")
        fs_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.fs_type,
            state="readonly",
            values=["fat32", "ntfs", "exfat", "ext4"],
            width=12,
        )
        fs_combo.pack(side="left", padx=8)

        ttk.Button(fmt_row, text="Formatar USB", command=self.format_selected).pack(side="left", padx=10)

        # Boot section
        boot_box = ttk.LabelFrame(frame, text="4) Tornar bootável", padding=10)
        boot_box.pack(fill="x", pady=6)

        boot_row = ttk.Frame(boot_box)
        boot_row.pack(fill="x")

        ttk.Button(boot_row, text="Criar USB bootável", command=self.make_bootable).pack(side="left")

        ttk.Label(
            boot_box,
            text=(
                "Windows ISO: tenta usar WoeUSB (recomendado).\n"
                "Outras ISOs: gravação com dd."
            ),
        ).pack(anchor="w", pady=(8, 0))

        # Logs
        log_box = ttk.LabelFrame(frame, text="Logs", padding=10)
        log_box.pack(fill="both", expand=True, pady=6)

        self.log_text = tk.Text(log_box, height=14, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def run_cmd(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        self.log(f"$ {' '.join(cmd)}")
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.stdout.strip():
            self.log(proc.stdout.strip())
        if proc.stderr.strip():
            self.log(proc.stderr.strip())
        if check and proc.returncode != 0:
            raise RuntimeError(f"Comando falhou ({proc.returncode}): {' '.join(cmd)}")
        return proc

    def refresh_devices(self) -> None:
        try:
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,PATH,RM,MODEL,SIZE,TYPE,TRAN"],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(result.stdout)
        except Exception as exc:
            messagebox.showerror("Erro", f"Não foi possível listar dispositivos: {exc}")
            return

        self.devices.clear()
        labels = []

        for dev in data.get("blockdevices", []):
            if dev.get("type") != "disk":
                continue
            is_usb = dev.get("rm") in (1, True) or dev.get("tran") == "usb"
            if not is_usb:
                continue

            path = dev.get("path") or f"/dev/{dev['name']}"
            model = (dev.get("model") or "").strip() or "USB"
            size = dev.get("size", "?")
            label = f"{path} — {model} ({size})"
            labels.append(label)
            self.devices[label] = dev

        self.device_combo["values"] = labels
        if labels:
            self.selected_device.set(labels[0])
            self._on_device_selected(None)
            self.log("Dispositivos USB atualizados.")
        else:
            self.selected_device.set("")
            self.device_info.configure(text="Nenhum pendrive detectado.")
            self.log("Nenhum pendrive removível foi detectado.")

    def _on_device_selected(self, _event) -> None:
        label = self.selected_device.get()
        dev = self.devices.get(label)
        if not dev:
            self.device_info.configure(text="Selecione um dispositivo.")
            return

        path = dev.get("path") or f"/dev/{dev['name']}"
        txt = (
            f"Selecionado: {path} | Modelo: {(dev.get('model') or 'USB').strip()} | "
            f"Tamanho: {dev.get('size', '?')}"
        )
        self.device_info.configure(text=txt)

    def choose_iso(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione a imagem ISO",
            filetypes=[("ISO", "*.iso"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.iso_path.set(path)
            self.log(f"ISO selecionada: {path}")

    def get_selected_device_path(self) -> Optional[str]:
        label = self.selected_device.get()
        dev = self.devices.get(label)
        if not dev:
            messagebox.showwarning("Atenção", "Selecione um pendrive primeiro.")
            return None
        return dev.get("path") or f"/dev/{dev['name']}"

    def _confirm_destruction(self, path: str, action: str) -> bool:
        return messagebox.askyesno(
            "Confirmação obrigatória",
            (
                f"Você está prestes a {action} em {path}.\n\n"
                "TODOS os dados serão apagados.\n\nDeseja continuar?"
            ),
        )

    def format_selected(self) -> None:
        path = self.get_selected_device_path()
        if not path:
            return

        fs = self.fs_type.get().lower()
        if fs not in {"fat32", "ntfs", "exfat", "ext4"}:
            messagebox.showerror("Erro", "Sistema de arquivos inválido.")
            return

        if not self._confirm_destruction(path, f"formatar o dispositivo"):
            return

        threading.Thread(target=self._format_worker, args=(path, fs), daemon=True).start()

    def _format_worker(self, device: str, fs: str) -> None:
        try:
            self.log(f"Iniciando formatação de {device} como {fs}...")
            self.run_cmd(["umount", f"{device}1"], check=False)
            self.run_cmd(["umount", device], check=False)

            self.run_cmd(["wipefs", "-a", device])
            self.run_cmd(["parted", "-s", device, "mklabel", "msdos"])
            self.run_cmd(["parted", "-s", device, "mkpart", "primary", "0%", "100%"])

            part = f"{device}1"
            if "nvme" in device or "mmcblk" in device:
                part = f"{device}p1"

            self.run_cmd(["udevadm", "settle"], check=False)

            if fs == "fat32":
                self.run_cmd(["mkfs.vfat", "-F", "32", "-n", "USBBOOT", part])
            elif fs == "ntfs":
                self.run_cmd(["mkfs.ntfs", "-f", "-L", "USBBOOT", part])
            elif fs == "exfat":
                self.run_cmd(["mkfs.exfat", "-n", "USBBOOT", part])
            else:
                self.run_cmd(["mkfs.ext4", "-F", "-L", "USBBOOT", part])

            self.log("Formatação concluída com sucesso.")
            messagebox.showinfo("Sucesso", f"{device} formatado como {fs}.")
        except Exception as exc:
            self.log(f"Erro na formatação: {exc}")
            messagebox.showerror("Erro", str(exc))

    def make_bootable(self) -> None:
        device = self.get_selected_device_path()
        if not device:
            return

        iso = self.iso_path.get().strip()
        if not iso or not os.path.isfile(iso):
            messagebox.showwarning("Atenção", "Selecione uma ISO válida.")
            return

        if not self._confirm_destruction(device, "gravar a ISO (modo bootável)"):
            return

        threading.Thread(target=self._boot_worker, args=(device, iso), daemon=True).start()

    def _is_windows_iso(self, iso_path: str) -> bool:
        name = os.path.basename(iso_path).lower()
        windows_markers = ["windows", "win10", "win11", "win8", "win7"]
        return any(marker in name for marker in windows_markers)

    def _boot_worker(self, device: str, iso: str) -> None:
        try:
            self.log(f"Preparando gravação bootável: {iso} -> {device}")
            self.run_cmd(["umount", f"{device}1"], check=False)
            self.run_cmd(["umount", device], check=False)

            is_windows = self._is_windows_iso(iso)
            woeusb_bin = shutil.which("woeusb") or shutil.which("woeusb-ng")

            if is_windows and woeusb_bin:
                self.log("ISO de Windows detectada. Usando WoeUSB...")
                if "woeusb-ng" in woeusb_bin:
                    self.run_cmd([woeusb_bin, "--device", iso, device])
                else:
                    self.run_cmd([woeusb_bin, "--target-filesystem", "NTFS", "--device", iso, device])
            else:
                if is_windows and not woeusb_bin:
                    self.log(
                        "WoeUSB não encontrado. Para ISOs do Windows, instale o WoeUSB para maior compatibilidade."
                    )
                self.log("Gravando ISO com dd (isso pode demorar)...")
                self.run_cmd(["dd", f"if={iso}", f"of={device}", "bs=4M", "status=progress", "oflag=sync"])
                self.run_cmd(["sync"])

            self.log("USB bootável criado com sucesso.")
            messagebox.showinfo("Sucesso", "Pendrive bootável criado com sucesso.")
        except Exception as exc:
            self.log(f"Erro ao criar bootável: {exc}")
            messagebox.showerror("Erro", str(exc))


def main() -> None:
    app = USBBootTool()
    app.mainloop()


if __name__ == "__main__":
    main()
