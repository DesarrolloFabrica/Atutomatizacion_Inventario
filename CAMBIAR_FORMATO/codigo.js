/**
 * CAMBIAR_FORMATO — codigo.js
 * ---------------------------
 * Alternativa en Google Apps Script (ejecución dentro de Google Drive).
 * Equivalente funcional a convertir_jpg_a_png.py.
 *
 * Uso:
 *   1) Extensiones → Apps Script
 *   2) Pegar este código
 *   3) Ejecutar convertirJPGaPNG
 *   4) Indicar el ID de carpeta cuando se solicite
 *
 * El flujo oficial del repositorio utiliza el script Python.
 */

function convertirJPGaPNG() {
  var idCarpeta = Browser.inputBox(
    'Conversión JPG a PNG',
    'Indique el ID de la carpeta de Drive a procesar:',
    Browser.Buttons.OK_CANCEL
  );

  if (!idCarpeta || idCarpeta === 'cancel') {
    Logger.log('Operación cancelada: no se indicó ID de carpeta.');
    return;
  }

  idCarpeta = String(idCarpeta).trim();
  var carpetaPrincipal = DriveApp.getFolderById(idCarpeta);

  var contador = 0;
  var errores = 0;

  function procesarCarpeta(carpeta) {
    var archivos = carpeta.getFilesByType(MimeType.JPEG);

    while (archivos.hasNext()) {
      var archivo = archivos.next();
      var nombreOriginal = archivo.getName();

      try {
        var blob = archivo.getBlob();
        var blobPNG = blob.getAs('image/png');
        var nuevoNombre = nombreOriginal.replace(/\.(jpg|jpeg)$/i, '') + '.png';
        blobPNG.setName(nuevoNombre);

        carpeta.createFile(blobPNG);
        archivo.setTrashed(true);

        contador++;
        Logger.log(
          'Convertido: ' + nombreOriginal + ' -> ' + nuevoNombre +
          ' (en carpeta: ' + carpeta.getName() + ')'
        );
      } catch (e) {
        errores++;
        Logger.log('Error al convertir ' + nombreOriginal + ': ' + e.message);
      }
    }

    var subcarpetas = carpeta.getFolders();
    while (subcarpetas.hasNext()) {
      procesarCarpeta(subcarpetas.next());
    }
  }

  procesarCarpeta(carpetaPrincipal);
  Logger.log(
    'Proceso terminado. Archivos convertidos: ' + contador +
    '. Errores: ' + errores
  );
}
