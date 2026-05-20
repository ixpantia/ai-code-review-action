#### Checklist para SQL
- [ ] La ortografía en comentarios y documentación es correcta  
- [ ] El código tiene suficientes comentarios para entenderlo  
- [ ] Los comentarios están actualizados  
- [ ] No hay pedazos de código comentado  

- [ ] Los nombres utilizados para los objetos (tablas, columnas, vistas...) son lo suficientemente descriptivos  
- [ ] Los nombres utilizados para los objetos son consistentes (de preferencia snake_case)  
- [ ] Evitar nombres que sean palabras reservadas  
- [ ] En los nombres, utilizar letras, números y guiones bajos solamente  
- [ ] Utilizar `AS` al crear un alias  
- [ ] Escoger alias cortos pero descriptivos y que tengan relación con el objeto referenciado  

- [ ] Las palabras clave de SQL, funciones y tipos de datos van en mayúscula  (por ejemplo `SELECT`, `WHERE`, `ROW_NUMBER`...)  
- [ ] El código está correctamente indentado para reflejar su estructura (cláusulas, subconsultas, CASE)  
- [ ] Hay un uso consistente de espacios alrededor de operadores (`=`, `+`, `<>`) para facilitar la lectura.  
- [ ] La longitud de las líneas de código no debe ser excesiva (en lo posible 80 a 120 caracteres)  
- [ ] El uso de comas es consistente para todo el código (al listar columnas por ejemplo)  

- [ ] Evitar el uso de `SELECT *` a menos que haya una justificación válida  
- [ ] Los filtros `WHERE` están correctamente justificados y entendidos para evitar excluir y/o incluir datos por error
- [ ] Verificar si los filtros que existen pueden ser aplicados lo antes posible para optimizar y reducir el volumen de datos 
- [ ] Al utilizar Window Functions, verificar que tengan correctamente definidos el `PARTITION BY` y el `ORDER BY`   
- [ ] Se usa el tipo de JOIN correcto para la lógica de negocio (`INNER`, `LEFT`, `RIGHT`, `FULL OUTER`)  

- [ ] Manejo de NULLs: se utilizan los operadores adecuados para tratar con NULLs, ya que las comparaciones directas (=, <>) resultan en UNKNOWN, lo que puede resultar en pérdida de información:  
    - [ ] Se usa `IS NULL` o `IS NOT NULL` para comparar con valores nulos, nunca `columna = NULL`  
    - [ ] Para comparar por igualdad, preferir utilizar `IS NOT DISTINCT FROM`  
    - [ ] Para comparar por desigualdad, preferir utilizar `IS DISTINCT FROM`  
    - Nota: `IS NOT DISTINCT FROM` no es compatible con MySQL, donde existe el operador equivalente `<=>`  
- [ ] Si se utiliza una división (/), asegurarse evitar errores cuando el denominador es cero. Se puede utilizar por ejemplo `NULLIF(denominador, 0)`  

- [ ] Si se crea una vista, asegurarse de haberla seleccionado (`SELECT * FROM vista`) para verificar que el código que la crea no contiene errores  
- [ ] Si se crea una tabla o vista, verificar que no contenga duplicados si se conocen las llaves  
- [ ] Si se crea una tabla o vista, verificar que los tipos de datos son los esperados  