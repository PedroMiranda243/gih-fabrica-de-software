# Converte o .docx da entrega em .pdf usando o Word instalado.
#
# O Word e usado porque e ele que renderiza os diagramas SVG embutidos como
# vetor. Um conversor que nao entenda SVG cairia no PNG de reserva e perderia a
# nitidez que a entrega cobra.
#
# O trabalho acontece numa pasta temporaria, e nao no repositorio. Nao e
# capricho: o caminho deste projeto tem acento, e o Word ja deu problema com ele
# antes. Copiar para uma area sem acento custa nada e tira a duvida.
#
# SE TRAVAR: e conhecido que o Word as vezes fica preso na exportacao sem erro e
# sem dialogo, consumindo memoria e nunca terminando. Quando acontecer:
#
#   1. Feche o Word (inclusive instancias invisiveis: Gerenciador de Tarefas).
#   2. Rode este script de novo, num PowerShell comum.
#   3. Se persistir, abra o .docx no Word e use Arquivo > Exportar > Criar PDF.
#      O resultado e o mesmo; o script so poupa os cliques.
#
# Uso:  powershell -ExecutionPolicy Bypass -File docs/entrega/converter_pdf.ps1

$nome = 'GRUPO-18-GIH-SPRINT-02'
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$origem = Join-Path $raiz "docs\entregas\$nome.docx"
$destino = Join-Path $raiz "docs\entregas\$nome.pdf"

if (-not (Test-Path $origem)) {
    Write-Output "Nao encontrei $origem"
    Write-Output "Rode 'node docs/entrega/gerar.js' antes."
    exit 1
}

if (Get-Process WINWORD -ErrorAction SilentlyContinue) {
    Write-Output "O Word ja esta em execucao. Feche-o antes: a automacao se anexa"
    Write-Output "a instancia existente, e se ela estiver ocupada a conversao nao termina."
    exit 1
}

$docxTemp = Join-Path $env:TEMP "$nome.docx"
$pdfTemp = Join-Path $env:TEMP "$nome.pdf"
Copy-Item $origem $docxTemp -Force
if (Test-Path $pdfTemp) { Remove-Item $pdfTemp }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

$doc = $word.Documents.Open($docxTemp, $false, $true)   # sem confirmar conversao, somente leitura
$paginas = $doc.ComputeStatistics(2)

# Sem [ref]: o PowerShell moderno passa os argumentos COM direto, e o
# empacotamento antigo falha convertendo o caminho. 17 = wdExportFormatPDF.
$tempo = Measure-Command { $doc.ExportAsFixedFormat($pdfTemp, 17) }

$doc.Close($false)
$word.Quit()

if (Test-Path $pdfTemp) {
    Copy-Item $pdfTemp $destino -Force
    Remove-Item $docxTemp, $pdfTemp -ErrorAction SilentlyContinue
    $tamanho = [math]::Round((Get-Item $destino).Length / 1MB, 2)
    Write-Output "gerado: docs\entregas\$nome.pdf"
    Write-Output "        $tamanho MB - $paginas paginas - $([math]::Round($tempo.TotalSeconds,1))s"
} else {
    Write-Output "O Word nao produziu o PDF. Veja a secao SE TRAVAR no topo deste arquivo."
    exit 1
}
