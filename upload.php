<?php
header("Content-Type: application/json; charset=utf-8");

$baseDir = __DIR__;
$uploadDir = $baseDir . "/uploads";
$outputDir = $baseDir . "/outputs";
$progressDir = $baseDir . "/progress";
$logDir = $baseDir . "/logs";

if (!isset($_FILES["archivo"])) {
    echo json_encode([
        "ok" => false,
        "mensaje" => "No se recibió archivo."
    ]);
    exit;
}

$url = $_POST["url"] ?? "http://localhost";
$url = trim($url);

$archivo = $_FILES["archivo"];
$ext = strtolower(pathinfo($archivo["name"], PATHINFO_EXTENSION));

$permitidos = ["csv", "xlsx", "xls"];

if (!in_array($ext, $permitidos)) {
    echo json_encode([
        "ok" => false,
        "mensaje" => "Formato no permitido. Usa CSV, XLSX o XLS."
    ]);
    exit;
}

$jobId = date("YmdHis") . "_" . bin2hex(random_bytes(4));

$inputPath = $uploadDir . "/input_" . $jobId . "." . $ext;
$outputPath = $outputDir . "/output_" . $jobId . ".xlsx";
$progressPath = $progressDir . "/progress_" . $jobId . ".json";
$logPath = $logDir . "/job_" . $jobId . ".log";

if (!move_uploaded_file($archivo["tmp_name"], $inputPath)) {
    echo json_encode([
        "ok" => false,
        "mensaje" => "No se pudo guardar el archivo."
    ]);
    exit;
}

$python = "/usr/bin/python3";
$script = $baseDir . "/scripts/buscar_web.py";

$cmd = sprintf(
    'nohup %s %s --input %s --output %s --progress %s --url %s > %s 2>&1 & echo $!',
    escapeshellcmd($python),
    escapeshellarg($script),
    escapeshellarg($inputPath),
    escapeshellarg($outputPath),
    escapeshellarg($progressPath),
    escapeshellarg($url),
    escapeshellarg($logPath)
);

$pid = trim(shell_exec($cmd));

echo json_encode([
    "ok" => true,
    "mensaje" => "Proceso iniciado.",
    "job_id" => $jobId,
    "pid" => $pid
]);