<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Geocodificador Nominatim</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background: #f5f6f8;
        }

        .card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            max-width: 800px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.12);
        }

        .progress-container {
            width: 100%;
            background: #ddd;
            border-radius: 20px;
            margin-top: 20px;
            overflow: hidden;
        }

        .progress-bar {
            width: 0%;
            height: 28px;
            background: #198754;
            color: white;
            text-align: center;
            line-height: 28px;
            transition: width 0.3s;
        }

        .estado {
            margin-top: 20px;
            font-size: 14px;
        }

        .ok { color: #198754; }
        .error { color: #dc3545; }
        .warning { color: #fd7e14; }

        button {
            background: #0d6efd;
            color: white;
            padding: 10px 18px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }

        input[type="file"] {
            margin: 15px 0;
        }

        a.btn {
            display: inline-block;
            margin-top: 15px;
            background: #198754;
            color: white;
            padding: 10px 15px;
            border-radius: 6px;
            text-decoration: none;
        }
    </style>
</head>
<body>

<div class="card">
    <h2>Geocodificador masivo con Nominatim local</h2>

    <form id="formUpload" enctype="multipart/form-data">
        <label>Archivo CSV / XLSX / XLS:</label><br>
        <input type="file" name="archivo" accept=".csv,.xlsx,.xls" required><br>

        <label>URL Nominatim:</label><br>
        <input type="text" name="url" value="http://localhost" style="width:100%;padding:8px;"><br><br>

        <button type="submit">Iniciar geocodificación</button>
    </form>

    <div class="progress-container">
        <div id="barra" class="progress-bar">0%</div>
    </div>

    <div id="estado" class="estado">
        Esperando archivo...
    </div>

    <div id="descarga"></div>
</div>

<script>
let jobId = null;
let interval = null;

document.getElementById("formUpload").addEventListener("submit", function(e) {
    e.preventDefault();

    let formData = new FormData(this);

    document.getElementById("estado").innerHTML = "Subiendo archivo...";
    document.getElementById("descarga").innerHTML = "";

    fetch("upload.php", {
        method: "POST",
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) {
            document.getElementById("estado").innerHTML = "<span class='error'>" + data.mensaje + "</span>";
            return;
        }

        jobId = data.job_id;
        document.getElementById("estado").innerHTML = "Proceso iniciado...";
        consultarEstado();

        interval = setInterval(consultarEstado, 1500);
    })
    .catch(err => {
        document.getElementById("estado").innerHTML = "<span class='error'>Error: " + err + "</span>";
    });
});

function consultarEstado() {
    fetch("status.php?job_id=" + encodeURIComponent(jobId))
    .then(r => r.json())
    .then(data => {
        let porcentaje = data.porcentaje || 0;

        let barra = document.getElementById("barra");
        barra.style.width = porcentaje + "%";
        barra.innerHTML = porcentaje + "%";

        document.getElementById("estado").innerHTML = `
            <b>Estado:</b> ${data.estado}<br>
            <b>Mensaje:</b> ${data.mensaje || ""}<br>
            <b>Procesados:</b> ${data.procesados || 0} / ${data.total || 0}<br>
            <span class="ok"><b>OK:</b> ${data.ok || 0}</span> |
            <span class="warning"><b>No encontrado:</b> ${data.no_encontrado || 0}</span> |
            <span class="error"><b>Errores:</b> ${data.errores || 0}</span>
        `;

        if (data.estado === "FINALIZADO") {
            clearInterval(interval);
            document.getElementById("descarga").innerHTML =
                `<a class="btn" href="download.php?job_id=${encodeURIComponent(jobId)}">Descargar Excel final</a>`;
        }

        if (data.estado === "ERROR") {
            clearInterval(interval);
        }
    });
}
</script>

</body>
</html>