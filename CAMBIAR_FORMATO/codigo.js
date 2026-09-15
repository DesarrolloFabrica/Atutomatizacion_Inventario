/**
 * CAMBIAR_FORMATO — codigo.js
 * ---------------------------
 * Versión alternativa en Google Apps Script (se corre DENTRO de Google,
 * no con Python en la PC).
 *
 * Hace lo mismo que convertir_jpg_a_png.py:
 *   JPG → PNG en una carpeta de Drive y subcarpetas; JPG a papelera.
 *
 * Cómo usarlo:
 *   1) En drive.google.com → Extensiones → Apps Script
 *   2) Pegar este código
 *   3) Cambiar idCarpeta al ID de tu carpeta
 *   4) Ejecutar convertirJPGaPNG
 *
 * El flujo oficial del repo usa el script Python; este JS es respaldo/legado.
 */

function convertirJPGaPNG() {
  // # Aquí se define el ID de la carpeta raíz a procesar (cambiar según el lote).
  var idCarpeta = '1LexISrqWxiC3tAgfq3SQjyL6Pxh_0-GM';
  // # Aquí se obtiene el objeto carpeta de Drive.
  var carpetaPrincipal = DriveApp.getFolderById(idCarpeta);

  // Contadores de resultado.
  var contador = 0;
  var errores = 0;

  function procesarCarpeta(carpeta) {
    // # Aquí se listan los JPG de ESTA carpeta.
    var archivos = carpeta.getFilesByType(MimeType.JPEG);

    while (archivos.hasNext()) {
      var archivo = archivos.next();
      var nombreOriginal = archivo.getName();

      try {
        // # Aquí se convierte el blob JPG a PNG.
        var blob = archivo.getBlob();
        var blobPNG = blob.getAs('image/png');

        // # Aquí se cambia la extensión del nombre a .png.
        var nuevoNombre = nombreOriginal.replace(/\.(jpg|jpeg)$/i, '') + '.png';
        blobPNG.setName(nuevoNombre);

        // # Aquí se crea el PNG y se manda el JPG a la papelera.
        carpeta.createFile(blobPNG);
        archivo.setTrashed(true);

        contador++;
        Logger.log('Convertido: ' + nombreOriginal + ' -> ' + nuevoNombre + ' (en carpeta: ' + carpeta.getName() + ')');

      } catch (e) {
        errores++;
        Logger.log('Error al convertir ' + nombreOriginal + ': ' + e.message);
      }
    }

    // # Aquí se entra recursivamente a cada subcarpeta.
    var subcarpetas = carpeta.getFolders();
    while (subcarpetas.hasNext()) {
      procesarCarpeta(subcarpetas.next());
    }
  }

  // Arranca desde la carpeta raíz.
  procesarCarpeta(carpetaPrincipal);

  Logger.log('Proceso terminado. Archivos convertidos: ' + contador + '. Errores: ' + errores);
}
