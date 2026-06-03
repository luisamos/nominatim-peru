<?php
header("Content-Type: application/json; charset=utf-8");

$jobId = $_GET["job_id"] ?? "";
$jobId = preg_replace("/[^a-zA-Z0-9_]/", "", $jobId);

if (!$jobId) {
    echo json_encode([
        "estado" => "ERROR",
        "mensaje" => "job_id inválido",
        "porcentaje" => 0
    ]);
    exit;
}

$progressPath = __DIR__ . "/progress/progress_" . $jobId . ".json";

if (!file_exists($progressPath)) {
    echo json_encode([
        "estado" => "INICIANDO",
        "mensaje" => "Esperando inicio del proceso",
        "porcentaje" => 0,
        "procesados" => 0,
        "total" => 0,
        "ok" => 0,
        "no_encontrado" => 0,
        "errores" => 0
    ]);
    exit;
}

echo file_get_contents($progressPath);