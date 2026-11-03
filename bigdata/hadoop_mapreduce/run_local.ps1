# Reproduces the Hadoop Streaming data flow locally:  input -> mapper -> sort (shuffle) -> reducer -> output
# Author: Abin Shaji Thomas
# Usage (from the repository root):  powershell -ExecutionPolicy Bypass -File bigdata\hadoop_mapreduce\run_local.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here "..\..")
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$sortExe = Join-Path $env:SystemRoot "System32\sort.exe"
$inFile = Join-Path $here "input\accidents.tsv"
$outDir = Join-Path $here "output"
New-Item -ItemType Directory -Force $outDir | Out-Null

if (-not (Test-Path $inFile)) { & $py (Join-Path $here "export_input.py") }

foreach ($job in @("state", "weather", "hour")) {
    $out = Join-Path $outDir "$job.tsv"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    # Same pipeline Hadoop Streaming runs: map -> sort by key -> reduce
    cmd /c "type `"$inFile`" | `"$py`" `"$here\mapper.py`" $job | `"$sortExe`" | `"$py`" `"$here\reducer.py`" $job > `"$out`""
    if ($LASTEXITCODE -ne 0) { throw "MapReduce job '$job' failed" }
    $sw.Stop()
    $n = (Get-Content $out | Measure-Object -Line).Lines
    Write-Output ("job={0,-8} output={1} keys={2} seconds={3:N1}" -f $job, "output\$job.tsv", $n, $sw.Elapsed.TotalSeconds)
}
