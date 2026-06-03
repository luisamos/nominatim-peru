<?php

$jobId = $_GET["job_id"] ?? "";
$jobId = preg_replace("/[^a-zA-Z0-9_]/", "", $jobId);

if (!$jobId) {
    die("job_id inválido");
}

$file = __DIR__ . "/outputs/output_" . $jobId . ".xlsx";

if (!file_exists($file)) {
    die("Archivo no encontrado");
}

header("Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
header("Content-Disposition: attachment; filename=DATOS_FINAL_" . $jobId . ".xlsx");
header("Content-Length: " . filesize($file));

readfile($file);
exit;