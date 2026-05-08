================================================================
       EXCEL COMBINER / COMBINADOR DE EXCEL
================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESPAÑOL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

¿QUÉ HACE?
  Combina automáticamente todos los archivos Excel (.xlsx) que
  estén en la misma carpeta que el programa, agrupándolos por
  estructura de columnas.

¿CÓMO SE USA?
  1. Pon el archivo "Combinador Excel.exe" en la misma carpeta
     que los archivos Excel que quieras combinar.
  2. Haz doble clic en "Combinador Excel.exe".
  3. Se abrirá una ventana mostrando el progreso y el resumen.
  4. Al terminar aparecerá el archivo combinado en la misma
     carpeta con el nombre: Combined_Excel_YYYYMMDD_HHMMSS.xlsx
  5. Pulsa Enter para cerrar la ventana.

REGLAS DE COMBINACIÓN:
  - Solo se combinan archivos que tengan exactamente las mismas
    columnas (el orden de las columnas no importa).
  - Si hay archivos con distintas columnas, se genera un archivo
    de salida separado por cada grupo.
  - Los archivos que no coincidan con ningún otro se omiten.
  - El formato de las celdas se ignora; solo se copian los datos.

ARCHIVO DE SALIDA:
  - Nombre: Combined_Excel_YYYYMMDD_HHMMSS.xlsx
    Ejemplo: Combined_Excel_20260506_143000.xlsx
  - Se añade automáticamente una columna "Origen" al final
    indicando de qué archivo Excel proviene cada fila.
  - Si hay varios grupos de columnas distintas, se generan
    varios archivos: Combined_Excel_..._1.xlsx, ..._2.xlsx, etc.

NOTAS:
  - Los archivos llamados "Combined_Excel_..." se excluyen
    automáticamente para evitar combinar resultados anteriores.
  - No es necesario instalar Python ni ningún programa adicional.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENGLISH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT DOES IT DO?
  Automatically combines all Excel files (.xlsx) located in the
  same folder as the program, grouping them by column structure.

HOW TO USE IT?
  1. Place "Combinador Excel.exe" in the same folder as the
     Excel files you want to combine.
  2. Double-click "Combinador Excel.exe".
  3. A window will open showing progress and a summary.
  4. When done, the combined file will appear in the same folder
     named: Combined_Excel_YYYYMMDD_HHMMSS.xlsx
  5. Press Enter to close the window.

COMBINATION RULES:
  - Only files with exactly the same columns are combined
    (column order does not matter).
  - If files have different column structures, a separate output
    file is generated for each group.
  - Files that do not match any other file are skipped.
  - Cell formatting is ignored; only data values are copied.

OUTPUT FILE:
  - Name: Combined_Excel_YYYYMMDD_HHMMSS.xlsx
    Example: Combined_Excel_20260506_143000.xlsx
  - A column called "Origen" (Source) is automatically added at
    the end, indicating which Excel file each row came from.
  - If there are multiple groups with different columns, several
    files are generated: Combined_Excel_..._1.xlsx, ..._2.xlsx, etc.

NOTES:
  - Files named "Combined_Excel_..." are automatically excluded
    to avoid re-combining previous results.
  - No need to install Python or any additional software.

================================================================
