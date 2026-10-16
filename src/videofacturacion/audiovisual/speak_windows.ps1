param(
    [Parameter(Mandatory=$true)][string]$Manifest,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$Voice = 'Microsoft Helena Desktop'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $installed = @($synth.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Name -eq $Voice -and $_.VoiceInfo.Culture.Name.StartsWith('es-')
    })
    if ($installed.Count -ne 1) { throw 'La voz espanola solicitada no esta disponible.' }
    $synth.SelectVoice($Voice)
    $synth.Rate = 0
    $synth.Volume = 100
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(
        22050,
        [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono
    )
    $payload = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($segment in $payload.segments) {
        # Nombre interno controlado; el texto se pronuncia literalmente, nunca se evalua.
        if ($segment.audio_file -notmatch '^audio-[0-9]{3}\.wav$') { throw 'Nombre de audio invalido.' }
        $target = Join-Path $OutputDirectory $segment.audio_file
        $synth.SetOutputToWaveFile($target, $format)
        $synth.Speak([string]$segment.text)
        $synth.SetOutputToNull()
    }
    [pscustomobject]@{voice=$installed[0].VoiceInfo.Name; locale=$installed[0].VoiceInfo.Culture.Name} |
        ConvertTo-Json -Compress
} finally {
    $synth.Dispose()
}
