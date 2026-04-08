# USB Boot Tool (Ubuntu)

Programa gráfico em Python/Tkinter para Linux Ubuntu que:

1. Detecta pendrives USB removíveis.
2. Formata o pendrive (FAT32, NTFS, exFAT ou ext4).
3. Grava ISO para deixar o pendrive bootável.
   - ISOs de Windows: prioriza `woeusb`/`woeusb-ng`.
   - Outras ISOs: usa `dd`.

## Requisitos

- Ubuntu Linux
- Python 3
- Dependências de sistema:

```bash
sudo apt update
sudo apt install -y python3 python3-tk util-linux parted dosfstools ntfs-3g exfatprogs
```

Para melhor suporte a ISOs de Windows:

```bash
# pacote pode variar conforme versão do Ubuntu
sudo apt install -y woeusb
```

## Execução

> **Importante:** execute como root para permitir formatação e gravação em bloco.

```bash
sudo python3 usb_boot_tool.py
```

## Observações de segurança

- A ferramenta é **destrutiva**: o dispositivo selecionado terá dados apagados.
- Confira com atenção o `/dev/sdX` selecionado antes de formatar ou gravar a ISO.
