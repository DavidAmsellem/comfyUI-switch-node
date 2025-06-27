// Fragmento para mostrar la imagen generada en el frontend (web_client.html)
// Inserta esto dentro de la función displayResults(data, processId = null)

function displayResults(data, processId = null) {
    const resultsSection = document.getElementById('resultsSection');
    const resultImages = document.getElementById('resultImages');
    resultImages.innerHTML = '';

    // Mostrar la imagen final si existe la URL
    if (data.final_image_url) {
        const img = document.createElement('img');
        img.src = data.final_image_url;
        img.alt = 'Imagen generada';
        img.className = 'result-image loaded';
        resultImages.appendChild(img);

        // Botón de descarga
        const downloadBtn = document.createElement('a');
        downloadBtn.href = data.final_image_url;
        downloadBtn.download = data.final_image?.filename || 'output.png';
        downloadBtn.className = 'download-btn';
        downloadBtn.textContent = 'Descargar imagen';
        resultImages.appendChild(downloadBtn);
    }
    // ...resto de tu lógica para mostrar otros resultados...
    resultsSection.style.display = 'block';
}
