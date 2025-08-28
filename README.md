# Conversor LAZ ⇄ LAS (v1.2.1)

GUI em **Tkinter** para converter entre **LAZ** (comprimido) e **LAS** (não comprimido), baseada em `laspy[lazrs]`.
Sem necessidade de PDAL/LAStools nem linha de comandos para o utilizador final.

---

## ⬇️ Como descarregar o executável (Windows)

> **Recomendado para utilizadores comuns (sem Python):** use o executável pronto em *Releases*.

1. Abra a página de **Releases** do projeto:
   - **Link direto para a última release:** https://github.com/edgarfigueira/laz-las-converter/releases/latest
2. Clique na release **v1.2.1** (ou a mais recente que aparecer).
3. Na secção **Assets**, faça download de **`LAZ_LAS_Converter.exe`**.
4. Execute o ficheiro `.exe`. Não precisa de instalar nada.
   - Se o Windows avisar com *SmartScreen*, clique em **Mais informações → Executar mesmo assim**.

> Se não vir o ficheiro `.exe` nos *Assets*, o autor ainda não o anexou. Siga as instruções em “Publicar o executável na Release” abaixo.

---

## ▶️ Como usar o programa (3 passos)

1. **Entrada:** escolha a pasta com ficheiros `.laz` e/ou `.las` (procura recursiva).
2. **Saída:** escolha a pasta onde quer guardar os ficheiros convertidos.
3. Carregue em **Iniciar** (deixe o *Modo* em **Automático** para decidir LAZ→LAS ou LAS→LAZ).

- A aplicação **preserva subpastas**, **salta ficheiros já convertidos** e cria um **log** na pasta de saída.
- Atalhos: `F1` Ajuda • `F5` Iniciar • `Esc` Parar.

---

## 🧪 Notas úteis

- **Espaço em disco:** `.las` pode ocupar ~5–10× o `.laz`. Planeie antes de converter grandes volumes.
- **Cloud/OneDrive:** pausar a sincronização pode acelerar e evitar ficheiros bloqueados.
- **Integridade:** metadados (classes, intensidades, CRS/WKT) são preservados por `laspy`.

---

## 🧰 Para quem quer correr a partir do código (dev)

```bash
pip install "laspy[lazrs]"
python app/LAZ_LAS_Converter_Public_v1_2_1.py
```

### Construir o executável (PyInstaller)
```bash
pyinstaller --onefile --noconsole -n LAZ_LAS_Converter app/LAZ_LAS_Converter_Public_v1_2_1.py
```
Saída: `dist/LAZ_LAS_Converter.exe`

---

## 📤 Publicar o executável na Release (para o autor)

1. Crie o `.exe` com PyInstaller (ver acima).
2. Vá a **Releases → Draft a new release** (ou edite a existente `v1.2.1`).
3. Em **Assets**, **anexe** o ficheiro `dist/LAZ_LAS_Converter.exe`.
4. Clique **Publish release**.

Os utilizadores passam então a descarregar o `.exe` em:
- https://github.com/edgarfigueira/laz-las-converter/releases/latest

---

## 👤 Autor / Contactos

- **LinkedIn:** https://www.linkedin.com/in/edgarfigueira/
- **ResearchGate:** https://www.researchgate.net/profile/Edgar-Figueira-2?ev=hdr_xprf
- **GitHub:** https://github.com/edgarfigueira
- **Email:** edgarjunceiro@gmail.com
