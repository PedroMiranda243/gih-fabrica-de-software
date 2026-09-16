# Converte o .docx da entrega em .pdf usando o Word instalado.
#
# A entrega exige PDF. O Word e usado porque e ele que renderiza os diagramas
# SVG embutidos como vetor — um conversor que nao entenda SVG cairia no PNG de
# reserva e perderia a nitidez que a entrega cobra.
#
# Uso:  powershell -File docs/entrega/converter_pdf.ps1

$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$docx = Join-Path $raiz 'docs\entregas\GRUPO-18-GIH-SPRINT-02.docx'
$pdf  = Join-Path $raiz 'docs\entregas\GRUPO-18-GIH-SPRINT-02.pdf'

if (-not (Test-Path $docx)) {
    Write-Error "Nao encontrei $docx. Rode 'node docs/entrega/gerar.js' antes."
}

$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    # Sem [ref]: o PowerShell moderno passa os argumentos COM direto, e o
    # empacotamento antigo falha convertendo o caminho.
    $doc = $word.Documents.Open($docx, $false, $true)   # sem confirmar conversao, somente leitura

    # 17 = wdExportFormatPDF
    $doc.ExportAsFixedFormat($pdf, 17)

    $tamanho = [math]::Round((Get-Item $pdf).Length / 1MB, 2)
    Write-Output "gerado: docs\entregas\GRUPO-18-GIH-SPRINT-02.pdf"
    Write-Output "        $tamanho MB - $($doc.ComputeStatistics(2)) paginas"
}
finally {
    if ($doc)  { $doc.Close([ref]$false) }
    if ($word) { $word.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
