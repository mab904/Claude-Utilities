import os
import sys
import pandas as pd
from collections import defaultdict
from datetime import datetime


def get_exe_dir():
    # Cuando se ejecuta como .exe (PyInstaller), sys.executable apunta al .exe
    # En modo script normal, usamos la ruta del propio .py
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def normalize_cols(columns):
    # Convierte las columnas a minúsculas y sin espacios para comparar
    # independientemente del orden o mayúsculas
    # Las columnas "Unnamed:..." son columnas vacías de Excel y se descartan
    return frozenset(str(c).strip().lower() for c in columns if not str(c).startswith("Unnamed:"))


def print_separator(char="=", width=60):
    print(char * width)


def main():
    folder = get_exe_dir()

    # Busca todos los .xlsx de la carpeta, excluyendo archivos generados
    # por el propio programa para evitar combinar resultados anteriores y que no se líe
    xlsx_files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith(".xlsx")
        and not f.lower().startswith("combined_excel_")
        and not f.upper().startswith("COMBINADO_")
    )

    print_separator()
    print("       EXCEL COMBINER / COMBINADOR DE EXCEL")
    print_separator()

    if not xlsx_files:
        print("\n[EN] No Excel files found in the folder.")
        print("[ES] No se encontraron archivos Excel en la carpeta.")
        input("\nPress Enter to exit / Pulsa Enter para salir...")
        return

    print(f"\n[EN] Excel files found: {len(xlsx_files)}")
    print(f"[ES] Archivos Excel encontrados: {len(xlsx_files)}")
    print("\n  " + "\n  ".join(xlsx_files))

    # groups: agrupa los DataFrames por conjunto de columnas
    # group_canonical_cols: guarda el orden de columnas del primer archivo
    # de cada grupo para usarlo como referencia al combinar
    groups = defaultdict(list)
    group_canonical_cols = {}
    errors = []

    print("\n[EN] Reading files... / [ES] Leyendo archivos...")

    for filename in xlsx_files:
        filepath = os.path.join(folder, filename)
        try:
            # Leemos todas las hojas del Excel con el motor "calamine"
            # que es compatible con Python 3.14 (openpyxl falla)
            all_sheets = pd.read_excel(filepath, sheet_name=None, engine="calamine")
            for _, df in all_sheets.items():
                # Eliminamos columnas vacías (sin nombre) y filas completamente vacías.
                df = df.loc[:, ~df.columns.str.startswith("Unnamed:")]
                df = df.dropna(how="all")
                if df.empty or len(df.columns) == 0:
                    continue

                # Usamos el conjunto de columnas normalizadas como clave de grupo
                key = normalize_cols(df.columns)
                if key not in group_canonical_cols:
                    group_canonical_cols[key] = list(df.columns)
                groups[key].append((filename, df))
        except Exception as e:
            errors.append(f"  {filename}: {e}")

    if errors:
        print(f"\n[EN] Files with errors ({len(errors)}):")
        print(f"[ES] Archivos con errores ({len(errors)}):")
        for msg in errors:
            print(msg)

    if not groups:
        print("\n [EN] Could not read any file correctly.")
        print("[ES] No se pudo leer ningún archivo correctamente.")
        input("\nPress Enter to exit / Pulsa Enter para salir...")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    n_groups = len(groups)
    saved = []
    skipped = []

    for i, (key, entries) in enumerate(groups.items(), 1):
        # Si un grupo tiene solo un archivo, no hay nada que combinar
        if len(entries) < 2:
            skipped.append(entries[0][0])
            continue

        canonical_cols = group_canonical_cols[key]
        dfs = []
        for filename, df in entries:
            # Reoordenamos las columnas de cada archivo para que coincidan
            # con el orden del primero del grupo antes de concatenar
            df = df.reindex(columns=canonical_cols)
            # Añadimos columna "Origen" para saber de qué archivo viene cada fila
            df["Origen"] = filename
            dfs.append(df)

        # Concatenamos todos los DataFrames del grupo en uno solo
        combined = pd.concat(dfs, ignore_index=True)

        # Si hay varios grupos, añadimos _1, _2... al nombre para poder diferenciarlos
        suffix = f"_{i}" if n_groups > 1 else ""
        output_name = f"Combined_Excel_{timestamp}{suffix}.xlsx"
        output_path = os.path.join(folder, output_name)

        combined.to_excel(output_path, index=False, engine="openpyxl")
        saved.append((output_name, [e[0] for e in entries], len(combined)))

    # Mostramos el resumen final
    print_separator()
    print("                    SUMMARY / RESUMEN")
    print_separator()

    if skipped:
        print(f"\n[EN] Skipped ({len(skipped)}) — unique columns, no matching files:")
        print(f"[ES] Saltados ({len(skipped)}) — columnas únicas, sin coincidencias:")
        for fn in skipped:
            print(f"  - {fn}")

    if saved:
        for output_name, filenames, n_rows in saved:
            print(f"\n[EN] Combined {len(filenames)} files into 1 output file.")
            print(f"[ES] Se combinaron {len(filenames)} archivos en 1 archivo de salida.")
            print(f"\n  Output file / Archivo de salida : {output_name}")
            print(f"  Total rows / Filas totales       : {n_rows}")
            print(f"  Files combined / Archivos combinados ({len(filenames)}):")
            for fn in filenames:
                print(f"    - {fn}")
    else:
        print("\n[EN] No files were combined (all have unique column structures).")
        print("[ES] No se combinó ningún archivo (todos tienen columnas únicas).")

    print_separator()
    input("\nPress Enter to exit / Pulsa Enter para salir...")


if __name__ == "__main__": #Esto es para que el programa se ejecute solo si se llama
    main() # directamente, no al importar como módulo en otro programa