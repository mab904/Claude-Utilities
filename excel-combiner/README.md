# Combinador de Excel / Excel Combiner


 

## Español

### ¿Qué hace?

Combina automáticamente todos los archivos Excel (`.xlsx`) que estén en la misma carpeta que el programa, agrupándolos por estructura de columnas.

### ¿Cómo se usa?

1. Compilar el `combinador.py`.
2. Pon el archivo `Combinador Excel.exe` en la misma carpeta que los archivos Excel que quieras combinar.
3. Haz doble clic en `Combinador Excel.exe`.
4. Se abrirá una ventana mostrando el progreso y el resumen.
5. Al terminar aparecerá el archivo combinado en la misma carpeta con el nombre: `Combined_Excel_YYYYMMDD_HHMMSS.xlsx`
6. Pulsa Enter para cerrar la ventana.

### Reglas de combinación

- Solo se combinan archivos que tengan exactamente las mismas columnas (el orden de las columnas no importa).
- Si hay archivos con distintas columnas, se genera un archivo de salida separado por cada grupo.
- Los archivos que no coincidan con ningún otro se omiten.
- El formato de las celdas se ignora, solo copia los datos.

### Archivo de salida

- Nombre: `Combined_Excel_YYYYMMDD_HHMMSS.xlsx`
- Se añade automáticamente una columna `Origen` al final indicando de qué archivo Excel proviene cada fila.
- Si hay varios grupos de columnas distintas, se generan varios archivos: `Combined_Excel_..._1.xlsx`, `Combined_Excel_..._2.xlsx`, etc.

### Notas

- Los archivos llamados `Combined_Excel_...` se excluyen automáticamente para evitar combinar resultados anteriores y que se mezclen.
- Librerías utilizadas: pandas, openpyxl y python-calamine

---

## English

### What does it do?

Automatically combines all Excel files (`.xlsx`) located in the same folder as the program, grouping them by column structure.

### How to use it?

1. Compile `combinador.py`.
2. Place `Combinador Excel.exe` in the same folder as the Excel files you want to combine.
3. Double-click `Combinador Excel.exe`.
4. A window will open showing progress and a summary.
5. When done, the combined file will appear in the same folder named: `Combined_Excel_YYYYMMDD_HHMMSS.xlsx`
6. Press Enter to close the window.

### Combination rules

- Only files with exactly the same columns are combined (column order does not matter).
- If files have different column structures, a separate output file is generated for each group.
- Files that do not match any other file are skipped.
- Cell formatting is ignored, only the data is copied.

### Output file

- Name: `Combined_Excel_YYYYMMDD_HHMMSS.xlsx`
- A column called `Origen` (Source) is automatically added at the end, indicating which Excel file each row came from.
- If there are multiple groups with different columns, several files are generated: `Combined_Excel_..._1.xlsx`, `Combined_Excel_..._2.xlsx`, etc.

### Notes

- Files named `Combined_Excel_...` are automatically excluded to avoid re-combining and mixing previous results.
- Libraries used: pandas, openpyxl and python-calamine 

