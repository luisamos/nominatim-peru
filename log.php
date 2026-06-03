<?php
header("Content-Type: application/json; charset=utf-8");

$jobId = $_GET["job_id"] ?? "";
$jobId = preg_replace("/[^a-zA-Z0-9_]/", "", $jobId);

if (!$jobId) {
    echo json_encode([
        "ok" => false,
        "mensaje" => "job_id inválido",
        "log" => ""
    ]);
    exit;
}

$logPath = __DIR__ . "/logs/job_" . $jobId . ".log";

if (!file_exists($logPath)) {
    echo json_encode([
        "ok" => true,
        "mensaje" => "Log todavía no generado",
        "log" => ""
    ]);
    exit;
}

$contenido = file_get_contents($logPath);

// Últimos 8000 caracteres para no cargar demasiado
$contenido = substr($contenido, -8000);

echo json_encode([
    "ok" => true,
    "mensaje" => "OK",
    "log" => $contenido
], JSON_UNESCAPED_UNICODE);